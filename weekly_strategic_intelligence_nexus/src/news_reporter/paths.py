from __future__ import annotations

import os
from pathlib import Path


def get_project_root() -> Path:
    env_root = os.getenv("NEWS_REPORTER_HOME", "").strip()
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[2]

