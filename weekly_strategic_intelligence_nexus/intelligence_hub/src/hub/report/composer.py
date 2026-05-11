"""
Composer do relatório HTML moderno.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from hub.models import NewsItem, WeeklySynthesis

logger = logging.getLogger(__name__)

_CATEGORY_ICONS = {
    "Economia": "💹", "Oportunidades": "🟢", "Infraestrutura": "🏗",
    "Energia": "⚡", "Tecnologia": "🖥", "Inovação": "🔬",
    "Geopolítica": "🌍", "Negócios": "💼", "Mercado": "📊",
    "Financeiro": "🏦", "Saúde": "🏥", "Sustentabilidade": "🌿",
    "Logística": "🚢", "Recursos Naturais": "🌎", "Geral": "📰",
    "Reddit": "🟠", "Notícias Mundiais": "🗺", "Brasil": "🇧🇷",
    "Portugal": "🇵🇹", "Angola": "🇦🇴",
}


class ReportComposer:
    """Gera o relatório HTML a partir dos itens curados."""

    def __init__(self) -> None:
        import sys
        if getattr(sys, "frozen", False):
            # Modo PyInstaller: templates bundled em _MEIPASS/hub_templates/
            self._templates_dir = Path(sys._MEIPASS) / "hub_templates"
        else:
            self._templates_dir = Path(__file__).parent / "templates"

    def compose(
        self,
        items: list[NewsItem],
        synthesis: WeeklySynthesis,
        output_dir: Path,
        title: str = "Intelligence Hub Report",
        theme: str = "dark",
        config: Any = None,
    ) -> Path:
        env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=select_autoescape(["html"]),
        )
        template = env.get_template("report.html")

        now = datetime.now(timezone.utc)
        generated_at = now.strftime("%d/%m/%Y %H:%M UTC")

        # Agrupar por categoria
        items_by_category: dict[str, list[NewsItem]] = defaultdict(list)
        for item in items:
            cats = item.categories or ["Geral"]
            items_by_category[cats[0]].append(item)

        # Ordenar categorias por contagem desc
        items_by_category = dict(
            sorted(items_by_category.items(), key=lambda x: len(x[1]), reverse=True)
        )

        # Oportunidades
        opp_items = [i for i in items if i.opportunity_signals]
        opp_items.sort(key=lambda x: x.score, reverse=True)

        # Distribuição por fonte
        source_dist: dict[str, int] = defaultdict(int)
        for item in items:
            source_dist[item.source_name] += 1
        source_distribution = sorted(source_dist.items(), key=lambda x: x[1], reverse=True)[:15]
        source_max = source_distribution[0][1] if source_distribution else 1

        # Regiões únicas
        all_regions = sorted({i.region for i in items if i.region})

        # Formatar datas nos itens
        for item in items:
            if item.published_at:
                item.raw["published_at_fmt"] = item.published_at.strftime("%d/%m %H:%M")
            else:
                item.raw["published_at_fmt"] = "—"
            # Domínio da URL para favicon no placeholder
            try:
                item.raw["url_domain"] = urlparse(item.url).netloc or ""
            except Exception:
                item.raw["url_domain"] = ""

        # JSON para interatividade
        items_json_data = []
        for item in items:
            items_json_data.append({
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "source_name": item.source_name,
                "source_type": item.source_type,
                "content": item.content[:800] if item.content else "",
                "author": item.author,
                "image_url": item.image_url,
                "published_at_fmt": item.raw.get("published_at_fmt", ""),
                "region": item.region,
                "categories": item.categories,
                "score": item.score,
                "opportunity_signals": item.opportunity_signals,
                "merged_count": item.merged_count,
            })

        # Contadores do config
        run_cfg = config.runtime if config else {}
        time_window_days = (config.filters.get("time_window_days", 7) if config else 7)

        context = {
            "title": title,
            "theme": theme,
            "generated_at": generated_at,
            "synthesis": synthesis.summary,
            "key_signals": synthesis.key_signals,
            "total_items": len(items),
            "source_count": len(set(i.source_id for i in items)),
            "opp_count": len(opp_items),
            "region_count": len(all_regions),
            "critical_count": sum(1 for i in items if i.score >= 0.85),
            "run_duration": "—",
            "time_window_days": time_window_days,
            "items_by_category": {
                cat: cat_items
                for cat, cat_items in items_by_category.items()
            },
            "opportunity_items": opp_items,
            "source_distribution": source_distribution,
            "source_max": source_max,
            "all_regions": all_regions,
            "category_icons": _CATEGORY_ICONS,
            "items_json": json.dumps(items_json_data, ensure_ascii=False, default=str),
            "source_errors": {},
            "total_collected": len(items),
            "total_filtered": 0,
            "total_deduped": 0,
        }

        # Adicionar formatação de data em cada item para o template
        for cat_items in items_by_category.values():
            for item in cat_items:
                item.raw["published_at_fmt"] = (
                    item.published_at.strftime("%d/%m %H:%M") if item.published_at else "—"
                )

        html = template.render(**context)

        # Salvar arquivo
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"report_{now.strftime('%Y%m%d_%H%M%S')}.html"
        out_path = output_dir / filename

        out_path.write_text(html, encoding="utf-8")
        logger.info("Relatório salvo: %s", out_path)
        return out_path
