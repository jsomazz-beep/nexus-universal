from __future__ import annotations

import os
from pathlib import Path


def resolve_templates_dir() -> str:
    # Caminho padrão durante desenvolvimento.
    local = Path(__file__).resolve().parent / "templates"
    if local.exists():
        return str(local)

    # Caminhos alternativos em runtime empacotado.
    bundle_root_raw = os.getenv("NEWS_BUNDLE_ROOT", "").strip()
    if bundle_root_raw:
        bundle_root = Path(bundle_root_raw)
        candidates = [
            bundle_root / "news_reporter" / "templates",
            bundle_root / "src" / "news_reporter" / "templates",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

    # Fallback final (deixa erro explícito se não existir).
    return str(local)

