"""
Tradutor automático para PT-BR.

Traduz título e resumo de artigos que não estão em português,
usando deep-translator (Google Translate, gratuito, sem chave de API).

Roda em paralelo para não atrasar o pipeline.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Sequence

from hub.models import NewsItem

logger = logging.getLogger(__name__)

# Idiomas considerados "já em português" (não traduzir)
_PT_LANGS = {"pt", "pt-br", "pt-pt", "por"}

# Tamanho máximo de texto enviado por chamada de tradução (chars)
_MAX_CHARS = 4000


def _is_portuguese(lang: str | None) -> bool:
    if not lang:
        return False
    return lang.lower().replace("_", "-").split("-")[0] in _PT_LANGS


def _detect_lang(text: str) -> str | None:
    try:
        from langdetect import detect, LangDetectException
        return detect(text)
    except Exception:
        return None


def _translate_text(text: str, src: str = "auto") -> str:
    """Traduz um texto para PT-BR via deep-translator (Google backend, gratuito)."""
    if not text or not text.strip():
        return text
    try:
        from deep_translator import GoogleTranslator
        chunk = text[:_MAX_CHARS]
        result = GoogleTranslator(source=src, target="pt").translate(chunk)
        return result or text
    except Exception as exc:
        logger.debug("Erro ao traduzir: %s", exc)
        return text


def _translate_item(item: NewsItem) -> NewsItem:
    """Detecta o idioma e traduz título + conteúdo se não for PT."""
    # Detecta idioma pelo título (mais rápido que pelo conteúdo inteiro)
    text_for_detection = f"{item.title} {item.content[:200]}"
    lang = item.language or _detect_lang(text_for_detection)

    if _is_portuguese(lang):
        return item  # já em PT, nada a fazer

    # Traduz título
    original_title = item.title
    item.title = _translate_text(item.title, src="auto")

    # Traduz conteúdo (até 4000 chars)
    if item.content:
        item.content = _translate_text(item.content[:_MAX_CHARS], src="auto")

    # Marca que foi traduzido (guarda original no raw)
    item.raw["original_title"] = original_title
    item.raw["original_lang"] = lang or "unknown"
    item.raw["translated"] = True

    logger.debug(
        "Traduzido [%s→pt]: %s", lang or "?", original_title[:60]
    )
    return item


def translate_items(
    items: Sequence[NewsItem],
    workers: int = 6,
    delay_between: float = 0.15,
) -> list[NewsItem]:
    """
    Traduz artigos não-portugueses para PT-BR em paralelo.

    Args:
        items: lista de NewsItems
        workers: threads paralelas (não exagerar para não ser bloqueado)
        delay_between: pausa entre cada requisição por thread (segundos)

    Returns:
        Lista com artigos traduzidos onde necessário.
    """
    try:
        from deep_translator import GoogleTranslator  # noqa — checa disponibilidade
    except ImportError:
        logger.warning(
            "deep-translator não instalado. Instale com: pip install deep-translator\n"
            "A tradução automática está DESATIVADA."
        )
        return list(items)

    needs_translation = []
    already_pt = []

    for item in items:
        text_for_detection = f"{item.title} {item.content[:200]}"
        lang = item.language or _detect_lang(text_for_detection)
        if _is_portuguese(lang):
            already_pt.append(item)
        else:
            needs_translation.append(item)

    logger.info(
        "Tradução: %d artigos em PT (ok), %d para traduzir → PT-BR",
        len(already_pt), len(needs_translation),
    )

    if not needs_translation:
        return list(items)

    translated: list[NewsItem] = list(already_pt)
    errors = 0

    # Throttle: pequeno delay para não saturar a API gratuita
    def _translate_with_delay(it: NewsItem) -> NewsItem:
        time.sleep(delay_between)
        return _translate_item(it)

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="transl") as pool:
        futures = {pool.submit(_translate_with_delay, it): it for it in needs_translation}
        for fut in as_completed(futures):
            try:
                translated.append(fut.result())
            except Exception as exc:
                original = futures[fut]
                logger.warning("Falha ao traduzir '%s': %s", original.title[:40], exc)
                translated.append(original)  # mantém original se falhar
                errors += 1

    ok = len(needs_translation) - errors
    logger.info("Tradução concluída: %d/%d artigos traduzidos", ok, len(needs_translation))
    return translated
