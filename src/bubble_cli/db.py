"""SQLite operations: schema persistence and data writes."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .schema import sqlite_type_for

# Campos internos do Bubble — sempre presentes em qualquer tabela.
INTERNAL_FIELDS = {
    "_id": "TEXT PRIMARY KEY",
    "Created Date": "TEXT",
    "Modified Date": "TEXT",
    "Created By": "TEXT",
}


def safe_table_name(type_name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in type_name).strip("_") or "t"


def safe_column_name(field_name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in field_name).strip("_") or "col"


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_meta_tables()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _init_meta_tables(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS _types (
                type_name TEXT PRIMARY KEY,
                table_name TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_scanned_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS _fields (
                type_name TEXT NOT NULL,
                field_name TEXT NOT NULL,
                column_name TEXT NOT NULL,
                bubble_type TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                PRIMARY KEY (type_name, field_name)
            );
            CREATE TABLE IF NOT EXISTS _sync_state (
                type_name TEXT PRIMARY KEY,
                last_sync_at TEXT,
                last_record_count INTEGER
            );
            """
        )
        self.conn.commit()

    # ---------- schema ----------

    def get_known_schema(self) -> dict[str, dict[str, str]]:
        rows = self.conn.execute(
            "SELECT type_name, field_name, bubble_type FROM _fields"
        ).fetchall()
        out: dict[str, dict[str, str]] = {}
        for type_name, field_name, bubble_type in rows:
            out.setdefault(type_name, {})[field_name] = bubble_type
        for (t,) in self.conn.execute("SELECT type_name FROM _types").fetchall():
            out.setdefault(t, {})
        return out

    def diff_schema(self, discovered: dict[str, dict[str, str]]) -> dict[str, Any]:
        known = self.get_known_schema()
        new_types = sorted(set(discovered) - set(known))
        removed_types = sorted(set(known) - set(discovered))
        changed: dict[str, dict[str, list[str]]] = {}
        for t, fields in discovered.items():
            if t not in known:
                continue
            known_fields = set(known[t])
            new_fields = sorted(set(fields) - known_fields)
            removed_fields = sorted(known_fields - set(fields))
            if new_fields or removed_fields:
                changed[t] = {"new": new_fields, "removed": removed_fields}
        return {
            "new_types": new_types,
            "removed_types": removed_types,
            "changed": changed,
        }

    def upsert_schema(self, discovered: dict[str, dict[str, str]]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.cursor()
        for type_name, fields in discovered.items():
            table = safe_table_name(type_name)
            cur.execute(
                """
                INSERT INTO _types(type_name, table_name, first_seen_at, last_scanned_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(type_name) DO UPDATE SET last_scanned_at=excluded.last_scanned_at
                """,
                (type_name, table, now, now),
            )
            self._ensure_data_table(table)
            existing_cols = self._existing_columns(table)
            for fname, ftype in fields.items():
                if fname in INTERNAL_FIELDS:
                    continue
                col = safe_column_name(fname)
                cur.execute(
                    """
                    INSERT OR IGNORE INTO _fields(type_name, field_name, column_name, bubble_type, first_seen_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (type_name, fname, col, ftype, now),
                )
                if col.lower() not in existing_cols:
                    sqlite_type = sqlite_type_for(ftype)
                    cur.execute(
                        f'ALTER TABLE "{table}" ADD COLUMN "{col}" {sqlite_type}'
                    )
                    existing_cols.add(col.lower())
        self.conn.commit()

    def _ensure_data_table(self, table: str) -> None:
        cols_sql = ", ".join(
            f'"{name}" {definition}' for name, definition in INTERNAL_FIELDS.items()
        )
        self.conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({cols_sql})')

    def _existing_columns(self, table: str) -> set[str]:
        # ponytail: lowercased because SQLite column names are case-insensitive;
        # comparing raw names would treat "Slug"/"slug" as distinct and crash on ALTER.
        rows = self.conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        return {r[1].lower() for r in rows}

    # ---------- data ----------

    def upsert_records(
        self,
        type_name: str,
        records: Iterable[dict[str, Any]],
    ) -> int:
        table = safe_table_name(type_name)
        rows = self.conn.execute(
            "SELECT field_name, column_name FROM _fields WHERE type_name=?",
            (type_name,),
        ).fetchall()
        field_to_col = {fn: cn for fn, cn in rows}
        existing_cols = self._existing_columns(table)
        cur = self.conn.cursor()
        inserted = 0
        for rec in records:
            cols: list[str] = []
            vals: list[Any] = []
            for k, v in rec.items():
                if k == "_id":
                    cols.append("_id")
                    vals.append(v)
                    continue
                if k in INTERNAL_FIELDS:
                    cols.append(k)
                    vals.append(_to_sqlite(v))
                    continue
                col = field_to_col.get(k) or safe_column_name(k)
                if col.lower() not in existing_cols:
                    cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}" TEXT')
                    existing_cols.add(col.lower())
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO _fields(type_name, field_name, column_name, bubble_type, first_seen_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            type_name,
                            k,
                            col,
                            "text",
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                cols.append(col)
                vals.append(_to_sqlite(v))

            placeholders = ", ".join("?" * len(cols))
            col_list = ", ".join(f'"{c}"' for c in cols)
            update_clause = ", ".join(
                f'"{c}"=excluded."{c}"' for c in cols if c != "_id"
            )
            if update_clause:
                sql = (
                    f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) '
                    f'ON CONFLICT("_id") DO UPDATE SET {update_clause}'
                )
            else:
                sql = f'INSERT OR REPLACE INTO "{table}" ({col_list}) VALUES ({placeholders})'
            cur.execute(sql, vals)
            inserted += 1
        self.conn.commit()
        return inserted

    def record_sync(self, type_name: str, count: int | None = None) -> None:
        """Grava timestamp do sync. Se count for None, conta a tabela atual."""
        if count is None:
            count = self.count_records(type_name)
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT INTO _sync_state(type_name, last_sync_at, last_record_count)
            VALUES (?, ?, ?)
            ON CONFLICT(type_name) DO UPDATE
              SET last_sync_at=excluded.last_sync_at,
                  last_record_count=excluded.last_record_count
            """,
            (type_name, now, count),
        )
        self.conn.commit()

    def count_records(self, type_name: str) -> int:
        table = safe_table_name(type_name)
        try:
            row = self.conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()
            return int(row[0]) if row else 0
        except sqlite3.OperationalError:
            return 0

    def type_has_data(self, type_name: str) -> bool:
        table = safe_table_name(type_name)
        try:
            row = self.conn.execute(f'SELECT 1 FROM "{table}" LIMIT 1').fetchone()
            return row is not None
        except sqlite3.OperationalError:
            return False

    def has_any_data(self) -> bool:
        """True se qualquer tabela de tipo registrada tem ao menos uma linha."""
        rows = self.conn.execute("SELECT table_name FROM _types").fetchall()
        for (table,) in rows:
            try:
                row = self.conn.execute(
                    f'SELECT 1 FROM "{table}" LIMIT 1'
                ).fetchone()
                if row is not None:
                    return True
            except sqlite3.OperationalError:
                continue
        return False

    def get_last_sync(self, type_name: str) -> str | None:
        row = self.conn.execute(
            "SELECT last_sync_at FROM _sync_state WHERE type_name=?",
            (type_name,),
        ).fetchone()
        return row[0] if row and row[0] else None

    def list_types(self) -> list[tuple[str, str | None, int | None]]:
        return self.conn.execute(
            """
            SELECT t.type_name, s.last_sync_at, s.last_record_count
            FROM _types t
            LEFT JOIN _sync_state s ON s.type_name = t.type_name
            ORDER BY t.type_name
            """
        ).fetchall()


def _to_sqlite(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (str, int, float)):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)
