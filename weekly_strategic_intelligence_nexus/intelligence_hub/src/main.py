"""
CLI de execução do Intelligence Hub.
Uso: python src/main.py [opções]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import webbrowser
from pathlib import Path

# Adiciona src ao path para imports locais
_SRC = Path(__file__).parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Intelligence Hub v2.0 — Agregador de Inteligência Estratégica",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python src/main.py                                   # Execução padrão
  python src/main.py --theme dark                      # Tema escuro
  python src/main.py --max-news 80 --open              # 80 notícias e abrir relatório
  python src/main.py --keywords "IA,energia,Angola"    # Palavras prioritárias
""",
    )
    parser.add_argument("--config", default="config/config.yaml", help="Arquivo de configuração YAML")
    parser.add_argument("--env-file", default=".env", help="Arquivo .env com chaves de API")
    parser.add_argument("--max-news", type=int, default=0, help="Máximo de notícias no relatório")
    parser.add_argument("--theme", choices=["dark", "light", "boardroom"], default="", help="Tema visual")
    parser.add_argument("--keywords", default="", help="Palavras-chave prioritárias separadas por vírgula")
    parser.add_argument("--open", action="store_true", help="Abrir relatório no browser após gerar")
    parser.add_argument("--verbose", "-v", action="store_true", help="Log detalhado")
    args = parser.parse_args()

    # Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)-25s %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        from hub.config import load_config
        from hub.pipeline import IntelligenceHubPipeline
    except ImportError as e:
        print(f"[ERRO] Falha ao importar módulos: {e}")
        print("Certifique-se de ter instalado as dependências: pip install -r requirements.txt")
        sys.exit(1)

    try:
        config = load_config(args.config, args.env_file)
    except FileNotFoundError as e:
        print(f"[ERRO] {e}")
        print(f"Crie o arquivo de configuração copiando o exemplo:")
        print(f"  copy config\\config.example.yaml config\\config.yaml")
        sys.exit(1)

    # Overrides via CLI
    overrides: dict = {}
    if args.max_news and args.max_news > 0:
        overrides["max_news"] = args.max_news
        config.raw.setdefault("project", {})["max_news"] = args.max_news
    if args.theme:
        overrides["theme"] = args.theme
        config.raw.setdefault("project", {})["report_theme"] = args.theme
    if args.keywords:
        kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
        if kws:
            config.raw.setdefault("monitoring", {})["priority_keywords"] = kws

    print()
    print("  ⬡  Intelligence Hub v2.0")
    print("  ─────────────────────────────────────")
    enabled = [s for s in config.sources if s.get("enabled", True)]
    print(f"  Fontes ativas  : {len(enabled)}")
    print(f"  Regiões        : {', '.join(config.monitoring.get('regions', []))}")
    print(f"  Janela         : {config.filters.get('time_window_days', 7)} dias")
    print(f"  Max notícias   : {config.raw.get('project', {}).get('max_news', 60)}")
    print()

    pipeline = IntelligenceHubPipeline(config)
    result = pipeline.run(overrides=overrides)

    print()
    print("  ✓ Execução concluída!")
    print(f"  Coletados   : {result.counters.collected}")
    print(f"  Filtrados   : {result.counters.filtered_out}")
    print(f"  Deduplicados: {result.counters.deduplicated}")
    print(f"  Aprovados   : {result.counters.approved}")
    print(f"  Duração     : {result.duration_seconds:.1f}s")
    print(f"  Relatório   : {result.report_path_html}")
    print()

    if result.source_errors:
        print(f"  ⚠ Fontes com erro ({len(result.source_errors)}):")
        for src_id, err in list(result.source_errors.items())[:5]:
            print(f"    - {src_id}: {err[:80]}")

    if args.open and result.report_path_html:
        rp = Path(result.report_path_html)
        if rp.exists():
            webbrowser.open(rp.as_uri())


if __name__ == "__main__":
    main()
