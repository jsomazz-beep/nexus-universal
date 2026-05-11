"""
Coletor The Guardian Open Platform API.
Chave gratuita disponível em: https://open-platform.theguardian.com/access/
12 milhões+ de artigos desde 1999 com busca avançada.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import requests

from hub.collectors.base import BaseCollector
from hub.models import NewsItem

logger = logging.getLogger(__name__)

GUARDIAN_API = "https://content.guardianapis.com/search"


class GuardianCollector(BaseCollector):
    """
    Coleta artigos da API The Guardian.
    Requer GUARDIAN_API_KEY no .env (plano gratuito disponível).
    """

    def collect(self) -> list[NewsItem]:
        api_key = self.app_cfg.guardian_api_key
        if not api_key:
            logger.debug("Guardian %s: sem chave de API, pulando.", self.source_id)
            return []

        query = self.source_cfg.get("query", "")
        section = self.source_cfg.get("section", "")
        page_size = int(self.source_cfg.get("page_size", 50))
        order_by = self.source_cfg.get("order_by", "newest")
        from_date = self.source_cfg.get("from_date", "")  # YYYY-MM-DD

        params: dict[str, Any] = {
            "api-key": api_key,
            "page-size": page_size,
            "order-by": order_by,
            "show-fields": "headline,body,thumbnail,byline,shortUrl",
        }
        if query:
            params["q"] = query
        if section:
            params["section"] = section
        if from_date:
            params["from-date"] = from_date

        try:
            resp = requests.get(
                GUARDIAN_API,
                params=params,
                timeout=self.timeout,
                headers=self._default_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Guardian %s erro: %s", self.source_id, exc)
            return []

        results = data.get("response", {}).get("results", [])
        items: list[NewsItem] = []
        for result in results:
            item = self._parse_result(result)
            if item:
                items.append(item)

        logger.info("Guardian %s: %d artigos", self.source_id, len(items))
        return items

    def _parse_result(self, result: dict[str, Any]) -> NewsItem | None:
        fields = result.get("fields", {})
        title = fields.get("headline") or result.get("webTitle", "")
        url = result.get("webUrl", "")
        if not title or not url:
            return None

        # Body text
        body = fields.get("body", "")
        # Strip basic HTML tags
        from html.parser import HTMLParser
        class _Strip(HTMLParser):
            def __init__(self):
                super().__init__()
                self._parts: list[str] = []
            def handle_data(self, data: str):
                self._parts.append(data)
            def text(self) -> str:
                return " ".join(self._parts).strip()
        s = _Strip(); s.feed(body)
        content = s.text()[:5000]

        # Data
        pub_dt: datetime | None = None
        raw_date = result.get("webPublicationDate", "")
        if raw_date:
            try:
                pub_dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except Exception:
                pass

        # Seção → categoria
        section_id = result.get("sectionId", "")
        section_name = result.get("sectionName", "")
        categories = [section_name] if section_name else []

        return NewsItem(
            title=title.strip(),
            url=url,
            source_id=self.source_id,
            source_name="The Guardian",
            source_type="guardian",
            content=content,
            author=fields.get("byline", ""),
            image_url=fields.get("thumbnail"),
            published_at=pub_dt,
            region=self.region_hint,
            categories=categories,
            tags=[section_id] if section_id else [],
            raw=result,
        )
