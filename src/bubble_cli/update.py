"""Check GitHub for a newer release and (optionally) self-update via pipx."""
from __future__ import annotations

import re
import shutil
import subprocess
from datetime import date

import httpx

from . import __version__
from . import prefs as prefs_mod

RAW_VERSION_URL = (
    "https://raw.githubusercontent.com/moabe-br-2019/bubble_cli/main/"
    "src/bubble_cli/__init__.py"
)
# Comando manual mostrado quando o pipx não está disponível.
MANUAL_UPGRADE_CMD = (
    "pip install -U git+https://github.com/moabe-br-2019/bubble_cli.git"
)


def _parse(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def fetch_latest() -> str | None:
    """Lê __version__ do main no GitHub. None em qualquer falha de rede."""
    try:
        r = httpx.get(RAW_VERSION_URL, timeout=5.0)
    except httpx.HTTPError:
        return None
    if r.status_code != 200:
        return None
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', r.text)
    return m.group(1) if m else None


def check_for_update(force: bool = False) -> str | None:
    """Versão mais nova que a instalada, ou None. Rede no máx. 1x/dia (cache em prefs)."""
    prefs = prefs_mod.load_prefs()
    today = date.today().isoformat()

    if not force and prefs.get("update_last_check") == today:
        cached = prefs.get("update_latest_seen")
    else:
        cached = fetch_latest()
        prefs["update_last_check"] = today
        if cached:
            prefs["update_latest_seen"] = cached
        prefs_mod.save_prefs(prefs)

    if cached and _parse(cached) > _parse(__version__):
        return cached
    return None


def run_self_update() -> bool:
    """Roda `pipx upgrade bubble-cli`. False se pipx não existe ou o upgrade falha."""
    pipx = shutil.which("pipx")
    if not pipx:
        return False
    return subprocess.run([pipx, "upgrade", "bubble-cli"]).returncode == 0
