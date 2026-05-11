from __future__ import annotations

import copy
import hashlib
import html
import json
import os
import re
import sys
import threading
import traceback
import unicodedata
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote_plus, urlparse

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from news_reporter.config import AppConfig, load_config
from news_reporter.logging_config import setup_logging
from news_reporter.paths import get_project_root
from nexus_like.pipeline import NexusCompatiblePipeline
from news_reporter.runtime import load_env_file

PROJECT_ROOT = get_project_root()
BUNDLE_ROOT = Path(os.getenv("NEWS_BUNDLE_ROOT", "")).expanduser() if os.getenv("NEWS_BUNDLE_ROOT") else None
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "config.yaml"
DEFAULT_ENV = PROJECT_ROOT / ".env"
THEMES = ["light", "dark_exec", "boardroom_print"]
EXTRA_SOURCE_CATALOG = [
    {
        "id": "google_news_global_it",
        "type": "rss",
        "enabled": True,
        "region_hint": "Global",
        "url": "https://news.google.com/rss/search?q=(technology+OR+informatica+OR+software+OR+cybersecurity)&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "google_news_global_agro",
        "type": "rss",
        "enabled": True,
        "region_hint": "Global",
        "url": "https://news.google.com/rss/search?q=(agribusiness+OR+agriculture+OR+agropecuaria+OR+farming)&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "google_news_global_infra",
        "type": "rss",
        "enabled": True,
        "region_hint": "Global",
        "url": "https://news.google.com/rss/search?q=(infrastructure+OR+logistics+OR+procurement+OR+concession)&hl=en-US&gl=US&ceid=US:en",
    },
]
SOURCE_PACKS = [
    {
        "id": "pack_americas_all",
        "label": "Google News - Todos os países das Américas",
        "countries": [
            "Antigua and Barbuda", "Argentina", "Bahamas", "Barbados", "Belize", "Bolivia", "Brazil",
            "Canada", "Chile", "Colombia", "Costa Rica", "Cuba", "Dominica", "Dominican Republic",
            "Ecuador", "El Salvador", "Grenada", "Guatemala", "Guyana", "Haiti", "Honduras", "Jamaica",
            "Mexico", "Nicaragua", "Panama", "Paraguay", "Peru", "Saint Kitts and Nevis", "Saint Lucia",
            "Saint Vincent and the Grenadines", "Suriname", "Trinidad and Tobago", "United States",
            "Uruguay", "Venezuela",
        ],
    },
    {
        "id": "pack_europe_main",
        "label": "Google News - Principais países da Europa",
        "countries": [
            "Germany", "France", "United Kingdom", "Italy", "Spain", "Portugal", "Netherlands", "Belgium",
            "Switzerland", "Austria", "Sweden", "Norway", "Denmark", "Finland", "Ireland", "Poland",
            "Czech Republic", "Romania", "Greece", "Turkey",
        ],
    },
]

# Mapa de variantes multilíngues (extensível para novos idiomas na V2).
# Chaves normalizadas (sem acento, minúsculas) para manter lookup determinístico.
MULTILINGUAL_TERM_VARIANTS = {
    "economia": ["economy", "economic", "economico", "economie", "wirtschaft", "经济", "經濟"],
    "investimento": ["investment", "investissement", "investition", "inversion", "投资", "投資"],
    "infraestrutura": ["infrastructure", "infrastructura", "infrastructure", "infrastruktur", "基础设施", "基礎設施"],
    "saneamento": ["sanitation", "water treatment", "wastewater", "saneamiento", "assainissement", "sanierung", "污水处理", "供水"],
    "facilities": ["facility management", "gestion de instalaciones", "gestion des installations", "gebaudemanagement", "物业管理", "设施管理"],
    "aquisicao": ["acquisition", "acquisicion", "acquisition", "ubernahme", "收购", "併購"],
    "veiculos": ["vehicles", "fleet", "vehiculos", "vehicules", "fahrzeuge", "车辆", "車輛"],
    "licitacao": ["tender", "bid", "licitacion", "appel d offres", "ausschreibung", "招标", "招標"],
    "concessao": ["concession", "concesion", "concession", "konzession", "特许经营", "特許經營"],
    "ppp": ["public private partnership", "partenariat public prive", "asociacion publico privada", "public private partnerschaft", "公私合作", "公私合營"],
    "obras": ["construction works", "public works", "obras publicas", "travaux publics", "bauarbeiten", "工程建设", "工程建設"],
    "manutencao": ["maintenance", "mantenimiento", "maintenance", "wartung", "维护", "維護"],
    "terceirizacao": ["outsourcing", "externalizacion", "externalisation", "outsourcing dienstleistungen", "外包"],
    "compras corporativas": ["corporate procurement", "achats corporatifs", "compras corporativas", "unternehmenseinkauf", "企业采购", "企業採購"],
    "mobilidade operacional": ["operational mobility", "movilidad operativa", "mobilite operationnelle", "betriebliche mobilitat", "运营机动性", "營運機動性"],
}


def _copy_if_missing(target: Path, source: Path | None) -> None:
    if target.exists() or source is None or not source.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def ensure_bootstrap_files() -> None:
    local_config_example = PROJECT_ROOT / "config" / "config.example.yaml"
    local_env_example = PROJECT_ROOT / ".env.example"
    bundle_config_example = (BUNDLE_ROOT / "config" / "config.example.yaml") if BUNDLE_ROOT else None
    bundle_env_example = (BUNDLE_ROOT / ".env.example") if BUNDLE_ROOT else None

    _copy_if_missing(local_config_example, bundle_config_example)
    _copy_if_missing(local_env_example, bundle_env_example)
    _copy_if_missing(DEFAULT_CONFIG, local_config_example)
    _copy_if_missing(DEFAULT_ENV, local_env_example)


@dataclass
class AppState:
    config_path: Path
    env_path: Path
    output_dir: Path
    all_keywords: list[str]
    default_keywords: list[str]
    all_regions: list[str]
    default_regions: list[str]
    configured_sources: list[dict]
    extra_sources: list[dict]
    default_source_ids: list[str]
    default_extra_source_ids: list[str]
    default_pack_ids: list[str]
    default_theme: str
    default_max_news: int
    default_time_window_days: int
    profiles_file: Path
    lock: threading.Lock
    profiles: dict[str, dict]
    default_profile_name: str | None = None
    selected_profile: str | None = None
    last_report_path: Path | None = None
    selected_report_name: str | None = None
    last_params: dict | None = None
    last_error: str | None = None
    last_counters: dict | None = None


def build_keywords(monitoring_cfg: dict) -> list[str]:
    primary = monitoring_cfg.get("priority_keywords", [])
    associated = monitoring_cfg.get("associated_keywords", [])
    merged: list[str] = []
    for kw in [*primary, *associated]:
        value = str(kw).strip()
        if value and value not in merged:
            merged.append(value)
    return merged


def parse_csv_list(raw: str) -> list[str]:
    return [v.strip() for v in (raw or "").split(",") if v.strip()]


def parse_source_urls(raw: str) -> list[str]:
    chunks = re.split(r"[\n,;]+", raw or "")
    out: list[str] = []
    for chunk in chunks:
        value = chunk.strip()
        if not value:
            continue
        if not value.lower().startswith(("http://", "https://")):
            value = f"https://{value}"
        if value not in out:
            out.append(value)
    return out


def source_site_label(source: dict) -> str:
    url = str(source.get("url", "")).strip()
    host = urlparse(url).netloc.lower().replace("www.", "") if url else ""
    source_type = str(source.get("type", "source")).strip() or "source"
    if host:
        return f"{host} ({source_type})"
    return f"{str(source.get('id', 'fonte')).strip()} ({source_type})"


def source_reference_label(source: dict) -> str:
    region_hint = str(source.get("region_hint", "")).strip() or "N/D"
    source_id = str(source.get("id", "")).strip() or "sem_id"
    url = str(source.get("url", "")).strip()

    query_hint = ""
    try:
        parsed = urlparse(url)
        q = parse_qs(parsed.query).get("q", [""])[0].strip()
        if q:
            query_hint = unquote_plus(q)
    except Exception:  # noqa: BLE001
        query_hint = ""

    if query_hint:
        query_hint = re.sub(r"\s+", " ", query_hint).strip()
        if len(query_hint) > 90:
            query_hint = f"{query_hint[:90]}..."
        return f"Ref: {region_hint} | Busca: {query_hint}"
    return f"Ref: {region_hint} | Fonte: {source_id}"


def custom_source_id(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8"), usedforsecurity=False).hexdigest()[:10]
    return f"custom_url_{digest}"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_only).strip("_").lower()
    return slug or "country"


def build_google_news_country_source(country: str, keywords: list[str], pack_id: str) -> dict:
    country_term = _term_for_query(country)
    selected_keywords = unique_keep_order(keywords)[:10]
    if not selected_keywords:
        selected_keywords = ["economy", "investment", "infrastructure", "procurement"]
    keyword_expr = " OR ".join([_term_for_query(k) for k in selected_keywords if _term_for_query(k)])
    query = f"({country_term}) AND ({keyword_expr})"
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    return {
        "id": f"{pack_id}_{slugify(country)}",
        "type": "rss",
        "enabled": True,
        "region_hint": country,
        "url": url,
    }


def pack_country_key(pack_id: str, country: str) -> str:
    return f"{pack_id}::{country}"


def build_pack_sources(selected_pack_country_keys: list[str], keywords: list[str]) -> list[dict]:
    selected = {str(v).strip() for v in selected_pack_country_keys if str(v).strip()}
    if not selected:
        return []
    sources: list[dict] = []
    for pack in SOURCE_PACKS:
        pack_id = str(pack.get("id", "")).strip()
        if not pack_id:
            continue
        for country in pack.get("countries", []):
            country_name = str(country).strip()
            if not country_name:
                continue
            if pack_country_key(pack_id, country_name) not in selected:
                continue
            sources.append(build_google_news_country_source(country_name, keywords, pack_id))
    return sources


def unique_keep_order(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        item = str(value).strip()
        if item and item not in out:
            out.append(item)
    return out


def normalize_term_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip().lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def expand_terms_multilingual(terms: list[str]) -> list[str]:
    expanded = unique_keep_order(terms)
    seen = {normalize_term_key(t) for t in expanded}
    for term in terms:
        key = normalize_term_key(term)
        variants = MULTILINGUAL_TERM_VARIANTS.get(key, [])
        for variant in variants:
            v = str(variant).strip()
            v_key = normalize_term_key(v)
            if v and v_key and v_key not in seen:
                expanded.append(v)
                seen.add(v_key)
    return expanded


def _term_for_query(term: str) -> str:
    value = term.strip()
    if not value:
        return ""
    if " " in value:
        return f'"{value}"'
    return value


COUNTRY_SYNONYMS = {
    "angola": ["angola", "ao", "luanda"],
    "brasil": ["brasil", "brazil", "br"],
    "portugal": ["portugal", "pt", "lisboa"],
    "espanha": ["espanha", "spain", "espana"],
    "spain": ["spain", "espanha", "espana"],
    "emirados arabes unidos": ["emirados arabes unidos", "united arab emirates", "uae", "dubai", "abu dhabi"],
    "united arab emirates": ["united arab emirates", "uae", "emirados arabes unidos", "dubai", "abu dhabi"],
    "uae": ["uae", "united arab emirates", "emirados arabes unidos", "dubai", "abu dhabi"],
    "estados unidos": ["estados unidos", "united states", "usa", "us"],
    "united states": ["united states", "usa", "us", "estados unidos"],
    "mexico": ["mexico", "méxico"],
    "mocambique": ["mocambique", "mozambique"],
    "mozambique": ["mozambique", "mocambique"],
}


def expand_region_synonyms(regions: list[str]) -> list[str]:
    expanded: list[str] = []
    for region in regions:
        r = str(region).strip()
        if not r:
            continue
        key = r.lower()
        mapped = COUNTRY_SYNONYMS.get(key, [r])
        for alias in mapped:
            if alias and alias not in expanded:
                expanded.append(alias)
    return expanded


def build_dynamic_google_source(regions: list[str], subregions: list[str], keywords: list[str]) -> dict | None:
    region_terms = unique_keep_order([*regions, *subregions])[:10]
    keyword_terms = unique_keep_order(keywords)[:14]
    if not region_terms or not keyword_terms:
        return None

    region_expr = " OR ".join([_term_for_query(r) for r in region_terms if _term_for_query(r)])
    keyword_expr = " OR ".join([_term_for_query(k) for k in keyword_terms if _term_for_query(k)])
    if not region_expr or not keyword_expr:
        return None

    query = f"({region_expr}) AND ({keyword_expr})"
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    return {
        "id": "google_news_dynamic_custom",
        "type": "rss",
        "enabled": True,
        "region_hint": "Custom",
        "url": url,
    }


def load_profiles(path: Path) -> tuple[dict[str, dict], str | None]:
    if not path.exists():
        return {}, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}, None
    if not isinstance(data, dict):
        return {}, None

    default_profile_name: str | None = None
    if "profiles" in data and isinstance(data.get("profiles"), dict):
        profiles_raw = data.get("profiles", {})
        meta = data.get("_meta", {})
        if isinstance(meta, dict):
            candidate = meta.get("default_profile")
            if isinstance(candidate, str) and candidate.strip():
                default_profile_name = candidate.strip()
    else:
        profiles_raw = data

    out: dict[str, dict] = {}
    for name, payload in profiles_raw.items():
        if isinstance(name, str) and isinstance(payload, dict):
            out[name] = payload
    if default_profile_name and default_profile_name not in out:
        default_profile_name = None
    return out, default_profile_name


def save_profiles(path: Path, profiles: dict[str, dict], default_profile_name: str | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_meta": {"default_profile": default_profile_name or ""},
        "profiles": profiles,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_reports(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = sorted(output_dir.glob("weekly_report_*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports


def safe_report_name(name: str) -> str:
    return Path(name or "").name


def selected_report_path(state: AppState) -> Path | None:
    reports = list_reports(state.output_dir)
    if not reports:
        return None

    if state.selected_report_name:
        wanted = safe_report_name(state.selected_report_name)
        for report in reports:
            if report.name == wanted:
                return report

    if state.last_report_path and state.last_report_path.exists():
        return state.last_report_path

    return reports[0]


def run_pipeline(
    config_path: Path,
    env_path: Path,
    selected_keywords: list[str],
    extra_keywords: list[str],
    selected_regions: list[str],
    extra_regions: list[str],
    subregion_terms: list[str],
    selected_source_ids: list[str],
    selected_extra_source_ids: list[str],
    selected_pack_country_keys: list[str],
    custom_source_urls: list[str],
    max_news: int,
    theme: str,
    time_window_days: int,
):
    base_cfg = load_config(config_path)
    cfg_raw = copy.deepcopy(base_cfg.raw)
    cfg_raw.setdefault("monitoring", {})
    cfg_raw.setdefault("project", {})
    cfg_raw.setdefault("filters", {})

    merged_keywords = unique_keep_order([*selected_keywords, *extra_keywords])
    multilingual_keywords = expand_terms_multilingual(merged_keywords)
    merged_regions = unique_keep_order([*selected_regions, *extra_regions])
    expanded_region_terms = expand_region_synonyms(merged_regions)

    cfg_raw["monitoring"]["priority_keywords"] = multilingual_keywords
    base_associated = [str(t).strip() for t in cfg_raw["monitoring"].get("associated_keywords", []) if str(t).strip()]
    cfg_raw["monitoring"]["associated_keywords"] = unique_keep_order(
        [*base_associated, *expand_terms_multilingual(base_associated)]
    )

    themes_cfg = cfg_raw["monitoring"].get("themes", {})
    if isinstance(themes_cfg, dict):
        for theme_name, terms in themes_cfg.items():
            if isinstance(terms, list):
                themes_cfg[theme_name] = expand_terms_multilingual([str(t).strip() for t in terms if str(t).strip()])

    opportunity_cfg = cfg_raw["monitoring"].get("opportunity_signals", {})
    if isinstance(opportunity_cfg, dict):
        for signal_name, terms in opportunity_cfg.items():
            if isinstance(terms, list):
                opportunity_cfg[signal_name] = expand_terms_multilingual([str(t).strip() for t in terms if str(t).strip()])

    if merged_regions:
        cfg_raw["monitoring"]["regions"] = merged_regions
    if subregion_terms:
        cfg_raw["monitoring"]["subregion_terms"] = subregion_terms

    region_aliases = cfg_raw["monitoring"].setdefault("region_aliases", {})
    for region in merged_regions:
        aliases = region_aliases.setdefault(region, [])
        if isinstance(aliases, list):
            existing = [str(a).lower() for a in aliases]
            for candidate in unique_keep_order([region, *COUNTRY_SYNONYMS.get(region.lower(), [])]):
                normalized = str(candidate).strip().lower()
                if normalized and normalized not in existing:
                    aliases.append(normalized)
                    existing.append(normalized)
    cfg_raw["project"]["max_news"] = int(max_news)
    cfg_raw["project"]["report_theme"] = theme
    cfg_raw["filters"]["time_window_days"] = int(time_window_days)
    cfg_raw["filters"]["strict_priority_keyword_match"] = bool(multilingual_keywords)

    configured_sources = [s for s in cfg_raw.get("sources", []) if s.get("id") != "google_news_dynamic_custom"]
    selected_source_set = {str(s).strip() for s in selected_source_ids if str(s).strip()}
    if selected_source_set:
        configured_sources = [s for s in configured_sources if str(s.get("id", "")).strip() in selected_source_set]
    else:
        configured_sources = [s for s in configured_sources if bool(s.get("enabled", True))]

    selected_extra_set = {str(s).strip() for s in selected_extra_source_ids if str(s).strip()}
    chosen_extra_sources = [s for s in EXTRA_SOURCE_CATALOG if str(s.get("id", "")).strip() in selected_extra_set]
    chosen_pack_sources = build_pack_sources(selected_pack_country_keys, multilingual_keywords)
    chosen_custom_sources = [
        {
            "id": custom_source_id(url),
            "type": "rss",
            "enabled": True,
            "region_hint": "Custom",
            "url": url,
        }
        for url in custom_source_urls
    ]

    sources = []
    seen_source_ids: set[str] = set()
    for src in [*configured_sources, *chosen_extra_sources, *chosen_pack_sources, *chosen_custom_sources]:
        src_id = str(src.get("id", "")).strip()
        if not src_id or src_id in seen_source_ids:
            continue
        sources.append(src)
        seen_source_ids.add(src_id)

    dynamic_source = build_dynamic_google_source(
        unique_keep_order([*merged_regions, *expanded_region_terms]),
        subregion_terms,
        multilingual_keywords,
    )
    if dynamic_source:
        sources.append(dynamic_source)
    cfg_raw["sources"] = sources

    cfg = AppConfig(raw=cfg_raw)
    runtime_cfg = cfg.runtime
    log_dir = runtime_cfg.get("log_dir", "logs")
    if not Path(log_dir).is_absolute():
        log_dir = str(PROJECT_ROOT / log_dir)
    setup_logging(log_dir=log_dir, level=runtime_cfg.get("log_level", "INFO"))

    env = load_env_file(str(env_path))
    pipeline = NexusCompatiblePipeline(cfg, env)
    return pipeline.run()


def render_page(state: AppState) -> str:
    profile_payload = state.profiles.get(state.selected_profile or "", {})
    form_keywords = profile_payload.get("keywords", [])
    form_regions = profile_payload.get("regions", state.default_regions)
    form_extra_keywords = profile_payload.get("extra_keywords", [])
    form_extra_regions = profile_payload.get("extra_regions", [])
    form_subregions = profile_payload.get("subregion_terms", [])
    form_source_ids = profile_payload.get("source_ids", state.default_source_ids)
    form_extra_source_ids = profile_payload.get("extra_source_ids", state.default_extra_source_ids)
    form_pack_ids = profile_payload.get("pack_ids", state.default_pack_ids)
    form_pack_country_keys = profile_payload.get("pack_country_keys", [])
    form_custom_source_urls = profile_payload.get("custom_source_urls", [])
    form_max_news = int(profile_payload.get("max_news", state.default_max_news))
    form_theme = str(profile_payload.get("theme", state.default_theme))
    form_days = int(profile_payload.get("time_window_days", state.default_time_window_days))

    if not form_pack_country_keys and form_pack_ids:
        selected_pack_id_set = {str(v).strip() for v in form_pack_ids if str(v).strip()}
        migrated_keys: list[str] = []
        for pack in SOURCE_PACKS:
            pack_id = str(pack.get("id", "")).strip()
            if pack_id not in selected_pack_id_set:
                continue
            for country in pack.get("countries", []):
                country_name = str(country).strip()
                if country_name:
                    migrated_keys.append(pack_country_key(pack_id, country_name))
        form_pack_country_keys = migrated_keys

    reports = list_reports(state.output_dir)
    report_options = []
    chosen_name = state.selected_report_name or (reports[0].name if reports else "")
    for report in reports:
        selected = "selected" if report.name == chosen_name else ""
        report_options.append(f'<option value="{html.escape(report.name)}" {selected}>{html.escape(report.name)}</option>')

    keyword_options = []
    for kw in state.all_keywords:
        checked = "checked" if kw in form_keywords else ""
        keyword_options.append(
            f'<label class="kw"><input type="checkbox" name="keywords" value="{html.escape(kw)}" {checked}> {html.escape(kw)}</label>'
        )
    region_options = []
    for region in state.all_regions:
        checked = "checked" if region in form_regions else ""
        region_options.append(
            f'<label class="kw"><input type="checkbox" name="regions" value="{html.escape(region)}" {checked}> {html.escape(region)}</label>'
        )
    source_options = []
    for src in state.configured_sources:
        source_id = str(src.get("id", "")).strip()
        if not source_id:
            continue
        checked = "checked" if source_id in form_source_ids else ""
        label = source_site_label(src)
        source_options.append(
            "<label class=\"kw\">"
            f'<input type="checkbox" name="source_ids" value="{html.escape(source_id)}" {checked}> '
            f"{html.escape(label)}"
            f'<span class="source-meta">{html.escape(source_reference_label(src))}</span>'
            "</label>"
        )
    extra_source_options = []
    for src in state.extra_sources:
        source_id = str(src.get("id", "")).strip()
        if not source_id:
            continue
        checked = "checked" if source_id in form_extra_source_ids else ""
        label = source_site_label(src)
        extra_source_options.append(
            "<label class=\"kw\">"
            f'<input type="checkbox" name="extra_source_ids" value="{html.escape(source_id)}" {checked}> '
            f"{html.escape(label)}"
            f'<span class="source-meta">{html.escape(source_reference_label(src))}</span>'
            "</label>"
        )
    pack_options = []
    for pack in SOURCE_PACKS:
        pack_id = str(pack.get("id", "")).strip()
        if not pack_id:
            continue
        label = str(pack.get("label", pack_id))
        countries = [str(c).strip() for c in pack.get("countries", []) if str(c).strip()]
        country_boxes = []
        for country in countries:
            country_key = pack_country_key(pack_id, country)
            checked = "checked" if country_key in form_pack_country_keys else ""
            country_boxes.append(
                f'<label class="country-check"><input type="checkbox" name="pack_country_keys" value="{html.escape(country_key)}" {checked}> {html.escape(country)}</label>'
            )
        pack_options.append(
            f'<div class="pack-block"><div class="pack-title">{html.escape(label)}</div><div class="pack-links">{"".join(country_boxes)}</div></div>'
        )
    profile_options = ['<option value="">(Sem perfil)</option>']
    for name in sorted(state.profiles.keys()):
        selected = "selected" if name == (state.selected_profile or "") else ""
        label = f"{name} (padrao)" if state.default_profile_name and name == state.default_profile_name else name
        profile_options.append(f'<option value="{html.escape(name)}" {selected}>{html.escape(label)}</option>')

    status_html = ""
    if state.last_error:
        status_html += f'<div class="error"><strong>Erro:</strong><pre>{html.escape(state.last_error)}</pre></div>'
    if state.last_report_path:
        counters = state.last_counters or {}
        p = state.last_params or {}
        status_html += (
            '<div class="ok">'
            f"<strong>Execucao concluida.</strong><br>"
            f"Parametros: max_news={html.escape(str(p.get('max_news', 'N/D')))} | "
            f"theme={html.escape(str(p.get('theme', 'N/D')))} | "
            f"periodo_dias={html.escape(str(p.get('time_window_days', 'N/D')))}<br>"
            f"Regioes: {html.escape(', '.join(p.get('regions', [])) or 'N/D')}<br>"
            f"Categorias extras: {html.escape(', '.join(p.get('extra_keywords', [])) or 'nenhuma')}<br>"
            f"Fontes ativas: {html.escape(', '.join(p.get('source_ids', [])) or 'default')}<br>"
            f"Fontes extras: {html.escape(', '.join(p.get('extra_source_ids', [])) or 'nenhuma')}<br>"
            f"Países dos pacotes: {html.escape(str(len(p.get('pack_country_keys', []))))} selecionado(s)<br>"
            f"Fontes custom: {html.escape(', '.join(p.get('custom_source_urls', [])) or 'nenhuma')}<br>"
            f"Coletadas={counters.get('collected', 0)} | Filtradas={counters.get('filtered', 0)} | "
            f"Aprovadas={counters.get('approved', 0)}<br>"
            '<a href="/report/current" target="_blank">Abrir relatorio em nova aba</a>'
            "</div>"
        )

    if reports:
        picker_body = (
            '<select name="report_name">'
            + "".join(report_options)
            + "</select>"
            '<div class="actions"><button type="submit" style="background:#334155;">Carregar selecionado</button></div>'
        )
    else:
        picker_body = '<p style="font-size:13px;color:#64748b;">Nenhum relatorio disponivel ainda. Gere um relatorio para habilitar a selecao.</p>'

    report_picker_html = (
        '<form method="get" action="/" class="card" style="margin-top:12px;">'
        '<h3>Visualizar relatorio ja gerado</h3>'
        + picker_body
        + "</form>"
    )

    return f"""<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Strategic Intelligence Reporter</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ width: 100%; overflow-x: hidden; }}
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 0; padding: 16px; background: linear-gradient(180deg, #eef2ff 0%, #f8fafc 100%); color: #0f172a; line-height: 1.4; }}
    .wrap {{ width: min(1280px, 100%); margin: 0 auto; background: #fff; border-radius: 16px; padding: clamp(14px, 2vw, 22px); border: 1px solid #dbe4ef; box-shadow: 0 8px 28px rgba(15, 23, 42, .06); }}
    .topbar {{ display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:10px; padding-bottom:8px; border-bottom:1px solid #e2e8f0; }}
    .brand {{ font-weight:800; letter-spacing:.2px; font-size:20px; }}
    .brand small {{ display:block; font-weight:500; font-size:12px; color:#64748b; margin-top:4px; }}
    .top-actions {{ display:flex; gap:8px; flex-wrap:wrap; }}
    .chip {{ border:1px solid #c7d2fe; background:#eef2ff; color:#3730a3; padding:6px 10px; border-radius:999px; font-size:12px; font-weight:700; }}
    .grid {{ display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 16px; align-items: stretch; }}
    .card {{ border: 1px solid #dbe4ef; border-radius: 10px; padding: 14px; background: #fff; min-width: 0; }}
    .kw {{ display: inline-block; width: calc(50% - 6px); margin: 3px 3px; vertical-align: top; }}
    .source-meta {{ display:block; margin-left:22px; font-size:12px; color:#64748b; }}
    details.advanced {{ margin-top:10px; border:1px solid #dbe4ef; border-radius:8px; padding:8px 10px; background:#f8fafc; }}
    details.advanced summary {{ cursor:pointer; font-weight:600; color:#334155; }}
    .pack-block {{ margin:8px 0 12px 0; }}
    .pack-title {{ font-size:13px; font-weight:600; color:#0f172a; margin-bottom:4px; }}
    .pack-links {{ margin: 4px 0 10px 10px; font-size: 12px; line-height: 1.5; display:flex; flex-wrap:wrap; gap:6px 10px; }}
    .country-check {{ display:inline-block; width:230px; }}
    label {{ font-size: 14px; }}
    input[type=number], input[type=text], select {{ width: 100%; max-width: 100%; padding: 8px; margin-top: 6px; border: 1px solid #cbd5e1; border-radius: 8px; }}
    .actions {{ margin-top: 12px; }}
    button {{ background: #0f766e; color: #fff; border: 0; border-radius: 8px; padding: 10px 14px; cursor: pointer; min-height: 40px; }}
    button:hover {{ opacity: .92; }}
    textarea {{ width: 100%; max-width: 100%; min-height: 70px; padding: 8px; margin-top: 6px; border: 1px solid #cbd5e1; border-radius: 8px; resize: vertical; }}
    .ok {{ margin-top: 10px; padding: 10px; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; }}
    .error {{ margin-top: 10px; padding: 10px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; }}
    pre {{ white-space: pre-wrap; font-size: 12px; }}
    iframe {{ width: 100%; height: min(72vh, 860px); border: 1px solid #dbe4ef; border-radius: 10px; margin-top: 12px; background: #fff; }}
    .form-actions-main {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
    .panel-toggle {{ margin-top: 10px; margin-bottom: 8px; border:1px solid #e2e8f0; border-radius:12px; background:#ffffff; }}
    .panel-toggle summary {{ list-style:none; cursor:pointer; font-weight:700; color:#0f172a; display:flex; align-items:center; justify-content:space-between; gap:10px; padding:12px 14px; }}
    .panel-toggle summary::-webkit-details-marker {{ display:none; }}
    .panel-toggle summary .summary-left {{ display:flex; align-items:center; gap:10px; }}
    .panel-toggle summary .summary-icon {{ width:28px; height:28px; border-radius:50%; background:#eef2ff; color:#3730a3; display:inline-flex; align-items:center; justify-content:center; font-size:16px; font-weight:900; transition:transform .2s ease; }}
    .panel-toggle[open] summary .summary-icon {{ transform:rotate(180deg); }}
    .panel-toggle summary .summary-help {{ font-size:12px; color:#64748b; font-weight:600; }}
    .panel-toggle .panel-body {{ padding: 0 8px 8px 8px; }}
    @media (max-width: 1024px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .kw {{ width: calc(50% - 6px); }}
      .country-check {{ width: calc(50% - 10px); }}
      iframe {{ height: 66vh; }}
    }}
    @media (max-width: 640px) {{
      body {{ padding: 10px; }}
      .topbar {{ flex-direction: column; align-items: flex-start; }}
      .top-actions {{ width: 100%; }}
      .chip {{ width: 100%; text-align: center; }}
      .kw {{ width: 100%; margin: 4px 0; }}
      .country-check {{ width: 100%; }}
      button {{ width: 100%; }}
      input[type=number], input[type=text], select, textarea {{ font-size: 16px; }}
      .actions button, .form-actions-main button {{ width: 100%; margin-left: 0 !important; }}
      iframe {{ height: 70vh; }}
    }}
  </style>
  <script>
    function selectAll(flag) {{
      const boxes = document.querySelectorAll('input[name="keywords"]');
      boxes.forEach(b => b.checked = flag);
    }}
    function selectAllRegions(flag) {{
      const boxes = document.querySelectorAll('input[name="regions"]');
      boxes.forEach(b => b.checked = flag);
    }}
    function selectAllSources(flag) {{
      const boxes = document.querySelectorAll('input[name="source_ids"]');
      boxes.forEach(b => b.checked = flag);
    }}
    function selectAllExtraSources(flag) {{
      const boxes = document.querySelectorAll('input[name="extra_source_ids"]');
      boxes.forEach(b => b.checked = flag);
    }}
    function loadSelectedProfile() {{
      const sel = document.getElementById('profile_name_picker');
      if (!sel) return;
      const v = (sel.value || '').trim();
      const target = v ? '/?profile_name=' + encodeURIComponent(v) : '/?profile_name=';
      window.location.href = target;
    }}
  </script>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="brand">Strategic Intelligence Reporter - Embarcado
        <small>Arquivo unico (.exe), sem dependencia externa para interface.</small>
      </div>
      <div class="top-actions">
        <span class="chip">WebApp local</span>
        <span class="chip">Relatório HTML</span>
      </div>
    </div>
    <details class="panel-toggle" open>
      <summary>
        <span class="summary-left"><span class="summary-icon">▾</span> Configurações de busca</span>
        <span class="summary-help">Clique para mostrar/ocultar</span>
      </summary>
      <div class="panel-body">
      <form method="post" action="/run">
      <div class="grid">
      <div class="card">
        <h3>Perfil de busca</h3>
        <div style="margin-bottom:10px;">
          <select id="profile_name_picker" name="profile_name_picker">{''.join(profile_options)}</select>
          <div class="actions"><button type="button" onclick="loadSelectedProfile()" style="background:#334155;">Carregar perfil</button></div>
        </div>

        <h3>Categorias / Palavras-chave</h3>
        <div style="margin-bottom:8px;">
          <button type="button" onclick="selectAll(true)">Selecionar Todas</button>
          <button type="button" onclick="selectAll(false)" style="margin-left:6px;background:#334155;">Limpar</button>
        </div>
        {''.join(keyword_options)}
        <label style="display:block;margin-top:12px;">Novas categorias (separadas por virgula)
          <textarea name="extra_keywords" placeholder="Ex.: informatica, agropecuaria">{html.escape(', '.join(form_extra_keywords))}</textarea>
        </label>
      </div>
      <div class="card">
          <h3>Parâmetros</h3>
          <details class="advanced" open>
            <summary>FILTROS</summary>
            <label style="display:block;margin-top:8px;">Paises / Regioes monitorados</label>
            <div style="margin-bottom:8px;">
              <button type="button" onclick="selectAllRegions(true)" style="background:#334155;">Selecionar Todos</button>
              <button type="button" onclick="selectAllRegions(false)" style="margin-left:6px;background:#64748b;">Limpar</button>
            </div>
            <div>{''.join(region_options)}</div>
            <label>Quantidade maxima de noticias
              <input type="number" name="max_news" min="1" max="200" value="{form_max_news}">
            </label>
            <label style="display:block;margin-top:10px;">Novos paises/regioes (separados por virgula)
              <textarea name="extra_regions" placeholder="Ex.: Mozambique, Espanha">{html.escape(', '.join(form_extra_regions))}</textarea>
            </label>
            <label style="display:block;margin-top:10px;">Subregioes opcionais (estados/provincias/condados)
              <textarea name="subregion_terms" placeholder="Ex.: Sao Paulo, Luanda, Porto">{html.escape(', '.join(form_subregions))}</textarea>
            </label>
            <label style="display:block;margin-top:10px;">Intervalo em dias
              <input type="number" name="time_window_days" min="1" max="365" value="{form_days}">
            </label>
          </details>
          <h3 style="margin-top:14px;">FONTES</h3>
          <details class="advanced">
            <summary>Fontes configuradas para coleta</summary>
            <div style="margin:8px 0;">
              <button type="button" onclick="selectAllSources(true)" style="background:#334155;">Selecionar Todas</button>
              <button type="button" onclick="selectAllSources(false)" style="margin-left:6px;background:#64748b;">Limpar</button>
            </div>
            <div>{''.join(source_options) or '<p style="font-size:13px;color:#64748b;">Nenhuma fonte configurada no config.yaml.</p>'}</div>
          </details>
          <details class="advanced">
            <summary>Fontes extras sugeridas (one-click)</summary>
            <div style="margin:8px 0;">
              <button type="button" onclick="selectAllExtraSources(true)" style="background:#475569;">Selecionar Todas</button>
              <button type="button" onclick="selectAllExtraSources(false)" style="margin-left:6px;background:#64748b;">Limpar</button>
            </div>
            <div>{''.join(extra_source_options) or '<p style="font-size:13px;color:#64748b;">Nenhuma fonte extra catalogada.</p>'}</div>
          </details>
          <details class="advanced">
            <summary>Pacotes geográficos</summary>
            <p style="font-size:12px;color:#64748b;margin:6px 0 8px 0;">Ative coleções prontas de Google News por país.</p>
            {''.join(pack_options) or '<p style="font-size:13px;color:#64748b;">Nenhum pacote disponível.</p>'}
          </details>
          <label style="display:block;margin-top:10px;">Novas fontes por URL (1 ou varias)</label>
          <textarea name="custom_source_urls" placeholder="Ex.: https://exemplo.com/rss&#10;https://outro-site.com/feed">{html.escape(', '.join(form_custom_source_urls))}</textarea>
          <label style="display:block;margin-top:10px;">Tema visual
            <select name="theme">
              {''.join([f'<option value="{t}" {"selected" if t == form_theme else ""}>{t}</option>' for t in THEMES])}
            </select>
          </label>
          <label style="display:block;margin-top:10px;">Nome do perfil para salvar
            <input type="text" name="profile_save_name" value="{html.escape(state.selected_profile or '')}" style="width:100%;padding:8px;margin-top:6px;border:1px solid #cbd5e1;border-radius:8px;">
          </label>
          <label style="display:block;margin-top:8px;">
            <input type="checkbox" name="make_default" value="1" {"checked" if state.selected_profile and state.selected_profile == state.default_profile_name else ""}> Definir como perfil padrao
          </label>
          <label style="display:block;margin-top:8px;">Nome para duplicar perfil
            <input type="text" name="duplicate_profile_name" value="" placeholder="Ex.: Agro 30 dias v2" style="width:100%;padding:8px;margin-top:6px;border:1px solid #cbd5e1;border-radius:8px;">
          </label>
          <p style="font-size:12px;color:#64748b;">Config: {html.escape(str(state.config_path))}</p>
          <p style="font-size:12px;color:#64748b;">Env: {html.escape(str(state.env_path))}</p>
      </div>
      </div>
      <input type="hidden" name="current_profile_name" value="{html.escape(state.selected_profile or '')}">
      <div class="form-actions-main">
        <button type="submit">Gerar Relatorio</button>
        <button type="submit" formaction="/save_profile" style="background:#1d4ed8;">Salvar perfil</button>
        <button type="submit" formaction="/duplicate_profile" style="background:#475569;">Duplicar perfil</button>
        <button type="submit" formaction="/delete_profile" style="background:#b91c1c;">Excluir perfil</button>
      </div>
      </form>
      </div>
    </details>
    {report_picker_html}
    {status_html}
    <iframe src="/report/current"></iframe>
  </div>
</body>
</html>"""


def make_handler(state: AppState):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query, keep_blank_values=True)

            if parsed.path == "/report/current":
                current = selected_report_path(state)
                if current and current.exists():
                    payload = current.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                payload = b"<html><body><h3>Nenhum relatorio gerado ainda.</h3></body></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

            if parsed.path == "/":
                chosen = safe_report_name((query.get("report_name", [""])[0] or "").strip())
                if chosen:
                    state.selected_report_name = chosen
                profile_name = (query.get("profile_name", [""])[0] or "").strip()
                if profile_name:
                    if profile_name in state.profiles:
                        state.selected_profile = profile_name
                elif "profile_name" in query:
                    state.selected_profile = None

            page = render_page(state).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def do_POST(self):
            parsed_path = urlparse(self.path).path
            if parsed_path not in ["/run", "/save_profile", "/duplicate_profile", "/delete_profile"]:
                self.send_error(404)
                return

            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            params = parse_qs(body, keep_blank_values=True)

            selected = [v.strip() for v in params.get("keywords", []) if v.strip()]
            selected_regions = [v.strip() for v in params.get("regions", []) if v.strip()]
            selected_source_ids = [v.strip() for v in params.get("source_ids", []) if v.strip()]
            selected_extra_source_ids = [v.strip() for v in params.get("extra_source_ids", []) if v.strip()]
            selected_pack_country_keys = [v.strip() for v in params.get("pack_country_keys", []) if v.strip()]
            custom_source_urls_raw = (params.get("custom_source_urls", [""])[0] or "").strip()
            custom_source_urls = parse_source_urls(custom_source_urls_raw)
            extra_keywords_raw = (params.get("extra_keywords", [""])[0] or "").strip()
            extra_keywords = [k.strip() for k in extra_keywords_raw.split(",") if k.strip()]
            extra_regions_raw = (params.get("extra_regions", [""])[0] or "").strip()
            extra_regions = parse_csv_list(extra_regions_raw)
            subregions_raw = (params.get("subregion_terms", [""])[0] or "").strip()
            subregion_terms = parse_csv_list(subregions_raw)
            current_profile_name = (params.get("current_profile_name", [""])[0] or "").strip()
            duplicate_profile_name = (params.get("duplicate_profile_name", [""])[0] or "").strip()
            max_news_raw = (params.get("max_news", [str(state.default_max_news)])[0] or "").strip()
            time_window_raw = (params.get("time_window_days", [str(state.default_time_window_days)])[0] or "").strip()
            theme = (params.get("theme", [state.default_theme])[0] or "").strip()
            make_default = (params.get("make_default", [""])[0] or "").strip() == "1"

            try:
                max_news = int(max_news_raw)
            except ValueError:
                max_news = state.default_max_news
            max_news = max(1, min(200, max_news))

            try:
                time_window_days = int(time_window_raw)
            except ValueError:
                time_window_days = state.default_time_window_days
            time_window_days = max(1, min(365, time_window_days))

            if theme not in THEMES:
                theme = state.default_theme
            if not selected_regions:
                selected_regions = list(state.default_regions)
            if not selected_source_ids:
                selected_source_ids = list(state.default_source_ids)
            if not selected_extra_source_ids:
                selected_extra_source_ids = list(state.default_extra_source_ids)

            if parsed_path == "/delete_profile":
                to_delete = current_profile_name or (state.selected_profile or "")
                if to_delete and to_delete in state.profiles:
                    del state.profiles[to_delete]
                    if state.default_profile_name == to_delete:
                        state.default_profile_name = None
                    if state.selected_profile == to_delete:
                        state.selected_profile = None
                    save_profiles(state.profiles_file, state.profiles, state.default_profile_name)
                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()
                return

            if parsed_path == "/duplicate_profile":
                source_name = current_profile_name or (state.selected_profile or "")
                if source_name and source_name in state.profiles:
                    target_name = duplicate_profile_name or f"{source_name} (copia)"
                    payload = copy.deepcopy(state.profiles[source_name])
                    state.profiles[target_name] = payload
                    state.selected_profile = target_name
                    save_profiles(state.profiles_file, state.profiles, state.default_profile_name)
                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()
                return

            if parsed_path == "/save_profile":
                profile_name = (params.get("profile_save_name", [""])[0] or "").strip()
                if profile_name:
                    state.profiles[profile_name] = {
                        "keywords": selected,
                        "extra_keywords": extra_keywords,
                        "regions": selected_regions,
                        "extra_regions": extra_regions,
                        "subregion_terms": subregion_terms,
                        "source_ids": selected_source_ids,
                        "extra_source_ids": selected_extra_source_ids,
                        "pack_country_keys": selected_pack_country_keys,
                        "custom_source_urls": custom_source_urls,
                        "max_news": max_news,
                        "time_window_days": time_window_days,
                        "theme": theme,
                    }
                    state.selected_profile = profile_name
                    if make_default:
                        state.default_profile_name = profile_name
                    save_profiles(state.profiles_file, state.profiles, state.default_profile_name)
                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()
                return

            with state.lock:
                try:
                    result = run_pipeline(
                        config_path=state.config_path,
                        env_path=state.env_path,
                        selected_keywords=selected,
                        extra_keywords=extra_keywords,
                        selected_regions=selected_regions,
                        extra_regions=extra_regions,
                        subregion_terms=subregion_terms,
                        selected_source_ids=selected_source_ids,
                        selected_extra_source_ids=selected_extra_source_ids,
                        selected_pack_country_keys=selected_pack_country_keys,
                        custom_source_urls=custom_source_urls,
                        max_news=max_news,
                        theme=theme,
                        time_window_days=time_window_days,
                    )
                    state.last_report_path = Path(result.report_path_html)
                    state.selected_report_name = state.last_report_path.name
                    state.last_params = {
                        "max_news": max_news,
                        "theme": theme,
                        "keywords": selected,
                        "extra_keywords": extra_keywords,
                        "regions": selected_regions,
                        "extra_regions": extra_regions,
                        "subregion_terms": subregion_terms,
                        "source_ids": selected_source_ids,
                        "extra_source_ids": selected_extra_source_ids,
                        "pack_country_keys": selected_pack_country_keys,
                        "custom_source_urls": custom_source_urls,
                        "time_window_days": time_window_days,
                    }
                    state.last_error = None
                    state.last_counters = {
                        "collected": result.counters.collected,
                        "filtered": result.counters.filtered,
                        "approved": result.counters.approved,
                    }
                except Exception:  # noqa: BLE001
                    state.last_error = traceback.format_exc()

            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

        def log_message(self, fmt, *args):  # noqa: A003
            return

    return Handler


def start_server(port: int = 8787, open_browser: bool = True) -> None:
    ensure_bootstrap_files()
    cfg = load_config(DEFAULT_CONFIG)
    monitoring = cfg.monitoring
    project = cfg.project
    filters_cfg = cfg.filters
    runtime_cfg = cfg.runtime

    output_dir_raw = runtime_cfg.get("output_dir", "output")
    output_dir = Path(output_dir_raw)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir

    all_keywords = build_keywords(monitoring)
    default_keywords = [kw for kw in monitoring.get("priority_keywords", []) if kw in all_keywords] or all_keywords[:4]
    all_regions = [str(r).strip() for r in monitoring.get("regions", []) if str(r).strip()]
    configured_sources = [
        s for s in cfg.raw.get("sources", [])
        if isinstance(s, dict) and str(s.get("id", "")).strip() and str(s.get("id", "")).strip() != "google_news_dynamic_custom"
    ]
    default_source_ids = [str(s.get("id", "")).strip() for s in configured_sources if bool(s.get("enabled", True))]
    default_extra_source_ids: list[str] = []
    default_pack_ids: list[str] = []
    default_regions = list(all_regions)
    default_theme = str(project.get("report_theme", "light"))
    if default_theme not in THEMES:
        default_theme = "light"
    default_max_news = int(project.get("max_news", 50))
    default_time_window_days = int(filters_cfg.get("time_window_days", 7))
    profiles_file = PROJECT_ROOT / "data" / "search_profiles.json"
    profiles, default_profile_name = load_profiles(profiles_file)

    state = AppState(
        config_path=DEFAULT_CONFIG,
        env_path=DEFAULT_ENV,
        output_dir=output_dir,
        all_keywords=all_keywords,
        default_keywords=default_keywords,
        all_regions=all_regions,
        default_regions=default_regions,
        configured_sources=configured_sources,
        extra_sources=copy.deepcopy(EXTRA_SOURCE_CATALOG),
        default_source_ids=default_source_ids,
        default_extra_source_ids=default_extra_source_ids,
        default_pack_ids=default_pack_ids,
        default_theme=default_theme,
        default_max_news=default_max_news,
        default_time_window_days=default_time_window_days,
        profiles_file=profiles_file,
        lock=threading.Lock(),
        profiles=profiles,
        default_profile_name=default_profile_name,
    )
    if state.default_profile_name and state.default_profile_name in state.profiles:
        state.selected_profile = state.default_profile_name

    reports = list_reports(state.output_dir)
    if reports:
        state.selected_report_name = reports[0].name

    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(state))
    url = f"http://127.0.0.1:{port}"
    print(f"WebApp embarcado em execucao: {url}")
    if open_browser:
        webbrowser.open(url, new=2)
    server.serve_forever()
