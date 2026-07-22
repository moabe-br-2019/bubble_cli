"""Internationalization: language detection and string lookup."""
from __future__ import annotations

import locale
import os

DEFAULT_LANG = "en"
SUPPORTED = ("en", "pt")

LANG_LABELS = {
    "en": "English",
    "pt": "Português (Brasil)",
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # General
        "subtitle.main": "Bubble.io Data API → SQLite",
        "subtitle.setup": "New project setup",
        "bye": "Bye.",
        "common.yes": "yes",
        "common.no": "no",
        "common.cancelled": "Cancelled.",

        # Errors
        "err.config_not_found": "bubble.json not found in {folder}. Run init first.",
        "err.config_read": "Failed to read bubble.json: {err}",
        "err.folder_missing": "Folder doesn't exist: {path}",
        "err.unknown_types": "Unknown types: {names}",

        # Menu — context headers
        "menu.no_project": "No project in this folder.",
        "menu.current_folder": "Current folder: ",
        "menu.project": "Project: ",
        "menu.folder": "Folder:  ",
        "menu.db": "DB:      ",

        # Menu items (label + description)
        "menu.label.status": "Status",
        "menu.desc.status": "Show project config",
        "menu.label.scan": "Scan",
        "menu.desc.scan": "Update schema (discover types/fields)",
        "menu.label.list": "List",
        "menu.desc.list": "List discovered types",
        "menu.label.pull": "Pull",
        "menu.desc.pull": "Download data",
        "menu.label.init": "Init",
        "menu.desc.init_existing": "Reconfigure (creates a new bubble.json)",
        "menu.desc.init_new": "Create new project here (or in a subfolder)",
        "menu.label.folder": "Change folder",
        "menu.desc.folder": "Switch to another folder",
        "menu.label.settings": "Settings",
        "menu.desc.settings": "Language and preferences",
        "menu.label.exit": "Exit",
        "menu.desc.exit": "Exit",

        "menu.folder_prompt": "Folder path [dim](relative or absolute, empty = cancel)[/]",

        # Init
        "init.subfolder_q": "Create a subfolder for this project?",
        "init.subfolder_name": "Subfolder name",
        "init.exists_warn": "bubble.json already exists in {target}. Overwrite?",
        "init.app_id": "App ID [dim](bubbleapps.io subdomain — e.g. 'myapp')[/]",
        "init.app_id_hint": "Tip: you can also find your app id in the editor URL:",
        "init.version": "Version",
        "init.api_key": "API key [dim](Data API)[/]",
        "init.testing": "Testing connection to /meta...",
        "init.conn_ok": "Connection OK.",
        "init.save_anyway": "Save config anyway?",
        "init.panel_title": "Project configured",
        "init.label.app_id": "App ID",
        "init.label.version": "Version",
        "init.label.base_url": "Base URL",
        "init.label.sqlite": "SQLite",
        "init.label.config": "Config",
        "init.run_scan_q": "Run [bold]scan[/] now?",

        # Scan
        "scan.fetching": "Fetching schema from /meta...",
        "scan.fetch_error": "Error fetching /meta: {err}",
        "scan.no_types": "/meta returned no types. Provide type names to infer the schema from a sample record.",
        "scan.types_prompt": "Types (comma-separated)",
        "scan.inferring": "Inferring {name}...",
        "scan.meta_dumped": "raw meta saved to {path}",
        "scan.done": "Schema updated. [bold {accent}]{n}[/] types total.",
        "scan.diff.none": "No schema changes.",
        "scan.diff.new_types": "+ New types:",
        "scan.diff.removed_types": "~ Types removed from API [dim](kept in DB)[/]:",
        "scan.diff.new_fields": "+ {type}: new fields {names}",
        "scan.diff.removed_fields": "~ {type}: removed fields {names}",

        # List
        "list.title": "Discovered types",
        "list.col.type": "Type",
        "list.col.last_sync": "Last sync",
        "list.col.count": "Records",
        "list.empty": "No types discovered. Run [bold {accent_blue}]scan[/] first.",

        # Pull
        "pull.schema_empty": "Schema empty. Run [bold {accent_blue}]scan[/] first.",
        "pull.dry_run_warn": "DRY-RUN — nothing will be written to SQLite.",
        "pull.counting": "Counting {type}...",
        "pull.dry_count": "{type}: [cyan]{n}[/] records available",
        "pull.empty": "{type}: empty.",
        "pull.saved": "  [green]✓[/] [bold]{n}[/] records saved to [dim]{type}[/]",
        "pull.pick.title": "Select types to download",
        "pull.pick.col_num": "#",
        "pull.pick.col_type": "Type",
        "pull.pick.prompt": "Types [dim](e.g. '1,3,5' or 'all')[/]",
        "pull.nothing_selected": "Nothing selected.",
        # Pull — sync modes
        "pull.mode.empty_db": "Database empty — running a [bold]full sync[/].",
        "pull.mode.title": "DB already has data. How do you want to sync?",
        "pull.mode.full.label": "Full update",
        "pull.mode.full.desc": "Re-fetch every record row by row (upsert).",
        "pull.mode.incremental.label": "Incremental",
        "pull.mode.incremental.desc": "Only records modified since the last sync.",
        "pull.mode.cancel.label": "Cancel",
        "pull.mode.cancel.desc": "Abort the pull.",
        "pull.mode.using_full": "Mode: [bold]full update[/].",
        "pull.mode.using_incremental": "Mode: [bold]incremental[/] (since {since}).",
        "pull.mode.no_last_sync": "{type}: no previous sync found — falling back to full.",
        "pull.incremental.empty": "{type}: no changes since last sync.",
        "pull.incremental.saved": "  [green]✓[/] [bold]{n}[/] new/modified records merged into [dim]{type}[/]",
        "pull.parallel.label": "Downloading tables ({jobs} in parallel)",

        # Status
        "status.title": "Bubble CLI — Status",
        "status.label.app_id": "App ID",
        "status.label.version": "Version",
        "status.label.base_url": "Base URL",
        "status.label.api_key": "API key",
        "status.label.folder": "Folder",
        "status.label.sqlite": "SQLite",
        "status.label.db_exists": "DB exists?",

        # Settings
        "settings.title": "Settings",
        "settings.lang_choose": "Choose language",
        "settings.lang_saved": "Language saved to {path}",
        "settings.cancel": "Cancel",

        # Update
        "update.available": "New version {latest} available (you have {current}).",
        "update.prompt": "Update now?",
        "update.updating": "Updating…",
        "update.done": "Updated. Restart the command to use the new version.",
        "update.failed": "Auto-update failed. Update manually:\n  {cmd}",
        "update.up_to_date": "Already on the latest version ({current}).",
        "whatsnew.title": "What's new in {version}",
        "menu.label.update": "Update",
        "menu.desc.update": "Check for and install a new version",

        # MCP
        "menu.label.mcp": "MCP",
        "menu.desc.mcp": "Use this CLI from AI clients (setup guide)",
        "mcp.title": "MCP server",
        "mcp.what": "Expose this CLI as a tool for AI clients (Claude Code, Claude Desktop...):\nthe AI runs scan, list, pull etc. for you.",
        "mcp.step_install": "Install the MCP SDK:",
        "mcp.step_register": "Register the server (Claude Code example):",
        "mcp.step_use": "Restart the AI client and ask things like \"list my Bubble types\".",
    },
    "pt": {
        # General
        "subtitle.main": "Bubble.io Data API → SQLite",
        "subtitle.setup": "Setup de novo projeto",
        "bye": "Tchau.",
        "common.yes": "sim",
        "common.no": "não",
        "common.cancelled": "Cancelado.",

        # Errors
        "err.config_not_found": "bubble.json não encontrado em {folder}. Rode init primeiro.",
        "err.config_read": "Falha ao ler bubble.json: {err}",
        "err.folder_missing": "Pasta não existe: {path}",
        "err.unknown_types": "Tipos desconhecidos: {names}",

        # Menu — context headers
        "menu.no_project": "Sem projeto nesta pasta.",
        "menu.current_folder": "Pasta atual: ",
        "menu.project": "Projeto: ",
        "menu.folder": "Pasta:   ",
        "menu.db": "DB:      ",

        # Menu items
        "menu.label.status": "Status",
        "menu.desc.status": "Ver config do projeto",
        "menu.label.scan": "Scan",
        "menu.desc.scan": "Atualizar schema (descobrir tipos/campos)",
        "menu.label.list": "List",
        "menu.desc.list": "Listar tipos descobertos",
        "menu.label.pull": "Pull",
        "menu.desc.pull": "Baixar dados",
        "menu.label.init": "Init",
        "menu.desc.init_existing": "Reconfigurar (cria novo bubble.json)",
        "menu.desc.init_new": "Criar novo projeto aqui (ou em subpasta)",
        "menu.label.folder": "Mudar pasta",
        "menu.desc.folder": "Trocar de pasta",
        "menu.label.settings": "Preferências",
        "menu.desc.settings": "Idioma e preferências",
        "menu.label.exit": "Sair",
        "menu.desc.exit": "Sair",

        "menu.folder_prompt": "Caminho da pasta [dim](relativo ou absoluto, vazio = cancelar)[/]",

        # Init
        "init.subfolder_q": "Criar uma subpasta para este projeto?",
        "init.subfolder_name": "Nome da subpasta",
        "init.exists_warn": "Já existe bubble.json em {target}. Sobrescrever?",
        "init.app_id": "App ID [dim](subdomínio de bubbleapps.io — ex: 'meuapp')[/]",
        "init.app_id_hint": "Dica: você também encontra o app id na URL do editor:",
        "init.version": "Versão",
        "init.api_key": "API key [dim](Data API)[/]",
        "init.testing": "Testando conexão com /meta...",
        "init.conn_ok": "Conexão OK.",
        "init.save_anyway": "Salvar config mesmo assim?",
        "init.panel_title": "Projeto configurado",
        "init.label.app_id": "App ID",
        "init.label.version": "Versão",
        "init.label.base_url": "Base URL",
        "init.label.sqlite": "SQLite",
        "init.label.config": "Config",
        "init.run_scan_q": "Rodar [bold]scan[/] agora?",

        # Scan
        "scan.fetching": "Buscando schema via /meta...",
        "scan.fetch_error": "Erro ao buscar /meta: {err}",
        "scan.no_types": "/meta não retornou tipos. Informe os nomes dos tipos para inferir o schema a partir de um registro de exemplo.",
        "scan.types_prompt": "Tipos (separados por vírgula)",
        "scan.inferring": "Inferindo {name}...",
        "scan.meta_dumped": "meta cru salvo em {path}",
        "scan.done": "Schema atualizado. [bold {accent}]{n}[/] tipos no total.",
        "scan.diff.none": "Nenhuma mudança no schema.",
        "scan.diff.new_types": "+ Novos tipos:",
        "scan.diff.removed_types": "~ Tipos sumiram da API [dim](mantidos no DB)[/]:",
        "scan.diff.new_fields": "+ {type}: novos campos {names}",
        "scan.diff.removed_fields": "~ {type}: campos removidos {names}",

        # List
        "list.title": "Tipos descobertos",
        "list.col.type": "Type",
        "list.col.last_sync": "Último sync",
        "list.col.count": "Registros",
        "list.empty": "Nenhum tipo descoberto. Rode [bold {accent_blue}]scan[/] primeiro.",

        # Pull
        "pull.schema_empty": "Schema vazio. Rode [bold {accent_blue}]scan[/] antes.",
        "pull.dry_run_warn": "DRY-RUN — nada será gravado no SQLite.",
        "pull.counting": "Contando {type}...",
        "pull.dry_count": "{type}: [cyan]{n}[/] registros disponíveis",
        "pull.empty": "{type}: vazio.",
        "pull.saved": "  [green]✓[/] [bold]{n}[/] registros gravados em [dim]{type}[/]",
        "pull.pick.title": "Selecione tipos pra baixar",
        "pull.pick.col_num": "#",
        "pull.pick.col_type": "Type",
        "pull.pick.prompt": "Tipos [dim](ex: '1,3,5' ou 'all')[/]",
        "pull.nothing_selected": "Nada selecionado.",
        # Pull — modos de sync
        "pull.mode.empty_db": "Banco vazio — rodando [bold]sync completo[/].",
        "pull.mode.title": "Banco já tem dados. Como você quer sincronizar?",
        "pull.mode.full.label": "Atualização completa",
        "pull.mode.full.desc": "Refaz tudo, registro por registro (upsert).",
        "pull.mode.incremental.label": "Incremental",
        "pull.mode.incremental.desc": "Apenas registros modificados desde o último sync.",
        "pull.mode.cancel.label": "Cancelar",
        "pull.mode.cancel.desc": "Aborta o pull.",
        "pull.mode.using_full": "Modo: [bold]atualização completa[/].",
        "pull.mode.using_incremental": "Modo: [bold]incremental[/] (desde {since}).",
        "pull.mode.no_last_sync": "{type}: sem sync anterior — caindo para modo completo.",
        "pull.incremental.empty": "{type}: nada novo desde o último sync.",
        "pull.incremental.saved": "  [green]✓[/] [bold]{n}[/] registros novos/modificados aplicados em [dim]{type}[/]",
        "pull.parallel.label": "Baixando tabelas ({jobs} em paralelo)",

        # Status
        "status.title": "Bubble CLI — Status",
        "status.label.app_id": "App ID",
        "status.label.version": "Versão",
        "status.label.base_url": "Base URL",
        "status.label.api_key": "API key",
        "status.label.folder": "Pasta",
        "status.label.sqlite": "SQLite",
        "status.label.db_exists": "DB existe?",

        # Settings
        "settings.title": "Preferências",
        "settings.lang_choose": "Escolha o idioma",
        "settings.lang_saved": "Idioma salvo em {path}",
        "settings.cancel": "Cancelar",

        # Update
        "update.available": "Nova versão {latest} disponível (você tem {current}).",
        "update.prompt": "Atualizar agora?",
        "update.updating": "Atualizando…",
        "update.done": "Atualizado. Rode o comando de novo para usar a nova versão.",
        "update.failed": "Auto-update falhou. Atualize manualmente:\n  {cmd}",
        "update.up_to_date": "Você já está na versão mais recente ({current}).",
        "whatsnew.title": "Novidades da versão {version}",
        "menu.label.update": "Atualizar",
        "menu.desc.update": "Verificar e instalar nova versão",

        # MCP
        "menu.label.mcp": "MCP",
        "menu.desc.mcp": "Usar esta CLI a partir de clientes de IA (guia de setup)",
        "mcp.title": "Servidor MCP",
        "mcp.what": "Expõe esta CLI como ferramenta para clientes de IA (Claude Code, Claude Desktop...):\na IA roda scan, list, pull etc. por você.",
        "mcp.step_install": "Instale o SDK do MCP:",
        "mcp.step_register": "Registre o servidor (exemplo com Claude Code):",
        "mcp.step_use": "Reinicie o cliente de IA e peça coisas como \"liste meus types do Bubble\".",
    },
}

_current_lang = DEFAULT_LANG


def detect_lang() -> str:
    """Detecta idioma do SO/env. pt-BR e variantes → 'pt'; resto → 'en'."""
    candidates: list[str | None] = [
        os.environ.get("BUBBLE_LANG"),
        os.environ.get("LC_ALL"),
        os.environ.get("LANG"),
        os.environ.get("LANGUAGE"),
    ]
    try:
        candidates.append(locale.getlocale()[0])
    except Exception:
        pass

    for raw in candidates:
        if not raw:
            continue
        c = raw.lower()
        if c.startswith("pt") or "portuguese" in c:
            return "pt"
        if c.startswith("en") or "english" in c:
            return "en"
    return DEFAULT_LANG


def set_lang(lang: str) -> None:
    global _current_lang
    if lang in TRANSLATIONS:
        _current_lang = lang


def get_lang() -> str:
    return _current_lang


def t(key: str, **kwargs: object) -> str:
    """Lookup traduzido. Faz fallback para inglês, depois para a chave crua."""
    text = (
        TRANSLATIONS.get(_current_lang, {}).get(key)
        or TRANSLATIONS["en"].get(key)
        or key
    )
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
