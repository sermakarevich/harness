"""A tiny outside tool server, used only by the tests."""

from mcp.server.fastmcp import FastMCP

server = FastMCP("demo")


@server.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@server.tool()
def shout(text: str) -> str:
    """Return the text in capitals."""
    return text.upper()


if __name__ == "__main__":
    server.run(transport="stdio")
