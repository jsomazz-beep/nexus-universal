"""
Intelligence Hub v2.0 — Web App com painel de filtros rico.
Acesso: http://127.0.0.1:8787
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any

if not getattr(sys, "frozen", False):
    _SRC = Path(__file__).parent
    if str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="Intelligence Hub", version="2.0.0")

_last_result: dict[str, Any] = {}
_is_running = False
_config_cache = None

# ── Regiões disponíveis por continente ────────────────────────────────────────
REGIONS_BY_CONTINENT = {
    "AMÉRICAS": [
        "Brasil", "EUA", "México", "Colômbia", "Argentina",
        "Chile", "Peru", "Equador", "Bolívia", "Paraguai",
        "Uruguai", "Venezuela", "Canadá", "Panamá",
    ],
    "EUROPA": [
        "Portugal", "Espanha", "Alemanha", "Reino Unido",
        "França", "Itália", "Holanda", "Bélgica",
        "Suíça", "Áustria", "Polônia", "Suécia",
    ],
    "ÁFRICA": [
        "Angola", "Moçambique", "África do Sul", "Nigéria",
        "Quênia", "Gana", "Cabo Verde", "Egito",
        "Etiópia", "Tanzânia", "Senegal", "Costa do Marfim",
    ],
    "ÁSIA / OCEANIA": [
        "Emirados Arabes Unidos", "China", "Índia", "Japão",
        "Singapura", "Austrália", "Coreia do Sul", "Malásia",
        "Arábia Saudita", "Qatar", "Turquia", "Israel",
    ],
}

# ── Categorias de palavras-chave ───────────────────────────────────────────────
KEYWORD_GROUPS = {
    "🏗 Infraestrutura & Obras": [
        "infraestrutura", "saneamento", "obras", "rodovia",
        "porto", "aeroporto", "pipeline", "utilities",
    ],
    "📋 Contratos & Licitações": [
        "licitação", "concessão", "ppp", "tender",
        "procurement", "edital", "concession", "bid",
    ],
    "💼 Negócios & Aquisições": [
        "aquisição", "expansão", "investimento", "outsourcing",
        "terceirização", "facilities", "frota", "veículos",
    ],
    "⚡ Energia & Sustentabilidade": [
        "energia", "renovável", "solar", "petróleo",
        "gás", "transição energética", "ESG", "carbono",
    ],
    "🖥 Tecnologia & Inovação": [
        "tecnologia", "IA", "startup", "digitalização",
        "fintech", "data center", "cibersegurança", "software",
    ],
    "💹 Economia & Mercado": [
        "economia", "mercado", "inflação", "juros",
        "câmbio", "PIB", "crescimento", "recessão",
    ],
    "🌍 Geopolítica": [
        "geopolítica", "sanção", "diplomacia", "guerra",
        "conflito", "crise", "regulação", "política",
    ],
}

# ── Modelos de request ─────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    max_news: int = 60
    theme: str = "dark"
    time_window_days: int = 7
    selected_regions: list[str] = []
    selected_keywords: list[str] = []
    extra_keywords: str = ""
    extra_regions: str = ""
    enabled_source_types: list[str] = []   # vazio = todos habilitados


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(_build_ui())


@app.post("/api/run")
async def run_pipeline(req: RunRequest, background_tasks: BackgroundTasks):
    global _is_running
    if _is_running:
        raise HTTPException(status_code=409, detail="Execução já em andamento")
    _is_running = True
    background_tasks.add_task(_run_task, req)
    return {"status": "started"}


@app.get("/api/status")
async def status():
    return {"is_running": _is_running, "last_result": _last_result}


@app.get("/api/config")
async def config_info():
    try:
        cfg = _get_config()
        return {
            "regions": cfg.monitoring.get("regions", []),
            "priority_keywords": cfg.monitoring.get("priority_keywords", []),
            "associated_keywords": cfg.monitoring.get("associated_keywords", []),
            "themes": list(cfg.monitoring.get("themes", {}).keys()),
            "sources": [
                {"id": s.get("id"), "type": s.get("type", "rss"),
                 "enabled": s.get("enabled", True), "region": s.get("region_hint", "")}
                for s in cfg.sources
            ],
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/report/{filename}")
async def serve_report(filename: str):
    rp = Path("output") / filename
    if not rp.exists() or not filename.endswith(".html"):
        raise HTTPException(status_code=404)
    return FileResponse(str(rp), media_type="text/html")


@app.get("/api/reports")
async def list_reports():
    out = Path("output")
    if not out.exists():
        return []
    files = sorted(out.glob("report_*.html"), reverse=True)
    return [{"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1)} for f in files[:20]]


# ── Pipeline task ──────────────────────────────────────────────────────────────

def _run_task(req: RunRequest) -> None:
    global _is_running, _last_result
    try:
        from hub.config import load_config
        from hub.pipeline import IntelligenceHubPipeline

        cfg = load_config("config/config.yaml", ".env")

        # Aplicar overrides da UI
        cfg.raw.setdefault("project", {})["max_news"] = req.max_news
        cfg.raw.setdefault("project", {})["report_theme"] = req.theme
        cfg.raw.setdefault("filters", {})["time_window_days"] = req.time_window_days

        # Regiões selecionadas
        regions = list(req.selected_regions)
        if req.extra_regions:
            for r in req.extra_regions.split(","):
                r = r.strip()
                if r and r not in regions:
                    regions.append(r)
        if regions:
            cfg.raw.setdefault("monitoring", {})["regions"] = regions

        # Palavras-chave selecionadas
        keywords = list(req.selected_keywords)
        if req.extra_keywords:
            for kw in req.extra_keywords.split(","):
                kw = kw.strip()
                if kw and kw not in keywords:
                    keywords.append(kw)
        if keywords:
            cfg.raw.setdefault("monitoring", {})["priority_keywords"] = keywords

        # Filtrar tipos de fonte
        if req.enabled_source_types:
            for src in cfg.raw.get("sources", []):
                if src.get("type", "rss") not in req.enabled_source_types:
                    src["enabled"] = False

        pipeline = IntelligenceHubPipeline(cfg)
        result = pipeline.run()

        _last_result = {
            "success": result.success,
            "approved": result.counters.approved,
            "collected": result.counters.collected,
            "filtered_out": result.counters.filtered_out,
            "deduplicated": result.counters.deduplicated,
            "sources_ok": result.counters.sources_ok,
            "sources_failed": result.counters.sources_failed,
            "duration": round(result.duration_seconds, 1),
            "report_filename": Path(result.report_path_html).name if result.report_path_html else "",
            "synthesis": result.synthesis[:600] if result.synthesis else "",
            "source_errors": list(result.source_errors.keys())[:5],
        }
    except Exception as exc:
        logger.exception("Erro no pipeline: %s", exc)
        _last_result = {"success": False, "error": str(exc)}
    finally:
        _is_running = False


def _get_config():
    global _config_cache
    if _config_cache is None:
        from hub.config import load_config
        _config_cache = load_config("config/config.yaml", ".env")
    return _config_cache


# ── UI HTML ────────────────────────────────────────────────────────────────────

def _build_ui() -> str:
    # Serializa dados de configuração para JS
    regions_json = json.dumps(REGIONS_BY_CONTINENT, ensure_ascii=False)
    keywords_json = json.dumps(KEYWORD_GROUPS, ensure_ascii=False)

    # Regiões padrão (do config)
    try:
        cfg = _get_config()
        default_regions = cfg.monitoring.get("regions", [])
        default_keywords = (
            cfg.monitoring.get("priority_keywords", []) +
            cfg.monitoring.get("associated_keywords", [])
        )
        source_types = list({s.get("type", "rss") for s in cfg.sources if s.get("enabled", True)})
        total_sources = sum(1 for s in cfg.sources if s.get("enabled", True))
    except Exception:
        default_regions = ["Angola", "Brasil", "Portugal", "Emirados Arabes Unidos"]
        default_keywords = ["saneamento", "licitação", "infraestrutura"]
        source_types = ["rss", "gdelt", "hackernews", "reddit"]
        total_sources = 0

    default_regions_json = json.dumps(default_regions, ensure_ascii=False)
    default_keywords_json = json.dumps(default_keywords, ensure_ascii=False)
    source_types_json = json.dumps(sorted(source_types), ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="pt-BR" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Intelligence Hub v2.0</title>
<style>
:root {{
  --bg:#0f1117; --surface:#1a1d2e; --surface2:#252840; --surface3:#2e3252;
  --border:rgba(255,255,255,0.08); --text:#e2e8f0; --muted:#94a3b8; --faint:#64748b;
  --accent:#6366f1; --accent2:#06b6d4; --success:#10b981; --warning:#f59e0b; --danger:#ef4444;
  --font:'Segoe UI',system-ui,sans-serif; --radius:10px;
}}
[data-theme="light"] {{
  --bg:#f1f5f9; --surface:#ffffff; --surface2:#f8fafc; --surface3:#e2e8f0;
  --border:rgba(0,0,0,0.08); --text:#1e293b; --muted:#64748b; --faint:#94a3b8;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100vh}}

/* Topbar */
.topbar{{
  background:var(--surface);border-bottom:1px solid var(--border);
  padding:0.7rem 1.5rem;display:flex;align-items:center;gap:0.75rem;
  position:sticky;top:0;z-index:100;
}}
.brand{{font-weight:800;color:var(--accent);font-size:1rem;letter-spacing:-0.3px}}
.brand-sub{{font-size:0.7rem;color:var(--muted)}}
.topbar-actions{{margin-left:auto;display:flex;gap:0.5rem;align-items:center}}
.btn-icon{{background:var(--surface2);border:1px solid var(--border);border-radius:8px;
  padding:0.35rem 0.7rem;font-size:0.72rem;color:var(--muted);cursor:pointer;
  font-family:var(--font);transition:all 0.15s}}
.btn-icon:hover{{color:var(--text);border-color:var(--accent)}}

/* Layout */
.layout{{display:grid;grid-template-columns:320px 1fr;min-height:calc(100vh - 48px)}}
@media(max-width:900px){{.layout{{grid-template-columns:1fr}}}}

/* Sidebar esquerda */
.sidebar{{
  background:var(--surface);border-right:1px solid var(--border);
  overflow-y:auto;max-height:calc(100vh - 48px);position:sticky;top:48px;
}}
.sidebar-section{{border-bottom:1px solid var(--border);padding:1rem}}
.sidebar-title{{
  font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
  color:var(--accent);margin-bottom:0.8rem;display:flex;align-items:center;gap:0.4rem;
}}
.section-actions{{margin-left:auto;display:flex;gap:0.3rem}}
.mini-btn{{
  font-size:0.6rem;padding:0.15rem 0.5rem;border-radius:4px;
  background:var(--surface2);border:1px solid var(--border);
  color:var(--muted);cursor:pointer;font-family:var(--font);transition:all 0.15s
}}
.mini-btn:hover{{color:var(--text);border-color:var(--accent)}}

/* Grupo de checkboxes */
.kw-group{{margin-bottom:0.8rem}}
.kw-group-label{{
  font-size:0.7rem;font-weight:600;color:var(--text);
  margin-bottom:0.35rem;cursor:pointer;display:flex;align-items:center;gap:0.3rem
}}
.kw-group-label::before{{content:'▾';font-size:0.6rem;color:var(--muted)}}
.kw-chips{{display:flex;flex-wrap:wrap;gap:0.3rem}}
.chip{{
  display:inline-flex;align-items:center;gap:0.25rem;
  padding:0.2rem 0.55rem;border-radius:100px;
  font-size:0.68rem;font-weight:500;cursor:pointer;transition:all 0.15s;
  background:var(--surface2);border:1px solid var(--border);color:var(--muted);
  user-select:none
}}
.chip:hover{{border-color:var(--accent);color:var(--text)}}
.chip.selected{{background:rgba(99,102,241,0.15);border-color:var(--accent);color:#a5b4fc;font-weight:600}}
.chip input{{display:none}}

/* Regiões por continente */
.continent-block{{margin-bottom:0.8rem}}
.continent-label{{
  font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;
  color:var(--faint);margin-bottom:0.35rem
}}
.region-chips{{display:flex;flex-wrap:wrap;gap:0.25rem}}

/* Painel principal */
.main-panel{{padding:1.25rem;overflow-y:auto}}

/* Card de parâmetros */
.params-card{{
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:1.2rem;margin-bottom:1.2rem
}}
.params-title{{font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;
  color:var(--accent);margin-bottom:1rem}}
.params-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0.8rem}}
.param-group label{{display:block;font-size:0.7rem;color:var(--muted);margin-bottom:0.3rem}}
.param-group input, .param-group select{{
  width:100%;background:var(--surface2);border:1px solid var(--border);
  border-radius:8px;padding:0.45rem 0.7rem;font-size:0.82rem;color:var(--text);
  font-family:var(--font);outline:none;transition:border-color 0.15s
}}
.param-group input:focus, .param-group select:focus{{border-color:var(--accent)}}
input[type=range]{{padding:0;background:none;border:none;accent-color:var(--accent)}}
.range-val{{font-size:0.7rem;color:var(--accent);font-weight:700;margin-left:0.4rem}}

/* Tipos de fonte */
.source-types{{display:flex;flex-wrap:wrap;gap:0.35rem;margin-top:0.5rem}}
.src-chip{{
  display:inline-flex;align-items:center;gap:0.25rem;
  padding:0.2rem 0.6rem;border-radius:100px;
  font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.3px;
  cursor:pointer;transition:all 0.15s;user-select:none;
  border:1px solid var(--border);background:var(--surface2);color:var(--muted)
}}
.src-chip.selected{{border-color:var(--accent2);color:var(--accent2);background:rgba(6,182,212,0.1)}}
.src-rss.selected{{border-color:#f59e0b;color:#f59e0b;background:rgba(245,158,11,0.1)}}
.src-gdelt.selected{{border-color:#a5b4fc;color:#a5b4fc;background:rgba(99,102,241,0.1)}}
.src-guardian.selected{{border-color:#10b981;color:#10b981;background:rgba(16,185,129,0.1)}}
.src-hackernews.selected{{border-color:#fb923c;color:#fb923c;background:rgba(249,115,22,0.1)}}
.src-reddit.selected{{border-color:#f87171;color:#f87171;background:rgba(239,68,68,0.1)}}
.src-newsapi.selected{{border-color:#22d3ee;color:#22d3ee;background:rgba(6,182,212,0.1)}}
.src-nytimes.selected{{border-color:#94a3b8;color:#94a3b8;background:rgba(148,163,184,0.1)}}

/* Botão Gerar */
.run-btn{{
  width:100%;padding:0.85rem;background:var(--accent);color:#fff;
  border:none;border-radius:var(--radius);font-size:0.95rem;font-weight:700;
  cursor:pointer;font-family:var(--font);transition:opacity 0.2s;
  display:flex;align-items:center;justify-content:center;gap:0.5rem;
  letter-spacing:-0.2px
}}
.run-btn:hover{{opacity:0.88}}
.run-btn:disabled{{opacity:0.45;cursor:not-allowed}}

/* Status card */
.status-card{{
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:1.2rem;margin-bottom:1.2rem;transition:border-color 0.3s
}}
.status-idle{{border-left:4px solid var(--faint)}}
.status-running{{border-left:4px solid var(--warning);animation:pulse 1.5s infinite}}
.status-success{{border-left:4px solid var(--success)}}
.status-error{{border-left:4px solid var(--danger)}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.65}}}}
.status-title{{font-size:0.78rem;font-weight:700;margin-bottom:0.4rem}}
.status-body{{font-size:0.78rem;color:var(--muted);line-height:1.5}}

.kpi-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:0.5rem;margin-top:0.8rem}}
.kpi{{text-align:center;background:var(--surface2);border-radius:8px;padding:0.6rem 0.4rem}}
.kpi-v{{font-size:1.3rem;font-weight:800;color:var(--accent)}}
.kpi-l{{font-size:0.6rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.3px}}

.synthesis-box{{
  font-size:0.78rem;color:var(--muted);line-height:1.6;
  background:var(--surface2);border-radius:8px;padding:0.8rem;margin-top:0.8rem
}}
.report-btn{{
  display:inline-flex;align-items:center;gap:0.4rem;
  background:var(--success);color:#fff;padding:0.6rem 1.2rem;
  border-radius:8px;font-size:0.82rem;font-weight:700;text-decoration:none;
  margin-top:0.8rem;transition:opacity 0.2s
}}
.report-btn:hover{{opacity:0.85}}

/* Relatórios anteriores */
.reports-list{{display:flex;flex-direction:column;gap:0.4rem;margin-top:0.5rem}}
.report-item{{
  display:flex;align-items:center;gap:0.5rem;
  background:var(--surface2);border-radius:8px;padding:0.5rem 0.7rem;
  font-size:0.75rem;
}}
.report-item a{{color:var(--accent2);text-decoration:none;flex:1}}
.report-item a:hover{{text-decoration:underline}}
.report-size{{color:var(--faint);font-size:0.65rem}}

/* Tags de seleção ativa */
.selection-summary{{
  display:flex;flex-wrap:wrap;gap:0.3rem;margin-top:0.5rem;margin-bottom:0.3rem
}}
.sel-tag{{
  font-size:0.6rem;padding:0.1rem 0.45rem;border-radius:100px;
  background:rgba(99,102,241,0.12);color:var(--accent);border:1px solid rgba(99,102,241,0.3)
}}
</style>
</head>
<body>

<div class="topbar">
  <div>
    <div class="brand">⬡ Intelligence Hub</div>
    <div class="brand-sub">v2.0 · {total_sources} fontes configuradas</div>
  </div>
  <div class="topbar-actions">
    <button class="btn-icon" onclick="cycleTheme()">🎨 Tema</button>
    <button class="btn-icon" onclick="loadReports()">📁 Relatórios</button>
  </div>
</div>

<div class="layout">

  <!-- ══ Sidebar esquerda ════════════════════════════════════════════════ -->
  <div class="sidebar">

    <!-- Palavras-chave / Categorias -->
    <div class="sidebar-section">
      <div class="sidebar-title">
        🔑 Palavras-chave & Categorias
        <div class="section-actions">
          <button class="mini-btn" onclick="selectAllKeywords()">Todas</button>
          <button class="mini-btn" onclick="clearKeywords()">Limpar</button>
        </div>
      </div>
      <div id="keywords-container"></div>
      <div style="margin-top:0.6rem">
        <label style="font-size:0.68rem;color:var(--muted)">Palavras extras (vírgula)</label>
        <input type="text" id="extra-keywords" placeholder="Ex.: mineração, ESG, logística"
          style="width:100%;margin-top:0.25rem;background:var(--surface2);border:1px solid var(--border);
          border-radius:6px;padding:0.35rem 0.6rem;font-size:0.75rem;color:var(--text);
          font-family:var(--font);outline:none">
      </div>
    </div>

    <!-- Regiões -->
    <div class="sidebar-section">
      <div class="sidebar-title">
        🌍 Regiões Monitoradas
        <div class="section-actions">
          <button class="mini-btn" onclick="selectAllRegions()">Todas</button>
          <button class="mini-btn" onclick="clearRegions()">Limpar</button>
        </div>
      </div>
      <div id="regions-container"></div>
      <div style="margin-top:0.6rem">
        <label style="font-size:0.68rem;color:var(--muted)">Regiões extras (vírgula)</label>
        <input type="text" id="extra-regions" placeholder="Ex.: Nigéria, Índia, Peru"
          style="width:100%;margin-top:0.25rem;background:var(--surface2);border:1px solid var(--border);
          border-radius:6px;padding:0.35rem 0.6rem;font-size:0.75rem;color:var(--text);
          font-family:var(--font);outline:none">
      </div>
    </div>

  </div><!-- /sidebar -->

  <!-- ══ Painel principal ════════════════════════════════════════════════ -->
  <div class="main-panel">

    <!-- Status -->
    <div id="status-card" class="status-card status-idle">
      <div id="status-title" class="status-title">⬡ Pronto para executar</div>
      <div id="status-body" class="status-body">Configure filtros e clique em Gerar Relatório.</div>
      <div id="kpi-row" class="kpi-row" style="display:none">
        <div class="kpi"><div class="kpi-v" id="k-approved">—</div><div class="kpi-l">Aprovadas</div></div>
        <div class="kpi"><div class="kpi-v" id="k-collected">—</div><div class="kpi-l">Coletadas</div></div>
        <div class="kpi"><div class="kpi-v" id="k-sources">—</div><div class="kpi-l">Fontes OK</div></div>
        <div class="kpi"><div class="kpi-v" id="k-duration">—</div><div class="kpi-l">Segundos</div></div>
      </div>
      <div id="synthesis-box" style="display:none" class="synthesis-box"></div>
      <div id="report-link-box"></div>
    </div>

    <!-- Parâmetros -->
    <div class="params-card">
      <div class="params-title">⚙ Parâmetros de Execução</div>
      <div class="params-grid">
        <div class="param-group">
          <label>Máx. notícias: <span class="range-val" id="max-news-val">60</span></label>
          <input type="range" id="max-news" min="10" max="200" step="10" value="60"
            oninput="document.getElementById('max-news-val').textContent=this.value">
        </div>
        <div class="param-group">
          <label>Janela (dias): <span class="range-val" id="days-val">7</span></label>
          <input type="range" id="time-window" min="1" max="30" step="1" value="7"
            oninput="document.getElementById('days-val').textContent=this.value">
        </div>
        <div class="param-group">
          <label>Tema do relatório</label>
          <select id="theme">
            <option value="dark">🌙 Dark</option>
            <option value="light">☀️ Light</option>
            <option value="boardroom">🏢 Boardroom</option>
          </select>
        </div>
      </div>

      <!-- Tipos de fonte -->
      <div style="margin-top:0.9rem">
        <label style="font-size:0.7rem;color:var(--muted);display:block;margin-bottom:0.4rem">
          📡 Tipos de fonte (vazio = todas)
        </label>
        <div class="source-types" id="source-types-container"></div>
      </div>

      <!-- Resumo da seleção -->
      <div id="selection-summary" class="selection-summary" style="margin-top:0.8rem"></div>

      <!-- Botão gerar -->
      <button class="run-btn" id="run-btn" onclick="runPipeline()" style="margin-top:1rem">
        ▶ Gerar Relatório de Inteligência
      </button>
    </div>

    <!-- Relatórios anteriores -->
    <div class="params-card" id="reports-section" style="display:none">
      <div class="params-title">📁 Relatórios Anteriores</div>
      <div class="reports-list" id="reports-list"></div>
    </div>

  </div><!-- /main-panel -->
</div><!-- /layout -->

<script>
// ── Dados de configuração ─────────────────────────────────────────────────────
const REGIONS_DATA = {regions_json};
const KEYWORDS_DATA = {keywords_json};
const DEFAULT_REGIONS = {default_regions_json};
const DEFAULT_KEYWORDS = {default_keywords_json};
const SOURCE_TYPES = {source_types_json};

// ── Estado ────────────────────────────────────────────────────────────────────
const selectedKeywords = new Set(DEFAULT_KEYWORDS);
const selectedRegions = new Set(DEFAULT_REGIONS);
const selectedSourceTypes = new Set(); // vazio = todos
let polling = null;

// ── Renderiza checkboxes de palavras-chave ────────────────────────────────────
function renderKeywords() {{
  const container = document.getElementById('keywords-container');
  container.innerHTML = '';
  for (const [group, keywords] of Object.entries(KEYWORDS_DATA)) {{
    const div = document.createElement('div');
    div.className = 'kw-group';
    div.innerHTML = `<div class="kw-group-label">${{group}}</div>`;
    const chips = document.createElement('div');
    chips.className = 'kw-chips';
    keywords.forEach(kw => {{
      const chip = document.createElement('label');
      chip.className = 'chip' + (selectedKeywords.has(kw) ? ' selected' : '');
      chip.title = kw;
      chip.innerHTML = `<input type="checkbox" value="${{kw}}" ${{selectedKeywords.has(kw)?'checked':''}}>${{kw}}`;
      chip.querySelector('input').addEventListener('change', e => {{
        if (e.target.checked) {{ selectedKeywords.add(kw); chip.classList.add('selected'); }}
        else {{ selectedKeywords.delete(kw); chip.classList.remove('selected'); }}
        updateSummary();
      }});
      chips.appendChild(chip);
    }});
    div.appendChild(chips);
    container.appendChild(div);
  }}
}}

// ── Renderiza regiões por continente ──────────────────────────────────────────
function renderRegions() {{
  const container = document.getElementById('regions-container');
  container.innerHTML = '';
  for (const [continent, regions] of Object.entries(REGIONS_DATA)) {{
    const div = document.createElement('div');
    div.className = 'continent-block';
    div.innerHTML = `<div class="continent-label">${{continent}}</div>`;
    const chips = document.createElement('div');
    chips.className = 'region-chips';
    regions.forEach(region => {{
      const chip = document.createElement('label');
      chip.className = 'chip' + (selectedRegions.has(region) ? ' selected' : '');
      chip.innerHTML = `<input type="checkbox" value="${{region}}" ${{selectedRegions.has(region)?'checked':''}}>${{region}}`;
      chip.querySelector('input').addEventListener('change', e => {{
        if (e.target.checked) {{ selectedRegions.add(region); chip.classList.add('selected'); }}
        else {{ selectedRegions.delete(region); chip.classList.remove('selected'); }}
        updateSummary();
      }});
      chips.appendChild(chip);
    }});
    div.appendChild(chips);
    container.appendChild(div);
  }}
}}

// ── Renderiza tipos de fonte ──────────────────────────────────────────────────
function renderSourceTypes() {{
  const container = document.getElementById('source-types-container');
  const icons = {{
    rss:'📰', gdelt:'🌐', guardian:'🗞', hackernews:'🟠',
    reddit:'🔴', newsapi:'📡', nytimes:'📝'
  }};
  SOURCE_TYPES.forEach(type => {{
    const chip = document.createElement('span');
    chip.className = `src-chip src-${{type}}`;
    chip.textContent = `${{icons[type]||'•'}} ${{type.toUpperCase()}}`;
    chip.onclick = () => {{
      if (selectedSourceTypes.has(type)) {{
        selectedSourceTypes.delete(type); chip.classList.remove('selected');
      }} else {{
        selectedSourceTypes.add(type); chip.classList.add('selected');
      }}
      updateSummary();
    }};
    container.appendChild(chip);
  }});
}}

// ── Resumo da seleção ─────────────────────────────────────────────────────────
function updateSummary() {{
  const box = document.getElementById('selection-summary');
  const tags = [];
  if (selectedRegions.size) tags.push(`🌍 ${{selectedRegions.size}} regiões`);
  if (selectedKeywords.size) tags.push(`🔑 ${{selectedKeywords.size}} palavras-chave`);
  if (selectedSourceTypes.size) tags.push(`📡 ${{[...selectedSourceTypes].join(', ')}}`);
  box.innerHTML = tags.map(t => `<span class="sel-tag">${{t}}</span>`).join('');
}}

// ── Ações em massa ────────────────────────────────────────────────────────────
function selectAllKeywords() {{
  document.querySelectorAll('#keywords-container input[type=checkbox]').forEach(cb => {{
    cb.checked = true; selectedKeywords.add(cb.value);
    cb.closest('.chip').classList.add('selected');
  }});
  updateSummary();
}}
function clearKeywords() {{
  document.querySelectorAll('#keywords-container input[type=checkbox]').forEach(cb => {{
    cb.checked = false; selectedKeywords.delete(cb.value);
    cb.closest('.chip').classList.remove('selected');
  }});
  updateSummary();
}}
function selectAllRegions() {{
  document.querySelectorAll('#regions-container input[type=checkbox]').forEach(cb => {{
    cb.checked = true; selectedRegions.add(cb.value);
    cb.closest('.chip').classList.add('selected');
  }});
  updateSummary();
}}
function clearRegions() {{
  document.querySelectorAll('#regions-container input[type=checkbox]').forEach(cb => {{
    cb.checked = false; selectedRegions.delete(cb.value);
    cb.closest('.chip').classList.remove('selected');
  }});
  updateSummary();
}}

// ── Execução ──────────────────────────────────────────────────────────────────
async function runPipeline() {{
  const btn = document.getElementById('run-btn');
  btn.disabled = true;
  btn.textContent = '⏳ Coletando notícias...';
  setStatus('running', '⏳ Pipeline em execução...', 'Coletando de todas as fontes selecionadas. Aguarde até 2 minutos.', null);

  const payload = {{
    max_news: parseInt(document.getElementById('max-news').value),
    theme: document.getElementById('theme').value,
    time_window_days: parseInt(document.getElementById('time-window').value),
    selected_regions: [...selectedRegions],
    selected_keywords: [...selectedKeywords],
    extra_keywords: document.getElementById('extra-keywords').value,
    extra_regions: document.getElementById('extra-regions').value,
    enabled_source_types: [...selectedSourceTypes],
  }};

  try {{
    const resp = await fetch('/api/run', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(payload),
    }});
    if (!resp.ok) {{
      const err = await resp.json();
      throw new Error(err.detail || 'Erro ao iniciar');
    }}
    polling = setInterval(checkStatus, 2500);
  }} catch(e) {{
    setStatus('error', '✗ Erro ao iniciar', e.message, null);
    btn.disabled = false; btn.innerHTML = '▶ Gerar Relatório de Inteligência';
  }}
}}

async function checkStatus() {{
  try {{
    const resp = await fetch('/api/status');
    const data = await resp.json();
    if (!data.is_running) {{
      clearInterval(polling);
      const r = data.last_result;
      if (r && r.success !== false) {{
        setStatus('success', '✓ Relatório gerado com sucesso!', '', r);
      }} else {{
        const err = r ? (r.error || 'Erro desconhecido') : 'Sem dados de retorno';
        setStatus('error', '✗ Falha na execução', err, null);
      }}
      const btn = document.getElementById('run-btn');
      btn.disabled = false; btn.innerHTML = '▶ Gerar Relatório de Inteligência';
    }}
  }} catch(e) {{}}
}}

function setStatus(type, title, body, result) {{
  const card = document.getElementById('status-card');
  card.className = 'status-card status-' + type;
  document.getElementById('status-title').textContent = title;
  document.getElementById('status-body').textContent = body;
  const kpiRow = document.getElementById('kpi-row');
  const synthBox = document.getElementById('synthesis-box');
  const linkBox = document.getElementById('report-link-box');
  if (result && result.approved !== undefined) {{
    kpiRow.style.display = 'grid';
    document.getElementById('k-approved').textContent = result.approved ?? '—';
    document.getElementById('k-collected').textContent = result.collected ?? '—';
    document.getElementById('k-sources').textContent = result.sources_ok ?? '—';
    document.getElementById('k-duration').textContent = result.duration ?? '—';
    if (result.synthesis) {{
      synthBox.style.display = 'block';
      synthBox.textContent = result.synthesis;
    }}
    if (result.report_filename) {{
      linkBox.innerHTML = `<a class="report-btn" href="/report/${{result.report_filename}}" target="_blank">🔗 Abrir Relatório Completo</a>`;
    }}
    if (result.source_errors && result.source_errors.length) {{
      document.getElementById('status-body').textContent =
        `⚠ Fontes com erro: ${{result.source_errors.join(', ')}}`;
    }}
  }} else {{
    kpiRow.style.display = 'none';
    synthBox.style.display = 'none';
    linkBox.innerHTML = '';
  }}
}}

// ── Relatórios anteriores ─────────────────────────────────────────────────────
async function loadReports() {{
  const section = document.getElementById('reports-section');
  const list = document.getElementById('reports-list');
  section.style.display = 'block';
  list.innerHTML = '<div style="font-size:0.75rem;color:var(--muted)">Carregando...</div>';
  try {{
    const resp = await fetch('/api/reports');
    const reports = await resp.json();
    if (!reports.length) {{ list.innerHTML = '<div style="font-size:0.75rem;color:var(--muted)">Nenhum relatório encontrado.</div>'; return; }}
    list.innerHTML = reports.map(r =>
      `<div class="report-item">
        <a href="/report/${{r.name}}" target="_blank">📄 ${{r.name}}</a>
        <span class="report-size">${{r.size_kb}} KB</span>
      </div>`
    ).join('');
  }} catch(e) {{
    list.innerHTML = '<div style="font-size:0.75rem;color:var(--danger)">Erro ao carregar relatórios.</div>';
  }}
}}

// ── Tema ──────────────────────────────────────────────────────────────────────
const THEMES = ['dark','light','boardroom'];
let themeIdx = 0;
function cycleTheme() {{
  themeIdx = (themeIdx + 1) % THEMES.length;
  document.documentElement.setAttribute('data-theme', THEMES[themeIdx]);
  document.getElementById('theme').value = THEMES[themeIdx];
}}

// ── Init ──────────────────────────────────────────────────────────────────────
renderKeywords();
renderRegions();
renderSourceTypes();
updateSummary();
checkStatus(); // carrega status da última execução
</script>
</body>
</html>"""


# ── Entry point ────────────────────────────────────────────────────────────────

def start_server(host: str = "127.0.0.1", port: int = 8787) -> None:
    try:
        import uvicorn
    except ImportError:
        print("[ERRO] uvicorn não está instalado. Execute: pip install uvicorn[standard]")
        sys.exit(1)

    print(f"[OK] Intelligence Hub disponível em http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Intelligence Hub Web App")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    start_server(host=args.host, port=args.port)
