"""Tools borrowed from outside servers, made to look like the local ones."""

import asyncio

from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from harness.config import ToolServer
from harness.model.text import join_text

NAME_SEPARATOR = "_"
TRANSPORT = "stdio"


def _server_tools(server: ToolServer) -> list:
    client = MultiServerMCPClient(
        {
            server.name: {
                "command": server.command,
                "args": list(server.args),
                "transport": TRANSPORT,
            }
        }
    )
    return asyncio.run(client.get_tools())


def _local_tool(server: ToolServer, remote):
    def run(**kwargs):
        return join_text(asyncio.run(remote.ainvoke(kwargs)))

    return StructuredTool(
        name=f"{server.name}{NAME_SEPARATOR}{remote.name}",
        description=remote.description,
        args_schema=remote.args_schema,
        func=run,
    )


def build_server_tools(servers) -> list:
    """List the tools borrowed from every server that answers."""
    tools = []
    for server in servers:
        try:
            remotes = _server_tools(server)
        except Exception:  # A server can fail in many ways; lose only its tools.
            continue
        tools.extend(_local_tool(server, remote) for remote in remotes)
    return tools
