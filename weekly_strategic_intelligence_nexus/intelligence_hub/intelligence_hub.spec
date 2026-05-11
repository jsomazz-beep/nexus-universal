# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — Intelligence Hub v2.0
Gera: dist/IntelligenceHub.exe  (único arquivo, ~200MB)

Para compilar:
    cd intelligence_hub
    python -m PyInstaller intelligence_hub.spec --noconfirm
    (ou use scripts\build_exe.bat)
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH)          # intelligence_hub/
SRC  = ROOT / "src"

# ── Data files ────────────────────────────────────────────────────────────────
datas = [
    # Templates HTML do relatório
    (str(ROOT / "src" / "hub" / "report" / "templates"), "hub_templates"),
    # Config de exemplo (copiada para config/config.yaml na primeira execução)
    (str(ROOT / "config" / "config.example.yaml"), "hub_config"),
    # .env de exemplo
    (str(ROOT / ".env.example"), "."),
]

# Inclui profiles do langdetect (necessário para detecção de idioma)
try:
    datas += collect_data_files("langdetect")
except Exception:
    pass

# Inclui dados do certifi (certificados TLS para requests/httpx)
try:
    datas += collect_data_files("certifi")
except Exception:
    pass

# ── Hidden imports ────────────────────────────────────────────────────────────
# Módulos importados dinamicamente (dentro de funções) que PyInstaller não detecta
hidden = [
    # uvicorn internals
    "uvicorn", "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.loops.asyncio", "uvicorn.protocols", "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan", "uvicorn.lifespan.off", "uvicorn.lifespan.on",
    "uvicorn.config", "uvicorn.main", "uvicorn.middleware",
    "uvicorn.middleware.proxy_headers",
    # anyio / asyncio
    "anyio", "anyio._backends._asyncio", "anyio.abc", "anyio.streams",
    "anyio.streams.memory",
    # FastAPI / Starlette
    "fastapi", "fastapi.routing", "fastapi.middleware",
    "starlette", "starlette.routing", "starlette.applications",
    "starlette.middleware", "starlette.responses", "starlette.background",
    "starlette.exceptions", "starlette.datastructures", "starlette.types",
    "starlette.concurrency",
    # Pydantic
    "pydantic", "pydantic.v1", "pydantic_core",
    # hub modules (todos importados dinamicamente dentro de funções)
    "hub", "hub.config", "hub.models", "hub.pipeline",
    "hub.collectors", "hub.collectors.base", "hub.collectors.rss",
    "hub.collectors.gdelt", "hub.collectors.guardian",
    "hub.collectors.hackernews", "hub.collectors.reddit",
    "hub.collectors.newsapi", "hub.collectors.nytimes",
    "hub.collectors.og_enricher",
    "hub.processors", "hub.processors.filter",
    "hub.processors.deduplicator", "hub.processors.scorer",
    "hub.processors.translator",
    "hub.storage", "hub.storage.database",
    "hub.report", "hub.report.composer",
    # dependências
    "feedparser", "feedparser.api", "feedparser.encodings",
    "yaml", "dateutil", "dateutil.parser",
    "langdetect", "langdetect.detector", "langdetect.detector_factory",
    "deep_translator", "deep_translator.google",
    "apscheduler", "apscheduler.schedulers", "apscheduler.schedulers.background",
    "rich", "rich.console", "rich.progress", "rich.table", "rich.logging",
    "bs4", "bs4.builder", "bs4.builder._htmlparser",
    "sqlite3", "httpx", "h11", "jinja2", "jinja2.ext",
    "multiprocessing", "concurrent.futures",
    "email", "email.mime", "html.parser",
    "urllib.parse", "urllib.request",
]

# Adiciona submodules do deep_translator automaticamente
try:
    hidden += collect_submodules("deep_translator")
except Exception:
    pass

# ── Análise ───────────────────────────────────────────────────────────────────
a = Analysis(
    [str(SRC / "main_exe.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "numpy", "pandas", "PIL", "Pillow",
        "tkinter", "tk", "PyQt5", "PyQt6", "wx",
        "IPython", "jupyter", "notebook",
        "pytest", "unittest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# ── Executável único (--onefile) ──────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="IntelligenceHub",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # comprime com UPX se disponível (~30% menor)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # mostra janela CMD com logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,          # adicione um .ico aqui se quiser ícone personalizado
)
