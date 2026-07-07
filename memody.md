# Sessão de trabalho — bubble_cli

Data: 2026-05-07

Resumo do que foi feito, em ordem cronológica.

---

## 1. Modos de sync no `bubble pull` (auto / full / incremental)

### Comportamento

- **DB inexistente ou vazio** → roda full sync direto, sem perguntar.
- **DB já tem dados** → menu interativo:
  1. **Atualização completa** — refaz registro a registro (upsert em tudo).
  2. **Incremental** — apenas registros com `Modified Date > last_sync_at`.
  3. **Cancelar** — aborta o pull.
- Por tipo: se incremental for escolhido mas o tipo nunca foi sincronizado (sem `last_sync_at`), cai automaticamente para full nesse tipo (com aviso).
- CLI não-interativo: nova flag `--mode {auto,full,incremental}` (default `auto`).

### Arquivos tocados

- **`src/bubble_cli/db.py`**
  - Novos helpers: `has_any_data()`, `type_has_data()`, `count_records()`, `get_last_sync()`.
  - `record_sync()` agora aceita `count=None` e calcula a partir da tabela.
- **`src/bubble_cli/api.py`**
  - `count()` aceita `constraints: list[dict] | None` (necessário para contar só os registros novos no modo incremental).
- **`src/bubble_cli/cli.py`**
  - Flag `--mode` no `pull`.
  - `_resolve_pull_mode(db, requested)` resolve auto vs explícito.
  - `_ask_pull_mode()` mostra o painel com as 3 opções (full/incremental/cancelar).
  - `_pull_one(..., mode=...)` monta a constraint `Modified Date > last_sync_at` quando incremental.
- **`src/bubble_cli/i18n.py`**
  - Strings PT/EN: `pull.mode.empty_db`, `pull.mode.title`, `pull.mode.full.label/desc`, `pull.mode.incremental.label/desc`, `pull.mode.cancel.label/desc`, `pull.mode.using_full`, `pull.mode.using_incremental`, `pull.mode.no_last_sync`, `pull.incremental.empty`, `pull.incremental.saved`.

### Detalhe técnico

- O cursor incremental é o `last_sync_at` salvo em `_sync_state` (UTC ISO).
- O timestamp novo só é gravado depois do pull bem sucedido — se algo for modificado durante o pull, é capturado na próxima rodada (upsert idempotente).

---

## 2. README em inglês + publicação no GitHub

### Criados

- **`README.md`** — features, install, comandos, layout do SQLite, modos de sync, idioma, dev layout, license.
- **`.gitignore`** — Python (`__pycache__`, `dist/`, venvs), Claude (`.claude/`), e artefatos locais do CLI (`bubble.json`, `*.sqlite*`).

### Git

- `git init` + branch `main`.
- `remote origin` → `https://github.com/moabe-br-2019/bubble_cli.git`.
- Commit inicial **`1c8a328`** — "Initial commit: Bubble.io Data API → SQLite CLI".
- Push para `origin/main`.

---

## 3. Licença MIT + seção de instalação detalhada

### Criados/alterados

- **`LICENSE`** (novo) — MIT, © 2026 Moabe.
- **`README.md`** — seção *Installation* reescrita: prerequisites (Python 3.10+, pip), 3 caminhos de instalação (`pipx` recomendado, clone editável, `pip install git+...`), verify, upgrade, uninstall, nota Windows sobre Unicode.
- **`README.md`** — seção *License* aponta para o arquivo (`[MIT](LICENSE) © 2026 Moabe`).
- **`pyproject.toml`** — `readme = "README.md"` e `license = { file = "LICENSE" }`.

### Git

- Commit **`a3eaad4`** — "Add MIT license, expand README installation section".
- Push para `origin/main`.

### Decisão sobre licença

Recomendei MIT por ser curtíssima, super permissiva (uso comercial OK, atribuição mínima), padrão para CLIs Python. Alternativas consideradas: Apache 2.0 (igual + cláusula de patentes, mais texto) e GPLv3 (copyleft forte — descartado). Escolha final: **MIT**.

---

## Estado atual do repo

- Branch: `main` em sincronia com `origin/main`.
- Últimos commits:
  - `a3eaad4` Add MIT license, expand README installation section
  - `1c8a328` Initial commit: Bubble.io Data API → SQLite CLI
- Arquivos públicos: `LICENSE`, `README.md`, `.gitignore`, `pyproject.toml`, `src/bubble_cli/*.py`.
- Não publicado (gitignored): `.claude/`, `bubble.json`, `*.sqlite*`, `__pycache__/`.
- Este arquivo (`memody.md`) **não foi commitado** — fica só local.
