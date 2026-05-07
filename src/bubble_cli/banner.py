"""ASCII banner and shared visual helpers."""
from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

BANNER_LINES = [
    "██████╗ ██╗   ██╗██████╗ ██████╗ ██╗     ███████╗",
    "██╔══██╗██║   ██║██╔══██╗██╔══██╗██║     ██╔════╝",
    "██████╔╝██║   ██║██████╔╝██████╔╝██║     █████╗  ",
    "██╔══██╗██║   ██║██╔══██╗██╔══██╗██║     ██╔══╝  ",
    "██████╔╝╚██████╔╝██████╔╝██████╔╝███████╗███████╗",
    "╚═════╝  ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚══════╝",
]

# Gradiente rosa → roxo → azul (vibe Bubble + Claude Code)
GRADIENT = [
    "#ff5ea0",
    "#ee5ab8",
    "#d65cd5",
    "#b85eee",
    "#9560ff",
    "#6e7aff",
]


def banner_text() -> Text:
    text = Text()
    for line, color in zip(BANNER_LINES, GRADIENT):
        text.append(line + "\n", style=f"bold {color}")
    return text


def print_banner(console: Console, subtitle: str | None = None) -> None:
    body = [Align.center(banner_text())]
    if subtitle:
        body.append(Align.center(Text(subtitle, style="dim cyan")))
    panel = Panel.fit(
        Group(*body),
        border_style="#9560ff",
        padding=(0, 2),
    )
    console.print(panel)


def print_compact_banner(console: Console) -> None:
    """Mini-banner para comandos não-interativos."""
    text = Text()
    text.append("◉ ", style="bold #ff5ea0")
    text.append("BUBBLE CLI", style="bold #9560ff")
    text.append("  Bubble.io → SQLite", style="dim cyan")
    console.print(text)


def section(console: Console, title: str, body: str | Text) -> None:
    """Painel curto pra destacar um bloco de output."""
    console.print(
        Panel(
            body if isinstance(body, Text) else Text(body),
            title=title,
            title_align="left",
            border_style="#6e7aff",
            padding=(0, 1),
        )
    )
