"""Nexus Intelligence — configuration loader."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class AppConfig:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    @property
    def project(self) -> dict[str, Any]:
        return self.raw.get("project", {})

    @property
    def monitoring(self) -> dict[str, Any]:
        return self.raw.get("monitoring", {})

    @property
    def topics(self) -> dict[str, Any]:
        return self.monitoring.get("topics", {})

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
    def runtime(self) -> dict[str, Any]:
        return self.raw.get("runtime", {})


def load_config(path: str | Path) -> AppConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    return AppConfig(raw=raw or {})
