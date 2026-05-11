from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    if getattr(sys, "frozen", False):
        app_home = Path(sys.executable).resolve().parent
        bundle_root = Path(getattr(sys, "_MEIPASS", app_home)).resolve()
    else:
        app_home = Path(__file__).resolve().parent
        bundle_root = app_home

    os.environ.setdefault("NEWS_REPORTER_HOME", str(app_home))
    os.environ.setdefault("NEWS_BUNDLE_ROOT", str(bundle_root))

    src_dir = bundle_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from embedded_webapp import start_server

    port_raw = os.getenv("NEWS_WEBAPP_PORT", "8787").strip()
    try:
        port = int(port_raw)
    except ValueError:
        port = 8787

    start_server(port=port, open_browser=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
