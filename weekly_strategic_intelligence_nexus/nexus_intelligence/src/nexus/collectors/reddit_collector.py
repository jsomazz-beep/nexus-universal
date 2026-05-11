"""Nexus Intelligence — Reddit collector (public JSON, no auth required)."""
from __future__ import annotations

import requests

from nexus.collectors.base import Collector
from nexus.models import NewsItem
from nexus.utils.text import now_utc, parse_datetime


class RedditCollector(Collector):
    def collect(self) -> list[NewsItem]:
        subreddit = self.source_config.get("subreddit", "worldnews")
        sort = self.source_config.get("sort", "hot")
        max_items = int(self.source_config.get("max_items", 25))
        authority = int(self.source_config.get("authority", 6))

        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={max_items}"
        headers = {**self.headers, "Accept": "application/json"}

        try:
            r = requests.get(url, timeout=self.timeout, headers=headers)
            r.raise_for_status()
            data = r.json()
        except Exception:
            return []

        items: list[NewsItem] = []
        for post in data.get("data", {}).get("children", []):
            d = post.get("data", {})
            title = (d.get("title") or "").strip()
            if not title or d.get("is_self"):
                continue

            link_url = d.get("url") or f"https://reddit.com{d.get('permalink', '')}"
            upvotes = d.get("score", 0)
            created = d.get("created_utc")
            published_at = parse_datetime(str(int(created))) if created else None

            thumbnail = d.get("thumbnail") or None
            if thumbnail and not thumbnail.startswith("http"):
                thumbnail = None

            flair = d.get("link_flair_text") or ""
            items.append(NewsItem(
                source_id=self.source_config.get("id", f"reddit_{subreddit}"),
                source_name=self.source_config.get("label", f"Reddit r/{subreddit}"),
                source_authority=authority,
                title=title,
                url=link_url,
                published_at=published_at,
                collected_at=now_utc(),
                description=f"r/{subreddit} | {upvotes:,} upvotes | {flair}".strip(" |"),
                content=title,
                image_url=thumbnail,
                tags=[flair] if flair else [],
                metadata={
                    "region_hint": self.source_config.get("region_hint", "Global"),
                    "source_type": "reddit",
                    "upvotes": upvotes,
                    "subreddit": subreddit,
                },
            ))

        return items
