# SINISA Web App (Neon Free + Render)

Este projeto publica o BI na web com:
- Neon Postgres (camada gratuita)
- Render (hospedagem do app Streamlit)

## 1) Criar banco grátis no Neon
1. Acesse https://neon.tech e crie conta.
2. Crie um projeto Postgres.
3. Copie a connection string (URI) no painel do Neon.
4. Garanta `sslmode=require` na URL.

## 2) Preparar variáveis
Copie `.env.example` para `.env` e preencha `DATABASE_URL`.

Exemplo:
`postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`

## 3) Carga de dados no Neon
No PowerShell, dentro desta pasta:

```powershell
$env:DATABASE_URL="postgresql://...?...sslmode=require"
$env:TABLE_NAME="saneamento_sp_municipios_selecionados"
python .\scripts\load_to_supabase.py
```

## 4) Teste local do app
```powershell
$env:DATABASE_URL="postgresql://...?...sslmode=require"
$env:TABLE_NAME="saneamento_sp_municipios_selecionados"
streamlit run .\app.py
```

## 5) Deploy no Render
1. Suba esta pasta para GitHub.
2. No Render, crie um novo Web Service apontando para o repo.
3. Use o `render.yaml`.
4. Configure env vars no Render:
   - `DATABASE_URL` (a URI do Neon)
   - `TABLE_NAME` (opcional, já tem padrão)

Pronto: o app terá URL pública fora da rede interna.

