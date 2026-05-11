"""
OG Image Enricher — busca og:image dos artigos que não têm imagem.

Estratégia em duas camadas:
  1. Tenta extrair og:image / twitter:image do <head> do artigo (paralelo, rápido).
  2. Para quem ainda não tiver imagem, gera URL contextual via LoremFlickr
     (foto real do Flickr CC, relevante ao tema, sem chave de API, determinística).

LoremFlickr: https://loremflickr.com/{w}/{h}/{keywords}?lock={seed}
  - lock = hash(url) garante sempre a mesma foto para o mesmo artigo.
  - keywords derivadas de categoria + região.
"""
from __future__ import annotations

import hashlib
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Sequence
from urllib.parse import quote

import requests

from hub.models import NewsItem

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# Domínios que redireccionam agressivamente ou têm pouco valor de OG image
_SKIP_DOMAINS = {
    "news.google.com",
    "google.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "reddit.com",
    "ycombinator.com",
    "youtube.com",
}

# Padrões que indicam imagem genérica/logo (não foto de artigo)
_GENERIC_PATTERNS = re.compile(
    r"(logo|icon|avatar|placeholder|default|blank|spacer|1x1|pixel|tracking"
    r"|banner|sprite|thumb/[0-9]+x[0-9]+(?:/[0-9]+x[0-9]+)?$)",
    re.IGNORECASE,
)


def _fetch_og_image(url: str, timeout: int = 6) -> str | None:
    """
    Faz GET na URL lendo apenas os primeiros ~12KB para extrair og:image.
    Retorna a URL da imagem ou None.
    """
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        if any(domain == d or domain.endswith("." + d) for d in _SKIP_DOMAINS):
            return None

        with requests.get(
            url,
            timeout=timeout,
            stream=True,
            headers=_HEADERS,
            allow_redirects=True,
        ) as resp:
            if not resp.ok:
                return None

            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type:
                return None

            # Lê até 12KB — suficiente para o <head>
            chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_content(chunk_size=2048):
                chunks.append(chunk)
                total += len(chunk)
                head_so_far = b"".join(chunks)
                if total >= 12_288 or b"</head>" in head_so_far.lower():
                    break

        html = b"".join(chunks).decode("utf-8", errors="ignore")

        # Tenta og:image em duas ordens de atributos
        patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']{10,})["\']',
            r'<meta[^>]+content=["\']([^"\']{10,})["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']{10,})["\']',
            r'<meta[^>]+content=["\']([^"\']{10,})["\'][^>]+name=["\']twitter:image["\']',
        ]
        for pattern in patterns:
            m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if m:
                img = m.group(1).strip()
                if img.startswith("http") and not _GENERIC_PATTERNS.search(img):
                    return img

    except Exception as exc:
        logger.debug("og_enricher: erro em %s — %s", url, exc)

    return None


# ── Fallback: Unsplash Source com keywords extraídas do título ───────────────
#
# Estratégia: cada artigo recebe keywords ÚNICAS derivadas do seu título,
# garantindo fotos diversas mesmo para artigos da mesma categoria.
# Usa Unsplash Source API (alta qualidade) com ?sig= para variedade.
#
# Fallback em cadeia: Unsplash Source → LoremFlickr (via onerror no template).

# Palavras PT (e variantes) → termo EN para busca de imagem
_PT_EN: dict[str, str] = {
    # Infraestrutura
    "infraestrutura": "infrastructure", "infraestruturas": "infrastructure",
    "construção": "construction", "construcao": "construction", "obras": "construction",
    "rodovia": "highway road", "rodovias": "highway", "estrada": "road",
    "ponte": "bridge", "pontes": "bridge",
    "porto": "harbor port", "portos": "harbor",
    "aeroporto": "airport", "aeroportos": "airport",
    "ferrovia": "railway train", "metro": "subway metro",
    "saneamento": "water sanitation", "esgoto": "sewage water",
    "água": "water", "agua": "water",
    "pipeline": "pipeline oil",
    # Energia
    "energia": "energy", "energética": "energy",
    "solar": "solar panels", "eólica": "wind turbine", "eolica": "wind turbine",
    "renovável": "renewable energy", "renovavel": "renewable energy",
    "petróleo": "oil petroleum", "petroleo": "oil",
    "gás": "gas pipeline", "gas": "natural gas",
    "hidrelétrica": "hydroelectric dam", "hidroeletrica": "hydroelectric",
    "nuclear": "nuclear power",
    # Tecnologia
    "tecnologia": "technology", "digital": "digital technology",
    "inovação": "innovation", "inovacao": "innovation",
    "inteligência": "artificial intelligence", "inteligencia": "artificial intelligence",
    "startup": "startup office",
    "dados": "data center", "cibersegurança": "cybersecurity",
    "software": "software coding", "satélite": "satellite space",
    # Economia / Finanças
    "economia": "economy", "económica": "economy",
    "mercado": "market finance", "bolsa": "stock market",
    "banco": "bank building", "bancos": "bank",
    "investimento": "investment", "investimentos": "investment",
    "financiamento": "financing", "financeiro": "financial",
    "capital": "capital finance",
    "crescimento": "economic growth", "pib": "economy gdp",
    "inflação": "inflation economics", "inflacao": "inflation",
    "dívida": "debt finance", "divida": "debt",
    "exportação": "export shipping", "exportacao": "export",
    "comércio": "trade commerce", "comercio": "trade",
    # Geopolítica / Governo
    "governo": "government parliament",
    "presidente": "president government",
    "diplomacia": "diplomacy",
    "guerra": "war conflict",
    "sanções": "sanctions diplomacy", "sancoes": "diplomacy",
    "cúpula": "summit meeting", "cupula": "summit",
    "eleições": "election vote", "eleicoes": "election",
    # Negócios
    "empresa": "corporate business", "empresas": "business",
    "contrato": "contract business", "contratos": "contract",
    "licitação": "procurement tender", "licitacao": "tender",
    "concessão": "concession contract", "concessao": "concession",
    "aquisição": "acquisition merger", "aquisicao": "acquisition",
    "parceria": "partnership",
    "projeto": "project planning",
    # Regiões (sempre incluir no contexto)
    "angola": "angola africa", "angolano": "angola",
    "brasil": "brazil", "brasileiro": "brazil",
    "portugal": "portugal lisbon", "português": "portugal",
    "dubai": "dubai skyscraper", "emirados": "dubai uae",
    "africa": "africa", "africano": "africa",
    "moçambique": "mozambique africa", "mocambique": "mozambique",
    "nigeria": "nigeria africa", "kenya": "kenya africa",
    "china": "china beijing", "chinês": "china",
    "india": "india", "índia": "india",
    "europa": "europe", "europeu": "europe",
    # Saúde / Social
    "saúde": "healthcare hospital", "saude": "healthcare",
    "hospital": "hospital medical",
    "educação": "education school", "educacao": "education",
    "universidade": "university education",
    "habitação": "housing urban", "habitacao": "housing",
    # Outros
    "mineração": "mining minerals", "mineracao": "mining",
    "agricultura": "agriculture farm",
    "floresta": "forest nature",
    "oceano": "ocean sea",
    "cidade": "city urban", "cidades": "city",
    "municipio": "municipality city",
    "transporte": "transport logistics",
    "logística": "logistics warehouse",
    "frota": "fleet vehicles",
    "veículos": "vehicles transport",
}

# Fallback por categoria quando o título não rende keywords suficientes
_CAT_FALLBACK: dict[str, str] = {
    "Infraestrutura":       "infrastructure construction",
    "Oportunidades":        "business deal handshake",
    "Economia":             "economy finance chart",
    "Energia":              "energy power plant",
    "Tecnologia":           "technology innovation",
    "Geopolítica":          "government capitol diplomacy",
    "Mercado Financeiro":   "stock market trading",
    "Facilities & Serviços":"office building facilities",
    "Reddit":               "world news media",
    "Inovação":             "innovation laboratory",
    "Investimentos":        "investment finance growth",
    "Notícias Mundiais":    "world globe news",
    "Geral":                "business news world",
}

# Regiões → termos EN para complementar a busca
_REGION_EXTRA: dict[str, str] = {
    "Angola":                 "angola",
    "Brasil":                 "brazil",
    "Portugal":               "portugal",
    "Emirados Arabes Unidos": "dubai",
    "África":                 "africa",
    "EUA":                    "new york usa",
    "China":                  "china",
    "Índia":                  "india",
    "Reino Unido":            "london",
    "Alemanha":               "germany",
}


def _title_to_keywords(title: str, max_terms: int = 4) -> list[str]:
    """Extrai até max_terms termos em EN relevantes a partir do título."""
    import unicodedata

    # Normaliza: lower + remove acentos para matching
    normalized = "".join(
        c for c in unicodedata.normalize("NFD", title.lower())
        if unicodedata.category(c) != "Mn"
    )

    found: list[str] = []
    seen: set[str] = set()
    for raw_word in re.split(r"[\s\-–|/,:;.!?()\[\]]+", normalized):
        word = re.sub(r"[^\w]", "", raw_word)
        if not word or len(word) < 4:
            continue
        en = _PT_EN.get(word)
        if en:
            term = en.split()[0]  # primeira palavra do mapeamento
            if term not in seen:
                seen.add(term)
                found.append(term)
                if len(found) >= max_terms:
                    break
    return found


def _contextual_image_url(item: NewsItem) -> str:
    """
    Gera URL LoremFlickr com keywords derivadas do título do artigo.
    Cada artigo recebe uma query única → fotos diversas e contextualmente relevantes.
    lock = hash(url) garante que o mesmo artigo sempre exibe a mesma foto.

    LoremFlickr usa fotos reais do Flickr (licença CC), é gratuito e sem API key.
    URL: https://loremflickr.com/{w}/{h}/{keywords}?lock={seed}
    """
    # 1. Keywords extraídas do título (específicas a este artigo)
    title_kw = _title_to_keywords(item.title, max_terms=3)

    # 2. Região como contexto adicional
    region = item.region or ""
    region_en = _REGION_EXTRA.get(region, "")

    # 3. Fallback de categoria se o título não rendeu keywords suficientes
    cat = (item.categories or ["Geral"])[0]
    cat_fallback = _CAT_FALLBACK.get(cat, "business news")

    # Monta query final
    parts = title_kw[:]
    if region_en:
        first_region_word = region_en.split()[0]
        if first_region_word not in parts:
            parts.append(first_region_word)
    if len(parts) < 2:
        # título sem keywords úteis → usa categoria
        parts = cat_fallback.split()[:3]

    # Máx 4 termos, sem vírgulas nos termos compostos
    keywords = ",".join(p.split()[0] for p in parts[:4])

    # Seed determinístico: mesmo artigo = sempre mesma foto
    seed = int(hashlib.md5(item.url.encode()).hexdigest(), 16) % 999_983

    return f"https://loremflickr.com/800/450/{quote(keywords)}?lock={seed}"


def _apply_fallback_images(items: list[NewsItem]) -> None:
    """Garante 100% de cobertura: todos os artigos sem image_url recebem imagem contextual."""
    without = [it for it in items if not it.image_url]
    for item in without:
        item.image_url = _contextual_image_url(item)
        item.raw["image_fallback"] = True
    if without:
        logger.info("og_enricher: %d artigos receberam imagem contextual (Unsplash)", len(without))


# ── Função principal ──────────────────────────────────────────────────────────

def enrich_images(
    items: Sequence[NewsItem],
    workers: int = 10,
    timeout: int = 6,
    max_to_enrich: int = 80,
) -> list[NewsItem]:
    """
    Para cada NewsItem sem image_url, tenta buscar og:image em paralelo.
    Retorna a lista (com image_url preenchido onde encontrado).

    Args:
        items: lista de NewsItems
        workers: número de threads paralelas
        timeout: timeout por requisição (segundos)
        max_to_enrich: limita quantos artigos sem imagem serão enriquecidos
    """
    needs_image = [it for it in items if not it.image_url]
    if not needs_image:
        return list(items)

    # Prioriza por score desc (artigos mais relevantes primeiro)
    needs_image_sorted = sorted(needs_image, key=lambda x: x.score, reverse=True)
    to_enrich = needs_image_sorted[:max_to_enrich]

    logger.info(
        "og_enricher: buscando imagens para %d/%d artigos (max=%d, workers=%d)",
        len(to_enrich), len(needs_image), max_to_enrich, workers,
    )

    url_to_item: dict[str, NewsItem] = {it.url: it for it in to_enrich}
    found = 0

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="og") as pool:
        futures = {pool.submit(_fetch_og_image, url, timeout): url for url in url_to_item}
        for fut in as_completed(futures):
            url = futures[fut]
            try:
                img_url = fut.result()
                if img_url:
                    url_to_item[url].image_url = img_url
                    found += 1
            except Exception:
                pass

    logger.info("og_enricher: %d imagens OG encontradas de %d artigos", found, len(to_enrich))

    # 2ª camada: garante 100% de cobertura com imagem contextual LoremFlickr
    result = list(items)
    _apply_fallback_images(result)
    return result
