from __future__ import annotations

from typing import Callable

from news_reporter.config import AppConfig
from news_reporter.models import ExecutionResult
from news_reporter.pipeline import WeeklyReporterPipeline


class NexusCompatiblePipeline:
    """
    Nexus-like facade for orchestration.

    Keeps feature parity by delegating to the legacy pipeline while exposing
    a stable entrypoint for future module migration.
    """

    def __init__(
        self,
        cfg: AppConfig,
        env: dict[str, str],
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> None:
        self._legacy = WeeklyReporterPipeline(cfg, env)
        self._progress_callback = progress_callback

    def run(self) -> ExecutionResult:
        if self._progress_callback:
            self._progress_callback("Iniciando pipeline Nexus-compatible...", 5)
        result = self._legacy.run()
        if self._progress_callback:
            self._progress_callback("Pipeline concluída", 100)
        return result
