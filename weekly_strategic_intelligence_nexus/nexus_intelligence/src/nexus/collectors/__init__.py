"""Nexus Intelligence — collectors package."""
from __future__ import annotations

from nexus.collectors.base import Collector
from nexus.collectors.rss_collector import RSSCollector
from nexus.collectors.hackernews_collector import HackerNewsCollector
from nexus.collectors.reddit_collector import RedditCollector
from nexus.collectors.newsapi_collector import NewsAPICollector


def build_collector(source: dict, runtime: dict, env: dict) -> Collector:
    source_type = source.get("type", "rss").lower()
    if source_type == "rss":
        return RSSCollector(source, runtime, env)
    if source_type == "hackernews":
        return HackerNewsCollector(source, runtime, env)
    if source_type == "reddit":
        return RedditCollector(source, runtime, env)
    if source_type == "newsapi":
        return NewsAPICollector(source, runtime, env)
    raise ValueError(f"Unknown collector type: {source_type}")
