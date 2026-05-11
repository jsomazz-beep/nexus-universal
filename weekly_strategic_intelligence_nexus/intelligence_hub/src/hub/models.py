"""
Modelos de dados centrais do Intelligence Hub.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    """Representa um item de notícia coletado de qualquer fonte."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    url: str
    source_id: str
    source_name: str
    source_type: str = "rss"  # rss, newsapi, gdelt, guardian, hackernews, reddit, nytimes

    # Conteúdo
    content: str = ""
    summary: str = ""
    author: str = ""
    image_url: Optional[str] = None

    # Metadados temporais
    published_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)

    # Classificação
    language: str = "unknown"
    region: str = ""
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    sentiment: float = 0.0  # -1.0 a 1.0

    # Scoring
    score: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    opportunity_signals: dict[str, list[str]] = Field(default_factory=dict)

    # Deduplicação
    duplicate_of: Optional[str] = None
    merged_sources: list[str] = Field(default_factory=list)
    merged_count: int = 1

    # Dados brutos
    raw: dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class SourceHealth(BaseModel):
    """Saúde de uma fonte de notícias."""

    source_id: str
    source_name: str
    last_checked: Optional[datetime] = None
    last_success: Optional[datetime] = None
    items_last_run: int = 0
    consecutive_failures: int = 0
    total_items_collected: int = 0
    avg_response_time_ms: float = 0.0
    is_healthy: bool = True
    error_message: str = ""


class RunCounters(BaseModel):
    """Contadores de uma execução do pipeline."""

    collected: int = 0
    filtered_out: int = 0
    deduplicated: int = 0
    approved: int = 0
    errors: int = 0
    sources_ok: int = 0
    sources_failed: int = 0


class ExecutionResult(BaseModel):
    """Resultado completo de uma execução do pipeline."""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime
    finished_at: datetime
    counters: RunCounters = Field(default_factory=RunCounters)
    approved_items: list[NewsItem] = Field(default_factory=list)
    source_errors: dict[str, str] = Field(default_factory=dict)
    report_path_html: Optional[str] = None
    synthesis: str = ""
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return self.counters.approved > 0


class WeeklySynthesis(BaseModel):
    """Síntese executiva semanal."""

    summary: str = ""
    key_signals: list[str] = Field(default_factory=list)
    top_regions: list[str] = Field(default_factory=list)
    top_categories: list[str] = Field(default_factory=list)
    opportunity_count: int = 0
    critical_alerts: list[str] = Field(default_factory=list)
