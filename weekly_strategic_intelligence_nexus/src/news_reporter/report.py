from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from news_reporter.models import NewsItem


class ReportComposer:
    def __init__(self, templates_dir: str, max_images: int = 8, include_images: bool = True) -> None:
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.max_images = max_images
        self.include_images = include_images

    def compose(
        self,
        items: list[NewsItem],
        synthesis: dict,
        title: str,
        report_date: datetime,
        output_dir: str,
        theme_name: str = "light",
        monitored_regions: list[str] | None = None,
        run_params: dict | None = None,
        market_snapshot: list[dict] | None = None,
    ) -> tuple[str, str, str]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        items_sorted = sorted(items, key=lambda i: i.score, reverse=True)
        self._assign_anchor_ids(items_sorted)
        self._mark_relevant_images(items_sorted)

        period_end = report_date.strftime("%d/%m/%Y")
        period_start = (report_date - timedelta(days=7)).strftime("%d/%m/%Y")

        strategic = self._build_strategic_blocks(items_sorted, period_start, period_end, monitored_regions)
        theme = self._resolve_theme(theme_name)

        template = self.env.get_template("report_email.html.j2")
        html = template.render(
            title=title,
            period_start=period_start,
            period_end=period_end,
            synthesis=synthesis,
            items=items_sorted,
            strategic=strategic,
            theme=theme,
            run_params=run_params or {},
            market_snapshot=market_snapshot or [],
        )

        text = self._to_text(items_sorted, synthesis, title, period_start, period_end)

        filename = f"weekly_report_{report_date.strftime('%Y%m%d_%H%M%S')}.html"
        full_path = output_path / filename
        full_path.write_text(html, encoding="utf-8")

        return html, text, str(full_path)

    @staticmethod
    def _resolve_theme(theme_name: str) -> dict[str, str]:
        themes = {
            "light": {
                "name": "light",
                "body_bg": "#f2f6fb",
                "container_bg": "#ffffff",
                "text": "#0f172a",
                "title": "#081f4d",
                "subtitle": "#475569",
                "card_bg": "#ffffff",
                "card_border": "#dbe4ef",
                "muted_bg": "#f8fbff",
                "table_head": "#f1f5f9",
                "node_border": "#94a3b8",
                "node_text": "#0f172a",
                "accent": "#0ea5e9",
                "container_shadow": "0 8px 24px rgba(2, 6, 23, .08)",
            },
            "dark_exec": {
                "name": "dark_exec",
                "label": "Dark Executive",
                "body_bg": "#0b1220",
                "container_bg": "#111a2b",
                "text": "#e5edf7",
                "title": "#dbeafe",
                "subtitle": "#9fb0c8",
                "card_bg": "#162237",
                "card_border": "#2a3c5b",
                "muted_bg": "#152239",
                "table_head": "#1f2d45",
                "node_border": "#3f5c8a",
                "node_text": "#e6eef8",
                "accent": "#38bdf8",
                "container_shadow": "0 14px 40px rgba(2, 6, 23, .55)",
            },
            "boardroom_print": {
                "name": "boardroom_print",
                "label": "Boardroom Print",
                "body_bg": "#f7f7f6",
                "container_bg": "#fffefb",
                "text": "#1b1b1b",
                "title": "#111827",
                "subtitle": "#3f3f46",
                "card_bg": "#ffffff",
                "card_border": "#d4d4d8",
                "muted_bg": "#fafafa",
                "table_head": "#f4f4f5",
                "node_border": "#71717a",
                "node_text": "#111827",
                "accent": "#334155",
                "container_shadow": "0 8px 24px rgba(24, 24, 27, .08)",
            },
        }
        selected = themes.get(theme_name, themes["light"]).copy()
        if "label" not in selected:
            selected["label"] = "Light"
        return selected

    def _build_strategic_blocks(
        self,
        items: list[NewsItem],
        period_start: str,
        period_end: str,
        monitored_regions: list[str] | None,
    ) -> dict:
        focus_regions = self._resolve_focus_regions(items, monitored_regions)

        cards = []
        color_cycle = ["alert", "positive", "warning", "info"]
        for idx, region in enumerate(focus_regions):
            region_items = [i for i in items if i.region == region][:1]
            if region_items:
                it = region_items[0]
                cards.append(
                    {
                        "color": color_cycle[idx % len(color_cycle)],
                        "label": region,
                        "title": it.translated_title_pt,
                        "metric": f"Score {it.score}",
                        "desc": it.short_summary_pt,
                    }
                )
            else:
                cards.append(
                    {
                        "color": color_cycle[idx % len(color_cycle)],
                        "label": region,
                        "title": "Sem item aderente na janela",
                        "metric": "Score N/D",
                        "desc": "Nenhuma notícia passou por todos os filtros para esta região nesta execução.",
                    }
                )

        macro = self._pick_macro_item(items)
        macro_block = {
            "title": macro.translated_title_pt if macro else "Sem gatilho macro dominante identificado.",
            "left": self._safe_summary(macro, "Impacto físico e energético não explícito na semana."),
            "right_top": "Possível retração de capital e revisão de cronogramas de investimento.",
            "right_bottom": "Respostas mitigatórias concentram-se em eficiência operacional e replanejamento.",
        }

        regional_briefs = {}
        for region in focus_regions:
            top = [i for i in items if i.region == region][:2]
            regional_briefs[region] = top

        comparative_rows = []
        for region in focus_regions:
            top = [i for i in items if i.region == region][:3]
            vector = self._join_unique([kw for i in top for kw in (i.detected_keywords + i.opportunity_types)], 3)
            risk = self._infer_risk(top)
            comparative_rows.append(
                {
                    "region": region,
                    "vector": vector or "Sinais distribuídos de oportunidade sem concentração dominante.",
                    "risk": risk,
                }
            )

        connector = {
            "left": "Volatilidade de insumos e cadeia logística",
            "right": "Capital imobilizado em expansão",
            "bottom": "Regulação e conformidade operacional",
            "center": "Excelência em O&M / Facilities Management",
        }

        source_names = sorted({i.source_name for i in items if i.source_name})

        return {
            "period_start": period_start,
            "period_end": period_end,
            "focus_regions": focus_regions,
            "volume": len(items),
            "signal_cards": cards,
            "macro": macro_block,
            "regional_briefs": regional_briefs,
            "comparative_rows": comparative_rows,
            "connector": connector,
            "sources": source_names,
        }

    @staticmethod
    def _resolve_focus_regions(items: list[NewsItem], monitored_regions: list[str] | None) -> list[str]:
        if monitored_regions:
            return [r for r in monitored_regions if r]
        inferred = []
        for item in items:
            if item.region and item.region not in inferred:
                inferred.append(item.region)
        return inferred or ["Angola", "Portugal", "Brasil", "Emirados Arabes Unidos"]

    def _pick_macro_item(self, items: list[NewsItem]) -> NewsItem | None:
        macro_terms = ["diesel", "petroleo", "petróleo", "inflacao", "inflação", "juros", "fed", "geopol"]
        for item in items:
            text = item.normalized_text.lower()
            if any(term in text for term in macro_terms):
                return item
        return items[0] if items else None

    @staticmethod
    def _safe_summary(item: NewsItem | None, fallback: str) -> str:
        if not item:
            return fallback
        return item.executive_summary_pt or item.short_summary_pt or fallback

    @staticmethod
    def _join_unique(values: list[str], max_items: int) -> str:
        out = []
        for v in values:
            if v and v not in out:
                out.append(v)
        return ", ".join(out[:max_items])

    @staticmethod
    def _infer_risk(items: list[NewsItem]) -> str:
        if not items:
            return "Baixa visibilidade de risco no recorte semanal."
        low_score = [i for i in items if i.score < 60]
        if low_score:
            return "Risco de execução e volatilidade regulatória/logística em parte dos eventos monitorados."
        return "Risco moderado com predominância de vetores de expansão e investimento."

    def _mark_relevant_images(self, items: list[NewsItem]) -> None:
        if not self.include_images:
            for item in items:
                item.show_image = False
            return

        for idx, item in enumerate(items, start=1):
            item.show_image = True
            if item.image_url:
                item.display_image_url = item.image_url
            else:
                item.display_image_url = self._build_photo_fallback_url(item, idx)

    @staticmethod
    def _build_photo_fallback_url(item: NewsItem, idx: int) -> str:
        seed = ReportComposer._slugify(
            f"{item.region}-{item.themes[0] if item.themes else 'geral'}-{item.source_name}-{idx}"
        )
        # Fallback fotográfico determinístico para manter cards com aparência visual.
        return f"https://picsum.photos/seed/{seed}/1200/700"

    @staticmethod
    def _build_kpi_image_data_uri(item: NewsItem) -> str:
        score = int(round(item.score))
        opp = "SIM" if item.opportunity_exists else "NAO"
        region = (item.region or "Indefinida")[:28]
        themes = ", ".join(item.themes[:2]) if item.themes else "N/D"
        kw_count = len(item.detected_keywords) + len(item.detected_associated_keywords)

        title = (item.translated_title_pt or item.title or "Noticia").strip()
        title = re.sub(r"\s+", " ", title)
        if len(title) > 70:
            title = title[:67] + "..."

        fill = "#16a34a" if score >= 70 else "#ca8a04" if score >= 45 else "#dc2626"
        bar_width = max(8, min(280, int(2.8 * score)))

        svg = f"""
<svg xmlns='http://www.w3.org/2000/svg' width='760' height='220' viewBox='0 0 760 220'>
  <rect width='760' height='220' fill='#f8fafc'/>
  <rect x='12' y='12' width='736' height='196' rx='10' fill='white' stroke='#dbe4ef'/>
  <text x='28' y='46' font-family='Segoe UI, Arial' font-size='20' fill='#0f172a'>KPI da Noticia</text>
  <text x='28' y='72' font-family='Segoe UI, Arial' font-size='15' fill='#334155'>{title}</text>
  <text x='28' y='102' font-family='Segoe UI, Arial' font-size='14' fill='#475569'>Regiao: {region} | Tema: {themes}</text>
  <text x='28' y='128' font-family='Segoe UI, Arial' font-size='14' fill='#475569'>Oportunidade: {opp} | Keywords detectadas: {kw_count}</text>
  <text x='28' y='160' font-family='Segoe UI, Arial' font-size='14' fill='#475569'>Score de relevancia</text>
  <rect x='28' y='170' width='300' height='18' rx='6' fill='#e2e8f0'/>
  <rect x='28' y='170' width='{bar_width}' height='18' rx='6' fill='{fill}'/>
  <text x='336' y='184' font-family='Segoe UI, Arial' font-size='13' fill='#0f172a'>{score}/100</text>
</svg>
""".strip()
        return "data:image/svg+xml;utf8," + quote(svg)

    @staticmethod
    def _slugify(value: str) -> str:
        base = (value or "").strip().lower()
        base = re.sub(r"[^a-z0-9]+", "-", base)
        base = re.sub(r"-+", "-", base).strip("-")
        return base or "item"

    def _assign_anchor_ids(self, items: list[NewsItem]) -> None:
        used: set[str] = set()
        for idx, item in enumerate(items, start=1):
            raw = f"{item.region}-{item.translated_title_pt or item.title}-{idx}"
            slug = self._slugify(raw)
            anchor = slug
            suffix = 1
            while anchor in used:
                suffix += 1
                anchor = f"{slug}-{suffix}"
            used.add(anchor)
            item.anchor_id = anchor

    @staticmethod
    def _to_text(items: list[NewsItem], synthesis: dict, title: str, period_start: str, period_end: str) -> str:
        lines = [
            title,
            f"Período: {period_start} a {period_end}",
            "",
            "Resumo executivo:",
            str(synthesis.get("executive_summary", "")),
            "",
            "Destaques:",
        ]
        lines.extend([f"- {i}" for i in synthesis.get("highlights", [])])
        lines.append("")
        lines.append("Notícias selecionadas:")
        for idx, item in enumerate(items, start=1):
            lines.extend(
                [
                    f"{idx}. {item.translated_title_pt}",
                    f"   Região: {item.region} | Score: {item.score}",
                    f"   Resumo: {item.short_summary_pt}",
                    f"   Oportunidade: {'Sim' if item.opportunity_exists else 'Não'}",
                    f"   Fonte: {item.url}",
                ]
            )
        return "\n".join(lines)
