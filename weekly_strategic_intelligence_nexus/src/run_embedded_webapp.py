from __future__ import annotations

import os

from embedded_webapp import start_server


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> None:
    host = os.getenv("NEWS_BIND_HOST", "").strip()
    if not host:
        host = "0.0.0.0" if os.getenv("RENDER") else "127.0.0.1"

    port_raw = os.getenv("PORT", os.getenv("NEWS_WEBAPP_PORT", "8787")).strip()
    try:
        port = int(port_raw)
    except ValueError:
        port = 8787
    open_browser = _as_bool(os.getenv("NEWS_OPEN_BROWSER"), default=False)
    start_server(host=host, port=port, open_browser=open_browser)


if __name__ == "__main__":
    main()
