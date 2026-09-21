"""Borrowed tools behave like the local ones once renamed."""

import sys
from pathlib import Path

from harness.config import ToolServer
from harness.tools.permission import needs_approval
from harness.tools.servers import build_server_tools

DEMO_PATH = str(Path(__file__).with_name("demo_server.py"))


def demo(name="demo"):
    return ToolServer(name=name, command=sys.executable, args=(DEMO_PATH,))


def test_names_carry_the_server():
    tools = build_server_tools([demo()])
    assert sorted(tool.name for tool in tools) == ["demo_add", "demo_shout"]


def test_borrowed_tool_runs_through_invoke():
    tools = build_server_tools([demo()])
    by_name = {tool.name: tool for tool in tools}
    assert by_name["demo_add"].invoke({"a": 2, "b": 3}) == "5"


def test_two_servers_do_not_collide():
    tools = build_server_tools([demo("demo"), demo("other")])
    assert len({tool.name: tool for tool in tools}) == 4


def test_dead_server_costs_only_its_tools():
    dead = ToolServer(name="dead", command="no-such-command", args=())
    tools = build_server_tools([dead, demo()])
    assert sorted(tool.name for tool in tools) == ["demo_add", "demo_shout"]


def test_borrowed_tool_needs_a_question():
    assert needs_approval("demo_add") is True
