"""
Motor de scoring para priorização de notícias.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from hub.models import NewsItem

logger = logging.getLogger(__name__)


class Scorer:
    """Pontua cada NewsItem com base em múltiplos critérios configuráveis."""

    def __init__(self, scoring_cfg: dict[str, Any], monitoring_cfg: dict[str, Any]) -> None:
        self.cfg = scoring_cfg
        self.monitoring = monitoring_cfg
        self.weights = scoring_cfg.get("weights", _DEFAULT_WEIGHTS)
        self.priority_kws = [k.lower() for k in monitoring_cfg.get("priority_keywords", [])]
        self.opp_signals = monitoring_cfg.get("opportunity_signals", {})
        self.regions = [r.lower() for r in monitoring_cfg.get("regions", [])]
        self.region_aliases = monitoring_cfg.get("region_aliases", {})
        self.themes = monitoring_cfg.get("themes", {})

    def score(self, items: list[NewsItem]) -> list[NewsItem]:
        """Pontua e anota todos os itens."""
        now = datetime.now(timezone.utc)
        for item in items:
            item.score, item.score_breakdown = self._compute_score(item, now)
            item.opportunity_signals = self._detect_opportunity_signals(item)
            item.categories = item.categories or self._detect_categories(item)
            item.region = item.region or self._detect_region(item)
        return items

    # ── Score composto ─────────────────────────────────────────────────────

    def _compute_score(
        self, item: NewsItem, now: datetime
    ) -> tuple[float, dict[str, float]]:
        breakdown: dict[str, float] = {}

        # 1. Recência (decaimento exponencial)
        breakdown["recency"] = self._score_recency(item, now)

        # 2. Região relevante
        breakdown["region_fit"] = self._score_region(item)

        # 3. Tema relevante
        breakdown["theme_fit"] = self._score_theme(item)

        # 4. Palavras-chave prioritárias
        breakdown["priority_keywords"] = self._score_priority_keywords(item)

        # 5. Sinais de oportunidade
        breakdown["opportunity_signals"] = self._score_opportunity(item)

        # 6. Multi-fonte (mesma notícia em várias fontes)
        breakdown["multi_source"] = min(1.0, (item.merged_count - 1) * 0.25)

        # 7. Qualidade do conteúdo
        breakdown["content_quality"] = self._score_content_quality(item)

        # 8. Engajamento (HN points, Reddit score)
        breakdown["engagement"] = self._score_engagement(item)

        # Score composto
        weights = self.weights
        score = sum(
            breakdown.get(k, 0.0) * weights.get(k, 0.0)
            for k in breakdown
        )
        # Normaliza [0, 1]
        score = max(0.0, min(1.0, score))
        return round(score, 4), breakdown

    # ── Critérios individuais ──────────────────────────────────────────────

    def _score_recency(self, item: NewsItem, now: datetime) -> float:
        if not item.published_at:
            return 0.3
        pub = item.published_at
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        age_hours = (now - pub).total_seconds() / 3600
        if age_hours <= 6:
            return 1.0
        elif age_hours <= 24:
            return 0.9
        elif age_hours <= 48:
            return 0.75
        elif age_hours <= 72:
            return 0.6
        elif age_hours <= 120:
            return 0.45
        else:
            return max(0.1, 1.0 - age_hours / 200)

    def _score_region(self, item: NewsItem) -> float:
        if not self.regions:
            return 0.5
        text = (item.title + " " + item.content + " " + item.region).lower()
        for region, aliases in self.region_aliases.items():
            all_terms = [region.lower()] + [a.lower() for a in aliases]
            if any(term in text for term in all_terms):
                return 1.0
        return 0.1

    def _score_theme(self, item: NewsItem) -> float:
        text = (item.title + " " + item.content[:1000]).lower()
        best = 0.0
        for theme_name, keywords in self.themes.items():
            hits = sum(1 for kw in keywords if kw.lower() in text)
            theme_score = min(1.0, hits / max(len(keywords) * 0.1, 1))
            if theme_score > best:
                best = theme_score
        return best

    def _score_priority_keywords(self, item: NewsItem) -> float:
        if not self.priority_kws:
            return 0.0
        text = (item.title + " " + item.content[:500]).lower()
        hits = sum(1 for kw in self.priority_kws if kw in text)
        return min(1.0, hits / max(len(self.priority_kws) * 0.2, 1))

    def _score_opportunity(self, item: NewsItem) -> float:
        if not self.opp_signals:
            return 0.0
        text = (item.title + " " + item.content[:1000]).lower()
        matched_signals = 0
        for signal_name, keywords in self.opp_signals.items():
            if any(kw.lower() in text for kw in keywords):
                matched_signals += 1
        return min(1.0, matched_signals * 0.2)

    def _score_content_quality(self, item: NewsItem) -> float:
        content_len = len(item.content)
        if content_len >= 500:
            return 1.0
        elif content_len >= 200:
            return 0.7
        elif content_len >= 80:
            return 0.5
        elif content_len > 0:
            return 0.3
        return 0.1

    def _score_engagement(self, item: NewsItem) -> float:
        raw = item.raw
        # HN points
        if "points" in raw:
            pts = int(raw.get("points", 0) or 0)
            return min(1.0, pts / 500)
        return 0.0

    # ── Detecção auxiliar ──────────────────────────────────────────────────

    def _detect_opportunity_signals(self, item: NewsItem) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        text = (item.title + " " + item.content[:1000]).lower()
        for signal_name, keywords in self.opp_signals.items():
            matched = [kw for kw in keywords if kw.lower() in text]
            if matched:
                found[signal_name] = matched
        return found

    def _detect_categories(self, item: NewsItem) -> list[str]:
        cats: list[str] = []
        text = (item.title + " " + item.content[:500]).lower()
        for theme_name, keywords in self.themes.items():
            hits = sum(1 for kw in keywords if kw.lower() in text)
            if hits >= 1:
                cats.append(theme_name)
        return cats or ["Geral"]

    def _detect_region(self, item: NewsItem) -> str:
        if item.region:
            return item.region
        text = (item.title + " " + item.content[:500]).lower()
        for region, aliases in self.region_aliases.items():
            all_terms = [region.lower()] + [a.lower() for a in aliases]
            if any(term in text for term in all_terms):
                return region
        return "Global"


_DEFAULT_WEIGHTS = {
    "recency": 0.20,
    "region_fit": 0.18,
    "theme_fit": 0.15,
    "priority_keywords": 0.15,
    "opportunity_signals": 0.15,
    "multi_source": 0.10,
    "content_quality": 0.05,
    "engagement": 0.02,
}
