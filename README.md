# Bubble CLI

A small command-line tool that mirrors a [Bubble.io](https://bubble.io) app's data into a local **SQLite** database via the Bubble Data API. Discover types, pull records, keep a local copy in sync — full or incremental.

Built with [click](https://click.palletsprojects.com/), [httpx](https://www.python-httpx.org/) and [rich](https://rich.readthedocs.io/) for a friendly terminal UI. UI is bilingual (English / Português).

---

## Features

- **Schema discovery** — pulls types and fields from the Bubble Data API `/meta` endpoint and stores them in SQLite alongside the data tables.
- **Field inference fallback** — if `/meta` returns no types, the CLI samples a record per type and infers fields from it.
- **Two sync modes**:
  - **Full update** — re-fetch every record and upsert row by row.
  - **Incremental** — fetch only records with `Modified Date` newer than the previous sync.
- **Schema diff** — every `scan` reports which types and fields were added or removed since the last run.
- **Per-folder projects** — config lives in `bubble.json` next to the SQLite file, so you can keep multiple Bubble apps side by side.
- **Interactive menu** when run without a subcommand, plus scriptable subcommands for CI/automation.
- **Bilingual UI** (English and Brazilian Portuguese) with auto-detection.

## Installation

Requires Python ≥ 3.10.

```bash
pip install .
# or, in editable mode while developing:
pip install -e .
```

This installs the `bubble` console script.

## Quick start

```bash
# 1. Configure a project in the current folder
bubble init

# 2. Discover types/fields from the Bubble Data API
bubble scan

# 3. Pull data into SQLite
bubble pull --all
```

Or run `bubble` with no arguments to use the interactive menu.

## Configuration

`bubble init` walks you through it and writes a `bubble.json` like:

```json
{
  "app_id": "your-app",
  "api_key": "your-bubble-data-api-key",
  "version": "live",
  "db_path": "your-app.sqlite"
}
```

| Field     | Description                                                     |
| --------- | --------------------------------------------------------------- |
| `app_id`  | Your Bubble app subdomain (the `xxx` in `xxx.bubbleapps.io`).   |
| `api_key` | A Data API key generated in Bubble's Settings → API.            |
| `version` | `live` or `test` (uses `/version-test` for the test endpoint).  |
| `db_path` | Relative path to the SQLite file inside the project folder.     |

> The Data API must be enabled in your Bubble app and each type you want to sync must have **"Expose for Data API"** turned on.

## Commands

| Command          | What it does                                                                 |
| ---------------- | ---------------------------------------------------------------------------- |
| `bubble`         | Interactive menu (project picker, scan, pull, settings, …).                  |
| `bubble init`    | Set up a new project (`bubble.json`) in the current folder or a subfolder.   |
| `bubble scan`    | Refresh the schema from the Data API and report a diff.                      |
| `bubble list`    | List discovered types with last sync timestamp and record count.             |
| `bubble pull`    | Download records into SQLite (see modes below).                              |
| `bubble status`  | Show project config and where the SQLite file lives.                         |

### `bubble pull`

```
bubble pull [--types t1,t2 | --all] [--mode auto|full|incremental] [--dry-run]
```

| Flag             | Meaning                                                                                         |
| ---------------- | ----------------------------------------------------------------------------------------------- |
| `--types`        | Comma-separated list of Bubble types to pull (e.g. `--types User,Order`).                       |
| `--all`          | Pull every type known to the local schema.                                                      |
| `--mode auto`    | (default) Full sync if the DB is empty; otherwise prompt full vs incremental.                   |
| `--mode full`    | Re-fetch every record row by row and upsert them.                                               |
| `--mode incremental` | Fetch only records with `Modified Date > last_sync_at`. Falls back to full per-type if there is no previous sync. |
| `--dry-run`      | Hit the API and report counts only — nothing is written to SQLite.                              |

### Sync modes in detail

- **DB empty (file missing or no rows)** → automatic full sync, no prompt.
- **DB already has data** → you'll see a menu:
  1. **Full update** — refetch and upsert everything.
  2. **Incremental** — only records modified since the last sync (`Modified Date > last_sync_at`).
  3. **Cancel** — abort the pull.

For unattended runs (CI, cron) pass `--mode full` or `--mode incremental` to skip the prompt.

## How the SQLite file is organized

The CLI keeps three internal tables alongside your data:

- `_types` — every discovered Bubble type and the matching SQLite table name.
- `_fields` — every field per type, with its Bubble type and SQLite column name.
- `_sync_state` — last sync timestamp and record count per type (used as the cursor for incremental pulls).

Plus one user-data table per Bubble type. Internal Bubble fields (`_id`, `Created Date`, `Modified Date`, `Created By`) are always present; new fields encountered during a pull are added on the fly via `ALTER TABLE`.

## Language

The CLI auto-detects English/Portuguese from your locale on first run. Change it any time with the **Settings** menu (or by setting `BUBBLE_LANG=en|pt`). Your choice is saved per user.

## Development

```bash
pip install -e .
bubble --help
```

The package layout:

```
src/bubble_cli/
  api.py       # Bubble Data API HTTP client (httpx)
  banner.py    # ASCII banner / rich helpers
  cli.py       # click commands + interactive menu
  config.py    # bubble.json read/write
  db.py        # SQLite schema and data writes
  i18n.py      # translations and language detection
  prefs.py     # per-user preferences (language, etc.)
  schema.py    # /meta normalization and field inference
```

## License

No license file is included yet — treat the code as all rights reserved unless you receive permission from the author.
