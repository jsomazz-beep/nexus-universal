"""Nexus Intelligence — multi-dimensional scorer."""
from __future__ import annotations

import math
import re
import unicodedata
from datetime import datetime, timezone

from nexus.models import NewsItem


def _deaccent(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").lower()


class Scorer:
    def __init__(self, scoring_cfg: dict, monitoring_cfg: dict) -> None:
        self.weights: dict[str, float] = scoring_cfg.get("weights", {})
        self.priority_keywords: list[str] = [
            _deaccent(kw) for kw in monitoring_cfg.get("priority_keywords", [])
        ]
        self.regions: list[str] = monitoring_cfg.get("regions", [])

    def score_items(self, items: list[NewsItem]) -> list[NewsItem]:
        now = datetime.now(timezone.utc)
        for item in items:
            bd: dict[str, float] = {}
            bd["recency"] = self._recency(item, now)
            bd["region_fit"] = self._region_fit(item)
            bd["topic_fit"] = self._topic_fit(item)
            bd["priority_keywords"] = self._priority_kw(item)
            bd["opportunity_signals"] = self._opportunity(item)
            bd["source_authority"] = item.source_authority / 10.0
            bd["multi_source_recurrence"] = min(len(item.secondary_sources) * 0.25, 1.0)
            bd["entities"] = min(len(item.entities) * 0.1, 1.0)

            total = 0.0
            for dim, val in bd.items():
                w = self.weights.get(dim, 0.0)
                total += val * w

            item.score = round(total * 100, 2)
            item.score_breakdown = {k: round(v, 3) for k, v in bd.items()}

        return items

    def _recency(self, item: NewsItem, now: datetime) -> float:
        if not item.published_at:
            return 0.3
        age_hours = (now - item.published_at).total_seconds() / 3600
        if age_hours < 6:
            return 1.0
        if age_hours < 24:
            return 0.85
        if age_hours < 48:
            return 0.65
        if age_hours < 96:
            return 0.45
        return max(0.1, 1.0 - (age_hours / (7 * 24)))

    def _region_fit(self, item: NewsItem) -> float:
        if item.region == "Global":
            return 0.6
        return 1.0 if item.region in self.regions else 0.3

    def _topic_fit(self, item: NewsItem) -> float:
        if not item.topics or item.topics == ["Geral"]:
            return 0.2
        return min(len(item.topics) * 0.35, 1.0)

    def _priority_kw(self, item: NewsItem) -> float:
        if not self.priority_keywords:
            return 0.0
        text = _deaccent(item.normalized_text)
        hits = sum(1 for kw in self.priority_keywords if re.search(r"\b" + re.escape(kw) + r"\b", text))
        return min(hits / max(len(self.priority_keywords), 1), 1.0)

    def _opportunity(self, item: NewsItem) -> float:
        if not item.opportunity_exists:
            return 0.0
        return min(len(item.opportunity_types) * 0.3, 1.0)
