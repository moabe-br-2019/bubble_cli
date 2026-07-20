"""O --dry-run tem que contar o mesmo recorte que o pull real.

Regressão: o preview forçava mode="full" e chamava count() sem constraints, então
anunciava o total da tabela inteira mesmo com --mode incremental.

Rodar: PYTHONPATH=src python tests/test_dry_run_mode.py
"""
import tempfile
from pathlib import Path

from bubble_cli import cli
from bubble_cli.config import Config
from bubble_cli.db import Database


class _FakeClient:
    """Captura as chamadas de count() para inspeção."""

    def __init__(self, *_, **__):
        self.calls: list[tuple[str, object]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def count(self, type_name, constraints=None):
        self.calls.append((type_name, constraints))
        return 159


def _project(tmp: Path, *, with_sync: bool) -> Config:
    """Pasta de projeto com o tipo Thing já no schema, opcionalmente com sync anterior."""
    config = Config(app_id="x", api_key="k")
    db = Database(tmp / config.db_path)
    try:
        db.upsert_schema({"Thing": {"Name": "text"}})
        if with_sync:
            db.upsert_records("Thing", [{"_id": "a", "Name": "n"}])
            db.record_sync("Thing")
    finally:
        db.close()
    return config


def _run_dry(config: Config, folder: Path, mode: str) -> _FakeClient:
    captured = {}

    def factory(cfg):
        captured["client"] = _FakeClient()
        return captured["client"]

    original = cli.BubbleClient
    cli.BubbleClient = factory
    try:
        cli._do_pull(folder, config, types_csv="Thing", dry_run=True, mode=mode)
    finally:
        cli.BubbleClient = original
    return captured["client"]


def test_dry_run_incremental_passa_constraints():
    tmp = Path(tempfile.mkdtemp())
    config = _project(tmp, with_sync=True)

    client = _run_dry(config, tmp, "incremental")

    assert len(client.calls) == 1, client.calls
    type_name, constraints = client.calls[0]
    assert type_name == "Thing"
    assert constraints, "dry-run incremental contou sem constraints (bug do preview)"
    assert constraints[0]["key"] == "Modified Date"
    assert constraints[0]["constraint_type"] == "greater than"
    assert constraints[0]["value"], "constraint sem timestamp de last_sync"


def test_dry_run_full_conta_sem_constraints():
    tmp = Path(tempfile.mkdtemp())
    config = _project(tmp, with_sync=True)

    client = _run_dry(config, tmp, "full")

    assert client.calls == [("Thing", None)], client.calls


def test_dry_run_incremental_sem_sync_anterior_cai_para_full():
    """Sem last_sync não há recorte possível — preview e pull real concordam em full."""
    tmp = Path(tempfile.mkdtemp())
    config = _project(tmp, with_sync=False)

    client = _run_dry(config, tmp, "incremental")

    assert client.calls == [("Thing", None)], client.calls


def test_dry_run_auto_nao_pergunta_nada():
    """Preview em auto não pode abrir prompt interativo."""
    tmp = Path(tempfile.mkdtemp())
    config = _project(tmp, with_sync=True)

    def _boom():
        raise AssertionError("dry-run não deveria perguntar o modo")

    original = cli._ask_pull_mode
    cli._ask_pull_mode = _boom
    try:
        client = _run_dry(config, tmp, "auto")
    finally:
        cli._ask_pull_mode = original

    assert client.calls == [("Thing", None)], client.calls


if __name__ == "__main__":
    test_dry_run_incremental_passa_constraints()
    test_dry_run_full_conta_sem_constraints()
    test_dry_run_incremental_sem_sync_anterior_cai_para_full()
    test_dry_run_auto_nao_pergunta_nada()
    print("OK: dry-run respeita o modo e conta o mesmo recorte do pull")
