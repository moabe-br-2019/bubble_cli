"""Vários workers escrevendo em tabelas diferentes do mesmo .db não podem estourar
'database is locked' — é o que o pull paralelo faz. Cobre o PRAGMA busy_timeout.

Rodar: PYTHONPATH=src python tests/test_concurrent_write.py
"""
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bubble_cli.db import Database


def _worker(db_path: Path, type_name: str) -> int:
    db = Database(db_path)
    try:
        db.upsert_schema({type_name: {"Slug": "text", "Name": "text"}})
        recs = [{"_id": f"{type_name}-{i}", "Slug": f"s{i}", "Name": f"n{i}"} for i in range(300)]
        return db.upsert_records(type_name, recs)
    finally:
        db.close()


def test_concurrent_writes_do_not_lock():
    db_path = Path(tempfile.mktemp(suffix=".db"))
    Database(db_path).close()  # cria o arquivo/meta uma vez
    types = [f"T{i}" for i in range(6)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        counts = list(ex.map(lambda tn: _worker(db_path, tn), types))
    assert counts == [300] * 6, counts

    db = Database(db_path)
    try:
        for tn in types:
            n = db.conn.execute(f'SELECT COUNT(*) FROM "{tn}"').fetchone()[0]
            assert n == 300, (tn, n)
    finally:
        db.close()


if __name__ == "__main__":
    test_concurrent_writes_do_not_lock()
    print("OK: escritas concorrentes serializadas sem lock")
