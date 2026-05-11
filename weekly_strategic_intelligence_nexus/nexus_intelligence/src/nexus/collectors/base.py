"""Nexus Intelligence — base collector."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from nexus.models import NewsItem


class Collector(ABC):
    def __init__(self, source_config: dict[str, Any], runtime: dict[str, Any], env: dict[str, str]) -> None:
        self.source_config = source_config
        self.runtime = runtime
        self.env = env
        self.timeout = int(runtime.get("per_source_timeout_seconds", 25))
        self.retries = int(runtime.get("retries", 3))
        ua = env.get("HTTP_USER_AGENT", "NexusIntelligence/2.0")
        self.headers = {"User-Agent": ua}

    @abstractmethod
    def collect(self) -> list[NewsItem]:
        ...
