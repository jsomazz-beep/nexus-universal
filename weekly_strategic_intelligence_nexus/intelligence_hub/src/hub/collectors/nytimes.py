"""
Coletor NY Times Article Search API.
Chave gratuita em: https://developer.nytimes.com/
Até 500 requisições/dia, 5 req/min.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from hub.collectors.base import BaseCollector
from hub.models import NewsItem

logger = logging.getLogger(__name__)

NYT_API = "https://api.nytimes.com/svc/search/v2/articlesearch.json"


class NYTimesCollector(BaseCollector):
    """Coleta artigos da API de busca do NY Times."""

    def collect(self) -> list[NewsItem]:
        api_key = self.app_cfg.nytimes_api_key
        if not api_key:
            logger.debug("NYTimes %s: sem chave, pulando.", self.source_id)
            return []

        query = self.source_cfg.get("query", "")
        news_desk = self.source_cfg.get("news_desk", "")  # Business, World, Technology
        page = int(self.source_cfg.get("page", 0))
        sort = self.source_cfg.get("sort", "newest")
        begin_date = self.source_cfg.get("begin_date", "")  # YYYYMMDD

        params: dict[str, Any] = {
            "api-key": api_key,
            "sort": sort,
            "page": page,
            "fl": "headline,abstract,web_url,pub_date,byline,section_name,multimedia",
        }
        if query:
            params["q"] = query
        if news_desk:
            params["fq"] = f'news_desk:("{news_desk}")'
        if begin_date:
            params["begin_date"] = begin_date

        try:
            resp = requests.get(NYT_API, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("NYTimes %s erro: %s", self.source_id, exc)
            return []

        docs = data.get("response", {}).get("docs", [])
        items: list[NewsItem] = []
        for doc in docs:
            item = self._parse_doc(doc)
            if item:
                items.append(item)

        logger.info("NYTimes %s: %d artigos", self.source_id, len(items))
        return items

    def _parse_doc(self, doc: dict[str, Any]) -> NewsItem | None:
        headline = doc.get("headline", {})
        title = headline.get("main", "").strip() or headline.get("print_headline", "")
        url = doc.get("web_url", "").strip()
        if not title or not url:
            return None

        content = doc.get("abstract", "") or ""

        # Data
        pub_dt: datetime | None = None
        raw_date = doc.get("pub_date", "")
        if raw_date:
            try:
                pub_dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except Exception:
                pass

        # Imagem
        image_url: str | None = None
        multimedia = doc.get("multimedia", [])
        for media in multimedia:
            if media.get("subtype") == "xlarge":
                image_url = "https://www.nytimes.com/" + media.get("url", "")
                break

        # Autor
        byline = doc.get("byline", {})
        author = byline.get("original", "") if isinstance(byline, dict) else ""
        if author.startswith("By "):
            author = author[3:]

        section = doc.get("section_name", "")

        return NewsItem(
            title=title,
            url=url,
            source_id=self.source_id,
            source_name="The New York Times",
            source_type="nytimes",
            content=content[:3000],
            author=author,
            image_url=image_url,
            published_at=pub_dt,
            region=self.region_hint,
            categories=[section] if section else [],
            raw=doc,
        )
