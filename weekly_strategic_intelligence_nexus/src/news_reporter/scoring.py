from __future__ import annotations

from datetime import timedelta

from news_reporter.models import NewsItem
from news_reporter.utils.text import now_utc


class Scorer:
    def __init__(self, cfg: dict, monitoring_cfg: dict) -> None:
        self.weights = cfg.get("weights", {})
        self.monitoring_cfg = monitoring_cfg

    def score_items(self, items: list[NewsItem]) -> list[NewsItem]:
        for item in items:
            breakdown = self._score_breakdown(item)
            weight_total = sum(self.weights.values()) or 1.0
            weighted = sum(breakdown[k] * self.weights.get(k, 0.0) for k in breakdown)
            item.score = round((weighted / weight_total) * 100, 2)
            item.score_breakdown = breakdown
            item.inclusion_reason = self._build_inclusion_reason(item)
        return items

    def _score_breakdown(self, item: NewsItem) -> dict[str, float]:
        now = now_utc()

        recency = 0.0
        if item.published_at:
            days = (now - item.published_at).total_seconds() / 86400
            recency = max(0.0, min(1.0, 1 - (days / 7)))

        region_fit = 1.0 if item.region in self.monitoring_cfg.get("regions", []) else 0.0
        theme_fit = min(1.0, len(item.themes) / 2)
        priority_kw = min(1.0, len(item.detected_keywords) / 2)
        opp_signals = min(1.0, len(item.opportunity_types) / 3)

        econ_tokens = [
            "investimento",
            "crescimento",
            "expansão",
            "pib",
            "inflação",
            "capex",
            "receita",
            "produção",
        ]
        text_lower = item.normalized_text.lower()
        economic_impact = min(1.0, sum(1 for token in econ_tokens if token in text_lower) / 4)

        recurrence = min(1.0, len(item.secondary_links) / 3)
        entities = min(1.0, len(item.entities) / 6)

        strategic_tokens = [
            "licitação",
            "concessão",
            "ppp",
            "contrato",
            "aquisição",
            "infraestrutura",
            "frota",
            "saneamento",
            "facilities",
        ]
        strategic_applicability = min(1.0, sum(1 for token in strategic_tokens if token in text_lower) / 4)

        return {
            "recency": round(recency, 4),
            "region_fit": round(region_fit, 4),
            "theme_fit": round(theme_fit, 4),
            "priority_keywords": round(priority_kw, 4),
            "opportunity_signals": round(opp_signals, 4),
            "economic_impact": round(economic_impact, 4),
            "multi_source_recurrence": round(recurrence, 4),
            "entities": round(entities, 4),
            "strategic_applicability": round(strategic_applicability, 4),
        }

    def _build_inclusion_reason(self, item: NewsItem) -> str:
        reasons: list[str] = []
        if item.detected_keywords:
            reasons.append(f"contém palavras-chave prioritárias ({', '.join(item.detected_keywords[:3])})")
        if item.opportunity_types:
            reasons.append(f"apresenta sinais de oportunidade ({', '.join(item.opportunity_types[:2])})")
        if len(item.secondary_links) >= 1:
            reasons.append("evento recorrente em múltiplas fontes")
        if item.score >= 70:
            reasons.append("alto score estratégico")
        return "; ".join(reasons) if reasons else "aderente ao escopo por região/tema"
