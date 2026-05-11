from __future__ import annotations

from datetime import timedelta
from difflib import SequenceMatcher

from news_reporter.models import NewsItem, SourceSecondaryLink
from news_reporter.utils.text import normalize_for_match


class Deduplicator:
    def __init__(self, cfg: dict) -> None:
        self.threshold = float(cfg.get("title_similarity_threshold", 0.84))
        self.merge_window_hours = int(cfg.get("merge_window_hours", 72))

    def deduplicate_and_merge(self, items: list[NewsItem]) -> list[NewsItem]:
        by_url: dict[str, NewsItem] = {}
        for item in items:
            url_key = item.url.strip().lower()
            if not url_key:
                continue
            if url_key not in by_url:
                by_url[url_key] = item

        unique_items = list(by_url.values())

        merged: list[NewsItem] = []
        for candidate in unique_items:
            was_merged = False
            for existing in merged:
                if self._is_same_event(existing, candidate):
                    existing.secondary_links.append(
                        SourceSecondaryLink(
                            source_id=candidate.source_id,
                            source_name=candidate.source_name,
                            url=candidate.url,
                        )
                    )
                    if len(candidate.normalized_text) > len(existing.normalized_text):
                        existing.content = candidate.content
                        existing.description = candidate.description
                    was_merged = True
                    break
            if not was_merged:
                merged.append(candidate)

        return merged

    def _is_same_event(self, left: NewsItem, right: NewsItem) -> bool:
        left_title = normalize_for_match(left.title)
        right_title = normalize_for_match(right.title)
        similarity = SequenceMatcher(None, left_title, right_title).ratio()

        if similarity < self.threshold:
            return False

        if left.published_at and right.published_at:
            delta = abs(left.published_at - right.published_at)
            return delta <= timedelta(hours=self.merge_window_hours)

        return True
