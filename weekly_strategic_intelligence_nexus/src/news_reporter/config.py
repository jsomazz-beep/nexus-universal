from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AppConfig:
    raw: dict[str, Any]

    @property
    def project(self) -> dict[str, Any]:
        return self.raw.get("project", {})

    @property
    def monitoring(self) -> dict[str, Any]:
        return self.raw.get("monitoring", {})

    @property
    def filters(self) -> dict[str, Any]:
        return self.raw.get("filters", {})

    @property
    def deduplication(self) -> dict[str, Any]:
        return self.raw.get("deduplication", {})

    @property
    def scoring(self) -> dict[str, Any]:
        return self.raw.get("scoring", {})

    @property
    def sources(self) -> list[dict[str, Any]]:
        return self.raw.get("sources", [])

    @property
    def email(self) -> dict[str, Any]:
        return self.raw.get("email", {})

    @property
    def runtime(self) -> dict[str, Any]:
        return self.raw.get("runtime", {})


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return AppConfig(raw=data)
