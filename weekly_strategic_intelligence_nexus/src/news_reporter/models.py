from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SourceSecondaryLink:
    source_id: str
    source_name: str
    url: str


@dataclass
class NewsItem:
    source_id: str
    source_name: str
    title: str
    subtitle: str | None
    url: str
    published_at: datetime | None
    collected_at: datetime
    raw_language: str | None
    description: str | None
    content: str | None
    image_url: str | None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    normalized_text: str = ""
    normalized_language: str = ""
    region: str = "Indefinida"
    themes: list[str] = field(default_factory=list)
    detected_keywords: list[str] = field(default_factory=list)
    detected_associated_keywords: list[str] = field(default_factory=list)
    opportunity_types: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)

    score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)
    opportunity_exists: bool = False
    opportunity_why: str = ""
    inclusion_reason: str = ""

    translated_title_pt: str = ""
    short_summary_pt: str = ""
    executive_summary_pt: str = ""

    secondary_links: list[SourceSecondaryLink] = field(default_factory=list)


@dataclass
class ExecutionCounters:
    collected: int = 0
    normalized: int = 0
    filtered: int = 0
    deduplicated: int = 0
    approved: int = 0


@dataclass
class ExecutionResult:
    started_at: datetime
    finished_at: datetime
    counters: ExecutionCounters
    report_html: str
    report_text: str
    report_path_html: str
    approved_items: list[NewsItem]
    warnings: list[str] = field(default_factory=list)
    source_errors: list[str] = field(default_factory=list)
