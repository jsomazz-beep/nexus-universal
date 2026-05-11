"""
Classe base para coletores de notícias.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from hub.models import NewsItem

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Interface comum para todos os coletores."""

    def __init__(self, source_cfg: dict[str, Any], app_cfg: Any) -> None:
        self.source_cfg = source_cfg
        self.app_cfg = app_cfg
        self.source_id: str = source_cfg.get("id", "unknown")
        self.source_name: str = source_cfg.get("name", source_cfg.get("id", "unknown"))
        self.region_hint: str = source_cfg.get("region_hint", "")
        self.logger = logging.getLogger(f"collector.{self.source_id}")

    @abstractmethod
    def collect(self) -> list[NewsItem]:
        """Coleta e retorna lista de NewsItem."""
        ...

    def _safe_collect(self) -> list[NewsItem]:
        try:
            return self.collect()
        except Exception as exc:
            self.logger.warning("Erro ao coletar %s: %s", self.source_id, exc)
            return []

    @property
    def timeout(self) -> int:
        return int(self.app_cfg.runtime.get("per_source_timeout_seconds", 20))

    @property
    def user_agent(self) -> str:
        return self.app_cfg.env.get(
            "HTTP_USER_AGENT",
            "IntelligenceHub/2.0 (+https://github.com/intelligence-hub)",
        )

    def _default_headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept": "application/json, text/html"}
