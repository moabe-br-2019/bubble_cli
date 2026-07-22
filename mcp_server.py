"""MCP server exposing the bubble CLI as a single generic tool."""
import os
import subprocess
import sys

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
    # -m em vez do shim bubble.exe: o .exe do pip trava sem console (deadlock no
    # communicate); DEVNULL evita filho esperando stdin; utf-8 pois o rich emite
    # UTF-8 mesmo em console cp1252.
    r = subprocess.run(
        [sys.executable, "-m", "bubble_cli", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=600, env=env, stdin=subprocess.DEVNULL,
    )
    return r.stdout + r.stderr


if __name__ == "__main__":
    mcp.run()  # stdio
