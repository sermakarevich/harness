from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES, RemoveMessage

from harness.chat.compact import build_compact, context_tokens, over_budget, split_at_turn
from harness.chat.usage import dollars, usage_of
from tests.conftest import FakeToolChatModel


def usage_reply(content, input_tokens):
    return AIMessage(
        content=content,
        usage_metadata={
            "input_tokens": input_tokens,
            "output_tokens": 10,
            "total_tokens": input_tokens + 10,
        },
    )


def test_context_tokens_reads_newest_reply():
    messages = [HumanMessage(content="a"), usage_reply("one", 100), usage_reply("two", 500)]
    assert context_tokens(messages) == 500


def test_context_tokens_empty_without_usage():
    assert context_tokens([HumanMessage(content="a"), AIMessage(content="no usage")]) == 0
    assert context_tokens([]) == 0


def test_over_budget_compares_newest_reply():
    messages = [HumanMessage(content="a"), usage_reply("one", 5000)]
    assert over_budget(messages, 4000) is True
    assert over_budget(messages, 6000) is False


def test_split_at_turn_keeps_recent_turns():
    messages = [
        HumanMessage(content="a"),
        AIMessage(content="one"),
        HumanMessage(content="b"),
        AIMessage(content="two"),
        HumanMessage(content="c"),
        AIMessage(content="three"),
    ]
    head, tail = split_at_turn(messages, 2)
    assert head == messages[:2]
    assert tail == messages[2:]
    assert isinstance(tail[0], HumanMessage)
    assert head + tail == messages


def test_split_at_turn_short_conversation_has_no_head():
    messages = [HumanMessage(content="a"), AIMessage(content="one")]
    head, tail = split_at_turn(messages, 2)
    assert head == []
    assert tail == messages


def test_split_never_separates_call_from_result():
    call = AIMessage(
        content="",
        tool_calls=[
            {"name": "shell", "args": {"command": "seq 1 3"}, "id": "call-1", "type": "tool_call"}
        ],
    )
    messages = [
        HumanMessage(content="run it"),
        call,
        ToolMessage(content="1 2 3", name="shell", tool_call_id="call-1"),
        HumanMessage(content="thanks"),
        AIMessage(content="done"),
    ]
    head, tail = split_at_turn(messages, 1)
    kept_calls = {message.tool_call_id for message in tail if isinstance(message, ToolMessage)}
    made_calls = {
        call["id"]
        for message in tail
        if isinstance(message, AIMessage)
        for call in (message.tool_calls or [])
    }
    assert kept_calls <= made_calls


def test_compact_node_replaces_head_with_summary(settings):
    head = [HumanMessage(content="a"), usage_reply("one", 3000)]
    tail = [
        HumanMessage(content="b"),
        AIMessage(content="two"),
        HumanMessage(content="c"),
        AIMessage(content="three"),
    ]
    summary = usage_reply("summary", 50)
    node = build_compact(FakeToolChatModel(messages=iter([summary])), "prompt", settings)
    result = node({"messages": head + tail})
    updated = result["messages"]
    assert isinstance(updated[0], RemoveMessage)
    assert updated[0].id == REMOVE_ALL_MESSAGES
    assert updated[1] is summary
    assert updated[2:] == tail
    assert result["carried_cost"] == dollars(usage_of(head), settings)


def test_compact_node_skips_short_conversation(settings):
    messages = [HumanMessage(content="a"), AIMessage(content="one")]
    node = build_compact(FakeToolChatModel(messages=iter([AIMessage(content="x")])), "p", settings)
    assert node({"messages": messages}) == {}
