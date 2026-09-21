"""Offline tests for the unattended task suite."""

import dataclasses
import tempfile
from pathlib import Path

from langchain_core.messages import AIMessage

from harness.chat.usage import Usage
from harness.evals.report import all_passed, rows, table
from harness.evals.run import Result, run_once, run_suite, run_task, write_files
from harness.evals.tasks import Task, load_tasks
from tests.conftest import FakeToolChatModel

ARITHMETIC_PROMPT = "What is 17 times 3? Answer with the number only."


def arithmetic_task() -> Task:
    return Task(name="arithmetic", prompt=ARITHMETIC_PROMPT, expect="51")


def scripted_model(*replies: str) -> FakeToolChatModel:
    return FakeToolChatModel(messages=iter([AIMessage(content=reply) for reply in replies]))


def made_result(task: str, passed: bool) -> Result:
    return Result(
        task=task,
        answer="yes" if passed else "no",
        passed=passed,
        usage=Usage(input_tokens=10, output_tokens=5),
        cost=0.0001,
        seconds=2.0,
    )


def test_load_tasks_returns_four_tasks():
    tasks = load_tasks()
    assert len(tasks) == 4
    assert tasks[0].name == "word"
    assert all(task.prompt and task.expect for task in tasks)
    assert sum(1 for task in tasks if task.files) == 2


def test_write_files_writes_task_files(tmp_path):
    task = Task(name="read_file", prompt="p", expect="blue", files={"colour.txt": "blue"})
    write_files(tmp_path, task)
    assert (tmp_path / "colour.txt").read_text() == "blue"


def test_run_once_passes_on_exact_answer(settings, tmp_path):
    result = run_once(settings, arithmetic_task(), tmp_path, model=scripted_model("51"))
    assert result.passed is True
    assert result.answer == "51"
    assert result.seconds > 0


def test_run_once_fails_on_wrong_answer(settings, tmp_path):
    result = run_once(settings, arithmetic_task(), tmp_path, model=scripted_model("fifty one"))
    assert result.passed is False


def test_run_once_strips_surrounding_whitespace(settings, tmp_path):
    result = run_once(settings, arithmetic_task(), tmp_path, model=scripted_model(" 51\n"))
    assert result.passed is True


def test_run_task_repeats_and_removes_folders(settings, monkeypatch):
    two_runs = dataclasses.replace(settings, eval_repeats=2)
    seen: list[str] = []
    real_temporary_directory = tempfile.TemporaryDirectory

    def recording(*args, **kwargs):
        folder = real_temporary_directory(*args, **kwargs)
        seen.append(folder.name)
        return folder

    monkeypatch.setattr(tempfile, "TemporaryDirectory", recording)
    results = run_task(
        two_runs,
        Task(name="word", prompt="Reply with exactly the word: ready", expect="ready"),
        model=scripted_model("ready", "ready"),
    )
    assert len(results) == 2
    assert seen and all(not Path(folder).exists() for folder in seen)


def test_rows_groups_passes_over_runs():
    grid = rows([made_result("word", True), made_result("word", False), made_result("word", True)])
    assert len(grid) == 1
    assert grid[0][1] == "2/3"


def test_table_has_heading_line_plus_one_line_per_task():
    results = [made_result("word", True), made_result("arithmetic", True)]
    lines = table(results).splitlines()
    assert len(lines) == 3
    assert lines[0].split()[0] == "task"


def test_all_passed_is_false_when_one_failed():
    assert all_passed([made_result("word", True), made_result("word", False)]) is False


class FailingChatModel(FakeToolChatModel):
    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError("overloaded")


def test_run_once_records_failed_call_as_failed_run(settings, tmp_path):
    model = FailingChatModel(messages=iter([]))
    result = run_once(settings, arithmetic_task(), tmp_path, model=model)
    assert result.passed is False
    assert "RuntimeError" in result.answer


def test_run_suite_runs_every_task_when_model_raises(settings):
    model = FailingChatModel(messages=iter([]))
    word = Task(name="word", prompt="Reply with exactly the word: ready", expect="ready")
    results = run_suite(settings, [arithmetic_task(), word], model=model)
    assert len(results) == 2 * settings.eval_repeats
    assert all(result.passed is False for result in results)
