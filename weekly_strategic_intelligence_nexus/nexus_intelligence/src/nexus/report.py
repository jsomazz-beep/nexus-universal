"""Nexus Intelligence — HTML report composer."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from nexus.models import NewsItem, TopicSynthesis, RegionalSynthesis
from nexus.utils.text import extract_domain, truncate


def _fmt_date(dt: datetime | None) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d/%m/%Y %H:%M UTC")


def _score_bar(score: float) -> str:
    pct = min(int(score), 100)
    color = "#22c55e" if pct >= 70 else "#f59e0b" if pct >= 45 else "#ef4444"
    return (
        f'<div class="score-bar-wrap" title="Score: {score}">'
        f'<div class="score-bar" style="width:{pct}%;background:{color}"></div>'
        f'<span class="score-label">{score}</span>'
        f'</div>'
    )


def _opportunity_badges(item: NewsItem) -> str:
    if not item.opportunity_types:
        return ""
    badges = "".join(
        f'<span class="opp-badge">{html.escape(t.replace("_", " "))}</span>'
        for t in item.opportunity_types[:3]
    )
    return f'<div class="opp-badges">{badges}</div>'


def _source_chips(item: NewsItem) -> str:
    sources = [item.source_name] + item.secondary_sources[:2]
    chips = "".join(f'<span class="source-chip">{html.escape(s)}</span>' for s in sources)
    return f'<div class="source-chips">{chips}</div>'


def _topic_chips(item: NewsItem) -> str:
    chips = "".join(f'<span class="topic-chip">{html.escape(t)}</span>' for t in item.topics[:3])
    return f'<div class="topic-chips">{chips}</div>'


def _news_card(item: NewsItem, index: int) -> str:
    title_esc = html.escape(item.translated_title or item.title)
    summary = html.escape(item.ai_summary or item.short_summary or "")
    domain = html.escape(extract_domain(item.url))
    date_str = _fmt_date(item.published_at)
    img_html = ""
    if item.image_url:
        img_html = f'<img class="card-img" src="{html.escape(item.image_url)}" alt="" loading="lazy" onerror="this.style.display=\'none\'">'

    opp_icon = "🎯 " if item.opportunity_exists else ""

    return f"""
<article class="news-card" id="item-{index}">
  {img_html}
  <div class="card-body">
    {_source_chips(item)}
    {_topic_chips(item)}
    <h3 class="card-title">
      <a href="{html.escape(item.url)}" target="_blank" rel="noopener">{opp_icon}{title_esc}</a>
    </h3>
    {_opportunity_badges(item)}
    <p class="card-summary">{summary}</p>
    <div class="card-meta">
      <span class="card-domain">🔗 {domain}</span>
      <span class="card-date">🕐 {date_str}</span>
      <span class="card-authority">⭐ Auth {item.source_authority}/10</span>
    </div>
    {_score_bar(item.score)}
  </div>
</article>"""


def _topic_section(ts: TopicSynthesis) -> str:
    cards = "\n".join(_news_card(it, i) for i, it in enumerate(ts.top_items))
    insight = f'<p class="topic-insight">💡 {html.escape(ts.key_insight)}</p>' if ts.key_insight else ""
    return f"""
<section class="topic-section" id="topic-{html.escape(ts.topic.replace(' ', '-').lower())}">
  <div class="topic-header" style="border-color:{ts.color}">
    <span class="topic-icon">{ts.icon}</span>
    <h2 class="topic-title" style="color:{ts.color}">{html.escape(ts.topic)}</h2>
    <span class="topic-count">{ts.count} notícias</span>
  </div>
  {insight}
  <div class="cards-grid">{cards}</div>
</section>"""


def _regional_panel(rs: RegionalSynthesis) -> str:
    signal_colors = {"low": "#6b7280", "moderate": "#f59e0b", "high": "#10b981", "critical": "#ef4444"}
    color = signal_colors.get(rs.signal_strength, "#6b7280")
    top_titles = "".join(
        f'<li><a href="{html.escape(it.url)}" target="_blank">{html.escape(it.translated_title or it.title)}</a></li>'
        for it in rs.top_items
    )
    return f"""
<div class="region-card">
  <div class="region-header">
    <span class="region-name">{html.escape(rs.region)}</span>
    <span class="region-signal" style="background:{color}">{rs.signal_strength.upper()}</span>
  </div>
  <span class="region-count">{rs.count} notícias</span>
  <ul class="region-items">{top_titles}</ul>
</div>"""


class ReportComposer:
    def compose(
        self,
        items: list[NewsItem],
        topic_syntheses: list[TopicSynthesis],
        regional_syntheses: list[RegionalSynthesis],
        title: str,
        theme: str,
        output_dir: str,
        generated_at: datetime,
    ) -> tuple[str, str]:
        html_content = self._render(items, topic_syntheses, regional_syntheses, title, theme, generated_at)

        ts = generated_at.strftime("%Y%m%d_%H%M%S")
        fname = f"nexus_report_{ts}.html"
        path = Path(output_dir) / fname
        path.write_text(html_content, encoding="utf-8")
        return html_content, str(path)

    def _render(
        self,
        items: list[NewsItem],
        topic_syntheses: list[TopicSynthesis],
        regional_syntheses: list[RegionalSynthesis],
        title: str,
        theme: str,
        generated_at: datetime,
    ) -> str:
        topic_sections = "\n".join(_topic_section(ts) for ts in topic_syntheses)
        regional_panels = "\n".join(_regional_panel(rs) for rs in regional_syntheses)

        # Opportunity highlights
        opps = [it for it in items if it.opportunity_exists][:6]
        opp_cards = "\n".join(_news_card(it, 9000 + i) for i, it in enumerate(opps))
        opp_section = f"""
<section class="topic-section" id="opportunities">
  <div class="topic-header" style="border-color:#8b5cf6">
    <span class="topic-icon">🎯</span>
    <h2 class="topic-title" style="color:#8b5cf6">Radar de Oportunidades</h2>
    <span class="topic-count">{len(opps)} sinais detectados</span>
  </div>
  <div class="cards-grid">{opp_cards}</div>
</section>""" if opps else ""

        # Stats bar
        total = len(items)
        topic_count = len(topic_syntheses)
        sources_used = len({it.source_name for it in items})
        with_opp = len(opps)
        gen_str = html.escape(_fmt_date(generated_at))

        # Navigation links
        nav_links = "\n".join(
            f'<a class="nav-link" href="#topic-{ts.topic.replace(" ", "-").lower()}">{ts.icon} {html.escape(ts.topic)}</a>'
            for ts in topic_syntheses
        )
        if opps:
            nav_links += '\n<a class="nav-link" href="#opportunities">🎯 Oportunidades</a>'
        nav_links += '\n<a class="nav-link" href="#regions">🌍 Regiões</a>'

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0a0f1e;
      --surface: #111827;
      --surface2: #1f2937;
      --border: #1e293b;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --accent: #6366f1;
      --accent2: #8b5cf6;
      --green: #10b981;
      --amber: #f59e0b;
      --red: #ef4444;
      --radius: 12px;
      --shadow: 0 4px 24px rgba(0,0,0,.4);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; opacity: .85; }}

    /* ── HEADER ── */
    .report-header {{
      background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
      border-bottom: 1px solid var(--border);
      padding: 40px 32px 32px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }}
    .report-header::before {{
      content: '';
      position: absolute; inset: 0;
      background: radial-gradient(ellipse at 50% 0%, rgba(99,102,241,.15) 0%, transparent 70%);
      pointer-events: none;
    }}
    .report-logo {{ font-size: 13px; font-weight: 700; letter-spacing: 4px; color: var(--accent); text-transform: uppercase; margin-bottom: 12px; }}
    .report-title {{ font-size: clamp(22px, 4vw, 36px); font-weight: 800; background: linear-gradient(135deg, #e2e8f0, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
    .report-subtitle {{ font-size: 14px; color: var(--text-muted); margin-top: 8px; }}

    /* ── STATS BAR ── */
    .stats-bar {{
      display: flex; flex-wrap: wrap; gap: 16px; justify-content: center;
      padding: 20px 32px; background: var(--surface); border-bottom: 1px solid var(--border);
    }}
    .stat-pill {{
      background: var(--surface2); border: 1px solid var(--border); border-radius: 999px;
      padding: 8px 18px; font-size: 13px; font-weight: 600;
      display: flex; align-items: center; gap: 8px;
    }}
    .stat-pill span {{ color: var(--accent); font-size: 18px; font-weight: 800; }}

    /* ── NAV ── */
    .side-nav {{
      position: sticky; top: 0; z-index: 100;
      background: rgba(10,15,30,.92); backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      padding: 10px 24px; overflow-x: auto;
      display: flex; gap: 6px; white-space: nowrap;
    }}
    .nav-link {{
      font-size: 12px; font-weight: 600; padding: 6px 12px; border-radius: 999px;
      background: var(--surface2); border: 1px solid var(--border);
      color: var(--text-muted); transition: all .2s;
    }}
    .nav-link:hover {{ background: var(--accent); color: #fff; border-color: var(--accent); text-decoration: none; }}

    /* ── MAIN LAYOUT ── */
    .main-wrap {{ max-width: 1400px; margin: 0 auto; padding: 32px 24px; }}

    /* ── TOPIC SECTION ── */
    .topic-section {{ margin-bottom: 48px; }}
    .topic-header {{
      display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
      padding-bottom: 12px; border-bottom: 2px solid;
    }}
    .topic-icon {{ font-size: 24px; }}
    .topic-title {{ font-size: 20px; font-weight: 700; flex: 1; }}
    .topic-count {{ font-size: 12px; background: var(--surface2); border: 1px solid var(--border); padding: 4px 10px; border-radius: 999px; color: var(--text-muted); }}
    .topic-insight {{ font-size: 13px; color: var(--text-muted); background: var(--surface); border-left: 3px solid var(--accent); padding: 10px 14px; border-radius: 0 8px 8px 0; margin-bottom: 16px; }}

    /* ── CARDS GRID ── */
    .cards-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }}

    /* ── NEWS CARD ── */
    .news-card {{
      background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
      overflow: hidden; display: flex; flex-direction: column;
      transition: transform .2s, box-shadow .2s; box-shadow: var(--shadow);
    }}
    .news-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 32px rgba(0,0,0,.5); border-color: #374151; }}
    .card-img {{ width: 100%; height: 160px; object-fit: cover; }}
    .card-body {{ padding: 16px; flex: 1; display: flex; flex-direction: column; gap: 8px; }}
    .card-title {{ font-size: 14px; font-weight: 600; line-height: 1.4; }}
    .card-title a {{ color: var(--text); }}
    .card-title a:hover {{ color: var(--accent); text-decoration: none; }}
    .card-summary {{ font-size: 12px; color: var(--text-muted); flex: 1; line-height: 1.5; }}
    .card-meta {{ display: flex; flex-wrap: wrap; gap: 6px; font-size: 11px; color: var(--text-muted); margin-top: 4px; }}

    /* Chips */
    .source-chips, .topic-chips, .opp-badges {{ display: flex; flex-wrap: wrap; gap: 4px; }}
    .source-chip {{ font-size: 10px; font-weight: 700; background: #1e293b; border: 1px solid #334155; padding: 2px 7px; border-radius: 999px; color: #94a3b8; }}
    .topic-chip {{ font-size: 10px; font-weight: 600; background: rgba(99,102,241,.15); border: 1px solid rgba(99,102,241,.3); padding: 2px 7px; border-radius: 999px; color: #818cf8; }}
    .opp-badge {{ font-size: 10px; font-weight: 700; background: rgba(139,92,246,.15); border: 1px solid rgba(139,92,246,.4); padding: 2px 8px; border-radius: 999px; color: #a78bfa; }}

    /* Score bar */
    .score-bar-wrap {{ display: flex; align-items: center; gap: 8px; margin-top: 6px; }}
    .score-bar {{ height: 4px; border-radius: 999px; transition: width .4s; }}
    .score-label {{ font-size: 11px; font-weight: 700; color: var(--text-muted); min-width: 30px; }}

    /* ── REGIONS ── */
    #regions {{ margin-bottom: 48px; }}
    .regions-title {{ font-size: 20px; font-weight: 700; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }}
    .regions-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }}
    .region-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; }}
    .region-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
    .region-name {{ font-size: 15px; font-weight: 700; }}
    .region-signal {{ font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 999px; color: #fff; letter-spacing: .5px; }}
    .region-count {{ font-size: 12px; color: var(--text-muted); display: block; margin-bottom: 10px; }}
    .region-items {{ list-style: none; display: flex; flex-direction: column; gap: 6px; }}
    .region-items li a {{ font-size: 12px; color: var(--text-muted); line-height: 1.4; }}
    .region-items li a:hover {{ color: var(--accent); }}

    /* ── FOOTER ── */
    .report-footer {{
      text-align: center; padding: 32px; font-size: 12px; color: var(--text-muted);
      border-top: 1px solid var(--border); background: var(--surface);
    }}

    /* ── RESPONSIVE ── */
    @media (max-width: 768px) {{
      .main-wrap {{ padding: 16px; }}
      .cards-grid {{ grid-template-columns: 1fr; }}
      .stats-bar {{ gap: 10px; padding: 14px; }}
    }}
  </style>
</head>
<body>

<header class="report-header">
  <div class="report-logo">⬡ Nexus Intelligence</div>
  <h1 class="report-title">{html.escape(title)}</h1>
  <p class="report-subtitle">Gerado em {gen_str}</p>
</header>

<div class="stats-bar">
  <div class="stat-pill">📰 <span>{total}</span> notícias aprovadas</div>
  <div class="stat-pill">📡 <span>{sources_used}</span> fontes ativas</div>
  <div class="stat-pill">🗂️ <span>{topic_count}</span> tópicos</div>
  <div class="stat-pill">🎯 <span>{with_opp}</span> oportunidades</div>
</div>

<nav class="side-nav">
  {nav_links}
</nav>

<main class="main-wrap">
  {opp_section}
  {topic_sections}
  <section id="regions">
    <h2 class="regions-title">🌍 Análise Regional</h2>
    <div class="regions-grid">{regional_panels}</div>
  </section>
</main>

<footer class="report-footer">
  Nexus Intelligence v2.0 — {gen_str} — {total} notícias de {sources_used} fontes globais
</footer>

</body>
</html>"""
