"""Calls that may run beside each other stay together."""

from harness.tools.concurrency import EXCLUSIVE_TOOLS, batch_calls, runs_alone
from harness.tools.edit_file import TOOL_NAME as EDIT_FILE
from harness.tools.write_file import TOOL_NAME as WRITE_FILE


def call(name, call_id):
    return {"name": name, "args": {}, "id": call_id, "type": "tool_call"}


def test_writing_tools_run_alone():
    assert EXCLUSIVE_TOOLS == frozenset({WRITE_FILE, EDIT_FILE})
    assert runs_alone(WRITE_FILE) is True
    assert runs_alone(EDIT_FILE) is True
    assert runs_alone("shell") is False


def test_one_safe_call_is_one_batch():
    calls = [call("shell", "call-1")]
    assert batch_calls(calls) == [calls]


def test_neighbouring_safe_calls_share_a_batch():
    calls = [call("shell", "call-1"), call("read_file", "call-2")]
    assert batch_calls(calls) == [calls]


def test_writing_call_gets_a_batch_of_its_own():
    calls = [call("shell", "call-1"), call("write_file", "call-2"), call("shell", "call-3")]
    batches = batch_calls(calls)
    assert batches == [[calls[0]], [calls[1]], [calls[2]]]


def test_every_call_appears_once_in_order():
    calls = [
        call("shell", "call-1"),
        call("shell", "call-2"),
        call("edit_file", "call-3"),
        call("write_file", "call-4"),
        call("read_file", "call-5"),
    ]
    batches = batch_calls(calls)
    assert [call for batch in batches for call in batch] == calls
