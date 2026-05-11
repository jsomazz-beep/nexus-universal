"""
Coletor RSS/Atom — suporta qualquer feed compatível com feedparser.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests
from dateutil import parser as dateutil_parser

from hub.collectors.base import BaseCollector
from hub.models import NewsItem

logger = logging.getLogger(__name__)


class RSSCollector(BaseCollector):
    """Coleta notícias de feeds RSS/Atom."""

    def collect(self) -> list[NewsItem]:
        url = self.source_cfg.get("url", "")
        if not url:
            return []

        try:
            # Fetch com requests para melhor controle de timeout e headers
            resp = requests.get(
                url,
                timeout=self.timeout,
                headers=self._default_headers(),
            )
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception:
            # Fallback: feedparser direto (resolve alguns redirecionamentos)
            feed = feedparser.parse(url)

        items: list[NewsItem] = []
        for entry in feed.entries:
            try:
                item = self._parse_entry(entry, feed)
                if item:
                    items.append(item)
            except Exception as exc:
                logger.debug("Erro ao parsear entrada RSS de %s: %s", self.source_id, exc)

        return items

    def _parse_entry(self, entry: Any, feed: Any) -> NewsItem | None:
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

        # Remover tags HTML simples
        from html.parser import HTMLParser
        class _Strip(HTMLParser):
            def __init__(self):
                super().__init__()
                self._text: list[str] = []
            def handle_data(self, data: str):
                self._text.append(data)
            def get_text(self) -> str:
                return " ".join(self._text).strip()

        stripper = _Strip()
        stripper.feed(content)
        content_clean = stripper.get_text()

        # Data de publicação
        pub_dt: datetime | None = None
        raw_date = getattr(entry, "published", "") or getattr(entry, "updated", "")
        if raw_date:
            try:
                pub_dt = dateutil_parser.parse(raw_date)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Imagem — múltiplas estratégias em ordem de confiabilidade
        image_url: str | None = None

        # 1. media:content (feeds modernos — Reuters, FT, etc.)
        if hasattr(entry, "media_content") and entry.media_content:
            mc = entry.media_content[0]
            if mc.get("medium", "") != "video":
                image_url = mc.get("url")

        # 2. media:thumbnail (feedparser pode expor como lista)
        if not image_url and hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            image_url = entry.media_thumbnail[0].get("url")

        # 3. Enclosures de imagem
        if not image_url and hasattr(entry, "enclosures") and entry.enclosures:
            for enc in entry.enclosures:
                t = enc.get("type", "")
                href = enc.get("href") or enc.get("url") or ""
                if "image" in t or href.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                    image_url = href
                    break

        # 4. Primeira <img> no HTML do conteúdo/summary
        if not image_url:
            html_content = ""
            if hasattr(entry, "content") and entry.content:
                html_content = entry.content[0].get("value", "")
            elif hasattr(entry, "summary"):
                html_content = entry.summary or ""
            if html_content:
                import re
                m = re.search(r'<img[^>]+src=["\']([^"\']{10,})["\']', html_content, re.IGNORECASE)
                if m:
                    candidate = m.group(1)
                    # Descartar tracking pixels e imagens tiny
                    skip = ("1x1", "pixel", "tracking", "transparent", "spacer", "blank",
                            ".gif", "icon", "logo", "avatar")
                    if not any(x in candidate.lower() for x in skip):
                        image_url = candidate

        # Nome da fonte (feed title)
        feed_title = getattr(feed.feed, "title", self.source_name) or self.source_name

        return NewsItem(
            title=title,
            url=url,
            source_id=self.source_id,
            source_name=feed_title,
            source_type="rss",
            content=content_clean[:5000],
            author=getattr(entry, "author", ""),
            image_url=image_url,
            published_at=pub_dt,
            region=self.region_hint,
            raw={"feed_title": feed_title, "entry_id": getattr(entry, "id", "")},
        )
