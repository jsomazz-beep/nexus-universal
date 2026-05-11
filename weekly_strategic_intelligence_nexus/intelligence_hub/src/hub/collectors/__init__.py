"""
Registry de coletores do Intelligence Hub.
Adicione novos coletores aqui para habilitá-los.
"""
from __future__ import annotations

from typing import Any

from hub.collectors.base import BaseCollector
from hub.collectors.gdelt import GDELTCollector
from hub.collectors.guardian import GuardianCollector
from hub.collectors.hackernews import HackerNewsCollector
from hub.collectors.newsapi import NewsAPICollector
from hub.collectors.nytimes import NYTimesCollector
from hub.collectors.reddit import RedditCollector
from hub.collectors.rss import RSSCollector

_REGISTRY: dict[str, type[BaseCollector]] = {
    "rss": RSSCollector,
    "newsapi": NewsAPICollector,
    "gdelt": GDELTCollector,
    "guardian": GuardianCollector,
    "hackernews": HackerNewsCollector,
    "hacker_news": HackerNewsCollector,
    "reddit": RedditCollector,
    "nytimes": NYTimesCollector,
    "ny_times": NYTimesCollector,
}


def build_collector(source_cfg: dict[str, Any], app_cfg: Any) -> BaseCollector:
    """Instancia o coletor correto baseado no campo 'type' da fonte."""
    source_type = source_cfg.get("type", "rss").lower()
    cls = _REGISTRY.get(source_type)
    if cls is None:
        raise ValueError(
            f"Tipo de coletor desconhecido: '{source_type}'. "
            f"Opções: {list(_REGISTRY.keys())}"
        )
    return cls(source_cfg, app_cfg)


def list_collector_types() -> list[str]:
    """Lista todos os tipos de coletor disponíveis."""
    return sorted(_REGISTRY.keys())
