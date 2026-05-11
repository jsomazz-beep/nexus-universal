from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


def http_get_json(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
    retries: int = 2,
    backoff_seconds: int = 2,
) -> dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < retries:
                sleep_time = backoff_seconds * (attempt + 1)
                logger.warning("Falha HTTP GET JSON, retry em %ss: %s", sleep_time, exc)
                time.sleep(sleep_time)
    raise RuntimeError(f"Falha em requisição JSON para {url}: {last_err}")


def http_get_text(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
    retries: int = 2,
    backoff_seconds: int = 2,
) -> str:
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < retries:
                sleep_time = backoff_seconds * (attempt + 1)
                logger.warning("Falha HTTP GET TEXT, retry em %ss: %s", sleep_time, exc)
                time.sleep(sleep_time)
    raise RuntimeError(f"Falha em requisição texto para {url}: {last_err}")
