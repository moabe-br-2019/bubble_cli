from bubble_cli import config
from bubble_cli.cli import _do_export
from bubble_cli.db import Database


def _project(tmp_path):
    cfg = config.Config(app_id="app", api_key="k")
    config.save(tmp_path, cfg)
    with Database(tmp_path / cfg.db_path) as db:
        db.upsert_schema({"Item": {"name": "text"}, "Empty": {}})
        db.upsert_records("Item", [{"_id": "1", "name": "Ação"}, {"_id": "2", "name": "b"}])
    return cfg


def test_export_writes_csv_skips_empty(tmp_path):
    cfg = _project(tmp_path)
    _do_export(tmp_path, cfg)
    out = tmp_path / "exports"
    files = sorted(p.name for p in out.glob("*.csv"))
    assert files == ["Item.csv"]  # tabela vazia não gera arquivo
    text = (out / "Item.csv").read_text(encoding="utf-8-sig")
    assert "Ação" in text and text.splitlines()[0].startswith("_id")


def test_export_unknown_type_writes_nothing(tmp_path):
    cfg = _project(tmp_path)
    _do_export(tmp_path, cfg, types_csv="Nope")
    assert not (tmp_path / "exports").exists()
