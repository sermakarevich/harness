"""A conversation kept as a plain list of messages that is resent whole on every turn."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from harness.model.text import text_of


class Chat:
    def __init__(self, model, system_prompt: str):
        self.model = model
        self.system_prompt = system_prompt
        self.messages = self._fresh()

    def _fresh(self) -> list:
        return [SystemMessage(content=self.system_prompt)]

    def ask(self, text: str) -> str:
        self.messages.append(HumanMessage(content=text))
        reply = self.model.invoke(self.messages)
        self.messages.append(reply)
        return text_of(reply)

    def reset(self) -> None:
        self.messages = self._fresh()

    def size(self) -> int:
        return len(self.messages)
