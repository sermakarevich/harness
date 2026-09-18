from langchain_core.messages import AIMessage, SystemMessage


class RecordingModel:
    def __init__(self):
        self.seen: list[int] = []
        self.first: list = []

    def invoke(self, messages):
        self.seen.append(len(messages))
        self.first.append(messages[0])
        return AIMessage(content=f"reply {len(self.seen)}")


def test_every_turn_sends_the_whole_list(chat_list):
    model = RecordingModel()
    out = list(chat_list.chat(model, "sys", ["hi", "there"]))
    assert model.seen == [2, 4]
    assert [count for _, count in out] == [3, 5]


def test_new_command_empties_the_list(chat_list):
    model = RecordingModel()
    out = list(chat_list.chat(model, "sys", ["hi", chat_list.NEW_COMMAND, "there"]))
    assert model.seen == [2, 2]
    assert out[1] == (chat_list.NEW_NOTICE, 1)


def test_system_prompt_is_always_first(chat_list):
    model = RecordingModel()
    list(chat_list.chat(model, "sys", ["hi", "there"]))
    assert model.first != []
    assert all(isinstance(message, SystemMessage) for message in model.first)
