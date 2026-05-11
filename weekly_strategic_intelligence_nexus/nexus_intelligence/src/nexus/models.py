"""Nexus Intelligence — models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class NewsItem:
    source_id: str
    source_name: str
    source_authority: int  # 1-10
    title: str
    url: str
    published_at: datetime | None
    collected_at: datetime
    description: str | None = None
    content: str | None = None
    image_url: str | None = None
    raw_language: str | None = None
    subtitle: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # enriched
    normalized_text: str = ""
    normalized_language: str = ""
    region: str = "Global"
    topics: list[str] = field(default_factory=list)
    detected_keywords: list[str] = field(default_factory=list)
    opportunity_types: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)

    score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)
    opportunity_exists: bool = False

    translated_title: str = ""
    short_summary: str = ""
    ai_summary: str = ""

    secondary_sources: list[str] = field(default_factory=list)


@dataclass
class ExecutionCounters:
    collected: int = 0
    normalized: int = 0
    filtered: int = 0
    deduplicated: int = 0
    approved: int = 0


@dataclass
class TopicSynthesis:
    topic: str
    icon: str
    color: str
    count: int
    top_items: list[NewsItem]
    key_insight: str = ""


@dataclass
class RegionalSynthesis:
    region: str
    count: int
    top_items: list[NewsItem]
    signal_strength: str = "moderate"  # low / moderate / high / critical


@dataclass
class ExecutionResult:
    started_at: datetime
    finished_at: datetime
    counters: ExecutionCounters
    approved_items: list[NewsItem]
    topic_syntheses: list[TopicSynthesis]
    regional_syntheses: list[RegionalSynthesis]
    report_path_html: str
    report_html: str = ""
    warnings: list[str] = field(default_factory=list)
    source_errors: list[str] = field(default_factory=list)
