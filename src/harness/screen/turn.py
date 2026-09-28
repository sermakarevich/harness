"""One full-screen turn: stream the reply, ask before tools run."""

from __future__ import annotations

from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from langgraph.types import Command

from harness.chat.graph import COMPACT_NODE
from harness.chat.lines import COMPACT_NOTICE, ERROR_LINE, call_text, cost_line, tool_line
from harness.chat.usage import dollars, usage_of
from harness.model.text import text_of
from harness.screen import permission
from harness.tools.permission import Answer
from harness.tools.todos import TOOL_NAME as WRITE_TODOS


class StreamState:
    def __init__(self, compact_notice: str = "") -> None:
        self.chunks: AIMessageChunk | None = None
        self.reply = ""
        self.tools_shown = False
        self.denied: set[str] = set()
        self.compact_notice = compact_notice
        self.compact_shown = False


def flush_reply(app, state: StreamState) -> None:
    if state.reply:
        app.call_from_thread(app.write, state.reply)
        state.reply = ""


def show_tool_call(app, message: ToolMessage, state: StreamState) -> None:
    state.tools_shown = True
    flush_reply(app, state)
    if message.tool_call_id in state.denied:
        return
    if message.name == WRITE_TODOS:
        app.call_from_thread(app.write, message.content)
        return
    calls = state.chunks.tool_calls if state.chunks is not None else []
    call = next((c for c in calls or [] if c.get("id") == message.tool_call_id), None)
    if call is None:
        return
    app.call_from_thread(app.write, tool_line(call.get("name"), call.get("args", {})))


def render_event(app, message, meta: dict, state: StreamState) -> None:
    """Show one piece of the reply as it arrives."""
    if isinstance(message, AIMessageChunk):
        if (meta or {}).get("langgraph_node") == COMPACT_NODE:
            if not state.compact_shown and state.compact_notice:
                app.call_from_thread(app.write, state.compact_notice)
                state.compact_shown = True
            return
        if state.tools_shown:
            state.chunks = None
            state.tools_shown = False
        text = text_of(message)
        if text:
            state.reply += text
        state.chunks = message if state.chunks is None else state.chunks + message
    elif isinstance(message, ToolMessage):
        show_tool_call(app, message, state)


def stream_turn(app, text: str) -> None:
    """Send one user message and show the reply as it arrives."""
    state = StreamState(COMPACT_NOTICE.format(budget=app.settings.compact_at_tokens))
    before_ids = {message.id for message in app.session.saved_messages()}
    request: dict | Command = {"messages": [HumanMessage(content=text)]}
    try:
        while True:
            events = app.session.graph.stream(request, app.session.config, stream_mode="messages")
            for message, meta in events:
                render_event(app, message, meta, state)
            flush_reply(app, state)
            pending = app.session.pending_request()
            if pending is None:
                break
            answer = permission.ask(app, call_text(pending["name"], pending["args"]))
            if answer == Answer.NO:
                state.denied.add(pending["id"])
            request = Command(resume=answer)
        flush_reply(app, state)
        messages = app.session.saved_messages()
        turn = usage_of([message for message in messages if message.id not in before_ids])
        total = usage_of(messages)
        total_cost = dollars(total, app.settings) + app.session.carried_cost()
        app.call_from_thread(
            app.set_status, cost_line(turn, total, dollars(turn, app.settings), total_cost)
        )
    except Exception as exc:
        app.call_from_thread(app.write, ERROR_LINE.format(name=type(exc).__name__, message=exc))
