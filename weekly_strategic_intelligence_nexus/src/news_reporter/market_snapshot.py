from __future__ import annotations

import logging

import requests

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

    order = ["DÓLAR", "EURO", "IBOVESPA", "NASDAQ"]
    return [out_map[k] for k in order]
