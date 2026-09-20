"""A helper does one job in its own conversation and sends back one answer."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from harness.chat.graph import build_graph
from harness.chat.helper import build_helper_runner, helper_tools
from harness.chat.thread import thread_config
from harness.tools.ask_helper import TOOL_NAME, ask_helper_tool
from harness.tools.permission import needs_approval
from harness.tools.registry import build_tools
from tests.conftest import FakeToolChatModel


def tool_call(name, args, call_id="call-1"):
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def test_helper_keeps_only_tools_that_need_no_question(settings, tmp_path):
    tools = build_tools(tmp_path, settings.shell_timeout_seconds, settings.skills_dir)
    kept = helper_tools(tools)
    assert [tool.name for tool in kept] == ["read_file", "read_skill", "write_todos"]
    assert all(not needs_approval(tool.name) for tool in kept)


def test_helper_cannot_pass_the_job_on(settings, tmp_path):
    tools = build_tools(tmp_path, settings.shell_timeout_seconds, settings.skills_dir)
    kept = helper_tools([*tools, ask_helper_tool(lambda job: "x")])
    assert TOOL_NAME not in [tool.name for tool in kept]


def test_parent_is_asked_before_a_helper_starts():
    assert needs_approval(TOOL_NAME) is True


class SingleAnswer:
    def invoke(self, payload):
        return {"messages": [HumanMessage(content="framed job"), AIMessage(content="the answer")]}


def test_runner_returns_the_helper_last_message():
    assert build_helper_runner(SingleAnswer())("some job") == "the answer"


class RecordingRunner(SingleAnswer):
    def __init__(self):
        self.calls = []

    def invoke(self, *args):
        self.calls.append(args)
        return super().invoke(*args)


def test_runner_frames_the_job_and_passes_no_config():
    stub = RecordingRunner()
    build_helper_runner(stub)("read the notes")
    assert len(stub.calls) == 1
    assert len(stub.calls[0]) == 1
    first = stub.calls[0][0]["messages"][0].content
    assert "read the notes" in first
    assert len(first) > len("read the notes")


def test_helper_conversation_stays_out_of_the_parent(settings, tmp_path):
    job = "summarise the hidden ledger file"
    answer = "the helper read everything and reports back"
    model = FakeToolChatModel(
        messages=iter(
            [
                AIMessage(content="", tool_calls=[tool_call(TOOL_NAME, {"job": job})]),
                AIMessage(content=answer),
                AIMessage(content="all done"),
            ]
        )
    )
    graph = build_graph(model, settings, cwd=tmp_path)
    cfg = thread_config("helper-hidden")
    payload = {"messages": [HumanMessage(content="go")], "always_allowed": [TOOL_NAME]}
    graph.invoke(payload, cfg)
    msgs = graph.get_state(cfg).values["messages"]
    assert len(msgs) == 4
    assert isinstance(msgs[2], ToolMessage) and msgs[2].content == answer
    assert all(job not in str(message.content) for message in msgs)


def test_helper_keeps_nothing_between_jobs(settings, tmp_path):
    model = FakeToolChatModel(
        messages=iter([AIMessage(content="first answer"), AIMessage(content="second answer")])
    )
    helper = build_graph(model, settings, cwd=tmp_path, helper=True)
    first_job = "count the green bottles"
    helper.invoke({"messages": [HumanMessage(content=first_job)]})
    second = helper.invoke({"messages": [HumanMessage(content="count the red bottles")]})
    assert all(first_job not in str(message.content) for message in second["messages"])
