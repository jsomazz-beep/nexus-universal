"""
Coletor GDELT 2.0 — acesso gratuito, sem chave de API.
Usa a API DOC 2.0 para busca de artigos por tema/região.
Documentação: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from hub.collectors.base import BaseCollector
from hub.models import NewsItem

logger = logging.getLogger(__name__)

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTCollector(BaseCollector):
    """
    Coleta artigos do GDELT Project (Global Database of Events, Language and Tone).
    Fonte gratuita e sem chave de API que cobre notícias mundiais em 65+ idiomas.
    """

    def collect(self) -> list[NewsItem]:
        query = self.source_cfg.get("query", "")
        mode = self.source_cfg.get("mode", "ArtList")
        max_records = int(self.source_cfg.get("max_records", 75))
        timespan = self.source_cfg.get("timespan", "7d")  # ex: 1d, 7d, 1m

        if not query:
            logger.warning("GDELT %s: query vazia, pulando.", self.source_id)
            return []

        params = {
            "query": query,
            "mode": mode,
            "maxrecords": max_records,
            "timespan": timespan,
            "format": "json",
            "sort": "DateDesc",
        }

        try:
            resp = requests.get(
                GDELT_DOC_API,
                params=params,
                timeout=self.timeout,
                headers=self._default_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("GDELT %s erro HTTP: %s", self.source_id, exc)
            return []

        articles = data.get("articles", [])
        items: list[NewsItem] = []

        for art in articles:
            item = self._parse_article(art)
            if item:
                items.append(item)

        logger.info("GDELT %s: %d artigos recebidos", self.source_id, len(items))
        return items

    def _parse_article(self, art: dict[str, Any]) -> NewsItem | None:
        title = (art.get("title") or "").strip()
        url = (art.get("url") or "").strip()
        if not title or not url:
            return None

        # Data
        pub_dt: datetime | None = None
        raw_date = art.get("seendate", "")
        if raw_date:
            try:
                # Formato GDELT: "20240115T120000Z"
                pub_dt = datetime.strptime(raw_date, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Domínio como nome da fonte
        domain = art.get("domain", self.source_name)
        language = art.get("language", "unknown")
        country = art.get("sourcecountry", self.region_hint)

        return NewsItem(
            title=title,
            url=url,
            source_id=self.source_id,
            source_name=f"GDELT/{domain}",
            source_type="gdelt",
            content=art.get("snippet", "")[:2000],
            image_url=art.get("socialimage"),
            published_at=pub_dt,
            language=language.lower() if language else "unknown",
            region=_gdelt_country_to_region(country) or self.region_hint,
            raw=art,
        )


def _gdelt_country_to_region(country_code: str) -> str:
    """Mapeia código de país GDELT para nome de região legível."""
    _MAP = {
        "BR": "Brasil", "PT": "Portugal", "AO": "Angola",
        "UAE": "Emirados Arabes Unidos", "AE": "Emirados Arabes Unidos",
        "US": "EUA", "GB": "Reino Unido", "DE": "Alemanha",
        "FR": "França", "CN": "China", "JP": "Japão",
        "IN": "Índia", "MZ": "Moçambique", "ZA": "África do Sul",
        "NG": "Nigéria", "KE": "Quênia", "GH": "Gana",
    }
    return _MAP.get(country_code.upper(), country_code)
