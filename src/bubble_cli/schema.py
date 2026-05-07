"""Schema discovery and SQLite type mapping."""
from __future__ import annotations

from typing import Any

# Mapping de tipos do Bubble para afinidade SQLite.
TYPE_MAP = {
    "text": "TEXT",
    "number": "REAL",
    "numeric": "REAL",
    "boolean": "INTEGER",
    "date": "TEXT",
    "date_interval": "TEXT",
    "image": "TEXT",
    "file": "TEXT",
    "geographic_address": "TEXT",
}


def sqlite_type_for(bubble_type: str) -> str:
    base = (bubble_type or "text").lower().strip()
    if base.startswith("list") or base.endswith("_list"):
        return "TEXT"  # lista serializada como JSON
    return TYPE_MAP.get(base, "TEXT")


def _field_name(f: dict) -> str | None:
    return (
        f.get("display")
        or f.get("name")
        or f.get("caption")
        or f.get("id")
    )


def _type_name(entry: dict) -> str | None:
    return (
        entry.get("display")
        or entry.get("name")
        or entry.get("caption")
        or entry.get("type")
        or entry.get("id")
    )


def _parse_fields(fields_obj: Any) -> dict[str, str]:
    """Aceita `fields` como lista de dicts OU dict de dicts."""
    out: dict[str, str] = {}
    if isinstance(fields_obj, list):
        for f in fields_obj:
            if not isinstance(f, dict):
                continue
            fname = _field_name(f)
            if not fname:
                continue
            out[fname] = f.get("type") or "text"
    elif isinstance(fields_obj, dict):
        for fname, fmeta in fields_obj.items():
            if isinstance(fmeta, dict):
                out[fname] = fmeta.get("type") or "text"
            else:
                out[fname] = "text"
    return out


def normalize_meta(meta: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Converte resposta do /meta em {type_name: {field_name: bubble_type}}.

    O /meta do Bubble varia entre apps; tentamos múltiplos formatos e
    mesclamos os resultados.
    """
    result: dict[str, dict[str, str]] = {}

    # Formato A: top-level "get" = lista de entradas de tipo.
    if isinstance(meta.get("get"), list):
        for entry in meta["get"]:
            if not isinstance(entry, dict):
                continue
            tname = _type_name(entry)
            if not tname:
                continue
            result.setdefault(tname, {}).update(_parse_fields(entry.get("fields")))

    # Formato B: top-level "types" = dict {chave: body}.
    if isinstance(meta.get("types"), dict):
        for key, body in meta["types"].items():
            if not isinstance(body, dict):
                continue
            tname = _type_name(body) or key
            result.setdefault(tname, {}).update(_parse_fields(body.get("fields")))

    return result


def infer_fields_from_record(record: dict[str, Any]) -> dict[str, str]:
    """Fallback: deduz tipos de um registro de exemplo."""
    out: dict[str, str] = {}
    for k, v in record.items():
        if isinstance(v, bool):
            out[k] = "boolean"
        elif isinstance(v, (int, float)):
            out[k] = "number"
        elif isinstance(v, list):
            out[k] = "list"
        else:
            out[k] = "text"
    return out
