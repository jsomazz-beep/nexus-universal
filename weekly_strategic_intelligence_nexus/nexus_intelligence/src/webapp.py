"""Nexus Intelligence — Flask webapp."""
from __future__ import annotations

import copy
import json
import os
import sys
import threading
import traceback
import webbrowser
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from flask import Flask, Response, jsonify, render_template_string, request, send_file
from nexus.config import load_config
from nexus.logging_config import setup_logging
from nexus.paths import get_project_root
from nexus.pipeline import NexusPipeline
from nexus.runtime import load_env_file

PROJECT_ROOT = get_project_root()
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "config.yaml"
DEFAULT_ENV = PROJECT_ROOT / ".env"

app = Flask(__name__)

# Shared state
_state = {
    "running": False,
    "progress": 0,
    "message": "",
    "last_report": None,
    "last_error": None,
    "counters": {},
    "lock": threading.Lock(),
}


def _sse(data: str) -> str:
    return f"data: {data}\n\n"


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    cfg = load_config(DEFAULT_CONFIG)
    topics = list(cfg.topics.keys())
    sources = cfg.sources
    regions = cfg.monitoring.get("regions", [])
    priority_kws = cfg.monitoring.get("priority_keywords", [])

    reports = sorted(
        (PROJECT_ROOT / "output").glob("nexus_report_*.html"),
        key=lambda p: p.stat().st_mtime, reverse=True
    )
    report_names = [p.name for p in reports[:20]]

    return render_template_string(
        _WEBAPP_HTML,
        topics=topics,
        sources=sources,
        regions=regions,
        priority_kws=priority_kws,
        report_names=report_names,
        state=_state,
    )


@app.route("/run", methods=["POST"])
def run_pipeline():
    with _state["lock"]:
        if _state["running"]:
            return jsonify({"error": "Já em execução"}), 409
        _state["running"] = True
        _state["progress"] = 0
        _state["message"] = "Iniciando…"
        _state["last_error"] = None
        _state["last_report"] = None

    form = request.get_json(silent=True) or request.form.to_dict(flat=False)

    def get(key, default=None):
        v = form.get(key, default)
        return v[0] if isinstance(v, list) else v

    def get_list(key):
        v = form.get(key, [])
        return v if isinstance(v, list) else [v]

    selected_topics = get_list("topics")
    selected_regions = get_list("regions")
    selected_source_ids = get_list("source_ids")
    extra_keywords = [k.strip() for k in (get("extra_keywords") or "").split(",") if k.strip()]
    max_news = int(get("max_news") or 80)
    time_window = int(get("time_window_days") or 7)

    def worker():
        try:
            base_cfg = load_config(DEFAULT_CONFIG)
            raw = copy.deepcopy(base_cfg.raw)

            # Apply form overrides
            if selected_regions:
                raw.setdefault("monitoring", {})["regions"] = selected_regions
            if selected_topics:
                raw.setdefault("monitoring", {})
                all_topics = raw["monitoring"].get("topics", {})
                raw["monitoring"]["topics"] = {k: v for k, v in all_topics.items() if k in selected_topics}
            if selected_source_ids:
                raw["sources"] = [s for s in raw.get("sources", []) if s.get("id") in selected_source_ids]
            if extra_keywords:
                existing = raw.get("monitoring", {}).get("priority_keywords", [])
                raw.setdefault("monitoring", {})["priority_keywords"] = list(dict.fromkeys(existing + extra_keywords))
            raw.setdefault("project", {})["max_news"] = max_news
            raw.setdefault("filters", {})["time_window_days"] = time_window

            from nexus.config import AppConfig
            cfg = AppConfig(raw=raw)
            env = load_env_file(DEFAULT_ENV)
            setup_logging(str(PROJECT_ROOT / "logs"))

            def progress_cb(msg, pct):
                with _state["lock"]:
                    _state["message"] = msg
                    _state["progress"] = pct

            pipeline = NexusPipeline(cfg, env, progress_cb)
            result = pipeline.run()

            with _state["lock"]:
                _state["last_report"] = result.report_path_html
                _state["counters"] = {
                    "collected": result.counters.collected,
                    "filtered": result.counters.filtered,
                    "deduplicated": result.counters.deduplicated,
                    "approved": result.counters.approved,
                }
                _state["progress"] = 100
                _state["message"] = "Concluído!"

        except Exception:
            with _state["lock"]:
                _state["last_error"] = traceback.format_exc()
                _state["message"] = "Erro na execução"
        finally:
            with _state["lock"]:
                _state["running"] = False

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return jsonify({"status": "started"})


@app.route("/status")
def status():
    with _state["lock"]:
        return jsonify({
            "running": _state["running"],
            "progress": _state["progress"],
            "message": _state["message"],
            "last_report": Path(_state["last_report"]).name if _state["last_report"] else None,
            "last_error": _state["last_error"],
            "counters": _state["counters"],
        })


@app.route("/report/latest")
def report_latest():
    reports = sorted(
        (PROJECT_ROOT / "output").glob("nexus_report_*.html"),
        key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not reports:
        return "Nenhum relatório encontrado.", 404
    return send_file(str(reports[0]))


@app.route("/report/<name>")
def report_by_name(name: str):
    safe = Path(name).name
    path = PROJECT_ROOT / "output" / safe
    if not path.exists():
        return "Relatório não encontrado.", 404
    return send_file(str(path))


# ── HTML ──────────────────────────────────────────────────────────────────────

_WEBAPP_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nexus Intelligence — Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#060d1a;--surface:#0d1526;--surface2:#111f35;--border:#1a2d4a;--text:#e2e8f0;--muted:#64748b;--accent:#6366f1;--accent2:#818cf8;--green:#10b981;--amber:#f59e0b;--red:#ef4444;--r:12px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;flex-direction:column}
a{color:var(--accent2)}
input,select,textarea{background:var(--surface2);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:8px 12px;font-size:13px;font-family:inherit;width:100%}
input:focus,select:focus,textarea:focus{outline:2px solid var(--accent);border-color:var(--accent)}
button{cursor:pointer;font-family:inherit;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:600;transition:all .2s}
.btn-primary{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff}
.btn-primary:hover{opacity:.85;transform:translateY(-1px)}
.btn-primary:disabled{opacity:.4;cursor:not-allowed;transform:none}
.btn-secondary{background:var(--surface2);color:var(--muted);border:1px solid var(--border)}
.btn-secondary:hover{border-color:var(--accent);color:var(--text)}
.btn-danger{background:rgba(239,68,68,.15);color:var(--red);border:1px solid rgba(239,68,68,.3)}

/* Header */
.header{background:linear-gradient(135deg,#060d1a 0%,#0f172a 50%,#0d1526 100%);border-bottom:1px solid var(--border);padding:20px 32px;display:flex;align-items:center;justify-content:space-between;position:relative;overflow:hidden}
.header::after{content:'';position:absolute;top:-60%;left:40%;width:400px;height:400px;background:radial-gradient(circle,rgba(99,102,241,.08),transparent 70%);pointer-events:none}
.brand{display:flex;align-items:center;gap:12px}
.brand-icon{width:40px;height:40px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px}
.brand-text{font-size:18px;font-weight:800;letter-spacing:-.3px}
.brand-sub{font-size:11px;color:var(--muted);font-weight:500;letter-spacing:1px;text-transform:uppercase}
.header-chips{display:flex;gap:8px}
.chip{font-size:11px;font-weight:700;padding:5px 12px;border-radius:999px;background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.25);color:var(--accent2);letter-spacing:.3px}

/* Layout */
.layout{display:grid;grid-template-columns:340px 1fr;flex:1;overflow:hidden;height:calc(100vh - 80px)}
.sidebar{background:var(--surface);border-right:1px solid var(--border);overflow-y:auto;padding:20px}
.main{overflow:hidden;display:flex;flex-direction:column}

/* Sidebar */
.section-label{font-size:10px;font-weight:800;letter-spacing:2px;color:var(--muted);text-transform:uppercase;margin:20px 0 10px}
.section-label:first-child{margin-top:0}
.form-group{margin-bottom:14px}
.form-group label{font-size:12px;font-weight:600;color:var(--muted);display:block;margin-bottom:5px}
.checkgrid{display:grid;grid-template-columns:1fr 1fr;gap:4px}
.check-item{display:flex;align-items:center;gap:7px;padding:6px 8px;border-radius:7px;border:1px solid transparent;cursor:pointer;transition:.15s;font-size:12px}
.check-item:hover{background:var(--surface2);border-color:var(--border)}
.check-item input[type=checkbox]{width:14px;height:14px;accent-color:var(--accent);cursor:pointer}
.check-item.full-width{grid-column:1/-1}
.source-hint{font-size:10px;color:var(--muted);margin-left:21px}

.num-row{display:flex;gap:8px}
.num-row .form-group{flex:1}
.run-btn{width:100%;margin-top:8px;padding:14px;font-size:14px;font-weight:700;letter-spacing:.3px}

/* Progress */
.progress-wrap{background:var(--surface);border-bottom:1px solid var(--border);padding:14px 20px;display:none}
.progress-wrap.visible{display:block}
.progress-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.progress-msg{font-size:13px;font-weight:600}
.progress-pct{font-size:12px;color:var(--muted);font-weight:700}
.progress-bar-bg{height:6px;background:var(--surface2);border-radius:999px;overflow:hidden}
.progress-bar-fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2));border-radius:999px;transition:width .4s ease;width:0%}

/* Status box */
.status-box{margin:16px 20px;border-radius:var(--r);padding:14px 18px;display:none}
.status-box.visible{display:block}
.status-ok{background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.25)}
.status-err{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25)}
.status-title{font-size:13px;font-weight:700;margin-bottom:8px}
.status-ok .status-title{color:var(--green)}
.status-err .status-title{color:var(--red)}
.counters{display:flex;flex-wrap:wrap;gap:10px;margin-top:10px}
.counter{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:8px 14px;text-align:center}
.counter-val{font-size:20px;font-weight:800;color:var(--accent2)}
.counter-lbl{font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.open-report-btn{display:inline-block;margin-top:12px;padding:9px 18px;background:var(--accent);color:#fff;border-radius:8px;font-weight:700;font-size:13px;cursor:pointer;border:none;text-decoration:none}
pre.err-trace{font-size:11px;color:var(--red);white-space:pre-wrap;max-height:200px;overflow-y:auto;margin-top:8px;background:rgba(239,68,68,.05);padding:10px;border-radius:8px}

/* Report frame */
.report-wrap{flex:1;overflow:hidden;position:relative}
.report-frame{width:100%;height:100%;border:none;background:#fff}
.report-placeholder{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:16px;color:var(--muted)}
.placeholder-icon{font-size:64px;opacity:.3}
.placeholder-text{font-size:14px;font-weight:500}

/* Report picker */
.report-picker{display:flex;gap:8px;align-items:center;padding:12px 20px;border-bottom:1px solid var(--border);background:var(--surface)}
.report-picker label{font-size:12px;font-weight:600;color:var(--muted);white-space:nowrap}
.report-picker select{flex:1}

@media(max-width:900px){
  .layout{grid-template-columns:1fr;height:auto}
  .main{height:70vh}
  .header{padding:14px 16px}
}
</style>
</head>
<body>

<header class="header">
  <div class="brand">
    <div class="brand-icon">⬡</div>
    <div>
      <div class="brand-text">Nexus Intelligence</div>
      <div class="brand-sub">Global News Aggregator v2.0</div>
    </div>
  </div>
  <div class="header-chips">
    <span class="chip">{{ sources|length }} Fontes</span>
    <span class="chip">{{ topics|length }} Tópicos</span>
    <span class="chip">WebApp Local</span>
  </div>
</header>

<div class="layout">
  <!-- SIDEBAR -->
  <aside class="sidebar">
    <div class="section-label">Tópicos</div>
    <div class="checkgrid" id="topics-grid">
      <label class="check-item full-width">
        <input type="checkbox" id="check-all-topics" onchange="toggleAll('topic-cb',this.checked)"> Todos os tópicos
      </label>
      {% for t in topics %}
      <label class="check-item">
        <input type="checkbox" class="topic-cb" name="topics" value="{{ t }}" checked> {{ t }}
      </label>
      {% endfor %}
    </div>

    <div class="section-label">Regiões</div>
    <div class="checkgrid">
      {% for r in regions %}
      <label class="check-item">
        <input type="checkbox" name="regions" value="{{ r }}" checked> {{ r }}
      </label>
      {% endfor %}
    </div>

    <div class="section-label">Fontes</div>
    <div style="max-height:220px;overflow-y:auto">
      <label class="check-item full-width">
        <input type="checkbox" id="check-all-sources" onchange="toggleAll('source-cb',this.checked)" checked> Todas as fontes
      </label>
      {% for s in sources %}
      <label class="check-item full-width">
        <input type="checkbox" class="source-cb" name="source_ids" value="{{ s.id }}" checked>
        {{ s.get('label', s.id) }}
        <span class="source-hint">{{ s.get('region_hint','') }} · {{ s.get('type','rss') }}</span>
      </label>
      {% endfor %}
    </div>

    <div class="section-label">Parâmetros</div>
    <div class="num-row">
      <div class="form-group">
        <label>Máx. notícias</label>
        <input type="number" name="max_news" value="80" min="10" max="300">
      </div>
      <div class="form-group">
        <label>Janela (dias)</label>
        <input type="number" name="time_window_days" value="7" min="1" max="30">
      </div>
    </div>

    <div class="form-group">
      <label>Palavras-chave extras (separadas por vírgula)</label>
      <textarea name="extra_keywords" rows="2" placeholder="ex.: fusão, startup, regulação"></textarea>
    </div>

    <button class="btn-primary run-btn" id="run-btn" onclick="runPipeline()">
      ⚡ Gerar Relatório
    </button>
  </aside>

  <!-- MAIN -->
  <div class="main">
    <!-- Progress -->
    <div class="progress-wrap" id="progress-wrap">
      <div class="progress-top">
        <span class="progress-msg" id="progress-msg">Aguardando…</span>
        <span class="progress-pct" id="progress-pct">0%</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" id="progress-fill"></div>
      </div>
    </div>

    <!-- Status -->
    <div class="status-box" id="status-box">
      <div class="status-title" id="status-title"></div>
      <div id="status-body"></div>
    </div>

    <!-- Report picker -->
    <div class="report-picker">
      <label>Relatório:</label>
      <select id="report-select" onchange="loadReport(this.value)">
        <option value="">— Selecionar —</option>
        {% for r in report_names %}
        <option value="{{ r }}">{{ r }}</option>
        {% endfor %}
      </select>
      <button class="btn-secondary" onclick="refreshReports()">↻</button>
    </div>

    <!-- Report frame -->
    <div class="report-wrap">
      <iframe class="report-frame" id="report-frame" style="display:none"></iframe>
      <div class="report-placeholder" id="placeholder">
        <div class="placeholder-icon">📡</div>
        <div class="placeholder-text">Gere um relatório ou selecione um existente</div>
      </div>
    </div>
  </div>
</div>

<script>
function toggleAll(cls, checked) {
  document.querySelectorAll('.' + cls).forEach(c => c.checked = checked);
}

function getFormData() {
  const data = {
    topics: [...document.querySelectorAll('.topic-cb:checked')].map(c => c.value),
    regions: [...document.querySelectorAll('[name=regions]:checked')].map(c => c.value),
    source_ids: [...document.querySelectorAll('.source-cb:checked')].map(c => c.value),
    max_news: document.querySelector('[name=max_news]').value,
    time_window_days: document.querySelector('[name=time_window_days]').value,
    extra_keywords: document.querySelector('[name=extra_keywords]').value,
  };
  return data;
}

async function runPipeline() {
  const btn = document.getElementById('run-btn');
  btn.disabled = true;
  btn.textContent = '⏳ Executando…';

  document.getElementById('progress-wrap').classList.add('visible');
  document.getElementById('status-box').classList.remove('visible');

  const resp = await fetch('/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(getFormData()),
  });
  if (!resp.ok) {
    const e = await resp.json();
    showError(e.error || 'Erro desconhecido');
    btn.disabled = false;
    btn.textContent = '⚡ Gerar Relatório';
    return;
  }
  pollStatus();
}

let _pollTimer = null;
function pollStatus() {
  clearTimeout(_pollTimer);
  fetch('/status').then(r => r.json()).then(data => {
    document.getElementById('progress-msg').textContent = data.message || '';
    document.getElementById('progress-pct').textContent = data.progress + '%';
    document.getElementById('progress-fill').style.width = data.progress + '%';

    if (data.running) {
      _pollTimer = setTimeout(pollStatus, 800);
    } else {
      const btn = document.getElementById('run-btn');
      btn.disabled = false;
      btn.textContent = '⚡ Gerar Relatório';
      document.getElementById('progress-wrap').classList.remove('visible');

      if (data.last_error) {
        showError(data.last_error);
      } else if (data.last_report) {
        showSuccess(data.counters, data.last_report);
        loadReport(data.last_report);
        refreshReports();
      }
    }
  }).catch(() => { _pollTimer = setTimeout(pollStatus, 2000); });
}

function showSuccess(counters, reportName) {
  const box = document.getElementById('status-box');
  box.className = 'status-box visible status-ok';
  document.getElementById('status-title').textContent = '✅ Relatório gerado com sucesso!';
  const body = document.getElementById('status-body');
  body.innerHTML = `
    <div class="counters">
      <div class="counter"><div class="counter-val">${counters.collected||0}</div><div class="counter-lbl">Coletadas</div></div>
      <div class="counter"><div class="counter-val">${counters.filtered||0}</div><div class="counter-lbl">Filtradas</div></div>
      <div class="counter"><div class="counter-val">${counters.deduplicated||0}</div><div class="counter-lbl">Dedup.</div></div>
      <div class="counter"><div class="counter-val">${counters.approved||0}</div><div class="counter-lbl">Aprovadas</div></div>
    </div>
    <a class="open-report-btn" href="/report/${reportName}" target="_blank">🔗 Abrir em nova aba</a>
  `;
}

function showError(msg) {
  const box = document.getElementById('status-box');
  box.className = 'status-box visible status-err';
  document.getElementById('status-title').textContent = '❌ Erro na execução';
  document.getElementById('status-body').innerHTML = `<pre class="err-trace">${msg}</pre>`;
}

function loadReport(name) {
  if (!name) return;
  const frame = document.getElementById('report-frame');
  const ph = document.getElementById('placeholder');
  const url = name.startsWith('http') ? name : '/report/' + name;
  frame.src = url;
  frame.style.display = 'block';
  ph.style.display = 'none';
}

function refreshReports() {
  fetch('/status').then(r => r.json()).then(() => {
    // reload page select silently via partial update would need AJAX;
    // for simplicity just reload if needed
  });
}

// Init
document.getElementById('check-all-topics').checked = true;
document.getElementById('check-all-sources').checked = true;
</script>
</body>
</html>"""


def main():
    env = load_env_file(DEFAULT_ENV)
    port = int(env.get("NEXUS_PORT") or 8788)
    setup_logging(str(PROJECT_ROOT / "logs"))

    def open_browser():
        import time; time.sleep(1.2)
        webbrowser.open(f"http://127.0.0.1:{port}")

    threading.Thread(target=open_browser, daemon=True).start()
    print(f"⬡ Nexus Intelligence rodando em http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
