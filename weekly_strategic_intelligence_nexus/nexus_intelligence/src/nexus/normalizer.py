"""Nexus Intelligence — normalizer."""
from __future__ import annotations

import logging
import re
import unicodedata

from nexus.models import NewsItem
from nexus.utils.text import strip_html, truncate

logger = logging.getLogger(__name__)

try:
    from langdetect import detect as _detect_lang  # type: ignore
    def detect_language(text: str) -> str:
        try:
            return _detect_lang(text[:500]) or "unknown"
        except Exception:
            return "unknown"
except ImportError:
    def detect_language(text: str) -> str:  # type: ignore
        return "unknown"


def _deaccent(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").lower()


class Normalizer:
    def __init__(self, monitoring_cfg: dict) -> None:
        self.monitoring = monitoring_cfg
        self.regions: list[str] = monitoring_cfg.get("regions", [])
        self.region_aliases: dict[str, list[str]] = monitoring_cfg.get("region_aliases", {})

    def normalize(self, items: list[NewsItem]) -> list[NewsItem]:
        out: list[NewsItem] = []
        for item in items:
            try:
                item = self._normalize_item(item)
                out.append(item)
            except Exception as exc:
                logger.debug("Normalizer skip %s: %s", item.url, exc)
        return out

    def _normalize_item(self, item: NewsItem) -> NewsItem:
        raw = " ".join(filter(None, [item.title, item.description, item.content]))
        clean = strip_html(raw)
        clean = re.sub(r"\s+", " ", clean).strip()
        item.normalized_text = truncate(clean, 2000)
        item.normalized_language = item.raw_language or detect_language(clean)
        item.region = self._detect_region(item)
        return item

    def _detect_region(self, item: NewsItem) -> str:
        region_hint = item.metadata.get("region_hint", "")
        if region_hint and region_hint != "Global":
            for region in self.regions:
                if region.lower() == region_hint.lower():
                    return region

        text = _deaccent(item.normalized_text + " " + item.title)
        for region, aliases in self.region_aliases.items():
            for alias in aliases:
                if re.search(r"\b" + re.escape(_deaccent(alias)) + r"\b", text):
                    return region

        return region_hint if region_hint else "Global"
