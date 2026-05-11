"""Nexus Intelligence — Hacker News collector."""
from __future__ import annotations

import requests

from nexus.collectors.base import Collector
from nexus.models import NewsItem
from nexus.utils.text import now_utc


class HackerNewsCollector(Collector):
    BASE = "https://hacker-news.firebaseio.com/v0"

    def collect(self) -> list[NewsItem]:
        endpoint = self.source_config.get("endpoint", f"{self.BASE}/topstories.json")
        max_items = int(self.source_config.get("max_items", 30))
        authority = int(self.source_config.get("authority", 8))

        try:
            ids_resp = requests.get(endpoint, timeout=self.timeout, headers=self.headers)
            ids_resp.raise_for_status()
            story_ids = ids_resp.json()[:max_items]
        except Exception:
            return []

        items: list[NewsItem] = []
        for sid in story_ids:
            try:
                r = requests.get(f"{self.BASE}/item/{sid}.json", timeout=self.timeout, headers=self.headers)
                r.raise_for_status()
                data = r.json()
                if not data or data.get("type") != "story":
                    continue
                title = (data.get("title") or "").strip()
                url = data.get("url") or f"https://news.ycombinator.com/item?id={sid}"
                score = data.get("score", 0)
                comments = data.get("descendants", 0)
                items.append(NewsItem(
                    source_id=self.source_config.get("id", "hackernews"),
                    source_name=self.source_config.get("label", "Hacker News"),
                    source_authority=authority,
                    title=title,
                    url=url,
                    published_at=None,
                    collected_at=now_utc(),
                    description=f"HN Score: {score} | Comments: {comments}",
                    content=title,
                    metadata={
                        "region_hint": self.source_config.get("region_hint", "Global"),
                        "source_type": "hackernews",
                        "hn_score": score,
                        "hn_comments": comments,
                    },
                ))
            except Exception:
                continue

        return items
