"""Nexus Intelligence — topic classifier and opportunity detector."""
from __future__ import annotations

import re
import unicodedata

from nexus.models import NewsItem


def _deaccent(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").lower()


class TopicClassifier:
    def __init__(self, topics_cfg: dict) -> None:
        self.topics: dict[str, list[str]] = {
            name: [_deaccent(kw) for kw in data.get("keywords", [])]
            for name, data in topics_cfg.items()
        }

    def classify(self, items: list[NewsItem]) -> list[NewsItem]:
        for item in items:
            text = _deaccent(item.normalized_text)
            matched: list[str] = []
            for topic, keywords in self.topics.items():
                hits = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text))
                if hits >= 1:
                    matched.append(topic)
            item.topics = matched or ["Geral"]
            item.detected_keywords = self._find_keywords(text)
        return items

    def _find_keywords(self, text: str) -> list[str]:
        all_kw: list[str] = []
        for kws in self.topics.values():
            all_kw.extend(kws)
        return [kw for kw in dict.fromkeys(all_kw) if re.search(r"\b" + re.escape(kw) + r"\b", text)][:10]


class OpportunityDetector:
    def __init__(self, signals_cfg: dict) -> None:
        self.signals: dict[str, list[str]] = {
            name: [_deaccent(t) for t in terms]
            for name, terms in signals_cfg.items()
        }

    def detect(self, items: list[NewsItem]) -> list[NewsItem]:
        for item in items:
            text = _deaccent(item.normalized_text)
            found = [
                name for name, terms in self.signals.items()
                if any(re.search(r"\b" + re.escape(t) + r"\b", text) for t in terms)
            ]
            item.opportunity_types = found
            item.opportunity_exists = bool(found)
        return items
