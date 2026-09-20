"""Run the tools the model asked for, asking first when the policy says so."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from langchain_core.messages import ToolMessage
from langgraph.types import interrupt

from harness.chat.state import HarnessState
from harness.tools.concurrency import batch_calls
from harness.tools.permission import DENIED_MESSAGE, Answer, needs_approval
from harness.tools.todos import todos_of

UNKNOWN_MESSAGE = "unknown tool: {name}"


def build_run_tools(tools: list, offload: Callable[[str], str], max_parallel: int):
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

        def run_one(call: dict) -> ToolMessage:
            name = call["name"]
            if answers.get(call["id"], Answer.YES) == Answer.NO:
                return ToolMessage(content=DENIED_MESSAGE, name=name, tool_call_id=call["id"])
            if name not in by_name:
                return ToolMessage(
                    content=UNKNOWN_MESSAGE.format(name=name),
                    name=name,
                    tool_call_id=call["id"],
                )
            result = by_name[name].invoke(call["args"])
            return ToolMessage(content=offload(str(result)), name=name, tool_call_id=call["id"])

        messages = []
        for batch in batch_calls(calls):
            workers = min(len(batch), max_parallel)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                messages.extend(pool.map(run_one, batch))
        already = set(state["always_allowed"])
        result = {
            "messages": messages,
            "always_allowed": [name for name in allowed if name not in already],
        }
        todos = todos_of(calls)
        if todos is not None:
            result["todos"] = todos
        return result

    return run_tools
