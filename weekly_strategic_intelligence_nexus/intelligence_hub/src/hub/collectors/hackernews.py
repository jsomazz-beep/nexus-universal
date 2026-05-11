"""
Coletor Hacker News via Algolia Search API.
Gratuito, sem chave de API. Cobre tech, negócios, startups, IA.
API: https://hn.algolia.com/api
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from hub.collectors.base import BaseCollector
from hub.models import NewsItem

logger = logging.getLogger(__name__)

HN_API = "https://hn.algolia.com/api/v1/search"
HN_ITEM_URL = "https://news.ycombinator.com/item?id={}"


class HackerNewsCollector(BaseCollector):
    """
    Coleta artigos do Hacker News (Y Combinator) via Algolia API.
    Ideal para tendências em tecnologia, IA, startups e negócios.
    """

    def collect(self) -> list[NewsItem]:
        query = self.source_cfg.get("query", "")
        tags = self.source_cfg.get("tags", "story")  # story, ask_hn, show_hn, job
        hits_per_page = int(self.source_cfg.get("hits_per_page", 30))
        min_points = int(self.source_cfg.get("min_points", 10))
        numeric_filters = self.source_cfg.get("numeric_filters", f"points>={min_points}")

        params: dict[str, Any] = {
            "tags": tags,
            "hitsPerPage": hits_per_page,
            "numericFilters": numeric_filters,
        }
        if query:
            params["query"] = query

        try:
            resp = requests.get(
                HN_API,
                params=params,
                timeout=self.timeout,
                headers=self._default_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("HackerNews %s erro: %s", self.source_id, exc)
            return []

        hits = data.get("hits", [])
        items: list[NewsItem] = []
        for hit in hits:
            item = self._parse_hit(hit)
            if item:
                items.append(item)

        logger.info("HackerNews %s: %d artigos (min_pts=%d)", self.source_id, len(items), min_points)
        return items

    def _parse_hit(self, hit: dict[str, Any]) -> NewsItem | None:
        title = (hit.get("title") or "").strip()
        # URL externa ou link HN
        url = hit.get("url") or HN_ITEM_URL.format(hit.get("objectID", ""))
        if not title:
            return None

        # Data
        pub_dt: datetime | None = None
        ts = hit.get("created_at_i")
        if ts:
            try:
                pub_dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            except Exception:
                pass

        # Conteúdo: comentário principal ou texto do item
        content = hit.get("story_text") or hit.get("comment_text") or ""
        if content:
            from html.parser import HTMLParser
            class _S(HTMLParser):
                def __init__(self): super().__init__(); self._p: list[str] = []
                def handle_data(self, d): self._p.append(d)
                def text(self): return " ".join(self._p).strip()
            s = _S(); s.feed(content); content = s.text()[:2000]

        points = hit.get("points", 0) or 0
        num_comments = hit.get("num_comments", 0) or 0

        # Imagem: favicon do domínio da URL externa (via serviço Google)
        image_url: str | None = None
        if url and "ycombinator.com" not in url:
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                if domain:
                    image_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=256"
            except Exception:
                pass

        return NewsItem(
            title=title,
            url=url,
            source_id=self.source_id,
            source_name="Hacker News",
            source_type="hackernews",
            content=content,
            author=hit.get("author", ""),
            image_url=image_url,
            published_at=pub_dt,
            region=self.region_hint or "Global",
            categories=["Tecnologia", "Inovação"],
            tags=[f"hn_points:{points}", f"hn_comments:{num_comments}"],
            raw={
                "points": points,
                "num_comments": num_comments,
                "hn_id": hit.get("objectID"),
            },
        )
