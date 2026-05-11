from __future__ import annotations

from news_reporter.collectors.base import Collector
from news_reporter.collectors.html_collector import HTMLCollector
from news_reporter.collectors.newsapi_collector import NewsAPICollector
from news_reporter.collectors.rss_collector import RSSCollector


def build_collector(source_cfg: dict, runtime_cfg: dict, env: dict[str, str]) -> Collector:
    source_type = source_cfg.get("type", "rss").lower()
    if source_type == "rss":
        return RSSCollector(source_cfg, runtime_cfg, env)
    if source_type == "newsapi":
        return NewsAPICollector(source_cfg, runtime_cfg, env)
    if source_type == "html":
        return HTMLCollector(source_cfg, runtime_cfg, env)
    raise ValueError(f"Tipo de fonte não suportado: {source_type}")
