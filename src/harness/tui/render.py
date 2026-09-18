"""Shows each model reply as it arrives.

Network errors show a message and the chat keeps going.
"""

from __future__ import annotations

from langchain_core.messages import AIMessageChunk, HumanMessage

from harness.model.text import text_of


def render_event(console, message, meta: dict) -> None:
    """Show one piece of the reply as it arrives."""
    if isinstance(message, AIMessageChunk):
        console.print(text_of(message), end="", markup=False, highlight=False, soft_wrap=True)


def run_turn(app, text: str) -> None:
    """Send one user message and show the reply as it arrives.

    Network errors show a message and the chat keeps going.
    """
    events = app.session.graph.stream(
        {"messages": [HumanMessage(content=text)]},
        app.session.config,
        stream_mode="messages",
    )
    try:
        for message, meta in events:
            render_event(app.console, message, meta)
    except Exception as exc:
        app.console.print(f"\n[red]error:[/red] {type(exc).__name__}: {exc}")
    finally:
        app.console.print()
