"""Drives one task with nobody watching."""

from __future__ import annotations

import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from harness.chat.session import Session
from harness.chat.usage import Usage, dollars, usage_of
from harness.config import Settings
from harness.evals.tasks import Task
from harness.model.text import text_of
from harness.tools.permission import Answer

AUTOMATIC_ANSWER = Answer.ALWAYS
ERROR_ANSWER = "{name}: {message}"


@dataclass(frozen=True)
class Result:
    task: str
    answer: str
    passed: bool
    usage: Usage
    cost: float
    seconds: float


def write_files(folder: Path, task: Task) -> None:
    """Write the files a task needs into its folder."""
    for name, text in task.files.items():
        (folder / name).write_text(text)


def last_answer(session: Session) -> str:
    """Newest non-blank model reply, or empty when there is none."""
    for message in reversed(session.saved_messages()):
        if isinstance(message, AIMessage) and text_of(message).strip():
            return text_of(message)
    return ""


def run_once(settings: Settings, task: Task, cwd: Path, model=None) -> Result:
    """Run one task once, saying yes to every permission question.

    A throw-away folder keeps that automatic yes away from the repository.
    A failed call is recorded as a failed run.
    """
    session = Session.start(settings, InMemorySaver(), cwd, model)
    before_ids = {message.id for message in session.saved_messages()}
    start = time.perf_counter()
    try:
        request: dict | Command = {"messages": [HumanMessage(content=task.prompt)]}
        while True:
            events = session.graph.stream(request, session.config, stream_mode="messages")
            for _message, _meta in events:
                pass
            pending = session.pending_request()
            if pending is None:
                break
            request = Command(resume=AUTOMATIC_ANSWER)
        answer = last_answer(session)
        passed = answer.strip() == task.expect
    except Exception as exc:
        answer = ERROR_ANSWER.format(name=type(exc).__name__, message=exc)
        passed = False
    fresh = [message for message in session.saved_messages() if message.id not in before_ids]
    usage = usage_of(fresh)
    return Result(
        task=task.name,
        answer=answer,
        passed=passed,
        usage=usage,
        cost=dollars(usage, settings),
        seconds=time.perf_counter() - start,
    )


def run_task(settings: Settings, task: Task, model=None) -> list[Result]:
    """Run one task as many times as the settings ask for."""
    results: list[Result] = []
    for _ in range(settings.eval_repeats):
        with tempfile.TemporaryDirectory() as folder:
            write_files(Path(folder), task)
            results.append(run_once(settings, task, Path(folder), model))
    return results


def run_suite(settings: Settings, tasks: tuple[Task, ...] | list[Task], model=None) -> list[Result]:
    """Run every task in order and return one flat list of results."""
    results: list[Result] = []
    for task in tasks:
        results.extend(run_task(settings, task, model))
    return results
