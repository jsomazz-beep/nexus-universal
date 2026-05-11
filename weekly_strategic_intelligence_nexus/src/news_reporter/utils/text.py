from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from html import unescape
from typing import Iterable

from bs4 import BeautifulSoup
from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        from dateutil import parser

        dt = parser.parse(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def clean_html_text(text: str | None) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    cleaned = soup.get_text(" ", strip=True)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")


def normalize_for_match(text: str) -> str:
    text = normalize_unicode(text.lower())
    text = strip_accents(text)
    # Mantém letras/dígitos Unicode (inclui CJK) para permitir matching multilíngue.
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_language_safe(text: str, fallback: str = "unknown") -> str:
    payload = text.strip()
    if len(payload) < 20:
        return fallback
    try:
        return detect(payload)
    except LangDetectException:
        return fallback


def contains_any(text: str, terms: Iterable[str]) -> list[str]:
    normalized = normalize_for_match(text)
    found: list[str] = []
    for term in terms:
        normalized_term = normalize_for_match(term)
        if not normalized_term:
            continue

        # Siglas pontuadas (ex.: "I.A.", "A.I.") viram "i a" na normalização;
        # aqui colapsamos para "ia"/"ai" para evitar ruído por sequência com espaço.
        if re.fullmatch(r"(?:[a-z]\s+){1,6}[a-z]", normalized_term):
            normalized_term = normalized_term.replace(" ", "")

        matched = False
        if " " in normalized_term:
            # Frase: exige fronteira de palavra.
            phrase = re.sub(r"\s+", r"\\s+", re.escape(normalized_term))
            matched = bool(re.search(rf"(?<!\w){phrase}(?!\w)", normalized, flags=re.UNICODE))
        elif len(normalized_term) <= 3 and re.fullmatch(r"[a-z0-9]+", normalized_term):
            # Termo curto: matching exato por token.
            matched = bool(re.search(rf"(?<!\w){re.escape(normalized_term)}(?!\w)", normalized, flags=re.UNICODE))
        else:
            matched = normalized_term in normalized

        if matched:
            found.append(term)
    return found
