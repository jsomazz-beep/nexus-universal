"""Nexus Intelligence — filter engine."""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timezone

from nexus.models import NewsItem

logger = logging.getLogger(__name__)


def _deaccent(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").lower()


class FilterEngine:
    def __init__(self, filters_cfg: dict, monitoring_cfg: dict) -> None:
        self.cfg = filters_cfg
        self.monitoring = monitoring_cfg
        self.time_window_days = int(filters_cfg.get("time_window_days", 7))
        self.min_text_length = int(filters_cfg.get("min_text_length", 60))
        self.min_fields = filters_cfg.get("minimum_fields", ["title", "url"])
        negative_raw = monitoring_cfg.get("negative_keywords", [])
        self.negative_words = [_deaccent(w) for w in negative_raw if w]

    def apply(self, items: list[NewsItem]) -> tuple[list[NewsItem], list[str]]:
        passed, logs = [], []
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - self.time_window_days * 86400

        for item in items:
            reason = self._reject_reason(item, now, cutoff)
            if reason:
                logs.append(f"REJECT [{item.source_id}] '{item.title[:60]}': {reason}")
            else:
                passed.append(item)

        logger.info("Filter: %d → %d items", len(items), len(passed))
        return passed, logs

    def _reject_reason(self, item: NewsItem, now: datetime, cutoff: float) -> str | None:
        # Missing required fields
        for field in self.min_fields:
            if not getattr(item, field, None):
                return f"missing field '{field}'"

        # No URL
        if not item.url or not item.url.startswith("http"):
            return "invalid URL"

        # Too old
        if item.published_at:
            ts = item.published_at.timestamp()
            if ts < cutoff:
                return f"too old ({(now.timestamp()-ts)/86400:.1f}d)"

        # Text too short
        if len(item.normalized_text) < self.min_text_length:
            return f"text too short ({len(item.normalized_text)} chars)"

        # Negative keyword match
        text = _deaccent(item.normalized_text)
        for neg in self.negative_words:
            if re.search(r"\b" + re.escape(neg) + r"\b", text):
                return f"negative keyword '{neg}'"

        return None
