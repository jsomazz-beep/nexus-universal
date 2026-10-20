# Estado da migração Nexus

Atualizado em 20/10/2026 para `rules-v2`.

## Implementado

- Entradas web, CLI e scheduler usam a fachada `src/nexus_like/pipeline.py`, que delega a `WeeklyReporterPipeline` em `src/news_reporter/pipeline.py`.
- O núcleo existente continua responsável por coleta, normalização, filtros, deduplicação, score, síntese e composição.
- Perfis, fontes, pacotes geográficos, cards, imagens e cotações permanecem no fluxo existente; isso não representa uma certificação exaustiva de paridade em todas as instalações.
- Resumo semanal, matriz e eixo usam análise por regras; `legacy` oferece a composição anterior.
- A v2 corrigiu tradução, consumo do texto traduzido pela análise e matriz contextual, preservando originais e avisos de falha.
- Código publicado no commit `3bae1c32f28d60a11822ccd4e3d99e285906e490`, branch `codex/cloud-nexus-render`.

## Verificado

41 testes automatizados aprovados, compilação de `src` e verificação de diff na entrega funcional v2. Nova geração de produção em 20/10/2026 confirmou a versão e os resultados registrados na [validação](VALIDACAO_CORRECAO_TRADUCAO.md).

## Ainda não concluído

- Migração integral do núcleo para módulos Nexus: a fachada delega ao núcleo existente.
- Novo build e validação do executável portátil: o script permanece disponível, mas o binário anterior não incorpora automaticamente a publicação web.
- Revisão dos feeds sem itens e das ambiguidades geográficas.
- Histórico estruturado de eventos e comparação temporal.
- Medição de qualidade e ganho operacional com avaliação humana.

O [plano de 20/10/2026](superpowers/plans/2026-10-20-analise-sem-llm.md) é um registro histórico da implementação inicial; suas contagens intermediárias não substituem o estado atual. Consulte [arquitetura e operação](ARQUITETURA_E_OPERACAO.md) para manutenção.
