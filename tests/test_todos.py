"""The model keeps one short task list outside the conversation."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import PrivateAttr

from harness.chat.graph import build_graph
from harness.chat.prompt import build_todos_prompt
from harness.chat.thread import thread_config
from harness.tools.todos import (
    EMPTY_TODOS,
    TOOL_NAME,
    Status,
    clean_todos,
    todo_lines,
    todos_of,
)
from tests.conftest import FakeToolChatModel


def named_call(name, args, call_id):
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def test_clean_reads_three_statuses_in_order():
    todos = clean_todos("TODO: write the file\nDoing: read it back\ndone: plan the work")
    assert [todo["status"] for todo in todos] == ["todo", "doing", "done"]
    assert [todo["text"] for todo in todos] == ["write the file", "read it back", "plan the work"]


def test_second_doing_becomes_todo():
    todos = clean_todos("doing: first\ndoing: second")
    assert [todo["status"] for todo in todos] == [Status.DOING, Status.TODO]
    assert todos[0]["text"] == "first"


def test_line_without_status_becomes_todo():
    assert clean_todos("just do it") == [{"text": "just do it", "status": "todo"}]
    assert clean_todos("later: just do it") == [{"text": "later: just do it", "status": "todo"}]


def test_blank_lines_disappear():
    assert clean_todos("write it\n\n   \nread it") == [
        {"text": "write it", "status": "todo"},
        {"text": "read it", "status": "todo"},
    ]
    assert clean_todos("doing:") == []


def test_todo_lines_shows_one_marked_line_per_item():
    todos = [
        {"text": "write it", "status": "todo"},
        {"text": "read it", "status": "doing"},
        {"text": "plan it", "status": "done"},
    ]
    assert todo_lines(todos) == "☐ write it\n◐ read it\n☑ plan it"
    assert todo_lines([]) == ""


def test_todos_of_returns_none_without_tool_call():
    calls = [named_call("read_file", {"path": "note.txt"}, "call-1")]
    assert todos_of(calls) is None


def test_todos_of_keeps_last_call():
    calls = [
        named_call(TOOL_NAME, {"items": "todo: first"}, "call-1"),
        named_call("read_file", {"path": "note.txt"}, "call-2"),
        named_call(TOOL_NAME, {"items": "done: second"}, "call-3"),
    ]
    assert todos_of(calls) == [{"text": "second", "status": "done"}]


def write_call(items, call_id="call-1"):
    return AIMessage(
        content="",
        tool_calls=[named_call(TOOL_NAME, {"items": items}, call_id)],
    )


def test_write_reaches_state_and_tool_message(settings, tmp_path):
    model = FakeToolChatModel(
        messages=iter([write_call("todo: write it\ndoing: read it"), AIMessage(content="done")])
    )
    graph = build_graph(model, settings, cwd=tmp_path)
    cfg = thread_config("todos-state")
    graph.invoke({"messages": [HumanMessage(content="plan it")]}, cfg)
    state = graph.get_state(cfg).values
    assert state["todos"] == [
        {"text": "write it", "status": "todo"},
        {"text": "read it", "status": "doing"},
    ]
    tool_message = next(m for m in state["messages"] if isinstance(m, ToolMessage))
    assert tool_message.content == todo_lines(state["todos"])


def test_second_write_replaces_whole_list(settings, tmp_path):
    model = FakeToolChatModel(
        messages=iter(
            [
                write_call("todo: write it\ntodo: read it", "call-1"),
                write_call("done: write it", "call-2"),
                AIMessage(content="done"),
            ]
        )
    )
    graph = build_graph(model, settings, cwd=tmp_path)
    cfg = thread_config("todos-replace")
    graph.invoke({"messages": [HumanMessage(content="plan it")]}, cfg)
    assert graph.get_state(cfg).values["todos"] == [{"text": "write it", "status": "done"}]


class RecordingModel(FakeToolChatModel):
    _seen: list = PrivateAttr(default_factory=list)

    @property
    def seen(self):
        return self._seen

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self._seen.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def test_stored_list_reaches_model_in_system_message(settings, tmp_path):
    model = RecordingModel(
        messages=iter([write_call("doing: write it\ntodo: read it"), AIMessage(content="done")])
    )
    graph = build_graph(model, settings, cwd=tmp_path)
    cfg = thread_config("todos-prompt")
    graph.invoke({"messages": [HumanMessage(content="plan it")]}, cfg)
    assert len(model.seen) == 2
    first_system = model.seen[0][0]
    assert isinstance(first_system, SystemMessage)
    assert EMPTY_TODOS in first_system.content
    second_system = model.seen[1][0]
    assert isinstance(second_system, SystemMessage)
    assert todo_lines(clean_todos("doing: write it\ntodo: read it")) in second_system.content


def usage_answer(content, input_tokens):
    return AIMessage(
        content=content,
        usage_metadata={
            "input_tokens": input_tokens,
            "output_tokens": 10,
            "total_tokens": input_tokens + 10,
        },
    )


def test_todos_survive_compaction(settings):
    model = FakeToolChatModel(
        messages=iter(
            [
                usage_answer("one", 100),
                usage_answer("two", settings.compact_at_tokens + 1000),
                usage_answer("summary", 50),
                usage_answer("three", 60),
            ]
        )
    )
    graph = build_graph(model, settings)
    cfg = thread_config("todos-compact")
    todos = clean_todos("doing: write it\ntodo: read it")
    graph.invoke({"messages": [HumanMessage(content="first")], "todos": todos}, cfg)
    graph.invoke({"messages": [HumanMessage(content="second")]}, cfg)
    graph.invoke({"messages": [HumanMessage(content="third")]}, cfg)
    assert graph.get_state(cfg).values["todos"] == todos


def test_todos_prompt_holds_current_list():
    prompt = build_todos_prompt(clean_todos("done: write it"))
    assert "☑ write it" in prompt
    assert "{todos}" not in prompt
    assert EMPTY_TODOS in build_todos_prompt([])
