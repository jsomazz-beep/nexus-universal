"""Nexus Intelligence — CLI entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nexus.config import load_config
from nexus.logging_config import setup_logging
from nexus.paths import get_project_root
from nexus.pipeline import NexusPipeline
from nexus.runtime import load_env_file


def main():
    parser = argparse.ArgumentParser(description="Nexus Intelligence CLI")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--max-news", type=int, default=0)
    parser.add_argument("--days", type=int, default=0)
    args = parser.parse_args()

    root = get_project_root()
    cfg = load_config(args.config)
    env = load_env_file(args.env_file)

    if args.max_news > 0:
        cfg.raw.setdefault("project", {})["max_news"] = args.max_news
    if args.days > 0:
        cfg.raw.setdefault("filters", {})["time_window_days"] = args.days

    setup_logging(str(root / "logs"), cfg.runtime.get("log_level", "INFO"))

    def progress(msg, pct):
        print(f"  [{pct:3d}%] {msg}")

    pipeline = NexusPipeline(cfg, env, progress)
    result = pipeline.run()

    print(f"\n✅ Relatório: {result.report_path_html}")
    print(f"   Coletadas={result.counters.collected} | Aprovadas={result.counters.approved}")


if __name__ == "__main__":
    main()
