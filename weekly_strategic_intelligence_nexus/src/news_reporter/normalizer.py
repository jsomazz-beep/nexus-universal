from __future__ import annotations

import logging
import re
from typing import Iterable

from news_reporter.models import NewsItem
from news_reporter.utils.text import (
    clean_html_text,
    contains_any,
    detect_language_safe,
    normalize_for_match,
    normalize_unicode,
)

logger = logging.getLogger(__name__)


class Normalizer:
    def __init__(self, monitoring_cfg: dict) -> None:
        self.monitoring_cfg = monitoring_cfg
        self.region_aliases: dict[str, list[str]] = monitoring_cfg.get("region_aliases", {})
        self.theme_keywords: dict[str, list[str]] = monitoring_cfg.get("themes", {})
        self.priority_keywords: list[str] = monitoring_cfg.get("priority_keywords", [])
        self.associated_keywords: list[str] = monitoring_cfg.get("associated_keywords", [])
        self.opportunity_signals: dict[str, list[str]] = monitoring_cfg.get("opportunity_signals", {})

    def normalize(self, items: Iterable[NewsItem]) -> list[NewsItem]:
        normalized: list[NewsItem] = []
        for item in items:
            text = " ".join(
                part
                for part in [item.title or "", item.description or "", item.content or "", " ".join(item.tags)]
                if part
            )
            text = normalize_unicode(clean_html_text(text))
            item.normalized_text = text

            language_candidate = item.raw_language or detect_language_safe(text)
            item.normalized_language = (language_candidate or "unknown").lower()

            item.region = self._infer_region(item)
            item.themes = self._infer_themes(text)
            item.detected_keywords = contains_any(text, self.priority_keywords)
            item.detected_associated_keywords = contains_any(text, self.associated_keywords)
            item.opportunity_types = self._infer_opportunity_types(text)
            item.entities = self._extract_entities(item)

            normalized.append(item)

        return normalized

    def _infer_region(self, item: NewsItem) -> str:
        # Inferência por score evita falso positivo de aliases curtos (ex.: "pt", "br").
        title = normalize_for_match(item.title or "")
        description = normalize_for_match(item.description or "")
        content = normalize_for_match(item.content or "")
        region_hint = normalize_for_match(str(item.metadata.get("region_hint", "")))
        url = normalize_for_match(item.url or "")

        scored: dict[str, float] = {}
        for region, aliases in self.region_aliases.items():
            score = 0.0
            for alias in aliases:
                alias_n = normalize_for_match(alias)
                if not alias_n:
                    continue

                if self._contains_alias(title, alias_n):
                    score += 4.0
                if self._contains_alias(description, alias_n):
                    score += 2.5
                if self._contains_alias(content, alias_n):
                    score += 1.0
                if self._contains_alias(region_hint, alias_n):
                    score += 3.0
                if self._contains_alias(url, alias_n):
                    score += 1.5

            if score > 0:
                scored[region] = score

        if scored:
            return max(scored.items(), key=lambda kv: kv[1])[0]
        return "Indefinida"

    @staticmethod
    def _contains_alias(text: str, alias_n: str) -> bool:
        if not text or not alias_n:
            return False
        # Para aliases muito curtos, exige token completo (evita "pt" bater em palavras comuns).
        if len(alias_n) <= 3:
            return bool(re.search(rf"\b{re.escape(alias_n)}\b", text))
        return alias_n in text

    def _infer_themes(self, text: str) -> list[str]:
        selected: list[str] = []
        for theme, terms in self.theme_keywords.items():
            if contains_any(text, terms):
                selected.append(theme)
        return selected

    def _infer_opportunity_types(self, text: str) -> list[str]:
        found: list[str] = []
        for opportunity_type, terms in self.opportunity_signals.items():
            if contains_any(text, terms):
                found.append(opportunity_type)
        return found

    def _extract_entities(self, item: NewsItem) -> list[str]:
        # Extração simples por heurística de tokens capitalizados.
        base_text = f"{item.title} {item.description or ''}"
        tokens = re.findall(r"\b[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+(?:\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+)?", base_text)
        unique = []
        for token in tokens:
            token = token.strip()
            if token and token not in unique:
                unique.append(token)
        return unique[:10]
