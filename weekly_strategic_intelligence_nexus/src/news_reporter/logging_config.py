from __future__ import annotations

import logging
from pathlib import Path


class SemiStructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        source_id = getattr(record, "source_id", None)
        step = getattr(record, "step", None)
        if source_id:
            base += f" | source_id={source_id}"
        if step:
            base += f" | step={step}"
        return base


def setup_logging(log_dir: str, level: str = "INFO") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(level.upper())
    logger.handlers.clear()

    formatter = SemiStructuredFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(Path(log_dir) / "weekly_reporter.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
