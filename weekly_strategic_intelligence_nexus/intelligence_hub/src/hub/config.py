"""
Carregamento e validação de configuração do Intelligence Hub.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def _load_env_file(path: str) -> dict[str, str]:
    env: dict[str, str] = {}
    p = Path(path)
    if not p.exists():
        return env
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


class AppConfig:
    """Configuração principal da aplicação."""

    def __init__(self, raw: dict[str, Any], env: dict[str, str]) -> None:
        self.raw = raw
        self.env = env

    # ── Seções principais ──────────────────────────────────────────────────

    @property
    def project(self) -> dict[str, Any]:
        return self.raw.get("project", {})

    @property
    def monitoring(self) -> dict[str, Any]:
        return self.raw.get("monitoring", {})

    @property
    def sources(self) -> list[dict[str, Any]]:
        return self.raw.get("sources", [])

    @property
    def filters(self) -> dict[str, Any]:
        return self.raw.get("filters", {})

    @property
    def deduplication(self) -> dict[str, Any]:
        return self.raw.get("deduplication", {})

    @property
    def scoring(self) -> dict[str, Any]:
        return self.raw.get("scoring", {})

    @property
    def runtime(self) -> dict[str, Any]:
        return self.raw.get("runtime", {})

    @property
    def ai(self) -> dict[str, Any]:
        return self.raw.get("ai", {})

    # ── API Keys (env tem precedência sobre yaml) ──────────────────────────

    def get_api_key(self, name: str) -> str:
        """Retorna chave de API: primeiro do env, depois do yaml."""
        env_val = self.env.get(name) or os.getenv(name, "")
        if env_val:
            return env_val
        # fallback para yaml api_keys section
        return self.raw.get("api_keys", {}).get(name.lower(), "")

    @property
    def newsapi_key(self) -> str:
        return self.get_api_key("NEWSAPI_KEY")

    @property
    def guardian_api_key(self) -> str:
        return self.get_api_key("GUARDIAN_API_KEY")

    @property
    def nytimes_api_key(self) -> str:
        return self.get_api_key("NYTIMES_API_KEY")

    @property
    def anthropic_api_key(self) -> str:
        return self.get_api_key("ANTHROPIC_API_KEY")

    @property
    def output_language(self) -> str:
        return self.project.get("output_language", "pt")

    @property
    def max_news(self) -> int:
        return int(self.project.get("max_news", 60))

    @property
    def report_theme(self) -> str:
        return self.project.get("report_theme", "dark")


def load_config(config_path: str, env_path: str = ".env") -> AppConfig:
    """Carrega configuração do arquivo YAML e variáveis de ambiente."""
    path = Path(config_path)
    if not path.exists():
        # tenta config.example.yaml como fallback
        example = path.parent / (path.stem + ".example" + path.suffix)
        if example.exists():
            path = example
        else:
            raise FileNotFoundError(f"Config não encontrado: {config_path}")

    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    env = _load_env_file(env_path)
    return AppConfig(raw, env)
