"""
Coletor Reddit via RSS público (sem OAuth).
Funciona com subreddits públicos sem precisar de API key.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from hub.collectors.base import BaseCollector
from hub.models import NewsItem

logger = logging.getLogger(__name__)


class RedditCollector(BaseCollector):
    """
    Coleta posts do Reddit via feed RSS público.
    Ótimo para capturar discussões e tendências emergentes.
    Não requer chave de API (usa feed público).
    """

    def collect(self) -> list[NewsItem]:
        subreddits = self.source_cfg.get("subreddits", [])
        sort = self.source_cfg.get("sort", "hot")  # hot, new, top, rising
        limit = int(self.source_cfg.get("limit", 25))
        min_score = int(self.source_cfg.get("min_score", 5))

        if not subreddits:
            url = self.source_cfg.get("url", "")
            if not url:
                return []
            subreddits = [url]

        all_items: list[NewsItem] = []
        for sub in subreddits:
            items = self._collect_subreddit(sub, sort, limit, min_score)
            all_items.extend(items)

        return all_items

    def _collect_subreddit(
        self, subreddit: str, sort: str, limit: int, min_score: int
    ) -> list[NewsItem]:
        # Constrói URL do feed RSS
        if subreddit.startswith("http"):
            url = subreddit
        else:
            sub_name = subreddit.lstrip("r/")
            url = f"https://www.reddit.com/r/{sub_name}/{sort}.rss?limit={limit}"

        headers = {
            **self._default_headers(),
            "User-Agent": "IntelligenceHub:RSS:v2.0",
        }

        try:
            resp = requests.get(url, timeout=self.timeout, headers=headers)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as exc:
            logger.warning("Reddit %s (%s) erro: %s", self.source_id, subreddit, exc)
            return []

        items: list[NewsItem] = []
        for entry in feed.entries:
            item = self._parse_entry(entry, subreddit)
            if item:
                items.append(item)

        logger.debug("Reddit r/%s: %d posts", subreddit, len(items))
        return items

    def _parse_entry(self, entry: Any, subreddit: str) -> NewsItem | None:
        title = getattr(entry, "title", "").strip()
        url = getattr(entry, "link", "").strip()
        if not title or not url:
            return None

        # Conteúdo
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary or ""

        # Strip HTML
        from html.parser import HTMLParser
        class _S(HTMLParser):
            def __init__(self): super().__init__(); self._p: list[str] = []
            def handle_data(self, d): self._p.append(d)
            def text(self): return " ".join(self._p).strip()
        s = _S(); s.feed(content); content_clean = s.text()[:3000]

        # Data
        pub_dt: datetime | None = None
        raw_date = getattr(entry, "published", "") or getattr(entry, "updated", "")
        if raw_date:
            try:
                from dateutil import parser as dp
                pub_dt = dp.parse(raw_date)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Imagem: extrair <img> do HTML do summary do Reddit
        image_url: str | None = None
        if content:  # content ainda é o HTML bruto aqui
            import re
            m = re.search(r'<img[^>]+src=["\']([^"\']{10,})["\']', content, re.IGNORECASE)
            if m:
                candidate = m.group(1)
                skip = ("1x1", "pixel", "tracking", "spacer", "blank", "icon", "logo",
                        "avatar", "external_link", "reddit.com/static")
                if not any(x in candidate.lower() for x in skip):
                    image_url = candidate

        sub_clean = subreddit.lstrip("r/").split("/")[0]
        return NewsItem(
            title=title,
            url=url,
            source_id=self.source_id,
            source_name=f"Reddit/r/{sub_clean}",
            source_type="reddit",
            content=content_clean,
            author=getattr(entry, "author", ""),
            image_url=image_url,
            published_at=pub_dt,
            region=self.region_hint or "Global",
            categories=["Reddit", _sub_to_category(sub_clean)],
            raw={"subreddit": sub_clean},
        )


def _sub_to_category(sub: str) -> str:
    _MAP = {
        "worldnews": "Notícias Mundiais",
        "economics": "Economia",
        "investing": "Investimentos",
        "technology": "Tecnologia",
        "business": "Negócios",
        "geopolitics": "Geopolítica",
        "energy": "Energia",
        "sustainability": "Sustentabilidade",
        "africa": "África",
        "brazil": "Brasil",
        "portugal": "Portugal",
    }
    return _MAP.get(sub.lower(), "Comunidade")
