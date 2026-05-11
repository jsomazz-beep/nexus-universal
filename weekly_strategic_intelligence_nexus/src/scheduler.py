from __future__ import annotations

import argparse
import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from news_reporter.config import load_config
from news_reporter.logging_config import setup_logging
from nexus_like.pipeline import NexusCompatiblePipeline
from news_reporter.runtime import load_env_file

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Weekly News Reporter Scheduler")
    parser.add_argument("--config", default="config/config.yaml", help="Caminho do arquivo YAML de configuração")
    parser.add_argument("--env-file", default=".env", help="Caminho do arquivo .env")
    parser.add_argument("--run-now", action="store_true", help="Executa imediatamente antes de iniciar agenda")
    return parser.parse_args()


def run_once(config_path: str, env_file: str) -> None:
    cfg = load_config(config_path)
    env = load_env_file(env_file)
    pipeline = NexusCompatiblePipeline(cfg, env)
    result = pipeline.run()
    logger.info(
        "Execução agendada concluída | aprovadas=%s | html=%s",
        result.counters.approved,
        result.report_path_html,
    )


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    runtime_cfg = cfg.runtime
    setup_logging(
        log_dir=runtime_cfg.get("log_dir", "logs"),
        level=runtime_cfg.get("log_level", "INFO"),
    )

    scheduler_cfg = runtime_cfg.get("scheduler", {})
    day_of_week = scheduler_cfg.get("day_of_week", "mon")
    hour = int(scheduler_cfg.get("hour", 8))
    minute = int(scheduler_cfg.get("minute", 0))
    timezone = scheduler_cfg.get("timezone", "UTC")

    logger.info(
        "Iniciando scheduler semanal | day_of_week=%s hour=%s minute=%s timezone=%s",
        day_of_week,
        hour,
        minute,
        timezone,
    )

    if args.run_now:
        logger.info("Executando rodada imediata (--run-now)")
        run_once(args.config, args.env_file)

    scheduler = BlockingScheduler(timezone=timezone)
    trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute, timezone=timezone)

    scheduler.add_job(
        run_once,
        trigger=trigger,
        args=[args.config, args.env_file],
        id="weekly_news_report_job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    next_run = scheduler.get_job("weekly_news_report_job").next_run_time
    logger.info("Próxima execução agendada: %s", next_run)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler finalizado em %s", datetime.utcnow().isoformat())


if __name__ == "__main__":
    main()
