import json
import sqlite3

from bubble_cli import config
from bubble_cli.mcp_server import query


def _project(tmp_path, rows=3):
    config.save(tmp_path, config.Config(app_id="app", api_key="k"))
    con = sqlite3.connect(tmp_path / "bubble.sqlite")
    con.execute("CREATE TABLE t (id INTEGER, name TEXT)")
    con.executemany("INSERT INTO t VALUES (?, ?)", [(i, f"n{i}") for i in range(rows)])
    con.commit()
    con.close()


def test_query_returns_rows(tmp_path):
    _project(tmp_path)
    out = json.loads(query("SELECT * FROM t ORDER BY id", folder=str(tmp_path)))
    assert out["columns"] == ["id", "name"]
    assert out["rows"] == [[0, "n0"], [1, "n1"], [2, "n2"]]
    assert out["truncated"] is False


def test_query_truncates(tmp_path):
    _project(tmp_path, rows=5)
    out = json.loads(query("SELECT * FROM t", folder=str(tmp_path), max_rows=2))
    assert len(out["rows"]) == 2
    assert out["truncated"] is True


def test_query_is_read_only(tmp_path):
    _project(tmp_path)
    result = query("DELETE FROM t", folder=str(tmp_path))
    assert "readonly" in result.lower() or "attempt to write" in result.lower()
