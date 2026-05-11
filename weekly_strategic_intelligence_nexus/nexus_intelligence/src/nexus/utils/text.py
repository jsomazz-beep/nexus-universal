"""Nexus Intelligence — text and datetime utilities."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return normalize_whitespace(text)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", ascii_only).strip("_").lower() or "item"


def truncate(text: str, max_len: int = 500) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rsplit(" ", 1)
    return (cut[0] if len(cut) > 1 else text[:max_len]) + "…"


def extract_domain(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1) if m else url
