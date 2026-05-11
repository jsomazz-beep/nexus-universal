"""
Motor de filtros para itens de notícia.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from hub.models import NewsItem

logger = logging.getLogger(__name__)


class FilterEngine:
    """Aplica filtros configuráveis a uma lista de NewsItem."""

    def __init__(self, filters_cfg: dict[str, Any], monitoring_cfg: dict[str, Any]) -> None:
        self.filters = filters_cfg
        self.monitoring = monitoring_cfg

    def apply(self, items: list[NewsItem]) -> tuple[list[NewsItem], list[str]]:
        """Retorna (itens aprovados, lista de logs de filtro)."""
        logs: list[str] = []
        passed: list[NewsItem] = []

        cutoff = self._time_cutoff()
        min_len = int(self.filters.get("min_text_length", 30))
        negative_kws = [k.lower() for k in self.monitoring.get("negative_keywords", [])]

        for item in items:
            reason = self._should_reject(item, cutoff, min_len, negative_kws)
            if reason:
                logs.append(f"REJEITADO [{item.source_id}] '{item.title[:60]}': {reason}")
            else:
                passed.append(item)

        if logs:
            logger.debug("Filtro: %d rejeitados de %d", len(logs), len(items))
        return passed, logs

    # ── Checagens individuais ──────────────────────────────────────────────

    def _should_reject(
        self,
        item: NewsItem,
        cutoff: datetime | None,
        min_len: int,
        negative_kws: list[str],
    ) -> str | None:
        """Retorna motivo de rejeição ou None se aprovado."""

        # 1. Janela temporal
        if cutoff and item.published_at:
            pub = item.published_at
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub < cutoff:
                return f"muito antigo ({pub.date()})"

        # 2. Título vazio
        if not item.title or len(item.title.strip()) < 5:
            return "título muito curto"

        # 3. URL inválida
        if not item.url or not item.url.startswith("http"):
            return "URL inválida"

        # 4. Comprimento mínimo de texto
        combined = (item.title + " " + item.content).strip()
        if len(combined) < min_len:
            return f"texto muito curto ({len(combined)} chars)"

        # 5. Palavras-chave negativas
        combined_lower = combined.lower()
        for kw in negative_kws:
            if kw in combined_lower:
                return f"palavra negativa: '{kw}'"

        # 6. Idioma (opcional — só filtra se aceito_languages explícito)
        accepted_langs = self.filters.get("accepted_languages", ["any"])
        if "any" not in accepted_langs and item.language != "unknown":
            if item.language not in accepted_langs:
                return f"idioma não aceito: {item.language}"

        # 7. Domínios bloqueados
        blocked_domains = [d.lower() for d in self.filters.get("blocked_domains", [])]
        if blocked_domains:
            url_lower = item.url.lower()
            for dom in blocked_domains:
                if dom in url_lower:
                    return f"domínio bloqueado: {dom}"

        return None

    def _time_cutoff(self) -> datetime | None:
        days = int(self.filters.get("time_window_days", 7))
        if days <= 0:
            return None
        return datetime.now(timezone.utc) - timedelta(days=days)
