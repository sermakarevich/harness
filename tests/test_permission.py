from harness.tools.permission import needs_approval
from harness.tools.read_file import TOOL_NAME


def test_read_tool_needs_no_approval():
    assert needs_approval(TOOL_NAME) is False


def test_change_tools_need_approval():
    assert needs_approval("write_file") is True
    assert needs_approval("edit_file") is True
    assert needs_approval("shell") is True


def test_unknown_tool_needs_approval():
    assert needs_approval("no_such_tool") is True
