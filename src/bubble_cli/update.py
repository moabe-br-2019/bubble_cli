"""Check GitHub for a newer release and (optionally) self-update via pipx."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
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


# ── What's new ──────────────────────────────────────────────
# Notas por versão, mostradas uma única vez logo após o usuário atualizar.
# Adicione uma entrada aqui a cada release (en + pt).
CHANGELOG: dict[str, dict[str, list[str]]] = {
    "0.1.8": {
        "en": [
            "New MCP menu item: setup guide to use the CLI from AI clients",
            "MCP server now ships inside the package (python -m bubble_cli.mcp_server)",
        ],
        "pt": [
            "Novo item MCP no menu: guia para usar a CLI a partir de clientes de IA",
            "Servidor MCP agora vem dentro do pacote (python -m bubble_cli.mcp_server)",
        ],
    },
    "0.1.7": {
        "en": [
            "BUBBLE_LANG env var now overrides the saved language preference",
            "MCP server: fixed hang, output encoding and language selection",
        ],
        "pt": [
            "Env BUBBLE_LANG agora tem prioridade sobre o idioma salvo nas preferências",
            "Servidor MCP: corrigidos travamento, encoding do output e seleção de idioma",
        ],
    },
    "0.1.6": {
        "en": [
            "This panel: release notes shown once right after an update",
            "MCP server (mcp_server.py) exposing the CLI to AI clients",
        ],
        "pt": [
            "Este painel: notas da versão exibidas uma vez logo após atualizar",
            "Servidor MCP (mcp_server.py) expondo a CLI para clientes de IA",
        ],
    },
    "0.1.5": {
        "en": [
            "Parallel table download in pull (-j/--jobs)",
            "Automatic retry with backoff on 429/5xx errors",
            "--dry-run now respects --mode incremental",
        ],
        "pt": [
            "Download de tabelas em paralelo no pull (-j/--jobs)",
            "Retry automático com backoff em erros 429/5xx",
            "--dry-run agora respeita --mode incremental",
        ],
    },
}


def whats_new_since(old: str, lang: str) -> list[tuple[str, list[str]]]:
    """Entradas do CHANGELOG com old < versão <= instalada, mais antigas primeiro."""
    entries = [
        (ver, notes.get(lang) or notes.get("en") or [])
        for ver, notes in CHANGELOG.items()
        if _parse(old) < _parse(ver) <= _parse(__version__)
    ]
    entries.sort(key=lambda e: _parse(e[0]))
    return entries


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
    """Atualiza via pipx se disponível, senão via pip do interpretador atual. False se falhar."""
    pipx = shutil.which("pipx")
    if pipx:
        cmd = [pipx, "upgrade", "bubble-cli"]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "-U",
               "git+https://github.com/moabe-br-2019/bubble_cli.git"]
    return subprocess.run(cmd).returncode == 0
