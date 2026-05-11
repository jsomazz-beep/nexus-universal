from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from news_reporter.models import ExecutionCounters, ExecutionResult


def _default_serializer(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Tipo não serializável: {type(value)}")


def append_execution_history(path: str, result: ExecutionResult) -> None:
    history_path = Path(path)
    history_path.parent.mkdir(parents=True, exist_ok=True)

    if history_path.exists():
        with history_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = {"executions": []}

    payload["executions"].append(
        {
            "started_at": result.started_at.isoformat(),
            "finished_at": result.finished_at.isoformat(),
            "counters": asdict(result.counters),
            "warnings": result.warnings,
            "source_errors": result.source_errors,
            "report_path_html": result.report_path_html,
        }
    )

    payload["executions"] = payload["executions"][-50:]

    with history_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=_default_serializer)


def empty_counters() -> ExecutionCounters:
    return ExecutionCounters()
