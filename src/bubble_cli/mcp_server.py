"""MCP server exposing the bubble CLI as a single generic tool."""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from bubble_cli import config as _config

mcp = FastMCP("bubble-cli")


@mcp.tool()
def bubble(args: list[str], lang: str = "en") -> str:
    """Run the bubble CLI (Bubble.io Data API -> SQLite extractor).

    Examples: ["--help"], ["status"], ["scan"], ["list"],
    ["pull", "--dry-run"], ["pull", "--mode", "incremental"],
    ["export", "--types", "User,Order", "--out", "reports"].
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


@mcp.tool()
def query(sql: str, folder: str = ".", max_rows: int = 200) -> str:
    """Run read-only SQL against the local SQLite mirror of the Bubble app.

    Much faster than the CLI for reading/exploring downloaded data.
    Discover tables: SELECT name FROM sqlite_master WHERE type='table'
    Columns: SELECT * FROM pragma_table_info('TableName')
    Then normal SELECTs (joins, aggregates, etc).

    folder: project folder containing bubble.json (default: cwd).
    max_rows: cap on returned rows (default 200).

    Returns JSON: {"columns": [...], "rows": [[...], ...], "truncated": bool}.
    """
    db_file = Path(folder).resolve() / _config.load(Path(folder)).db_path
    if not db_file.exists():
        return f"Database not found: {db_file}. Run pull first."
    # mode=ro: garante somente leitura mesmo com SQL arbitrário do cliente
    con = sqlite3.connect(f"{db_file.as_uri()}?mode=ro", uri=True)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(max_rows)
        truncated = cur.fetchone() is not None
    except sqlite3.Error as e:
        return f"SQL error: {e}"
    finally:
        con.close()
    return json.dumps(
        {"columns": cols, "rows": rows, "truncated": truncated},
        ensure_ascii=False, default=str,
    )


if __name__ == "__main__":
    mcp.run()  # stdio
