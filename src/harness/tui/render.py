"""Shows each model reply and tool call as it arrives.

Network errors show a message and the chat keeps going.
"""

from __future__ import annotations

import re

from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from langgraph.types import Command

from harness.model.text import text_of
from harness.tools.permission import Answer
from harness.tui.ask import ask_permission

TOOL_ARROW = "→"
TOOL_ARG_WIDTH = 60


def shorten(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value))
    return text if len(text) <= TOOL_ARG_WIDTH else text[:TOOL_ARG_WIDTH] + "…"


def call_text(name: str, args: dict) -> str:
    """Text of one tool call for the terminal."""
    params = " ".join(f"{key}={shorten(value)}" for key, value in args.items())
    return f"{name} {params}".rstrip()


class StreamState:
    def __init__(self) -> None:
        self.chunks: AIMessageChunk | None = None
        self.printed_text = False
        self.tools_shown = False
        self.denied: set[str] = set()


def end_line(console, state: StreamState) -> None:
    if state.printed_text:
        console.print()
        state.printed_text = False


def show_tool_call(console, message: ToolMessage, state: StreamState) -> None:
    state.tools_shown = True
    if message.tool_call_id in state.denied:
        return
    calls = state.chunks.tool_calls if state.chunks is not None else []
    call = next((c for c in calls or [] if c.get("id") == message.tool_call_id), None)
    if call is None:
        return
    end_line(console, state)
    console.print(
        f"{TOOL_ARROW} {call_text(call.get('name'), call.get('args', {}))}",
        style="dim",
        markup=False,
        highlight=False,
        soft_wrap=True,
    )


def render_event(console, message, meta: dict, state: StreamState) -> None:
    """Show one piece of the reply as it arrives."""
    if isinstance(message, AIMessageChunk):
        if state.tools_shown:
            state.chunks = None
            state.tools_shown = False
        text = text_of(message)
        if text:
            console.print(text, end="", markup=False, highlight=False, soft_wrap=True)
            state.printed_text = True
        state.chunks = message if state.chunks is None else state.chunks + message
    elif isinstance(message, ToolMessage):
        show_tool_call(console, message, state)


def run_turn(app, text: str) -> None:
    """Send one user message and show the reply as it arrives.

    Network errors show a message and the chat keeps going.
    """
    state = StreamState()
    request: dict | Command = {"messages": [HumanMessage(content=text)]}
    try:
        while True:
            events = app.session.graph.stream(
                request,
                app.session.config,
                stream_mode="messages",
            )
            for message, meta in events:
                render_event(app.console, message, meta, state)
            pending = app.session.pending_request()
            if pending is None:
                break
            end_line(app.console, state)
            answer = ask_permission(app, call_text(pending["name"], pending["args"]))
            if answer == Answer.NO:
                state.denied.add(pending["id"])
            request = Command(resume=answer)
    except Exception as exc:
        app.console.print(f"\n[red]error:[/red] {type(exc).__name__}: {exc}")
    finally:
        app.console.print()
