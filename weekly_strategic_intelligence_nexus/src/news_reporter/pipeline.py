from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from news_reporter.collectors import build_collector
from news_reporter.config import AppConfig
from news_reporter.deduplicator import Deduplicator
from news_reporter.filters import FilterEngine
from news_reporter.models import ExecutionCounters, ExecutionResult, NewsItem
from news_reporter.market_snapshot import fetch_market_snapshot
from news_reporter.normalizer import Normalizer
from news_reporter.opportunities import OpportunityAnalyzer
from news_reporter.paths import get_project_root
from news_reporter.persistence import append_execution_history
from news_reporter.report import ReportComposer
from news_reporter.scoring import Scorer
from news_reporter.summarizer import Summarizer
from news_reporter.template_paths import resolve_templates_dir

logger = logging.getLogger(__name__)


class WeeklyReporterPipeline:
    def __init__(self, cfg: AppConfig, env: dict[str, str]) -> None:
        self.cfg = cfg
        self.env = env
        self.runtime = cfg.runtime
        self.monitoring = cfg.monitoring

    def run(self) -> ExecutionResult:
        started = datetime.now(timezone.utc)
        counters = ExecutionCounters()

        raw_items, source_errors = self._collect_all()
        counters.collected = len(raw_items)

        normalized = Normalizer(self.monitoring).normalize(raw_items)
        counters.normalized = len(normalized)

        filtered, filter_logs = FilterEngine(self.cfg.filters, self.monitoring).apply(normalized)
        counters.filtered = len(filtered)

        deduped = Deduplicator(self.cfg.deduplication).deduplicate_and_merge(filtered)
        counters.deduplicated = len(deduped)

        scored = Scorer(self.cfg.scoring, self.monitoring).score_items(deduped)
        analyzed = OpportunityAnalyzer().annotate(scored)

        max_news = int(self.cfg.project.get("max_news", 50))
        approved = sorted(analyzed, key=lambda x: x.score, reverse=True)[:max_news]
        counters.approved = len(approved)

        output_language = self.cfg.project.get("output_language", "pt")
        summarizer = Summarizer(output_language=output_language)
        approved = summarizer.summarize(approved)
        synthesis = summarizer.weekly_synthesis(approved, expected_regions=self.monitoring.get("regions", []))

        output_dir = self._resolve_runtime_path(self.runtime.get("output_dir", "output"))
        templates_dir = resolve_templates_dir()
        composer = ReportComposer(
            templates_dir=templates_dir,
            max_images=int(self.cfg.project.get("max_images", 8)),
            include_images=bool(self.cfg.project.get("include_images", True)),
        )
        report_html, report_text, report_path_html = composer.compose(
            approved,
            synthesis,
            self.cfg.project.get("report_title", "Relatório Semanal"),
            datetime.now(timezone.utc),
            output_dir,
            self.cfg.project.get("report_theme", "light"),
            self.monitoring.get("regions", []),
            {
                "max_news": max_news,
                "theme": self.cfg.project.get("report_theme", "light"),
                "priority_keywords": self.monitoring.get("priority_keywords", []),
            },
            market_snapshot=fetch_market_snapshot(timeout=int(self.runtime.get("per_source_timeout_seconds", 8))),
        )

        finished = datetime.now(timezone.utc)
        result = ExecutionResult(
            started_at=started,
            finished_at=finished,
            counters=counters,
            report_html=report_html,
            report_text=report_text,
            report_path_html=report_path_html,
            approved_items=approved,
            warnings=filter_logs,
            source_errors=source_errors,
        )

        if bool(self.runtime.get("keep_execution_history", True)):
            append_execution_history(self._resolve_runtime_path(self.runtime.get("history_file", "data/history.json")), result)

        logger.info(
            "Resumo execução | coletados=%s normalizados=%s filtrados=%s deduplicados=%s aprovados=%s",
            counters.collected,
            counters.normalized,
            counters.filtered,
            counters.deduplicated,
            counters.approved,
        )
        logger.info("Artefato gerado | html=%s", report_path_html)

        for msg in filter_logs:
            logger.info(msg)

        if source_errors:
            logger.warning("Erros por fonte: %s", source_errors)

        return result

    def _collect_all(self) -> tuple[list[NewsItem], list[str]]:
        items: list[NewsItem] = []
        errors: list[str] = []

        for source in self.cfg.sources:
            if not source.get("enabled", True):
                continue
            source_id = source.get("id", "unknown")
            try:
                collector = build_collector(source, self.runtime, self.env)
                source_items = collector.collect()
                items.extend(source_items)
                logger.info("Fonte coletada com sucesso: %s (itens=%s)", source_id, len(source_items), extra={"source_id": source_id, "step": "collect"})
            except Exception as exc:  # noqa: BLE001
                msg = f"Fonte {source_id} falhou: {exc}"
                errors.append(msg)
                logger.exception(msg, extra={"source_id": source_id, "step": "collect"})

        return items, errors

    def _resolve_runtime_path(self, relative_or_abs_path: str) -> str:
        path = Path(relative_or_abs_path)
        if path.is_absolute():
            path.parent.mkdir(parents=True, exist_ok=True)
            return str(path)

        project_root = get_project_root()
        full = project_root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        return str(full)
