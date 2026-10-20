# Weekly Strategic Intelligence Nexus

Monitoramento de notícias com filtros, perfis reutilizáveis, cards, imagens e relatório executivo. O resumo semanal, a matriz comparativa e o eixo conector usam regras determinísticas, sem chamadas a LLM. A tradução automática utiliza serviço externo e exige internet.

Estado documentado em **20/10/2026**: análise `rules-v2`, publicada no commit `3bae1c32f28d60a11822ccd4e3d99e285906e490`. O executável portátil ainda precisa de novo build para incorporar essa versão.

## Documentação

- [Visão gerencial, responsabilidades e limites](DOCUMENTACAO_SOLUCAO_TI_INOVACAO.md)
- [Arquitetura e operação](docs/ARQUITETURA_E_OPERACAO.md)
- [Análise sem LLM: tradução, matriz e evidências](docs/ANALISE_SEM_LLM.md)
- [Validação da correção v2](docs/VALIDACAO_CORRECAO_TRADUCAO.md)
- [Estado da migração Nexus](docs/NEXUS_MIGRATION_STATUS.md)

## Execução local

Execute na pasta `weekly_strategic_intelligence_nexus`, com Python 3.11. Os comandos de cópia criam somente arquivos ausentes; configurações existentes devem ser preservadas.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .\config\config.yaml)) {
    Copy-Item .\config\config.example.yaml .\config\config.yaml
}
if (-not (Test-Path .\.env)) {
    Copy-Item .\.env.example .\.env
}
python src\run_embedded_webapp.py
```

Abra [WebApp local](http://127.0.0.1:8787). Ajuste fontes, período, regiões, temas e palavras-chave antes de gerar. A coleta, as cotações e a tradução dependem dos serviços externos; execução local não significa operação integralmente offline.

## Aplicação publicada

[Abrir Nexus no Render](https://weekly-strategic-intelligence-nexus.onrender.com/) · [Relatório atual](https://weekly-strategic-intelligence-nexus.onrender.com/report/current)

Repositório existente: [jsomazz-beep/nexus-universal](https://github.com/jsomazz-beep/nexus-universal). Branch de publicação: `codex/cloud-nexus-render`. O Blueprint na raiz do repositório aponta `rootDir` para `weekly_strategic_intelligence_nexus`, com runtime Docker, plano Free e `autoDeploy: true`.

O servidor usa `PORT` quando definido pelo Render. O cabeçalho HTTP `X-Nexus-Analysis-Version: rules-v2` identifica o código instalado; um relatório antigo pode ter sido produzido por uma versão anterior. Gere novo relatório para aplicar as correções.

Não é necessário inicializar outro repositório nem criar outro serviço. Para atualização e reversão, siga o [procedimento de operação](docs/ARQUITETURA_E_OPERACAO.md#publicação-e-reversão).

## Persistência opcional no Supabase

Os scripts abaixo são preparações para uma instalação nova. Em ambiente existente, confira as tabelas antes de executá-los.

| Uso | Script | Configuração opcional |
| --- | --- | --- |
| Perfis | [supabase_profiles_setup.sql](docs/supabase_profiles_setup.sql) | `SUPABASE_PROFILES_TABLE=profile_sets`, `SUPABASE_PROFILE_SET_ID=default` |
| Relatórios HTML | [supabase_reports_setup.sql](docs/supabase_reports_setup.sql) | `SUPABASE_REPORTS_TABLE=intelligence_reports` |

Ambos utilizam `SUPABASE_URL` (URL base do projeto, sem `/rest/v1`) e `SUPABASE_SERVICE_ROLE_KEY` no servidor. Não inclua credenciais em commits, relatórios ou código enviado ao navegador. Sem a configuração remota, os perfis usam armazenamento local. O sistema tenta restaurar até 25 relatórios remotos ao iniciar; falhas remotas podem coexistir com uma geração local bem-sucedida. Veja os detalhes e limites na documentação de operação.

## Verificação e build portátil

```powershell
python -m unittest discover -s tests -q
python -m compileall -q src
git diff --check
```

A validação v2 registrou **41 testes aprovados**. Os testes com fixtures não substituem a verificação dos serviços externos.

O fluxo de empacotamento Windows foi preservado:

```powershell
scripts\build_onefile_webapp_portable_py311.bat
```

Saída: `dist/StrategicIntelligenceWebApp.exe`. O script encerra processos do executável anterior e substitui o binário; execute em uma janela de manutenção local. Nenhum novo `.exe` foi construído ou validado na entrega v2.
