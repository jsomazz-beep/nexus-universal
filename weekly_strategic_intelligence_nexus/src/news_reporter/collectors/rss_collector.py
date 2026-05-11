from __future__ import annotations

from datetime import timezone

import feedparser

from news_reporter.collectors.base import Collector
from news_reporter.models import NewsItem
from news_reporter.utils.text import now_utc, parse_datetime


class RSSCollector(Collector):
    def collect(self) -> list[NewsItem]:
        feed_url = self.source_config["url"]
        feed = feedparser.parse(feed_url)

        source_name = feed.feed.get("title") or self.source_config.get("id", "rss")
        items: list[NewsItem] = []

        for entry in feed.entries:
            published_raw = entry.get("published") or entry.get("updated")
            published_at = parse_datetime(published_raw)

            image_url = None
            if "media_content" in entry and entry.media_content:
                image_url = entry.media_content[0].get("url")
            if not image_url and "links" in entry:
                for link in entry.links:
                    if link.get("type", "").startswith("image"):
                        image_url = link.get("href")
                        break

            tags = [tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")]

            items.append(
                NewsItem(
                    source_id=self.source_config.get("id", "rss"),
                    source_name=source_name,
                    title=(entry.get("title") or "").strip(),
                    subtitle=None,
                    url=entry.get("link", "").strip(),
                    published_at=published_at,
                    collected_at=now_utc(),
                    raw_language=entry.get("language"),
                    description=entry.get("summary"),
                    content=(entry.get("summary") or entry.get("title") or ""),
                    image_url=image_url,
                    tags=tags,
                    metadata={
                        "region_hint": self.source_config.get("region_hint", ""),
                        "source_type": "rss",
                        "published_raw": published_raw,
                    },
                )
            )

        return items
