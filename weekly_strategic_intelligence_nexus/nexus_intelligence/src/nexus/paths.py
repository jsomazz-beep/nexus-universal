"""Nexus Intelligence — paths helper."""
from __future__ import annotations

import sys
from pathlib import Path


def get_project_root() -> Path:
    """Return the nexus_intelligence project root directory."""
    # When running as script: src/nexus/paths.py → up 3 levels
    candidate = Path(__file__).resolve().parent.parent.parent
    if (candidate / "config").exists():
        return candidate
    # Fallback: cwd
    return Path.cwd()
