# Arquitetura e operação

Referência: código `rules-v2`, commit `3bae1c32f28d60a11822ccd4e3d99e285906e490`, conferido em 20/10/2026.

## Componentes e fluxo

| Componente | Localização | Função |
| --- | --- | --- |
| WebApp | `src/embedded_webapp.py` | Formulário, perfis, geração e visualização de relatórios; servidor HTTP embarcado. |
| Entradas | `src/run_embedded_webapp.py`, `src/main.py`, `src/scheduler.py` | Entrada web, linha de comando e agendamento. |
| Fachada Nexus | `src/nexus_like/pipeline.py` | Delega a execução ao núcleo existente. |
| Pipeline | `src/news_reporter/pipeline.py` | Coordena coleta, seleção, síntese e saída. |
| Tradução | `src/news_reporter/translation.py`, `summarizer.py` | Tradução, cache, estados e resumo de itens. |
| Análise | `src/news_reporter/intelligence.py`, `context_rules.py` | Evidências, estágios, assuntos, matriz e conexão temática. |
| Composição | `src/news_reporter/report.py` e templates | HTML e representação textual, escape e links HTTP(S). |
| Persistência | `persistence.py`, `supabase_reports.py` e WebApp | Histórico local, relatórios remotos e perfis. |

Fluxo: coleta → normalização → filtros → deduplicação → score de relevância → anotações legadas de oportunidade → limite de notícias → tradução/resumo → síntese semanal → composição → armazenamento.

A fachada ainda utiliza o núcleo `news_reporter`; a migração não é uma reescrita integral. A análise nova é determinística e não chama LLM. Tradução, RSS e cotações continuam dependendo de serviços externos.

## Configuração

O padrão local é `config/config.yaml`; `.env` contém variáveis de ambiente da instalação. `NEWS_REPORTER_HOME` permite outra raiz de dados/configuração. Preserve os arquivos existentes ao atualizar. O exemplo público não substitui os parâmetros privados da instalação.

| Parâmetro | Efeito |
| --- | --- |
| `project.analysis_mode: rules` | Composição analítica atual; padrão quando omitido. |
| `project.analysis_mode: legacy` | Composição anterior do resumo semanal, matriz e eixo. |
| `project.include_images` | Controla exibição de imagens; mantenha a estrutura do exemplo existente. |
| `PORT` / `NEWS_WEBAPP_PORT` | Porta HTTP; `PORT` tem precedência, padrão 8787. |
| `NEWS_OPEN_BROWSER` | Controla abertura automática do navegador; usar `0` no servidor. |

A seleção `analysis_mode` é feita no YAML carregado e não foi adicionada ao formulário de perfis. O modo legado mantém as correções de tradução, escape HTML e saneamento de links. Nenhum modo recalcula HTML já salvo.

O bind padrão é `127.0.0.1` localmente e `0.0.0.0` quando a variável `RENDER` está presente. O WebApp embarcado não acrescenta uma camada própria de autenticação nesta entrega; não pressupor controle de acesso multiusuário.

## Tradução e fontes

O tradutor usa os endpoints públicos Google `translate.googleapis.com/translate_a/single` e, como contingência, `translate.google.com/m`. Há timeout de conexão/leitura, cache por execução, divisão de textos e interrupção após duas falhas consecutivas. A solicitação usa destino `pt`; o conteúdo é apresentado como português no relatório, sem garantia de revisão linguística regional.

Títulos/corpos originais são preservados. Os estados são `not_requested`, `original_pt`, `translated`, `partial` e `failed`. Falhas geram avisos visíveis; o original pode continuar aparecendo quando a tradução falha. Texto de notícia é enviado ao serviço externo para tradução; não há chave adicional nem SLA contratado nesse fluxo.

HTTP 200 de um feed não comprova recebimento de notícias válidas. Confira contagens e erros da execução, não apenas a URL. Nos RSS agregados, o veículo informado pelo item é usado quando disponível, preservando o feed nos metadados; isso não certifica autoria nem independência.

## Dados e persistência

| Dado | Comportamento |
| --- | --- |
| Perfis locais | `data/search_profiles.json`, conjuntos reutilizáveis; sem versionamento histórico automático. |
| Perfis Supabase | Tabela padrão `profile_sets`, conjunto `default`; conjunto remoto disponível tem precedência. Se remoto estiver vazio e houver perfis locais, tenta sincronizá-los. Em erro remoto, usa local. |
| Gravação de perfis | Tenta remoto; se falhar ou não estiver configurado, grava local. Uma gravação remota bem-sucedida não atualiza necessariamente a cópia local. |
| Relatórios | HTML `weekly_report_*.html` no diretório de saída configurado; tentativa de gravação remota quando configurada. |
| Restauração | Ao iniciar o WebApp, tenta recuperar até 25 relatórios remotos ausentes localmente. |
| Retenção remota | `runtime.report_history_keep`, padrão 1000, mínimo 50; limpeza limitada por consulta e executada como melhor esforço. |
| Histórico de execução | `data/history.json` por padrão, últimos 50 registros de metadados, contagens, avisos e caminhos; sem snapshot completo dos artigos. |

Supabase exige URL base e chave de serviço somente no servidor. Tabelas e variáveis estão no [README](../README.md#persistência-opcional-no-supabase). Falhas de gravação de relatórios são registradas e podem não interromper a geração. Portanto, relatório visível não prova recuperação após reinicialização. Em nuvem, arquivos locais não devem ser a única garantia de continuidade.

## Publicação e reversão

Repositório: [nexus-universal](https://github.com/jsomazz-beep/nexus-universal). Branch: `codex/cloud-nexus-render`. O `render.yaml` da raiz define `rootDir: weekly_strategic_intelligence_nexus`, Dockerfile do projeto e publicação automática. O YAML dentro da subpasta não deve ser confundido com o Blueprint da raiz.

1. Trabalhe em checkout da branch de publicação e confira `git status`. No ambiente local original, o repositório pai contém outros projetos e alterações alheias.
2. Selecione somente os arquivos do Nexus pretendidos; confira o diff antes do commit. Evite `git add .` no repositório pai.
3. Para mudanças de código, rode a suíte indicada no README e as verificações da alteração. Publique na branch e acompanhe a implantação do Render.
4. Confira a página inicial e o cabeçalho `X-Nexus-Analysis-Version`. Para validar comportamento novo, gere um relatório com os parâmetros de teste e confira o conteúdo. O cabeçalho sozinho confirma versão do código, não o sucesso da tradução.
5. Confira os avisos e a persistência conforme o objetivo do teste. Não altere perfis salvos apenas para verificar uma geração.

Para voltar a composição analítica anterior, use `analysis_mode: legacy` e gere novo relatório. Para reverter código, faça um commit de reversão dos commits identificados, revise, teste e publique na mesma branch; não use force push. O commit funcional v2 é `3bae1c32f28d60a11822ccd4e3d99e285906e490`; uma reversão deve considerar alterações posteriores, sem sobrescrevê-las. Preserve perfis e relatórios antes de qualquer operação de recuperação.

## Verificação e pendências

A suíte v2 passou com 41 testes e compilação Python. A [validação](VALIDACAO_CORRECAO_TRADUCAO.md) registra separadamente a amostra local e a geração em produção. Testes com fixtures não gravam em produção nem comprovam disponibilidade contínua de serviços.

Pendências conhecidas: reconstruir e testar o `.exe`, revisar feeds sem itens, melhorar ambiguidades geográficas e avaliar resultados com a equipe. Comparação histórica estruturada de eventos não foi implementada. Essas pendências não foram resolvidas por uma atualização de documentação.
