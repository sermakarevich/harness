"""Full-screen terminal front end."""

from pathlib import Path

from textual import work
from textual.app import App as TextualApp
from textual.app import ComposeResult
from textual.widgets import Input, RichLog, Static

from harness.chat.lines import MEMORY_LINE, SKILLS_LINE
from harness.chat.memory import memory_paths, short_path
from harness.chat.session import Session
from harness.chat.sessions import short_id
from harness.chat.store import open_store
from harness.config import Settings
from harness.screen import keys
from harness.screen.turn import stream_turn
from harness.tools.skills import skill_names

LOG_ID = "log"
INPUT_ID = "box"
STATUS_ID = "status"
PROMPT_PLACEHOLDER = "Type a message, /exit to quit"
ECHO_PREFIX = "> "
QUIT_TAIL = "to quit"


class ScreenApp(TextualApp):
    def __init__(self, settings: Settings, cwd=None, model=None, checkpointer=None):
        super().__init__()
        self.settings = settings
        self.cwd = cwd or Path.cwd()
        self._model = model
        self.checkpointer = checkpointer or open_store(self.settings.sessions_db)
        self.session = self._new_session()

    def _new_session(self) -> Session:
        return Session.start(self.settings, self.checkpointer, self.cwd, model=self._model)

    def compose(self) -> ComposeResult:
        yield RichLog(id=LOG_ID, highlight=False, markup=False, wrap=True)
        yield Input(placeholder=PROMPT_PLACEHOLDER, id=INPUT_ID)
        yield Static(id=STATUS_ID)

    def on_mount(self) -> None:
        for line in self.banner_lines():
            self.query_one(f"#{LOG_ID}", RichLog).write(line)
        self.query_one(f"#{INPUT_ID}", Input).focus()

    def banner_lines(self) -> list[str]:
        head = (
            f"harness · model {self.settings.model} · session "
            f"{short_id(self.session.session_id)} · {keys.EXIT} {QUIT_TAIL}"
        )
        lines = [head]
        paths = memory_paths(self.cwd, self.settings.memory_file_names)
        if paths:
            names = ", ".join(short_path(path, self.cwd) for path in paths)
            lines.append(MEMORY_LINE.format(names=names))
        skills = skill_names(self.cwd, self.settings.skills_dir)
        if skills:
            lines.append(SKILLS_LINE.format(names=", ".join(skills)))
        return lines

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        if text == keys.EXIT:
            self.exit()
            return
        self.query_one(f"#{INPUT_ID}", Input).clear()
        self.write(f"{ECHO_PREFIX}{event.value}")
        self.run_turn(event.value)

    @work(thread=True)
    def run_turn(self, text: str) -> None:
        stream_turn(self, text)

    def set_status(self, text: str) -> None:
        self.query_one(f"#{STATUS_ID}", Static).update(text)

    def write(self, text: str) -> None:
        self.query_one(f"#{LOG_ID}", RichLog).write(text)
