"""A modal question that blocks the turn worker until answered."""

import threading

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from harness.tools.permission import Answer

QUESTION = "allow {call}?"
BUTTONS = (
    (Answer.YES, "yes", "y"),
    (Answer.ALWAYS, "always", "a"),
    (Answer.NO, "no", "n"),
)


class PermissionScreen(ModalScreen[Answer]):
    BINDINGS = [(key, f"answer_{answer.value}", label) for answer, label, key in BUTTONS]

    def __init__(self, call: str) -> None:
        super().__init__()
        self.call = call

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(QUESTION.format(call=self.call))
            for answer, label, _key in BUTTONS:
                yield Button(label, id=answer.value)

    def on_mount(self) -> None:
        self.query_one(f"#{Answer.YES.value}", Button).focus()

    @on(Button.Pressed)
    def choose_button(self, event: Button.Pressed) -> None:
        self.dismiss(Answer(event.button.id))

    def action_answer_yes(self) -> None:
        self.dismiss(Answer.YES)

    def action_answer_always(self) -> None:
        self.dismiss(Answer.ALWAYS)

    def action_answer_no(self) -> None:
        self.dismiss(Answer.NO)


def ask(app, call: str) -> Answer:
    """Block the turn worker until the person answers. Call only from the worker thread."""
    box: dict = {}
    done = threading.Event()

    def on_done(answer: Answer) -> None:
        box["answer"] = answer
        done.set()

    app.call_from_thread(app.push_screen, PermissionScreen(call), on_done)
    done.wait()
    return box["answer"]
