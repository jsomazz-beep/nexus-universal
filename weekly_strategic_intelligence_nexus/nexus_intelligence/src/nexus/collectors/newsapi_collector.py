"""Nexus Intelligence — NewsAPI collector (requires API key)."""
from __future__ import annotations

import requests

from nexus.collectors.base import Collector
from nexus.models import NewsItem
from nexus.utils.text import now_utc, parse_datetime, strip_html


class NewsAPICollector(Collector):
    def collect(self) -> list[NewsItem]:
        api_key = self.env.get("NEWSAPI_KEY", "")
        if not api_key:
            return []

        endpoint = self.source_config.get("endpoint", "https://newsapi.org/v2/everything")
        query = self.source_config.get("query", "")
        max_items = int(self.source_config.get("max_items", 50))
        authority = int(self.source_config.get("authority", 8))

        params = {
            "q": query,
            "language": self.source_config.get("language", ""),
            "pageSize": min(max_items, 100),
            "sortBy": "publishedAt",
            "apiKey": api_key,
        }
        params = {k: v for k, v in params.items() if v}

        try:
            r = requests.get(endpoint, params=params, timeout=self.timeout, headers=self.headers)
            r.raise_for_status()
            data = r.json()
        except Exception:
            return []

        items: list[NewsItem] = []
        for article in data.get("articles", []):
            title = (article.get("title") or "").strip()
            if not title or title == "[Removed]":
                continue
            items.append(NewsItem(
                source_id=self.source_config.get("id", "newsapi"),
                source_name=article.get("source", {}).get("name") or "NewsAPI",
                source_authority=authority,
                title=title,
                url=article.get("url") or "",
                published_at=parse_datetime(article.get("publishedAt")),
                collected_at=now_utc(),
                description=strip_html(article.get("description") or ""),
                content=strip_html(article.get("content") or article.get("description") or ""),
                image_url=article.get("urlToImage"),
                metadata={
                    "region_hint": self.source_config.get("region_hint", "Global"),
                    "source_type": "newsapi",
                },
            ))
        return items
