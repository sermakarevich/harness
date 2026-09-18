"""Shows each model reply and tool call as it arrives.

Network errors show a message and the chat keeps going.
"""

from __future__ import annotations

import re

from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage

from harness.model.text import text_of

TOOL_ARROW = "→"
TOOL_ARG_WIDTH = 60


def shorten(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value))
    return text if len(text) <= TOOL_ARG_WIDTH else text[:TOOL_ARG_WIDTH] + "…"


class StreamState:
    def __init__(self) -> None:
        self.chunks: AIMessageChunk | None = None
        self.printed_text = False
        self.tools_shown = False


def show_tool_call(console, message: ToolMessage, state: StreamState) -> None:
    calls = state.chunks.tool_calls if state.chunks is not None else []
    call = next((c for c in calls or [] if c.get("id") == message.tool_call_id), None)
    if call is None:
        return
    if state.printed_text:
        console.print()
        state.printed_text = False
    args = " ".join(f"{key}={shorten(value)}" for key, value in call.get("args", {}).items())
    console.print(
        f"{TOOL_ARROW} {call.get('name')} {args}".rstrip(),
        style="dim",
        markup=False,
        highlight=False,
        soft_wrap=True,
    )
    state.tools_shown = True


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
    events = app.session.graph.stream(
        {"messages": [HumanMessage(content=text)]},
        app.session.config,
        stream_mode="messages",
    )
    try:
        for message, meta in events:
            render_event(app.console, message, meta, state)
    except Exception as exc:
        app.console.print(f"\n[red]error:[/red] {type(exc).__name__}: {exc}")
    finally:
        app.console.print()
