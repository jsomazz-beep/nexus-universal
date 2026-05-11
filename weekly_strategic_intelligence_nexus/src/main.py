from __future__ import annotations

import argparse
import os
from pathlib import Path

from news_reporter.config import load_config
from news_reporter.logging_config import setup_logging
from news_reporter.paths import get_project_root
from nexus_like.pipeline import NexusCompatiblePipeline
from news_reporter.runtime import load_env_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Weekly News Reporter")
    parser.add_argument("--config", default="config/config.yaml", help="Caminho do arquivo YAML de configuração")
    parser.add_argument("--env-file", default=".env", help="Caminho do arquivo .env")
    parser.add_argument(
        "--priority-keywords",
        default="",
        help="Lista CSV de palavras-chave prioritárias para sobrescrever a configuração desta execução",
    )
    parser.add_argument(
        "--max-news",
        type=int,
        default=0,
        help="Quantidade máxima de notícias para sobrescrever a configuração desta execução",
    )
    parser.add_argument(
        "--theme",
        default="",
        choices=["light", "dark_exec", "boardroom_print", ""],
        help="Tema visual do relatório: light, dark_exec, boardroom_print",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = load_config(args.config)
    priority_keywords_input = args.priority_keywords.strip() or os.getenv("NEWS_PRIORITY_KEYWORDS", "").strip()
    max_news_input = args.max_news if args.max_news and args.max_news > 0 else 0
    if max_news_input <= 0:
        try:
            max_news_input = int(os.getenv("NEWS_MAX_NEWS", "0") or 0)
        except ValueError:
            max_news_input = 0
    theme_input = args.theme.strip() or os.getenv("NEWS_REPORT_THEME", "").strip()

    if priority_keywords_input:
        override = [kw.strip() for kw in priority_keywords_input.split(",") if kw.strip()]
        if override:
            config.raw.setdefault("monitoring", {})
            config.raw["monitoring"]["priority_keywords"] = override
    if max_news_input and max_news_input > 0:
        config.raw.setdefault("project", {})
        config.raw["project"]["max_news"] = int(max_news_input)
    if theme_input:
        config.raw.setdefault("project", {})
        config.raw["project"]["report_theme"] = theme_input

    runtime_cfg = config.runtime
    log_dir = runtime_cfg.get("log_dir", "logs")
    if not Path(log_dir).is_absolute():
        log_dir = str(get_project_root() / log_dir)

    setup_logging(log_dir=log_dir, level=runtime_cfg.get("log_level", "INFO"))

    env = load_env_file(args.env_file)

    pipeline = NexusCompatiblePipeline(config, env)
    result = pipeline.run()

    print("Execução concluída")
    print(f"Relatório HTML: {result.report_path_html}")
    print(f"Aprovadas: {result.counters.approved}")


if __name__ == "__main__":
    main()
