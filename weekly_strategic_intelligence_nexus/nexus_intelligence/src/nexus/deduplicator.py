"""Nexus Intelligence — deduplicator with fuzzy merge."""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from nexus.models import NewsItem


def _normalize_title(title: str) -> str:
    nfkd = unicodedata.normalize("NFKD", title.lower())
    text = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", text).strip()


def _jaccard(a: str, b: str) -> float:
    wa = set(a.split())
    wb = set(b.split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


class Deduplicator:
    def __init__(self, cfg: dict) -> None:
        self.threshold: float = float(cfg.get("title_similarity_threshold", 0.82))

    def deduplicate_and_merge(self, items: list[NewsItem]) -> list[NewsItem]:
        # Group by URL first
        by_url: dict[str, NewsItem] = {}
        for item in items:
            url = item.url.strip().rstrip("/")
            if url in by_url:
                # Merge secondary source
                existing = by_url[url]
                if item.source_name not in existing.secondary_sources:
                    existing.secondary_sources.append(item.source_name)
                if not existing.image_url and item.image_url:
                    existing.image_url = item.image_url
            else:
                by_url[url] = item

        unique = list(by_url.values())

        # Fuzzy title dedup
        merged: list[NewsItem] = []
        used: set[int] = set()
        norm_titles = [_normalize_title(it.title) for it in unique]

        for i, item in enumerate(unique):
            if i in used:
                continue
            used.add(i)
            canonical = item
            for j in range(i + 1, len(unique)):
                if j in used:
                    continue
                sim = _jaccard(norm_titles[i], norm_titles[j])
                if sim >= self.threshold:
                    used.add(j)
                    other = unique[j]
                    if other.source_name not in canonical.secondary_sources:
                        canonical.secondary_sources.append(other.source_name)
                    # Keep highest authority source as canonical
                    if other.source_authority > canonical.source_authority:
                        other.secondary_sources = canonical.secondary_sources[:]
                        canonical = other
            merged.append(canonical)

        return merged
