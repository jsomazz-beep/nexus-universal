from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def _cfg() -> dict[str, str] | None:
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
    return {
        "url": url,
        "key": key,
        "table": (os.getenv("SUPABASE_REPORTS_TABLE") or "intelligence_reports").strip(),
    }


def _headers(key: str, *, json_content: bool = False, upsert: bool = False) -> dict[str, str]:
    headers = {"apikey": key, "Accept": "application/json"}
    if not key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {key}"
    if json_content:
        headers["Content-Type"] = "application/json"
    if upsert:
        headers["Prefer"] = "resolution=merge-duplicates"
    return headers


def save_report_snapshot(report_name: str, html_content: str, max_keep: int = 1000) -> None:
    cfg = _cfg()
    if not cfg:
        return

    endpoint = f"{cfg['url']}/rest/v1/{cfg['table']}"
    headers = _headers(cfg["key"], json_content=True, upsert=True)
    row = [{"report_name": report_name, "html_content": html_content}]

    try:
        resp = requests.post(endpoint, headers=headers, params={"on_conflict": "report_name"}, data=json.dumps(row), timeout=20)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao salvar relatório no Supabase: %s", exc)
        return

    _enforce_retention(cfg, max_keep=max_keep)


def hydrate_local_reports(output_dir: Path, max_fetch: int = 25) -> None:
    cfg = _cfg()
    if not cfg:
        return

    endpoint = f"{cfg['url']}/rest/v1/{cfg['table']}"
    headers = _headers(cfg["key"])
    params = {
        "select": "report_name,html_content",
        "order": "created_at.desc",
        "limit": str(max(1, int(max_fetch))),
    }
    try:
        resp = requests.get(endpoint, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        rows = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao restaurar relatórios do Supabase: %s", exc)
        return

    if not isinstance(rows, list):
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("report_name", "")).strip()
        html = row.get("html_content")
        if not name or not isinstance(html, str) or not html.strip():
            continue
        safe_name = Path(name).name
        if not safe_name.endswith(".html"):
            continue
        target = output_dir / safe_name
        if not target.exists():
            target.write_text(html, encoding="utf-8")


def _enforce_retention(cfg: dict[str, str], max_keep: int) -> None:
    max_keep = max(50, int(max_keep))
    endpoint = f"{cfg['url']}/rest/v1/{cfg['table']}"
    headers = _headers(cfg["key"])
    params = {"select": "id", "order": "created_at.desc", "limit": str(max_keep + 200)}
    try:
        resp = requests.get(endpoint, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        rows = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao consultar retenção de relatórios: %s", exc)
        return

    if not isinstance(rows, list) or len(rows) <= max_keep:
        return

    ids_to_delete: list[str] = []
    for row in rows[max_keep:]:
        if isinstance(row, dict) and row.get("id") is not None:
            ids_to_delete.append(str(row["id"]))
    if not ids_to_delete:
        return

    delete_filter = ",".join(ids_to_delete)
    try:
        del_resp = requests.delete(endpoint, headers=headers, params={"id": f"in.({delete_filter})"}, timeout=20)
        del_resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao aplicar retenção de relatórios: %s", exc)
