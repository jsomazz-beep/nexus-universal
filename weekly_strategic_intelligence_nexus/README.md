# Weekly Strategic Intelligence Nexus

Projeto paralelo para evoluir o `weekly_strategic_intelligence_reporter` para uma arquitetura **cloud-first (Nexus-like)**, sem alterar o projeto original.

## Objetivos preservados

- Paridade funcional com o reporter original
- WebApp com filtros, perfis, fontes, pacotes geográficos, cards de notícia, fallback de imagem e cards de mercado
- Build `.exe` portátil para uso local/offline operacional
- Evolução para deploy em nuvem (GitHub + Render)

## Execução local (desenvolvimento)

```powershell
cd "C:\Users\zigur\OneDrive\Documentos\New project\weekly_strategic_intelligence_nexus"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .\config\config.example.yaml .\config\config.yaml -Force
Copy-Item .\.env.example .\.env -Force
python src\run_embedded_webapp.py
```

WebApp local: `http://127.0.0.1:8787`

## Deploy em nuvem (Render)

Este repositório já está preparado para Render com:

- `Dockerfile` cloud-ready
- `render.yaml` (Blueprint)
- suporte a `PORT` (padrão Render)
- browser auto-open desligado no servidor

### 1) Subir no GitHub

```powershell
cd "C:\Users\zigur\OneDrive\Documentos\New project\weekly_strategic_intelligence_nexus"
git init
git add .
git commit -m "chore: cloud-ready nexus baseline"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/weekly_strategic_intelligence_nexus.git
git push -u origin main
```

### 2) Publicar no Render

1. Acesse Render e escolha **New + > Blueprint**
2. Conecte o repositório do GitHub
3. O Render detecta o `render.yaml` automaticamente
4. Clique em **Apply** para criar o serviço

URL final: `https://<nome-do-servico>.onrender.com`

## Build `.exe` portátil (mantido)

Script recomendado:

```powershell
scripts\build_onefile_webapp_portable_py311.bat
```

Gera:

- `dist\StrategicIntelligenceWebApp.exe`

## Estrutura principal

- `src/embedded_webapp.py`: webapp embarcado
- `src/nexus_like/`: facade de orquestração Nexus-like
- `src/news_reporter/`: núcleo funcional em paridade
- `render.yaml`: blueprint de deploy cloud
- `Dockerfile`: container para execução em nuvem

## Perfis em Supabase (opcional, recomendado na nuvem)

1. No Supabase SQL Editor, execute: docs/supabase_profiles_setup.sql`n2. Configure no serviço (Render env vars):
   - SUPABASE_URL`n   - SUPABASE_SERVICE_ROLE_KEY`n   - opcional: SUPABASE_PROFILES_TABLE=profile_sets`n   - opcional: SUPABASE_PROFILE_SET_ID=default`n3. Sem essas variáveis, o app continua salvando local em data/search_profiles.json.

