"""Run the tools the model asked for, asking first when the policy says so."""

from collections.abc import Callable

from langchain_core.messages import ToolMessage
from langgraph.types import interrupt

from harness.chat.state import HarnessState
from harness.tools.permission import DENIED_MESSAGE, Answer, needs_approval

UNKNOWN_MESSAGE = "unknown tool: {name}"


def build_run_tools(tools: list, offload: Callable[[str], str]):
    """Build the node that asks before risky calls and runs them after."""
    by_name = {tool.name: tool for tool in tools}

    def run_tools(state: HarnessState) -> dict:
        calls = state["messages"][-1].tool_calls or []
        allowed = set(state["always_allowed"])
        answers: dict[str, str] = {}
        for call in calls:
            name = call["name"]
            if not needs_approval(name) or name in allowed:
                continue
            answer = interrupt({"id": call["id"], "name": name, "args": call["args"]})
            if answer == Answer.ALWAYS:
                allowed.add(name)
            answers[call["id"]] = answer
        messages = []
        for call in calls:
            name = call["name"]
            if answers.get(call["id"], Answer.YES) == Answer.NO:
                messages.append(
                    ToolMessage(content=DENIED_MESSAGE, name=name, tool_call_id=call["id"])
                )
            elif name not in by_name:
                messages.append(
                    ToolMessage(
                        content=UNKNOWN_MESSAGE.format(name=name),
                        name=name,
                        tool_call_id=call["id"],
                    )
                )
            else:
                result = by_name[name].invoke(call["args"])
                messages.append(
                    ToolMessage(content=offload(str(result)), name=name, tool_call_id=call["id"])
                )
        already = set(state["always_allowed"])
        return {
            "messages": messages,
            "always_allowed": [name for name in allowed if name not in already],
        }

    return run_tools
