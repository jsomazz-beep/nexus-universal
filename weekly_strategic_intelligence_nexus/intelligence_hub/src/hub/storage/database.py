"""
Camada de persistência usando SQLite.
Muito mais robusto que o JSON do projeto anterior.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hub.models import NewsItem, RunCounters

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS news_items (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    source_id TEXT,
    source_name TEXT,
    source_type TEXT,
    content TEXT,
    summary TEXT,
    author TEXT,
    image_url TEXT,
    published_at TEXT,
    collected_at TEXT,
    language TEXT,
    region TEXT,
    categories TEXT,   -- JSON list
    tags TEXT,         -- JSON list
    score REAL,
    opportunity_signals TEXT,  -- JSON dict
    merged_count INTEGER DEFAULT 1,
    run_id TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT,
    finished_at TEXT,
    duration_seconds REAL,
    collected INTEGER,
    filtered_out INTEGER,
    deduplicated INTEGER,
    approved INTEGER,
    errors INTEGER,
    sources_ok INTEGER,
    sources_failed INTEGER,
    report_path TEXT
);

CREATE INDEX IF NOT EXISTS idx_items_run ON news_items(run_id);
CREATE INDEX IF NOT EXISTS idx_items_score ON news_items(score DESC);
CREATE INDEX IF NOT EXISTS idx_items_published ON news_items(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_items_source ON news_items(source_id);
"""


class Database:
    """Gerencia persistência de notícias e histórico de execuções."""

    def __init__(self, db_path: str = "data/hub.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # ── Itens de notícia ────────────────────────────────────────────────────

    def save_items(self, items: list[NewsItem], run_id: str = "") -> int:
        """Salva lista de itens. Ignora duplicatas por ID."""
        if not items:
            return 0
        rows = [_item_to_row(item, run_id) for item in items]
        with self._connect() as conn:
            conn.executemany(
                """INSERT OR IGNORE INTO news_items
                   (id, title, url, source_id, source_name, source_type,
                    content, summary, author, image_url, published_at,
                    collected_at, language, region, categories, tags,
                    score, opportunity_signals, merged_count, run_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            return conn.total_changes

    def get_recent_items(self, limit: int = 100, region: str = "") -> list[dict[str, Any]]:
        """Retorna itens recentes do banco."""
        sql = "SELECT * FROM news_items"
        params: list[Any] = []
        if region:
            sql += " WHERE region = ?"
            params.append(region)
        sql += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get_top_items_by_run(self, run_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Retorna os top itens de uma execução específica."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM news_items WHERE run_id=? ORDER BY score DESC LIMIT ?",
                (run_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    # ── Execuções ────────────────────────────────────────────────────────────

    def save_run(
        self,
        started: datetime,
        finished: datetime,
        counters: RunCounters,
        report_path: Any = None,
        run_id: str = "",
    ) -> str:
        duration = (finished - started).total_seconds()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO runs
                   (run_id, started_at, finished_at, duration_seconds,
                    collected, filtered_out, deduplicated, approved, errors,
                    sources_ok, sources_failed, report_path)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id or str(finished.timestamp()),
                    started.isoformat(),
                    finished.isoformat(),
                    duration,
                    counters.collected,
                    counters.filtered_out,
                    counters.deduplicated,
                    counters.approved,
                    counters.errors,
                    counters.sources_ok,
                    counters.sources_failed,
                    str(report_path) if report_path else "",
                ),
            )
        return run_id

    def get_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_source_stats(self) -> list[dict[str, Any]]:
        """Estatísticas por fonte."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT source_id, source_name, COUNT(*) as total,
                          AVG(score) as avg_score,
                          MAX(collected_at) as last_seen
                   FROM news_items
                   GROUP BY source_id
                   ORDER BY total DESC"""
            ).fetchall()
        return [dict(row) for row in rows]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _item_to_row(item: NewsItem, run_id: str) -> tuple:
    return (
        item.id,
        item.title,
        item.url,
        item.source_id,
        item.source_name,
        item.source_type,
        item.content[:10000] if item.content else "",
        item.summary,
        item.author,
        item.image_url,
        item.published_at.isoformat() if item.published_at else None,
        item.collected_at.isoformat(),
        item.language,
        item.region,
        json.dumps(item.categories, ensure_ascii=False),
        json.dumps(item.tags, ensure_ascii=False),
        item.score,
        json.dumps(item.opportunity_signals, ensure_ascii=False),
        item.merged_count,
        run_id,
    )
