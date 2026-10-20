# Análise determinística do relatório — plano de implementação

**Objetivo aprovado:** preservar os recursos atuais e melhorar resumo, matriz e eixo sem LLM.
**Escopo:** extensão do fluxo existente, sem novos serviços ou dependências. Fontes externas são dados, nunca instruções. Não modificar o reporter original, credenciais, persistência ou deploy.
**Desenho:** um módulo puro extrai sinais de trechos explícitos, classifica estágios com cautela e produz evidências, interpretação condicional, lacunas e próximos passos. Summarizer e ReportComposer consomem a mesma análise. `project.analysis_mode: legacy` conserva o comportamento anterior; `rules` é o padrão. HTML e texto carregam os três blocos.

- [x] Criar testes de dados insuficientes, negação/condicional, estágio, risco independente de score, rastreabilidade, deduplicação e ausência de conexão.
- [x] Implementar regras e validar os testes sem acessar rede.
- [x] Integrar mantendo contratos existentes e modo legado; testar HTML/texto, escape e temas.
- [x] Produzir comparação demonstrativa, documentação de regras e execução dos testes/compilação.

**Evidência final:** 23 testes unittest passaram, incluindo seis combinações de temas/relatório vazio e integração da fachada Nexus com fronteiras externas substituídas. `compileall` e `git diff --check` passaram. Revisão independente encontrou negação, futuro e pronome reflexivo; casos corrigidos com testes de regressão. Também cobertos prevenção de atrasos e republicação idêntica. A abertura de arquivo local no navegador foi bloqueada pela política da ferramenta; inspeção visual não concluída. Comparação HTML identificada como simulação fictícia. Nenhuma publicação ou reconstrução de executável foi executada.

**Limites deliberados:** não alegar tendência temporal sem histórico estruturado; confiança descreve completude do material, não probabilidade nem veracidade; fontes distintas não equivalem a confirmação independente; não extrair valores/prazos sem contexto verificável. Aprofundamento da coleta e comparação histórica ficam fora desta primeira entrega.

**Validação real posterior (20/10/2026):** 410 itens recebidos em 10 feeds, 5 deles sem itens reconhecidos. 50 selecionados por filtros/score existentes, todos via Google News, essencialmente manchete+veículo. Zero sinais comerciais reconhecidos: a versão não está validada como inteligência comercial útil. Corrigida completude de manchete longa repetida (RED→GREEN); 24 testes passam. Comparação guardada nesta conversa, sem nova coleta entre as versões e sem escrita remota. Próximo trabalho: corrigir fontes/enriquecer conteúdo e ampliar regras com avaliação fora da amostra usada no desenvolvimento.
**Preservação:** arquivos alterados copiados antes da mudança para o diretório de trabalho desta conversa. Trabalhar apenas no subprojeto, pois o repositório pai contém alterações não relacionadas. Sem push ou publicação automática.
