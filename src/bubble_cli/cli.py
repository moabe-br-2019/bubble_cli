"""CLI entry points."""
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

# UTF-8 em consoles Windows (PowerShell/cmd que defaultam para cp1252).
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from . import __version__
from . import config as cfg
from . import prefs as prefs_mod
from . import update as update_mod
from .api import BubbleAPIError, BubbleClient
from .banner import print_banner, print_compact_banner
from .db import Database
from .i18n import LANG_LABELS, SUPPORTED, detect_lang, get_lang, set_lang, t
from .schema import infer_fields_from_record, normalize_meta

console = Console()

ACCENT = "#9560ff"
ACCENT_PINK = "#ff5ea0"
ACCENT_BLUE = "#6e7aff"


def _db_filename_from(app_id: str) -> str:
    """Deriva nome do .sqlite a partir do app_id (sanitizado)."""
    import re
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", app_id).strip("._-") or "bubble"
    return f"{safe}.sqlite"


def _bootstrap_lang() -> None:
    """Resolve idioma: env BUBBLE_LANG → prefs salva → auto-detect → en.

    Env vem antes da pref: BUBBLE_LANG é o canal programático por invocação
    (ex.: servidor MCP), a pref é só o default salvo.
    """
    prefs = prefs_mod.load_prefs()
    lang = (
        os.environ.get("BUBBLE_LANG")
        or prefs.get("lang")
        or detect_lang()
    )
    set_lang(lang)


_bootstrap_lang()


def _load_config_or_abort(folder: Path) -> cfg.Config:
    try:
        return cfg.load(folder)
    except FileNotFoundError:
        console.print(f"[red]✗[/] {t('err.config_not_found', folder=folder)}")
        raise click.Abort()


# ============================================================
# Click entry points (thin wrappers around _do_* helpers)
# ============================================================


def _do_mcp() -> None:
    """Guia de setup do servidor MCP embutido."""
    cmd = f"claude mcp add bubble -- {sys.executable} -m bubble_cli.mcp_server"
    body = (
        f"{t('mcp.what')}\n\n"
        f"[bold]1.[/] {t('mcp.step_install')}\n   [{ACCENT_BLUE}]pip install mcp[/]\n"
        f"[bold]2.[/] {t('mcp.step_register')}\n   [{ACCENT_BLUE}]{cmd}[/]\n"
        f"[bold]3.[/] {t('mcp.step_use')}"
    )
    console.print(
        Panel(body, title=t("mcp.title"), border_style=ACCENT, expand=False)
    )


def _maybe_show_whats_new() -> None:
    """Painel de novidades, exibido uma única vez logo após uma atualização."""
    prefs = prefs_mod.load_prefs()
    old = prefs.get("last_run_version")
    if old != __version__:
        prefs["last_run_version"] = __version__
        prefs_mod.save_prefs(prefs)
    if not old or old == __version__:
        return  # primeira execução ou versão inalterada
    entries = update_mod.whats_new_since(old, get_lang())
    if not entries:
        return
    body = "\n".join(
        f"[bold]{ver}[/]\n" + "\n".join(f"  • {note}" for note in notes)
        for ver, notes in entries
    )
    console.print(
        Panel(
            body,
            title=t("whatsnew.title", version=__version__),
            border_style=ACCENT,
            expand=False,
        )
    )


def _maybe_notify_update() -> None:
    """One-line notice if a newer version exists. Silent on network failure."""
    latest = update_mod.check_for_update()
    if latest:
        console.print(
            f"[{ACCENT_PINK}]↑[/] "
            + t("update.available", latest=latest, current=__version__)
            + f" [dim]bubble update[/]"
        )


def _do_update() -> None:
    latest = update_mod.check_for_update(force=True)
    if not latest:
        console.print(f"[green]✓[/] {t('update.up_to_date', current=__version__)}")
        return
    console.print(
        f"[{ACCENT_PINK}]↑[/] {t('update.available', latest=latest, current=__version__)}"
    )
    if not Confirm.ask(f"[{ACCENT_PINK}]?[/] {t('update.prompt')}", default=True):
        return
    console.print(f"[dim]{t('update.updating')}[/]")
    if update_mod.run_self_update():
        console.print(f"[green]✓[/] {t('update.done')}")
    else:
        console.print(
            f"[yellow]![/] {t('update.failed', cmd=update_mod.MANUAL_UPGRADE_CMD)}"
        )


@click.group(invoke_without_command=True)
@click.version_option()
@click.pass_context
def cli(ctx: click.Context):
    """CLI to extract Bubble.io app data via the Data API into SQLite."""
    if ctx.invoked_subcommand is None:
        try:
            interactive_menu(Path.cwd())
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[dim]{t('bye')}[/]")
    elif ctx.invoked_subcommand != "update":
        _maybe_show_whats_new()
        _maybe_notify_update()


@cli.command()
def init():
    """Configure a new Bubble project in the current folder (or a subfolder)."""
    print_banner(console, subtitle=t("subtitle.setup"))
    console.print()
    _do_init(Path.cwd())


@cli.command()
@click.option("--folder", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option(
    "--dump-meta",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Save raw /meta response to a JSON file (for debugging).",
)
def scan(folder: Optional[Path], dump_meta: Optional[Path]):
    """Discover types and fields from the Data API."""
    folder = folder or Path.cwd()
    config = _load_config_or_abort(folder)
    print_compact_banner(console)
    console.print()
    _do_scan(folder, config, dump_meta=dump_meta)


@cli.command(name="list")
@click.option("--folder", type=click.Path(file_okay=False, path_type=Path), default=None)
def list_types(folder: Optional[Path]):
    """List discovered types and last sync info."""
    folder = folder or Path.cwd()
    config = _load_config_or_abort(folder)
    _do_list(folder, config)


@cli.command()
@click.option("--folder", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option("--types", "types_csv", default=None, help="Types to download (comma-separated).")
@click.option("--all", "all_types", is_flag=True, help="Download all types.")
@click.option("--dry-run", is_flag=True, help="Read from Bubble but don't write to SQLite.")
@click.option(
    "--mode",
    type=click.Choice(["auto", "full", "incremental"]),
    default="auto",
    help=(
        "Sync mode. 'auto' (default): full sync if DB is empty, otherwise prompt. "
        "'full': re-fetch every record. 'incremental': only records modified since the last sync."
    ),
)
@click.option(
    "-j",
    "--jobs",
    type=int,
    default=4,
    show_default=True,
    help="Tables to download in parallel (1 = sequential). Lower it if Bubble returns 429.",
)
def pull(
    folder: Optional[Path],
    types_csv: Optional[str],
    all_types: bool,
    dry_run: bool,
    mode: str,
    jobs: int,
):
    """Download records into SQLite (or simulate with --dry-run)."""
    folder = folder or Path.cwd()
    config = _load_config_or_abort(folder)
    print_compact_banner(console)
    console.print()
    _do_pull(
        folder,
        config,
        types_csv=types_csv,
        all_types=all_types,
        dry_run=dry_run,
        mode=mode,
        jobs=jobs,
    )


@cli.command()
def update():
    """Check GitHub for a newer version and install it."""
    _do_update()


@cli.command()
@click.option("--folder", type=click.Path(file_okay=False, path_type=Path), default=None)
def status(folder: Optional[Path]):
    """Show current config and DB location."""
    folder = folder or Path.cwd()
    config = _load_config_or_abort(folder)
    _do_status(folder, config)


# ============================================================
# Action implementations (reusable from CLI commands and menu)
# ============================================================


def _do_init(starting_folder: Path) -> Optional[Path]:
    """Run init flow. Returns the project folder created, or None."""
    create_sub = Confirm.ask(
        f"[{ACCENT_PINK}]?[/] {t('init.subfolder_q')}", default=False
    )
    if create_sub:
        folder_name = Prompt.ask(f"[{ACCENT_PINK}]?[/] {t('init.subfolder_name')}")
        target = starting_folder / folder_name
        target.mkdir(parents=True, exist_ok=True)
    else:
        target = starting_folder

    if cfg.exists(target):
        if not Confirm.ask(
            f"[yellow]![/] {t('init.exists_warn', target=target)}", default=False
        ):
            console.print(f"[yellow]{t('common.cancelled')}[/]")
            return None

    hint = Text()
    hint.append(t("init.app_id_hint") + "\n", style="dim")
    hint.append("  https://bubble.io/page?id=", style="dim")
    hint.append("[your-app-id]", style=f"bold {ACCENT_PINK}")
    hint.append("&tab=Design", style="dim")
    console.print(hint)
    app_id = Prompt.ask(f"[{ACCENT_PINK}]?[/] {t('init.app_id')}")
    version = Prompt.ask(
        f"[{ACCENT_PINK}]?[/] {t('init.version')}",
        choices=["live", "test"],
        default="live",
    )
    api_key = Prompt.ask(f"[{ACCENT_PINK}]?[/] {t('init.api_key')}")
    db_path = _db_filename_from(app_id)

    config = cfg.Config(
        app_id=app_id, api_key=api_key, version=version, db_path=db_path
    )

    with console.status(f"[{ACCENT}]{t('init.testing')}[/]", spinner="dots"):
        try:
            with BubbleClient(config) as client:
                client.get_meta()
            ok, err = True, None
        except BubbleAPIError as e:
            ok, err = False, str(e)

    if ok:
        console.print(f"[green]✓[/] {t('init.conn_ok')}")
    else:
        console.print(f"[red]✗[/] {err}")
        if not Confirm.ask(t("init.save_anyway"), default=False):
            return None

    saved_at = cfg.save(target, config)

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="dim")
    summary.add_column()
    summary.add_row(t("init.label.app_id"), f"[bold]{config.app_id}[/]")
    summary.add_row(t("init.label.version"), f"[bold]{config.version}[/]")
    summary.add_row(t("init.label.base_url"), config.base_url)
    summary.add_row(t("init.label.sqlite"), str(target / config.db_path))
    summary.add_row(t("init.label.config"), str(saved_at))
    console.print(
        Panel(
            summary,
            title=f"[bold]{t('init.panel_title')}[/]",
            title_align="left",
            border_style=ACCENT,
            padding=(1, 2),
        )
    )

    if Confirm.ask(f"[{ACCENT_PINK}]?[/] {t('init.run_scan_q')}", default=True):
        console.print()
        _do_scan(target, config)

    return target


def _do_scan(
    folder: Path,
    config: cfg.Config,
    dump_meta: Optional[Path] = None,
) -> None:
    import json as _json

    db_file = folder / config.db_path

    with BubbleClient(config) as client:
        with console.status(f"[{ACCENT}]{t('scan.fetching')}[/]", spinner="dots"):
            try:
                meta = client.get_meta()
            except BubbleAPIError as e:
                console.print(f"[red]✗[/] {t('scan.fetch_error', err=e)}")
                return
            if dump_meta:
                dump_meta.write_text(
                    _json.dumps(meta, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                console.print(f"[dim]{t('scan.meta_dumped', path=dump_meta)}[/]")
            discovered = normalize_meta(meta)

        if not discovered:
            console.print(f"[yellow]![/] {t('scan.no_types')}")
            names_raw = Prompt.ask(
                f"[{ACCENT_PINK}]?[/] {t('scan.types_prompt')}"
            )
            names = [n.strip() for n in names_raw.split(",") if n.strip()]
            for name in names:
                with console.status(
                    f"[{ACCENT}]{t('scan.inferring', name=name)}[/]",
                    spinner="dots",
                ):
                    try:
                        sample = next(client.iter_records(name), None)
                    except BubbleAPIError as e:
                        console.print(f"[red]✗ {name}:[/] {e}")
                        continue
                discovered[name] = (
                    infer_fields_from_record(sample) if sample else {}
                )

    with Database(db_file) as db:
        diff = db.diff_schema(discovered)
        db.upsert_schema(discovered)

    _print_diff(diff)
    console.print(
        f"[green]✓[/] {t('scan.done', n=len(discovered), accent=ACCENT)}"
    )


def _do_list(folder: Path, config: cfg.Config) -> None:
    with Database(folder / config.db_path) as db:
        rows = db.list_types()

    if not rows:
        console.print(f"[yellow]![/] {t('list.empty', accent_blue=ACCENT_BLUE)}")
        return

    table = Table(
        title=t("list.title"),
        title_style=f"bold {ACCENT}",
        border_style=ACCENT_BLUE,
        header_style=f"bold {ACCENT_PINK}",
    )
    table.add_column(t("list.col.type"))
    table.add_column(t("list.col.last_sync"), style="dim")
    table.add_column(t("list.col.count"), justify="right", style="cyan")
    for name, last_sync, count in rows:
        table.add_row(
            name,
            last_sync or "—",
            str(count) if count is not None else "—",
        )
    console.print(table)


def _do_pull(
    folder: Path,
    config: cfg.Config,
    *,
    types_csv: Optional[str] = None,
    all_types: bool = False,
    dry_run: bool = False,
    mode: str = "auto",
    jobs: int = 4,
) -> None:
    db_file = folder / config.db_path

    with Database(db_file) as db:
        known = sorted(db.get_known_schema())
        if not known:
            console.print(f"[yellow]![/] {t('pull.schema_empty', accent_blue=ACCENT_BLUE)}")
            return

        if all_types:
            chosen = known
        elif types_csv:
            requested = [t_.strip() for t_ in types_csv.split(",") if t_.strip()]
            unknown = sorted(set(requested) - set(known))
            if unknown:
                console.print(
                    f"[red]✗[/] {t('err.unknown_types', names=', '.join(unknown))}"
                )
                return
            chosen = requested
        else:
            chosen = _interactive_pick(known)
            if not chosen:
                console.print(f"[yellow]{t('pull.nothing_selected')}[/]")
                return

        if dry_run:
            console.print(
                Panel(
                    Text(t("pull.dry_run_warn"), style="yellow"),
                    border_style="yellow",
                    padding=(0, 2),
                )
            )

        # Decide modo (full vs incremental) quando não passado explicitamente.
        if dry_run:
            # Preview não pergunta nada: "auto" vira full, mas modo explícito é respeitado.
            resolved_mode = mode if mode in ("full", "incremental") else "full"
        else:
            resolved_mode = _resolve_pull_mode(db, mode)
            if resolved_mode is None:
                console.print(f"[yellow]{t('common.cancelled')}[/]")
                return

        if dry_run:
            with BubbleClient(config) as client:
                for type_name in chosen:
                    constraints, _ = _incremental_constraints(
                        db, type_name, resolved_mode, verbose=True
                    )
                    with console.status(
                        f"[{ACCENT}]{t('pull.counting', type=type_name)}[/]",
                        spinner="dots",
                    ):
                        try:
                            total = client.count(type_name, constraints=constraints)
                        except BubbleAPIError as e:
                            console.print(f"[red]✗ {type_name}:[/] {e}")
                            continue
                    console.print(
                        f"[bold {ACCENT}]" + t("pull.dry_count", type=type_name, n=total)
                    )
            return

        if jobs > 1 and len(chosen) > 1:
            _pull_parallel(db_file, config, chosen, resolved_mode, jobs)
        else:
            with BubbleClient(config) as client:
                for type_name in chosen:
                    console.print(_pull_one(db, client, type_name, mode=resolved_mode))


def _resolve_pull_mode(db: Database, requested: str) -> Optional[str]:
    """Resolve o modo final do pull. Retorna None se o usuário cancelar."""
    if requested == "full":
        console.print(f"[dim]{t('pull.mode.using_full')}[/]")
        return "full"
    if requested == "incremental":
        return "incremental"

    # auto: full se DB vazio, senão pergunta.
    if not db.has_any_data():
        console.print(f"[dim]{t('pull.mode.empty_db')}[/]")
        return "full"

    return _ask_pull_mode()


def _ask_pull_mode() -> Optional[str]:
    """Prompt interativo entre full / incremental / cancelar."""
    options: list[tuple[str, str, str, str]] = [
        ("1", "full", t("pull.mode.full.label"), t("pull.mode.full.desc")),
        (
            "2",
            "incremental",
            t("pull.mode.incremental.label"),
            t("pull.mode.incremental.desc"),
        ),
        ("0", "cancel", t("pull.mode.cancel.label"), t("pull.mode.cancel.desc")),
    ]

    console.print(
        Panel(
            Text(t("pull.mode.title")),
            border_style=ACCENT,
            padding=(0, 1),
        )
    )
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style=f"bold {ACCENT_PINK}", justify="right")
    grid.add_column(style="bold")
    grid.add_column(style="dim")
    for num, _key, label, desc in options:
        grid.add_row(num, label, desc)
    console.print(grid)

    valid = [num for num, _, _, _ in options]
    choice = Prompt.ask(
        f"[{ACCENT_PINK}]›[/]", choices=valid, show_choices=False
    )
    key = next(k for num, k, _, _ in options if num == choice)
    if key == "cancel":
        return None
    return key


def _incremental_constraints(
    db: Database,
    type_name: str,
    mode: str,
    *,
    verbose: bool = True,
) -> tuple[Optional[list[dict]], str]:
    """Constraints do modo incremental + modo efetivo (cai para full sem sync anterior)."""
    if mode != "incremental":
        return None, mode

    since = db.get_last_sync(type_name)
    if not since or not db.type_has_data(type_name):
        if verbose:
            console.print(f"[dim]{t('pull.mode.no_last_sync', type=type_name)}[/]")
        return None, "full"

    if verbose:
        console.print(f"[dim]{t('pull.mode.using_incremental', since=since)}[/]")
    return [
        {
            "key": "Modified Date",
            "constraint_type": "greater than",
            "value": since,
        }
    ], "incremental"


def _pull_one(
    db: Database,
    client: BubbleClient,
    type_name: str,
    *,
    mode: str = "full",
    show_progress: bool = True,
) -> str:
    """Baixa um tipo e devolve a linha-resumo (Rich markup). Só desenha barra se show_progress."""
    constraints, effective_mode = _incremental_constraints(
        db, type_name, mode, verbose=show_progress
    )

    try:
        total = client.count(type_name, constraints=constraints)
    except BubbleAPIError as e:
        return f"[red]✗ {type_name}:[/] {e}"

    if total == 0:
        db.record_sync(type_name)
        key = "pull.incremental.empty" if effective_mode == "incremental" else "pull.empty"
        return f"[dim]{t(key, type=type_name)}[/]"

    progress = None
    task = None
    if show_progress:
        progress = Progress(
            SpinnerColumn(style=ACCENT_PINK),
            TextColumn(f"[bold {ACCENT}]{type_name}[/]"),
            BarColumn(bar_width=None, complete_style=ACCENT, finished_style="green"),
            TextColumn("[cyan]{task.completed}[/]/[dim]{task.total}[/]"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        )
        progress.start()
        task = progress.add_task(type_name, total=total)

    BATCH_SIZE = 200
    batch: list[dict] = []
    count = 0
    try:
        for rec in client.iter_records(type_name, constraints=constraints):
            batch.append(rec)
            count += 1
            if len(batch) >= BATCH_SIZE:
                db.upsert_records(type_name, batch)
                batch.clear()
            if progress is not None:
                progress.update(task, completed=count)
        if batch:
            db.upsert_records(type_name, batch)
            if progress is not None:
                progress.update(task, completed=count)
    except BubbleAPIError as e:
        return f"[red]✗ {type_name}:[/] {e}"
    finally:
        if progress is not None:
            progress.stop()

    db.record_sync(type_name)
    msg_key = "pull.incremental.saved" if effective_mode == "incremental" else "pull.saved"
    return t(msg_key, n=count, type=type_name)


def _pull_parallel(
    db_file: Path,
    config: cfg.Config,
    chosen: list[str],
    mode: str,
    jobs: int,
) -> None:
    """Baixa várias tabelas em paralelo. Cada worker abre a própria conexão SQLite e client;
    o busy_timeout do SQLite serializa as escritas. Só a thread principal toca a barra/console."""

    def worker(type_name: str) -> str:
        db = Database(db_file)
        try:
            with BubbleClient(config) as client:
                return _pull_one(db, client, type_name, mode=mode, show_progress=False)
        except Exception as e:  # ponytail: um worker nunca derruba o pool; vira uma linha vermelha
            return f"[red]✗ {type_name}:[/] {e}"
        finally:
            db.close()

    progress = Progress(
        SpinnerColumn(style=ACCENT_PINK),
        TextColumn(f"[bold {ACCENT}]{t('pull.parallel.label', jobs=jobs)}[/]"),
        BarColumn(bar_width=None, complete_style=ACCENT, finished_style="green"),
        TextColumn("[cyan]{task.completed}[/]/[dim]{task.total}[/]"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )
    with progress:
        task = progress.add_task("pull", total=len(chosen))
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            futures = [ex.submit(worker, tn) for tn in chosen]
            for fut in as_completed(futures):
                console.print(fut.result())
                progress.advance(task)


def _do_status(folder: Path, config: cfg.Config) -> None:
    db_file = folder / config.db_path

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", justify="right")
    grid.add_column()
    grid.add_row(t("status.label.app_id"), f"[bold]{config.app_id}[/]")
    grid.add_row(t("status.label.version"), f"[bold]{config.version}[/]")
    grid.add_row(t("status.label.base_url"), config.base_url)
    grid.add_row(
        t("status.label.api_key"),
        (config.api_key[:6] + "…") if config.api_key else "—",
    )
    grid.add_row(t("status.label.folder"), str(folder))
    grid.add_row(t("status.label.sqlite"), str(db_file))
    grid.add_row(
        t("status.label.db_exists"),
        f"[green]{t('common.yes')}[/]" if db_file.exists() else f"[yellow]{t('common.no')}[/]",
    )

    console.print(
        Panel(
            grid,
            title=f"[bold]{t('status.title')}[/]",
            title_align="left",
            border_style=ACCENT,
            padding=(1, 2),
        )
    )


def _do_settings() -> None:
    """Permite ao usuário trocar idioma e ver onde fica o prefs."""
    console.print(
        Panel(
            Text(t("settings.lang_choose")),
            title=f"[bold]{t('settings.title')}[/]",
            title_align="left",
            border_style=ACCENT,
            padding=(0, 1),
        )
    )

    options: list[tuple[str, str]] = []
    for i, code in enumerate(SUPPORTED, 1):
        marker = " (current)" if code == get_lang() else ""
        options.append((str(i), f"{LANG_LABELS[code]}{marker}"))
    options.append(("0", t("settings.cancel")))

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style=f"bold {ACCENT_PINK}", justify="right")
    grid.add_column()
    for num, label in options:
        grid.add_row(num, label)
    console.print(grid)

    choice = Prompt.ask(
        f"[{ACCENT_PINK}]›[/]",
        choices=[num for num, _ in options],
        show_choices=False,
    )
    if choice == "0":
        return
    new_lang = SUPPORTED[int(choice) - 1]
    set_lang(new_lang)
    prefs = prefs_mod.load_prefs()
    prefs["lang"] = new_lang
    saved = prefs_mod.save_prefs(prefs)
    console.print(f"[green]✓[/] {t('settings.lang_saved', path=saved)}")


def _print_diff(diff: dict) -> None:
    if not (diff["new_types"] or diff["removed_types"] or diff["changed"]):
        console.print(f"[dim]{t('scan.diff.none')}[/]")
        return
    if diff["new_types"]:
        console.print(
            f"[green]{t('scan.diff.new_types')}[/] {', '.join(diff['new_types'])}"
        )
    if diff["removed_types"]:
        console.print(
            f"[yellow]{t('scan.diff.removed_types')}[/] {', '.join(diff['removed_types'])}"
        )
    for type_name, info in diff["changed"].items():
        if info["new"]:
            console.print(
                f"[green]{t('scan.diff.new_fields', type=type_name, names=', '.join(info['new']))}[/]"
            )
        if info["removed"]:
            console.print(
                f"[yellow]{t('scan.diff.removed_fields', type=type_name, names=', '.join(info['removed']))}[/]"
            )


def _interactive_pick(types: list[str]) -> list[str]:
    table = Table(
        title=t("pull.pick.title"),
        title_style=f"bold {ACCENT}",
        border_style=ACCENT_BLUE,
        header_style=f"bold {ACCENT_PINK}",
    )
    table.add_column(t("pull.pick.col_num"), justify="right", style="cyan")
    table.add_column(t("pull.pick.col_type"))
    for i, type_name in enumerate(types, 1):
        table.add_row(str(i), type_name)
    console.print(table)
    raw = Prompt.ask(f"[{ACCENT_PINK}]?[/] {t('pull.pick.prompt')}")
    if raw.strip().lower() == "all":
        return types
    chosen: list[str] = []
    for tok in raw.split(","):
        tok = tok.strip()
        if tok.isdigit() and 1 <= int(tok) <= len(types):
            chosen.append(types[int(tok) - 1])
    return chosen


# ============================================================
# Interactive menu
# ============================================================


def _project_header(folder: Path, config: cfg.Config) -> Panel:
    db_file = folder / config.db_path
    body = Text()
    body.append(t("menu.project"), style="dim")
    body.append(config.app_id, style=f"bold {ACCENT}")
    body.append(f"  ({config.version})", style="dim")
    body.append("\n")
    body.append(t("menu.folder"), style="dim")
    body.append(str(folder))
    body.append("\n")
    body.append(t("menu.db"), style="dim")
    body.append(
        config.db_path,
        style="green" if db_file.exists() else "yellow",
    )
    return Panel(body, border_style=ACCENT_BLUE, padding=(0, 1))


def _no_project_header(folder: Path) -> Panel:
    body = Text()
    body.append(t("menu.no_project") + "\n", style="yellow")
    body.append(t("menu.current_folder"), style="dim")
    body.append(str(folder))
    return Panel(body, border_style="yellow", padding=(0, 1))


def _change_folder(current: Path) -> Path:
    raw = Prompt.ask(
        f"[{ACCENT_PINK}]?[/] {t('menu.folder_prompt')}",
        default="",
        show_default=False,
    )
    if not raw.strip():
        return current
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = (current / candidate).resolve()
    if not candidate.exists() or not candidate.is_dir():
        console.print(f"[red]✗[/] {t('err.folder_missing', path=candidate)}")
        return current
    return candidate


def interactive_menu(starting_folder: Path) -> None:
    """Menu interativo exibido ao rodar `bubble` sem subcomando."""
    print_banner(console, subtitle=t("subtitle.main"))
    console.print()
    _maybe_show_whats_new()
    _maybe_notify_update()

    current = starting_folder
    first = True

    while True:
        if not first:
            console.print()
        first = False

        config: Optional[cfg.Config] = None
        if cfg.exists(current):
            try:
                config = cfg.load(current)
            except Exception as e:
                console.print(f"[red]✗[/] {t('err.config_read', err=e)}")
                config = None

        if config:
            console.print(_project_header(current, config))
            options = [
                ("1", "status", t("menu.label.status"), t("menu.desc.status")),
                ("2", "scan", t("menu.label.scan"), t("menu.desc.scan")),
                ("3", "list", t("menu.label.list"), t("menu.desc.list")),
                ("4", "pull", t("menu.label.pull"), t("menu.desc.pull")),
                ("5", "init", t("menu.label.init"), t("menu.desc.init_existing")),
                ("6", "folder", t("menu.label.folder"), t("menu.desc.folder")),
                ("7", "settings", t("menu.label.settings"), t("menu.desc.settings")),
                ("8", "mcp", t("menu.label.mcp"), t("menu.desc.mcp")),
                ("9", "update", t("menu.label.update"), t("menu.desc.update")),
                ("0", "exit", t("menu.label.exit"), t("menu.desc.exit")),
            ]
        else:
            console.print(_no_project_header(current))
            options = [
                ("1", "init", t("menu.label.init"), t("menu.desc.init_new")),
                ("2", "folder", t("menu.label.folder"), t("menu.desc.folder")),
                ("3", "settings", t("menu.label.settings"), t("menu.desc.settings")),
                ("4", "mcp", t("menu.label.mcp"), t("menu.desc.mcp")),
                ("5", "update", t("menu.label.update"), t("menu.desc.update")),
                ("0", "exit", t("menu.label.exit"), t("menu.desc.exit")),
            ]

        menu = Table.grid(padding=(0, 2))
        menu.add_column(style=f"bold {ACCENT_PINK}", justify="right")
        menu.add_column(style="bold")
        menu.add_column(style="dim")
        for num, _key, label, desc in options:
            menu.add_row(num, label, desc)
        console.print(menu)

        valid = [num for num, _, _, _ in options]
        choice = Prompt.ask(
            f"[{ACCENT_PINK}]›[/]", choices=valid, show_choices=False
        )
        action = next(key for num, key, _, _ in options if num == choice)
        console.print()

        if action == "exit":
            console.print(f"[dim]{t('bye')}[/]")
            return
        if action == "folder":
            current = _change_folder(current)
            continue
        if action == "settings":
            _do_settings()
            continue
        if action == "mcp":
            _do_mcp()
            continue
        if action == "update":
            _do_update()
            continue
        if action == "init":
            new_folder = _do_init(current)
            if new_folder is not None:
                current = new_folder
            continue

        # Demais ações exigem config carregada.
        assert config is not None
        if action == "status":
            _do_status(current, config)
        elif action == "scan":
            _do_scan(current, config)
        elif action == "list":
            _do_list(current, config)
        elif action == "pull":
            _do_pull(current, config)


if __name__ == "__main__":
    cli()
