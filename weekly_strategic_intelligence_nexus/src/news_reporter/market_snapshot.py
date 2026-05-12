from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

from news_reporter.paths import get_project_root

logger = logging.getLogger(__name__)


def _fmt_number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "N/D"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/D"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%".replace(".", ",")


def _parse_fmt_number(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "N/D":
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except Exception:  # noqa: BLE001
        return None


def _cache_path() -> Path:
    return get_project_root() / "data" / "market_snapshot_cache.json"


def _load_cache() -> dict[str, dict]:
    path = _cache_path()
    try:
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        out: dict[str, dict] = {}
        for key, value in payload.items():
            if isinstance(key, str) and isinstance(value, dict):
                out[key] = value
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao carregar cache de mercado: %s", exc)
        return {}


def _save_cache(out_map: dict[str, dict]) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cache_now = _load_cache()
    for name, item in out_map.items():
        if item.get("value") != "N/D":
            cache_now[name] = item
    path.write_text(json.dumps(cache_now, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_market_snapshot(timeout: int = 8) -> list[dict]:
    symbols = "USDBRL=X,EURBRL=X,^BVSP,^IXIC"
    url = "https://query1.finance.yahoo.com/v7/finance/quote"
    params = {"symbols": symbols}

    mapping = {
        "USDBRL=X": ("DÓLAR", "R$"),
        "EURBRL=X": ("EURO", "R$"),
        "^BVSP": ("IBOVESPA", ""),
        "^IXIC": ("NASDAQ", ""),
    }

    defaults = [
        {"name": "DÓLAR", "prefix": "R$", "value": "N/D", "pct": "N/D", "positive": False},
        {"name": "EURO", "prefix": "R$", "value": "N/D", "pct": "N/D", "positive": False},
        {"name": "IBOVESPA", "prefix": "", "value": "N/D", "pct": "N/D", "positive": False},
        {"name": "NASDAQ", "prefix": "", "value": "N/D", "pct": "N/D", "positive": False},
    ]

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        }
    )

    out_map: dict[str, dict] = {d["name"]: d.copy() for d in defaults}

    # 1) Tenta Yahoo quote (todos de uma vez)
    try:
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        results = payload.get("quoteResponse", {}).get("result", [])
        by_symbol = {item.get("symbol"): item for item in results if item.get("symbol")}
        for symbol, (name, prefix) in mapping.items():
            item = by_symbol.get(symbol, {})
            value = item.get("regularMarketPrice")
            pct = item.get("regularMarketChangePercent")
            if value is not None:
                out_map[name] = {
                    "name": name,
                    "prefix": prefix,
                    "value": _fmt_number(value, 2 if symbol in {"USDBRL=X", "EURBRL=X"} else 1),
                    "pct": _fmt_pct(pct),
                    "positive": bool(pct is not None and pct > 0),
                }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha Yahoo quote: %s", exc)

    # 2) Fallback BR robusto para câmbio
    try:
        fx_url = "https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL"
        fx = session.get(fx_url, timeout=timeout)
        fx.raise_for_status()
        data = fx.json()
        usd = data.get("USDBRL", {})
        eur = data.get("EURBRL", {})
        if usd.get("bid") is not None:
            pct = float(usd.get("pctChange")) if usd.get("pctChange") is not None else None
            out_map["DÓLAR"] = {
                "name": "DÓLAR",
                "prefix": "R$",
                "value": _fmt_number(float(usd.get("bid")), 2),
                "pct": _fmt_pct(pct),
                "positive": bool(pct is not None and pct > 0),
            }
        if eur.get("bid") is not None:
            pct = float(eur.get("pctChange")) if eur.get("pctChange") is not None else None
            out_map["EURO"] = {
                "name": "EURO",
                "prefix": "R$",
                "value": _fmt_number(float(eur.get("bid")), 2),
                "pct": _fmt_pct(pct),
                "positive": bool(pct is not None and pct > 0),
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha AwesomeAPI FX: %s", exc)

    # 2b) Fallback global para FX (sem chave) via Frankfurter.
    # Retorna cotação (sem variação intraday), então % pode cair para cache/0,00%.
    try:
        if out_map["DÓLAR"]["value"] == "N/D":
            usd_resp = session.get("https://api.frankfurter.dev/v1/latest?base=USD&symbols=BRL", timeout=timeout)
            usd_resp.raise_for_status()
            usd_data = usd_resp.json()
            usd_brl = (usd_data.get("rates", {}) or {}).get("BRL")
            if usd_brl is not None:
                out_map["DÓLAR"] = {
                    "name": "DÓLAR",
                    "prefix": "R$",
                    "value": _fmt_number(float(usd_brl), 2),
                    "pct": "N/D",
                    "positive": False,
                }

        if out_map["EURO"]["value"] == "N/D":
            eur_resp = session.get("https://api.frankfurter.dev/v1/latest?base=EUR&symbols=BRL", timeout=timeout)
            eur_resp.raise_for_status()
            eur_data = eur_resp.json()
            eur_brl = (eur_data.get("rates", {}) or {}).get("BRL")
            if eur_brl is not None:
                out_map["EURO"] = {
                    "name": "EURO",
                    "prefix": "R$",
                    "value": _fmt_number(float(eur_brl), 2),
                    "pct": "N/D",
                    "positive": False,
                }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha Frankfurter FX: %s", exc)

    # 3) Fallback por ativo no endpoint chart do Yahoo (índices)
    index_symbols = {
        "^BVSP": ("IBOVESPA", ""),
        "^IXIC": ("NASDAQ", ""),
    }
    for symbol, (name, prefix) in index_symbols.items():
        if out_map.get(name, {}).get("value") != "N/D":
            continue
        try:
            chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            r = session.get(chart_url, params={"range": "1d", "interval": "1d"}, timeout=timeout)
            r.raise_for_status()
            payload = r.json()
            result = payload.get("chart", {}).get("result", [{}])[0]
            meta = result.get("meta", {})
            value = meta.get("regularMarketPrice")
            prev = meta.get("previousClose")
            pct = None
            if value is not None and prev not in (None, 0):
                pct = ((float(value) - float(prev)) / float(prev)) * 100.0
            if value is not None:
                out_map[name] = {
                    "name": name,
                    "prefix": prefix,
                    "value": _fmt_number(float(value), 1),
                    "pct": _fmt_pct(pct),
                    "positive": bool(pct is not None and pct > 0),
                }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha Yahoo chart %s: %s", symbol, exc)

    # 4) Fallback final pelo último snapshot válido salvo localmente.
    cache = _load_cache()
    for name, cached in cache.items():
        current = out_map.get(name)
        if not current:
            continue
        if current.get("value") == "N/D" and isinstance(cached, dict) and cached.get("value") != "N/D":
            out_map[name] = cached
            continue
        # Se valor existe mas percentual falhou nesta rodada, reutiliza percentual do cache.
        if (
            current.get("value") != "N/D"
            and current.get("pct") == "N/D"
            and isinstance(cached, dict)
            and cached.get("pct") not in (None, "", "N/D")
        ):
            current["pct"] = cached.get("pct")
            current["positive"] = bool(cached.get("positive", False))

        # Se ainda sem percentual, tenta calcular pelo delta vs último valor em cache.
        if current.get("value") != "N/D" and current.get("pct") == "N/D" and isinstance(cached, dict):
            now_v = _parse_fmt_number(current.get("value"))
            old_v = _parse_fmt_number(cached.get("value"))
            if now_v is not None and old_v not in (None, 0):
                pct = ((now_v - old_v) / old_v) * 100.0
                current["pct"] = _fmt_pct(pct)
                current["positive"] = bool(pct > 0)

    # 4b) Fallback visual final: evita N/D em % quando já existe cotação/índice.
    for item in out_map.values():
        if item.get("value") != "N/D" and item.get("pct") == "N/D":
            item["pct"] = "0,00%"
            item["positive"] = False

    # 5) Persistência para aumentar resiliência entre execuções.
    try:
        _save_cache(out_map)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao salvar cache de mercado: %s", exc)

    order = ["DÓLAR", "EURO", "IBOVESPA", "NASDAQ"]
    return [out_map[k] for k in order]
