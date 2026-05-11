"""Nexus Intelligence — main pipeline."""
from __future__ import annotations

import concurrent.futures
import logging
from datetime import datetime, timezone
from pathlib import Path

from nexus.classifier import TopicClassifier, OpportunityDetector
from nexus.collectors import build_collector
from nexus.config import AppConfig
from nexus.deduplicator import Deduplicator
from nexus.filters import FilterEngine
from nexus.models import ExecutionCounters, ExecutionResult, NewsItem
from nexus.normalizer import Normalizer
from nexus.paths import get_project_root
from nexus.report import ReportComposer
from nexus.scoring import Scorer
from nexus.summarizer import Summarizer

logger = logging.getLogger(__name__)


class NexusPipeline:
    def __init__(self, cfg: AppConfig, env: dict[str, str], progress_cb=None) -> None:
        self.cfg = cfg
        self.env = env
        self.progress_cb = progress_cb or (lambda msg, pct: None)

    def run(self) -> ExecutionResult:
        started = datetime.now(timezone.utc)
        counters = ExecutionCounters()
        project_root = get_project_root()

        self.progress_cb("Coletando fontes…", 5)
        raw_items, source_errors = self._collect_all()
        counters.collected = len(raw_items)
        logger.info("Collected: %d items from %d sources", counters.collected, len(self.cfg.sources))

        self.progress_cb("Normalizando textos…", 25)
        normalized = Normalizer(self.cfg.monitoring).normalize(raw_items)
        counters.normalized = len(normalized)

        self.progress_cb("Aplicando filtros…", 35)
        filtered, filter_logs = FilterEngine(self.cfg.filters, self.cfg.monitoring).apply(normalized)
        counters.filtered = len(filtered)

        self.progress_cb("Deduplicando…", 45)
        deduped = Deduplicator(self.cfg.deduplication).deduplicate_and_merge(filtered)
        counters.deduplicated = len(deduped)

        self.progress_cb("Classificando tópicos…", 55)
        classified = TopicClassifier(self.cfg.topics).classify(deduped)
        classified = OpportunityDetector(self.cfg.monitoring.get("opportunity_signals", {})).detect(classified)

        self.progress_cb("Calculando scores…", 65)
        scored = Scorer(self.cfg.scoring, self.cfg.monitoring).score_items(classified)

        max_news = int(self.cfg.project.get("max_news", 80))
        approved = sorted(scored, key=lambda x: x.score, reverse=True)[:max_news]
        counters.approved = len(approved)

        self.progress_cb("Gerando resumos…", 75)
        gemini_key = self.env.get("GEMINI_API_KEY", "")
        output_lang = self.cfg.project.get("output_language", "pt")
        summarizer = Summarizer(output_language=output_lang, gemini_api_key=gemini_key)
        approved = summarizer.summarize(approved)
        topic_syntheses = summarizer.build_topic_syntheses(approved, self.cfg.topics)
        regional_syntheses = summarizer.build_regional_syntheses(
            approved, self.cfg.monitoring.get("regions", [])
        )

        self.progress_cb("Compondo relatório…", 88)
        output_dir = self._resolve(self.cfg.runtime.get("output_dir", "output"))
        composer = ReportComposer()
        report_html, report_path = composer.compose(
            items=approved,
            topic_syntheses=topic_syntheses,
            regional_syntheses=regional_syntheses,
            title=self.cfg.project.get("report_title", "Nexus Intelligence"),
            theme=self.cfg.project.get("report_theme", "dark"),
            output_dir=output_dir,
            generated_at=datetime.now(timezone.utc),
        )

        self.progress_cb("Concluído!", 100)
        finished = datetime.now(timezone.utc)

        logger.info(
            "Pipeline done | collected=%d normalized=%d filtered=%d deduped=%d approved=%d | %.1fs",
            counters.collected, counters.normalized, counters.filtered, counters.deduplicated,
            counters.approved, (finished - started).total_seconds()
        )

        return ExecutionResult(
            started_at=started,
            finished_at=finished,
            counters=counters,
            approved_items=approved,
            topic_syntheses=topic_syntheses,
            regional_syntheses=regional_syntheses,
            report_path_html=report_path,
            report_html=report_html,
            warnings=filter_logs,
            source_errors=source_errors,
        )

    def _collect_all(self) -> tuple[list[NewsItem], list[str]]:
        sources = [s for s in self.cfg.sources if s.get("enabled", True)]
        max_workers = int(self.cfg.runtime.get("max_concurrent_sources", 10))
        items: list[NewsItem] = []
        errors: list[str] = []

        def fetch(source: dict):
            sid = source.get("id", "?")
            try:
                collector = build_collector(source, self.cfg.runtime, self.env)
                result = collector.collect()
                logger.info("Source OK: %s (%d items)", sid, len(result))
                return result, None
            except Exception as exc:
                msg = f"{sid}: {exc}"
                logger.warning("Source FAIL: %s", msg)
                return [], msg

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(fetch, src): src for src in sources}
            for future in concurrent.futures.as_completed(futures):
                result, err = future.result()
                items.extend(result)
                if err:
                    errors.append(err)

        return items, errors

    def _resolve(self, rel_or_abs: str) -> str:
        p = Path(rel_or_abs)
        if p.is_absolute():
            p.mkdir(parents=True, exist_ok=True)
            return str(p)
        full = get_project_root() / p
        full.mkdir(parents=True, exist_ok=True)
        return str(full)
