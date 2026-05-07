"""Global user preferences (separate from per-project bubble.json)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PREFS_FILENAME = "prefs.json"


def prefs_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / "bubble-cli"


def prefs_path() -> Path:
    return prefs_dir() / PREFS_FILENAME


def load_prefs() -> dict:
    path = prefs_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_prefs(prefs: dict) -> Path:
    path = prefs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return path
