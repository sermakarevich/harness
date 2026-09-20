"""One short task list the model keeps up to date."""

from enum import StrEnum
from typing import TypedDict

from langchain_core.tools import tool

TOOL_NAME = "write_todos"

EMPTY_TODOS = "No todos yet."

SEPARATOR = ":"


class Status(StrEnum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"


class Todo(TypedDict):
    text: str
    status: str


STATUS_MARKS = {
    Status.TODO: "☐",
    Status.DOING: "◐",
    Status.DONE: "☑",
}


def clean_todos(items: str) -> list[Todo]:
    """Read the model's lines into a task list with at most one item in progress."""
    todos: list[Todo] = []
    for line in items.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        status = Status.TODO
        text = stripped
        if SEPARATOR in stripped:
            head, rest = stripped.split(SEPARATOR, 1)
            try:
                status = Status(head.strip().lower().replace(" ", ""))
            except ValueError:
                status = Status.TODO
            else:
                text = rest.strip()
        if not text:
            continue
        todos.append({"text": text, "status": status.value})
    seen_doing = False
    for todo in todos:
        if todo["status"] == Status.DOING:
            if seen_doing:
                todo["status"] = Status.TODO.value
            else:
                seen_doing = True
    return todos


def todo_lines(todos: list[Todo]) -> str:
    """Render the stored list for the terminal and the model."""
    return "\n".join(f"{STATUS_MARKS[Status(todo['status'])]} {todo['text']}" for todo in todos)


def todos_of(calls: list) -> list[Todo] | None:
    """Cleaned list from the last write_todos call in a turn, if there was one."""
    found = None
    for call in calls:
        if call["name"] == TOOL_NAME:
            found = clean_todos((call.get("args") or {}).get("items", ""))
    return found


def write_todos_tool():
    """Build the tool that replaces the whole task list."""

    @tool(TOOL_NAME)
    def write_todos(items: str) -> str:
        """Replace the whole task list, one item per line as status: text."""
        return todo_lines(clean_todos(items))

    return write_todos
