"""Nexus Intelligence — RSS collector."""
from __future__ import annotations

import feedparser

from nexus.collectors.base import Collector
from nexus.models import NewsItem
from nexus.utils.text import now_utc, parse_datetime, strip_html


class RSSCollector(Collector):
    def collect(self) -> list[NewsItem]:
        url = self.source_config["url"]
        feed = feedparser.parse(url, request_headers=self.headers, agent=self.headers["User-Agent"])

        source_name = (
            self.source_config.get("label")
            or getattr(feed.feed, "title", None)
            or self.source_config.get("id", "rss")
        )
        authority = int(self.source_config.get("authority", 5))
        region_hint = self.source_config.get("region_hint", "Global")
        items: list[NewsItem] = []

        for entry in feed.entries:
            title = (entry.get("title") or "").strip()
            if not title:
                continue

            url_entry = (entry.get("link") or "").strip()
            published_at = parse_datetime(entry.get("published") or entry.get("updated"))

            # Image extraction
            image_url: str | None = None
            if entry.get("media_content"):
                image_url = entry.media_content[0].get("url")
            if not image_url:
                for link in entry.get("links", []):
                    if str(link.get("type", "")).startswith("image"):
                        image_url = link.get("href")
                        break
            if not image_url:
                enc = entry.get("enclosures", [])
                if enc and str(enc[0].get("type", "")).startswith("image"):
                    image_url = enc[0].get("href") or enc[0].get("url")

            description = strip_html(entry.get("summary") or "")
            tags = [t.get("term", "") for t in entry.get("tags", []) if t.get("term")]

            items.append(NewsItem(
                source_id=self.source_config.get("id", "rss"),
                source_name=source_name,
                source_authority=authority,
                title=title,
                url=url_entry,
                published_at=published_at,
                collected_at=now_utc(),
                description=description,
                content=description,
                image_url=image_url,
                raw_language=entry.get("language"),
                tags=tags,
                metadata={
                    "region_hint": region_hint,
                    "source_type": "rss",
                },
            ))

        return items
