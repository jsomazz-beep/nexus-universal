from __future__ import annotations

from news_reporter.models import NewsItem


class OpportunityAnalyzer:
    def annotate(self, items: list[NewsItem]) -> list[NewsItem]:
        for item in items:
            item.opportunity_exists = len(item.opportunity_types) > 0
            if item.opportunity_exists:
                item.opportunity_why = self._build_why(item)
            else:
                item.opportunity_why = "Sem sinal explícito de oportunidade acionável na V1."
        return items

    def _build_why(self, item: NewsItem) -> str:
        top_types = ", ".join(item.opportunity_types[:3])
        keywords = item.detected_keywords + item.detected_associated_keywords
        top_keywords = ", ".join(keywords[:4]) if keywords else "termos estratégicos"
        return (
            f"Indícios para {top_types} com base em menções a {top_keywords}, "
            f"na região {item.region} e no contexto econômico identificado."
        )
