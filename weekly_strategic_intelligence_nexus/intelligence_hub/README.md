# Intelligence Hub v2.0 🔬

Agregador de inteligência estratégica de próxima geração. Versão 2.0 do `weekly_strategic_intelligence_reporter`, completamente reescrito com arquitetura moderna, mais fontes e interface atualizada.

## ✨ O que é novo nesta versão

| Aspecto | V1 (anterior) | V2 (este projeto) |
|---|---|---|
| **Fontes** | RSS + NewsAPI | RSS + NewsAPI + **GDELT + Guardian + HN + Reddit + NYTimes** |
| **Coleta** | Sequencial | **Paralela** (ThreadPool, 12 workers) |
| **Persistência** | JSON | **SQLite** com índices |
| **Web App** | HTTP simples | **FastAPI** com API REST |
| **Relatório** | HTML estático | **Interativo** (dark/light/boardroom, filtros, busca) |
| **Config** | YAML | YAML + **Pydantic** com validação |
| **Dedup** | Similaridade básica | Jaccard + URL normalizada |

## 🚀 Início rápido

### 1. Setup (primeira vez)
```powershell
cd intelligence_hub
scripts\setup.bat
```

### 2. Configurar (opcional — funciona sem API keys)
Edite `.env` com suas chaves de API gratuitas:
- `GUARDIAN_API_KEY` — [open-platform.theguardian.com](https://open-platform.theguardian.com/access/)
- `NYTIMES_API_KEY` — [developer.nytimes.com](https://developer.nytimes.com/)
- `NEWSAPI_KEY` — [newsapi.org/register](https://newsapi.org/register)

### 3. Executar

**Linha de comando (gera relatório HTML):**
```powershell
scripts\run_now.bat
```

**Web App (interface gráfica em http://127.0.0.1:8787):**
```powershell
scripts\webapp.bat
```

## 📊 Fontes de dados (30+)

### Gratuitas e sem API key
| Fonte | Tipo | Cobertura |
|---|---|---|
| **GDELT Project** | API | 65+ idiomas, cobertura global |
| **Hacker News** | API (Algolia) | Tech, startups, IA |
| **Reddit** | RSS público | Discussões globais |
| **Google News** | RSS | Busca dinâmica por query |
| **World Bank** | RSS | Desenvolvimento global |
| **IFC** | RSS | Investimentos privados |
| **African Dev Bank** | RSS | África |
| **Reuters Business** | RSS | Global |
| **Khaleej Times** | RSS | UAE/Golfo |
| **Valor Econômico** | RSS | Brasil |
| **Dinheiro Vivo** | RSS | Portugal |
| **Jornal de Angola** | RSS | Angola |
| **PPP Bulletin** | RSS | PPPs globais |

### Com chave de API gratuita
| Fonte | Chave | Limite gratuito |
|---|---|---|
| **The Guardian** | `GUARDIAN_API_KEY` | 12M artigos, sem limite req |
| **NewsAPI** | `NEWSAPI_KEY` | 100 req/dia |
| **NY Times** | `NYTIMES_API_KEY` | 500 req/dia |

## ⚙️ Configuração avançada

Edite `config/config.yaml`:

```yaml
project:
  max_news: 80
  report_theme: "dark"  # dark | light | boardroom

monitoring:
  regions:
    - Angola
    - Brasil
    - Portugal
  priority_keywords:
    - licitação
    - saneamento
    - facilities
```

## 💻 Uso via CLI

```powershell
# Padrão
python src/main.py

# Com parâmetros
python src/main.py --max-news 80 --theme dark --open

# Palavras prioritárias customizadas
python src/main.py --keywords "IA,energia,Angola" --verbose

# Modo verboso
python src/main.py --verbose
```

## 🗂️ Estrutura do projeto

```
intelligence_hub/
├── src/
│   ├── main.py              # CLI entry point
│   ├── webapp.py            # FastAPI web app
│   └── hub/
│       ├── config.py        # Configuração
│       ├── models.py        # Modelos Pydantic
│       ├── pipeline.py      # Pipeline principal
│       ├── collectors/      # Coletores por tipo
│       │   ├── rss.py       # RSS/Atom
│       │   ├── gdelt.py     # GDELT Project
│       │   ├── guardian.py  # The Guardian
│       │   ├── hackernews.py# Hacker News
│       │   ├── reddit.py    # Reddit RSS
│       │   ├── newsapi.py   # NewsAPI.org
│       │   └── nytimes.py   # New York Times
│       ├── processors/      # Filtro, dedup, scoring
│       ├── storage/         # SQLite database
│       └── report/          # Templates HTML
├── config/
│   └── config.example.yaml  # Configuração exemplo
├── scripts/
│   ├── setup.bat            # Setup inicial
│   ├── run_now.bat          # Executar agora
│   └── webapp.bat           # Web App
├── output/                  # Relatórios gerados
├── data/                    # Banco SQLite
└── requirements.txt
```

## 📈 Relatório gerado

O relatório HTML inclui:
- **KPIs executivos** (notícias curadas, fontes, oportunidades, regiões)
- **Síntese executiva** gerada automaticamente
- **Top oportunidades** ranqueadas por score
- **Gráfico de fontes** (distribuição por origem)
- **Cards por categoria** com filtros interativos e busca
- **Modal de detalhes** ao clicar em qualquer notícia
- **3 temas visuais**: dark, light, boardroom (impressão)
- **Toggle dark/light** em tempo real

## 🔧 Adicionar novas fontes

Para adicionar uma fonte RSS:
```yaml
# Em config/config.yaml, seção sources:
- id: minha_fonte
  type: rss
  enabled: true
  name: "Minha Fonte"
  region_hint: "Brasil"
  url: "https://exemplo.com/rss.xml"
```

Para adicionar um novo tipo de coletor, crie `src/hub/collectors/meu_coletor.py`
e registre em `src/hub/collectors/__init__.py`.

---
*Intelligence Hub v2.0 — construído sobre o `weekly_strategic_intelligence_reporter` v1*
