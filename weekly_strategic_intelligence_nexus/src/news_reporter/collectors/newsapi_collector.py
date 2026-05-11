from __future__ import annotations

from news_reporter.collectors.base import Collector
from news_reporter.models import NewsItem
from news_reporter.utils.http import http_get_json
from news_reporter.utils.text import now_utc, parse_datetime


class NewsAPICollector(Collector):
    def collect(self) -> list[NewsItem]:
        api_key = self.env.get("NEWSAPI_KEY", "")
        if not api_key:
            raise RuntimeError("NEWSAPI_KEY não definido no .env")

        endpoint = self.source_config["endpoint"]
        timeout = int(self.runtime_config.get("per_source_timeout_seconds", 20))
        retries = int(self.runtime_config.get("retries", 2))
        backoff = int(self.runtime_config.get("retry_backoff_seconds", 2))

        params = {
            "q": self.source_config.get("query", ""),
            "language": self.source_config.get("language", ""),
            "sortBy": "publishedAt",
            "pageSize": 100,
            "apiKey": api_key,
        }

        payload = http_get_json(
            endpoint,
            params=params,
            headers={"Accept": "application/json"},
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff,
        )

        articles = payload.get("articles", [])
        items: list[NewsItem] = []
        for article in articles:
            items.append(
                NewsItem(
                    source_id=self.source_config.get("id", "newsapi"),
                    source_name=(article.get("source", {}) or {}).get("name", "NewsAPI"),
                    title=(article.get("title") or "").strip(),
                    subtitle=None,
                    url=(article.get("url") or "").strip(),
                    published_at=parse_datetime(article.get("publishedAt")),
                    collected_at=now_utc(),
                    raw_language=self.source_config.get("language") or None,
                    description=article.get("description"),
                    content=article.get("content") or article.get("description") or article.get("title") or "",
                    image_url=article.get("urlToImage"),
                    tags=[],
                    metadata={
                        "source_type": "newsapi",
                        "author": article.get("author"),
                        "region_hint": self.source_config.get("region_hint", ""),
                    },
                )
            )
        return items
