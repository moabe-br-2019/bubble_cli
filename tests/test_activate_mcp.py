import shutil

from bubble_cli import cli


def test_no_claude_cli_shows_manual_cmd(monkeypatch, capsys):
    # SDK presente (mcp está instalado no ambiente de dev) + claude ausente:
    # deve instruir registro manual sem tentar subprocess.
    monkeypatch.setattr(shutil, "which", lambda _: None)
    cli._activate_mcp()
    out = capsys.readouterr().out
    assert "claude mcp add bubble" in out
