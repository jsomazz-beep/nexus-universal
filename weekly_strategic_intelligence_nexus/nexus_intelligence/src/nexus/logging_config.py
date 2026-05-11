"""Nexus Intelligence — logging setup."""
from __future__ import annotations

import logging
import os
from pathlib import Path


def setup_logging(log_dir: str = "logs", level: str = "INFO") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "nexus.log"

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.FileHandler(str(log_file), encoding="utf-8"),
    ]

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
        force=True,
    )
