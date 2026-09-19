from langchain_core.messages import AIMessage, HumanMessage

from harness.chat.session import Session
from harness.chat.store import open_store
from harness.chat.usage import Usage, dollars, usage_of
from tests.conftest import FakeToolChatModel


def usage_reply(input_tokens, cached, output_tokens, reasoning):
    return AIMessage(
        content="ok",
        usage_metadata={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_token_details": {"cache_read": cached},
            "output_token_details": {"reasoning": reasoning},
        },
    )


def test_usage_of_empty():
    assert usage_of([]) == Usage()


def test_usage_of_adds_replies_and_skips_other_messages():
    messages = [
        HumanMessage(content="hi"),
        usage_reply(914, 113, 26, 15),
        usage_reply(100, 40, 10, 2),
        AIMessage(content="no usage"),
    ]
    assert usage_of(messages) == Usage(
        input_tokens=1014,
        cached_input_tokens=153,
        output_tokens=36,
        reasoning_tokens=17,
    )


def test_dollars_prices_each_part_at_its_rate(settings):
    assert dollars(Usage(input_tokens=1_000_000), settings) == 0.1
    assert dollars(Usage(input_tokens=1_000_000, cached_input_tokens=1_000_000), settings) == 0.002
    assert dollars(Usage(output_tokens=1_000_000), settings) == 0.2


def test_dollars_mixes_all_parts(settings):
    usage = Usage(input_tokens=914, cached_input_tokens=113, output_tokens=26, reasoning_tokens=15)
    assert dollars(usage, settings) == (801 * 0.1 + 113 * 0.002 + 26 * 0.2) / 1_000_000


def test_usage_survives_store_reopen(settings, tmp_path):
    path = tmp_path / "sessions.db"
    first = open_store(path)
    session = Session.start(
        settings,
        first,
        cwd=tmp_path,
        model=FakeToolChatModel(messages=iter([usage_reply(914, 113, 26, 15)])),
    )
    session.graph.invoke({"messages": [HumanMessage(content="hi")]}, session.config)
    before = usage_of(session.saved_messages())
    second = open_store(path)
    resumed = Session.resume(
        settings,
        session.session_id,
        second,
        cwd=tmp_path,
        model=FakeToolChatModel(messages=iter([AIMessage(content="again")])),
    )
    assert usage_of(resumed.saved_messages()) == before
    assert before == Usage(
        input_tokens=914,
        cached_input_tokens=113,
        output_tokens=26,
        reasoning_tokens=15,
    )
