# Nexus Intelligence v2.0

> Agregador global de notícias com IA — mais moderno, mais fontes, interface premium.

## 🚀 Início rápido

### 1 clique — WebApp
```
scripts\start_webapp.bat
```
Abre automaticamente em **http://127.0.0.1:8788**

### CLI direto
```powershell
cd nexus_intelligence
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
set PYTHONPATH=src
python src\nexus\pipeline_cli.py --max-news 80 --days 7
```

## 📡 Fontes (35+)

| Categoria | Fontes |
|-----------|--------|
| 🇧🇷 Brasil | Valor Econômico, Folha, Estadão, InfoMoney, CNN Brasil, Senado |
| 🇵🇹 Portugal | Público, Observador, Jornal de Notícias |
| 🇦🇴 Angola | Angola Digital, AfDB |
| 🇦🇪 UAE | Khaleej Times, Zawya |
| 🌍 Economia Global | Reuters, FT, Bloomberg, FMI, World Bank, IFC |
| 🤖 Tecnologia | TechCrunch, Wired, MIT Tech Review, Ars Technica, The Verge, VentureBeat |
| 🌐 Geopolítica | BBC World, The Guardian, Foreign Affairs, AP News |
| 🔬 Ciência | Nature, Science Daily, NIH |
| 🌱 Clima/ESG | Carbon Brief, Renewable Energy World |
| 💬 Comunidade | Hacker News (top 30), Reddit (r/worldnews, r/investing, r/economics) |
| 🔍 Google News | BR, PT, Angola, UAE, ESG — buscas dinâmicas |

## 🗂️ Tópicos classificados automaticamente

- 📈 Economia & Finanças
- 🤖 Tecnologia & IA
- ⚡ Infraestrutura & Energia
- 🌐 Geopolítica & Diplomacia
- 🔬 Saúde & Ciência
- 💼 Oportunidades & Negócios
- 🌱 Clima & Sustentabilidade

## ✨ Diferenciais vs V1

| Feature | V1 | Nexus v2 |
|---------|-----|----------|
| Fontes | ~11 RSS | 35+ (RSS, HN, Reddit, NewsAPI) |
| Coleta | Sequencial | **Paralela** (ThreadPool) |
| Tópicos | 2 (Economia, Oportunidades) | **7 tópicos** com ícones e cores |
| Interface | HTML básico | **Dark mode premium** com barra de progresso |
| IA | ❌ | **Gemini Flash** (opcional) para resumos |
| Score | Simples | Multi-dimensional com autoridade da fonte |
| Relatório | Tema único | Dark-mode responsivo com radar de oportunidades |

## ⚙️ Variáveis de ambiente (`.env`)

```
NEWSAPI_KEY=          # newsapi.org (opcional)
GEMINI_API_KEY=       # Google AI Studio (opcional — resumos IA)
HTTP_USER_AGENT=NexusIntelligence/2.0
OUTPUT_LANGUAGE=pt
```

## 📁 Estrutura

```
nexus_intelligence/
├── config/config.yaml     # Configuração principal
├── src/
│   ├── nexus/
│   │   ├── collectors/    # RSS, HackerNews, Reddit, NewsAPI
│   │   ├── normalizer.py
│   │   ├── filters.py
│   │   ├── deduplicator.py
│   │   ├── classifier.py  # Tópicos + Oportunidades
│   │   ├── scoring.py
│   │   ├── summarizer.py  # + Gemini AI
│   │   ├── pipeline.py    # Orquestrador paralelo
│   │   └── report.py      # HTML premium dark-mode
│   └── webapp.py          # Flask + UI moderna
├── scripts/
│   ├── start_webapp.bat   ← USE ESTE
│   ├── run_now.bat
│   └── install_deps.bat
├── output/                # Relatórios gerados
└── requirements.txt
```
