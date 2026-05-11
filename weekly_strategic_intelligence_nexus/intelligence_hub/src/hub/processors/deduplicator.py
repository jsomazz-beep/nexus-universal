"""
Deduplicador de notícias por similaridade de título e URL.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from hub.models import NewsItem

logger = logging.getLogger(__name__)


def _normalize_title(title: str) -> str:
    """Normaliza título para comparação."""
    t = title.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # Remove stopwords comuns PT/EN
    _STOP = {
        "o", "a", "os", "as", "de", "do", "da", "dos", "das", "em", "no", "na",
        "nos", "nas", "e", "ou", "que", "se", "por", "para", "com", "um", "uma",
        "the", "a", "an", "in", "on", "at", "of", "to", "and", "or", "for",
        "is", "are", "was", "were", "be", "been", "by", "this", "that", "it",
    }
    words = [w for w in t.split() if w not in _STOP and len(w) > 2]
    return " ".join(words)


def _title_fingerprint(title: str) -> str:
    """Gera fingerprint do título normalizado."""
    norm = _normalize_title(title)
    return hashlib.md5(norm.encode()).hexdigest()


def _jaccard_similarity(a: str, b: str) -> float:
    """Calcula similaridade Jaccard entre dois conjuntos de palavras."""
    set_a = set(_normalize_title(a).split())
    set_b = set(_normalize_title(b).split())
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _normalize_url(url: str) -> str:
    """Normaliza URL removendo parâmetros de rastreamento."""
    # Remove parâmetros UTM e similares
    url = re.sub(r"[?&](utm_[^&]+|source=[^&]+|ref=[^&]+|campaign=[^&]+)", "", url)
    url = url.rstrip("?&/")
    # Remove protocolo e www para comparação
    url = re.sub(r"^https?://(www\.)?", "", url.lower())
    return url


class Deduplicator:
    """Remove duplicatas de uma lista de NewsItem."""

    def __init__(self, dedup_cfg: dict[str, Any]) -> None:
        self.threshold: float = float(dedup_cfg.get("title_similarity_threshold", 0.75))
        self.use_url_exact: bool = bool(dedup_cfg.get("url_exact_match", True))

    def run(self, items: list[NewsItem]) -> list[NewsItem]:
        """Deduplicar: mantém o item com maior score ou mais fontes."""
        if not items:
            return []

        # Fase 1: URL exata
        if self.use_url_exact:
            items = self._dedup_by_url(items)

        # Fase 2: Similaridade de título
        items = self._dedup_by_title(items)

        return items

    def _dedup_by_url(self, items: list[NewsItem]) -> list[NewsItem]:
        seen_urls: dict[str, NewsItem] = {}
        result: list[NewsItem] = []
        for item in items:
            norm = _normalize_url(item.url)
            if norm in seen_urls:
                existing = seen_urls[norm]
                # Mesclar fontes
                existing.merged_count += 1
                if item.source_id not in existing.merged_sources:
                    existing.merged_sources.append(item.source_id)
            else:
                seen_urls[norm] = item
                result.append(item)
        return result

    def _dedup_by_title(self, items: list[NewsItem]) -> list[NewsItem]:
        result: list[NewsItem] = []
        for item in items:
            matched = False
            for existing in result:
                sim = _jaccard_similarity(item.title, existing.title)
                if sim >= self.threshold:
                    # Mesclar no existente
                    existing.merged_count += 1
                    if item.source_id not in existing.merged_sources:
                        existing.merged_sources.append(item.source_id)
                    # Manter o conteúdo mais longo
                    if len(item.content) > len(existing.content):
                        existing.content = item.content
                    # Manter imagem se existente não tem
                    if not existing.image_url and item.image_url:
                        existing.image_url = item.image_url
                    matched = True
                    break
            if not matched:
                result.append(item)
        return result
