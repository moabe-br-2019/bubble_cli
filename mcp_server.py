"""MCP server exposing the bubble CLI as a single generic tool."""
import os
import subprocess

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("bubble-cli")


@mcp.tool()
def bubble(args: list[str], lang: str = "en") -> str:
    """Run the bubble CLI (Bubble.io Data API -> SQLite extractor).

    Examples: ["--help"], ["status"], ["scan"], ["list"],
    ["pull", "--dry-run"], ["pull", "--mode", "incremental"].
    Run ["--help"] to discover all commands and options.

    lang: output language, "en" or "pt" (default "en").
    """
    env = {**os.environ, "BUBBLE_LANG": lang}
    r = subprocess.run(
        ["bubble", *args], capture_output=True, text=True, timeout=600, env=env
    )
    return r.stdout + r.stderr


if __name__ == "__main__":
    mcp.run()  # stdio
