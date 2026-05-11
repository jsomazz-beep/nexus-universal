"""
Pipeline principal do Intelligence Hub.
Coleta em paralelo, processa, deduPlica, pontua e gera relatório.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hub.collectors import build_collector
from hub.collectors.og_enricher import enrich_images
from hub.config import AppConfig
from hub.models import ExecutionResult, NewsItem, RunCounters, WeeklySynthesis
from hub.processors.deduplicator import Deduplicator
from hub.processors.filter import FilterEngine
from hub.processors.scorer import Scorer
from hub.processors.translator import translate_items
from hub.report.composer import ReportComposer
from hub.storage.database import Database

logger = logging.getLogger(__name__)


class IntelligenceHubPipeline:
    """Pipeline completo de coleta e análise de inteligência."""

    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        self.db = Database(cfg.runtime.get("db_path", "data/hub.db"))

    # ── Execução principal ─────────────────────────────────────────────────

    def run(self, overrides: dict[str, Any] | None = None) -> ExecutionResult:
        started = datetime.now(timezone.utc)
        overrides = overrides or {}
        counters = RunCounters()

        # 1. Coleta paralela de todas as fontes
        logger.info("Iniciando coleta de %d fontes configuradas...", len(self.cfg.sources))
        raw_items, source_errors = self._collect_parallel()
        counters.collected = len(raw_items)
        counters.sources_ok = len(self.cfg.sources) - len(source_errors)
        counters.sources_failed = len(source_errors)
        logger.info("Coletados %d itens brutos (%d fontes com erro)", len(raw_items), len(source_errors))

        # 2. Filtro
        max_age_days = int(self.cfg.filters.get("time_window_days", 7))
        filter_engine = FilterEngine(self.cfg.filters, self.cfg.monitoring)
        filtered, filter_logs = filter_engine.apply(raw_items)
        counters.filtered_out = counters.collected - len(filtered)
        logger.info("Após filtro: %d itens (%d removidos)", len(filtered), counters.filtered_out)

        # 3. Deduplicação
        deduped = Deduplicator(self.cfg.deduplication).run(filtered)
        counters.deduplicated = len(filtered) - len(deduped)
        logger.info("Após deduplicação: %d itens únicos", len(deduped))

        # 3b. Tradução automática para PT-BR (artigos em outros idiomas)
        logger.info("Traduzindo artigos não-portugueses para PT-BR...")
        deduped = translate_items(deduped, workers=5, delay_between=0.1)

        # 4. Scoring e ordenação
        scored = Scorer(self.cfg.scoring, self.cfg.monitoring).score(deduped)
        max_news = int(overrides.get("max_news", self.cfg.max_news))
        approved = sorted(scored, key=lambda x: x.score, reverse=True)[:max_news]
        counters.approved = len(approved)
        logger.info("Aprovados (top-%d): %d itens", max_news, len(approved))

        # 4b. Enriquecimento de imagens OG — só os artigos aprovados (eficiente)
        logger.info("Buscando imagens OG para artigos aprovados sem foto...")
        approved = enrich_images(approved, workers=8, timeout=5, max_to_enrich=len(approved))

        # 5. Síntese
        synthesis = self._build_synthesis(approved)

        # 6. Relatório
        output_dir = Path(self.cfg.runtime.get("output_dir", "output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        theme = overrides.get("theme", self.cfg.report_theme)
        composer = ReportComposer()
        report_path = composer.compose(
            items=approved,
            synthesis=synthesis,
            output_dir=output_dir,
            title=self.cfg.project.get("report_title", "Intelligence Hub Report"),
            theme=theme,
            config=self.cfg,
        )

        # 7. Persistência
        self.db.save_items(approved)
        self.db.save_run(started, datetime.now(timezone.utc), counters, report_path)

        finished = datetime.now(timezone.utc)
        return ExecutionResult(
            started_at=started,
            finished_at=finished,
            counters=counters,
            approved_items=approved,
            source_errors=source_errors,
            report_path_html=str(report_path),
            synthesis=synthesis.summary,
            duration_seconds=(finished - started).total_seconds(),
        )

    # ── Coleta paralela ────────────────────────────────────────────────────

    def _collect_parallel(self) -> tuple[list[NewsItem], dict[str, str]]:
        enabled_sources = [s for s in self.cfg.sources if s.get("enabled", True)]
        all_items: list[NewsItem] = []
        errors: dict[str, str] = {}
        max_workers = int(self.cfg.runtime.get("parallel_workers", 10))
        timeout = int(self.cfg.runtime.get("per_source_timeout_seconds", 20))

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._collect_source, src, timeout): src["id"]
                for src in enabled_sources
            }
            for future in as_completed(futures, timeout=timeout * 2):
                src_id = futures[future]
                try:
                    items = future.result(timeout=5)
                    all_items.extend(items)
                    logger.debug("Fonte %s: %d itens", src_id, len(items))
                except Exception as exc:
                    errors[src_id] = str(exc)
                    logger.warning("Fonte %s falhou: %s", src_id, exc)

        return all_items, errors

    def _collect_source(self, source_cfg: dict[str, Any], timeout: int) -> list[NewsItem]:
        collector = build_collector(source_cfg, self.cfg)
        return collector.collect()

    # ── Síntese ────────────────────────────────────────────────────────────

    def _build_synthesis(self, items: list[NewsItem]) -> WeeklySynthesis:
        if not items:
            return WeeklySynthesis(summary="Nenhum item aprovado nesta execução.")

        # Top regiões
        region_counts: dict[str, int] = {}
        for item in items:
            r = item.region or "Global"
            region_counts[r] = region_counts.get(r, 0) + 1
        top_regions = sorted(region_counts, key=region_counts.get, reverse=True)[:5]

        # Top categorias
        cat_counts: dict[str, int] = {}
        for item in items:
            for cat in item.categories:
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
        top_cats = sorted(cat_counts, key=cat_counts.get, reverse=True)[:5]

        # Sinais de oportunidade
        opp_count = sum(1 for i in items if i.opportunity_signals)

        # Alertas críticos (score > 0.85)
        critical = [i.title for i in items if i.score >= 0.85][:5]

        # Resumo textual simples
        summary_lines = [
            f"Análise de {len(items)} notícias curadas de {len(set(i.source_id for i in items))} fontes distintas.",
            f"Principais regiões monitoradas: {', '.join(top_regions)}.",
            f"Categorias em destaque: {', '.join(top_cats)}.",
            f"{opp_count} itens apresentam sinais de oportunidade de negócio.",
        ]
        if critical:
            summary_lines.append(f"Destaques críticos: {'; '.join(critical[:3])}.")

        return WeeklySynthesis(
            summary=" ".join(summary_lines),
            key_signals=critical,
            top_regions=top_regions,
            top_categories=top_cats,
            opportunity_count=opp_count,
            critical_alerts=critical,
        )
