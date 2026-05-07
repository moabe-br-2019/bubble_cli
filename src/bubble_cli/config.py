"""Per-folder config for a Bubble app project."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

CONFIG_FILENAME = "bubble.json"


@dataclass
class Config:
    app_id: str
    api_key: str
    version: str = "live"
    db_path: str = "bubble.sqlite"

    @property
    def base_url(self) -> str:
        version_segment = "" if self.version == "live" else "/version-test"
        return f"https://{self.app_id}.bubbleapps.io{version_segment}/api/1.1"


def config_path(folder: Path) -> Path:
    return folder / CONFIG_FILENAME


def load(folder: Path) -> Config:
    path = config_path(folder)
    if not path.exists():
        raise FileNotFoundError(
            f"bubble.json não encontrado em {folder}. Rode `bubble init` primeiro."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return Config(**data)


def save(folder: Path, config: Config) -> Path:
    path = config_path(folder)
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
    return path


def exists(folder: Path) -> bool:
    return config_path(folder).exists()
