from langchain_core.messages import SystemMessage

from harness.chat.loop import Chat
from tests.conftest import RecordingModel


def test_every_turn_sends_the_whole_list(settings):
    chat = Chat(RecordingModel(), "sys")
    chat.ask("hi")
    assert chat.size() == 3
    chat.ask("there")
    assert chat.size() == 5
    assert chat.model.seen == [2, 4]


def test_reset_keeps_only_the_system_message(settings):
    chat = Chat(RecordingModel(), "sys")
    chat.ask("hi")
    chat.reset()
    assert chat.size() == 1
    chat.ask("there")
    assert chat.model.seen == [2, 2]


def test_system_prompt_is_always_first(settings):
    chat = Chat(RecordingModel(), "sys")
    chat.ask("hi")
    chat.ask("there")
    assert chat.model.first != []
    assert all(isinstance(message, SystemMessage) for message in chat.model.first)
