"""
Coletor NewsAPI.org — agregador de notícias premium.
Plano gratuito: 100 requisições/dia.
Chave em: https://newsapi.org/register
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests
from dateutil import parser as dateutil_parser

from hub.collectors.base import BaseCollector
from hub.models import NewsItem

logger = logging.getLogger(__name__)

NEWSAPI_EVERYTHING = "https://newsapi.org/v2/everything"
NEWSAPI_TOP = "https://newsapi.org/v2/top-headlines"


class NewsAPICollector(BaseCollector):
    """Coleta notícias via NewsAPI.org."""

    def collect(self) -> list[NewsItem]:
        api_key = self.app_cfg.newsapi_key
        if not api_key:
            logger.debug("NewsAPI %s: sem chave, pulando.", self.source_id)
            return []

        endpoint = self.source_cfg.get("endpoint", NEWSAPI_EVERYTHING)
        query = self.source_cfg.get("query", "")
        language = self.source_cfg.get("language", "")
        sort_by = self.source_cfg.get("sort_by", "publishedAt")
        page_size = int(self.source_cfg.get("page_size", 50))
        sources = self.source_cfg.get("news_sources", "")  # Ex: "bbc-news,reuters"
        domains = self.source_cfg.get("domains", "")  # Ex: "reuters.com,bloomberg.com"
        country = self.source_cfg.get("country", "")

        params: dict[str, Any] = {
            "apiKey": api_key,
            "pageSize": page_size,
            "sortBy": sort_by,
        }
        if query:
            params["q"] = query
        if language:
            params["language"] = language
        if sources:
            params["sources"] = sources
        if domains:
            params["domains"] = domains
        if country and "top-headlines" in endpoint:
            params["country"] = country

        try:
            resp = requests.get(endpoint, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("NewsAPI %s erro: %s", self.source_id, exc)
            return []

        if data.get("status") != "ok":
            logger.warning("NewsAPI %s: status=%s msg=%s", self.source_id,
                           data.get("status"), data.get("message"))
            return []

        articles = data.get("articles", [])
        items: list[NewsItem] = []
        for art in articles:
            item = self._parse_article(art)
            if item:
                items.append(item)

        logger.info("NewsAPI %s: %d artigos", self.source_id, len(items))
        return items

    def _parse_article(self, art: dict[str, Any]) -> NewsItem | None:
        title = (art.get("title") or "").strip()
        url = (art.get("url") or "").strip()
        if not title or not url or title == "[Removed]":
            return None

        pub_dt: datetime | None = None
        raw_date = art.get("publishedAt", "")
        if raw_date:
            try:
                pub_dt = dateutil_parser.parse(raw_date)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        source_info = art.get("source", {})
        source_name = source_info.get("name", self.source_name) or self.source_name
        content = art.get("content") or art.get("description") or ""
        content = content.replace("[+", "").strip()[:5000]

        return NewsItem(
            title=title,
            url=url,
            source_id=self.source_id,
            source_name=source_name,
            source_type="newsapi",
            content=content,
            author=art.get("author", ""),
            image_url=art.get("urlToImage"),
            published_at=pub_dt,
            region=self.region_hint,
            raw=art,
        )
