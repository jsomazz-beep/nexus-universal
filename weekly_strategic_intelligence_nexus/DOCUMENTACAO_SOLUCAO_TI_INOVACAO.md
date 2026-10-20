# Solução TI/Inovação — Weekly Strategic Intelligence Nexus

Documento gerencial de referência, atualizado em **20/10/2026** para a versão `rules-v2`. Para instalação e manutenção, consulte o [README](README.md) e a [documentação de operação](docs/ARQUITETURA_E_OPERACAO.md).

## 1. Processo e objetivo

O Nexus apoia monitoramento, curadoria e síntese de notícias de mercado. Automatiza coleta, organização e composição do relatório para que a equipe concentre a revisão na relevância dos fatos e nos próximos passos comerciais.

O resultado é apoio à decisão. Uma notícia setorial, um investimento citado ou uma recomendação de verificação não confirma uma compra disponível, elegibilidade comercial ou venda futura.

## 2. Funcionamento implementado

1. O usuário escolhe fontes, período, regiões, temas, palavras-chave e limite de notícias, podendo reutilizar perfis salvos.
2. O pipeline coleta, normaliza, filtra, deduplica e pontua os itens.
3. Títulos e conteúdo disponíveis são traduzidos para português quando necessário, preservando o original e indicando falhas.
4. Regras classificam estágio, assunto, sinais e suficiência do material recebido.
5. O relatório reúne cards com imagens, resumo semanal, matriz comparativa e eixo conector com referências.
6. Perfis e relatórios podem usar Supabase, conforme configuração. Existe também armazenamento local, com limites de continuidade em nuvem.

A versão v2 diferencia assuntos e eventos na matriz e evita preencher todas as notícias com uma interpretação genérica. Itens sem evidência suficiente para uma linha específica continuam nos cards. O eixo relaciona publicações por sinal compatível; não demonstra causalidade nem independência editorial.

## 3. Fatores de avaliação da prática

| Fator | Recurso implementado | Evidência e limite |
| --- | --- | --- |
| Enxuto | Coleta, deduplicação e composição automatizadas | Reduz etapas manuais potenciais; economia de horas ainda não medida com baseline. |
| Proativo | Filtros, avisos de tradução e registro de falhas | Ajuda a localizar lacunas; não garante disponibilidade de fontes ou captura de todos os eventos. |
| Digital | WebApp, perfis reutilizáveis e relatório HTML | Fluxo digital operacional; acesso e persistência dependem da instalação. |
| Abrangente | Fontes e pacotes geográficos configuráveis | Abrangência depende da cobertura e integridade dos feeds; classificação geográfica é heurística. |
| Efetivo | Seleção priorizada e perguntas de acompanhamento por assunto | Apoia triagem; acurácia comercial e impacto em decisões exigem avaliação humana. |
| Inovador | Síntese rastreável e análise determinística sem LLM | Automação por regras; não deve ser apresentada como raciocínio generativo ou inteligência autônoma. |

## 4. Evidências disponíveis

Na entrega v2, 41 testes automatizados passaram. A revisão incluiu preservação de magnitude monetária, diferenciação entre conclusão de estudo e entrega de ativo e tratamento de investimento negado no corpo da notícia.

Uma nova geração em produção, verificada em 20/10/2026 às 10h53 BRT, apresentou 50 cards, 25 notícias originalmente em inglês com títulos exibidos em português e nenhuma indicação de falha de tradução. A matriz teve 21 linhas, com 13 leituras textualmente distintas e 8 ações distintas. São resultados de uma execução, não metas permanentes nem comprovação da verdade das notícias ou da precisão das interpretações.

A [validação técnica](docs/VALIDACAO_CORRECAO_TRADUCAO.md) separa essa execução da amostra local anterior.

## 5. Responsabilidades

| Papel | Responsabilidade |
| --- | --- |
| TI/Inovação | Manter código, dependências, fontes, configuração, publicação e investigação de falhas. |
| Operação/Inteligência | Definir perfis, revisar tradução, fontes, pertinência, região e lacunas das notícias. |
| Gestão/Comercial | Confirmar fatos e condições comerciais nas fontes antes de decidir ou abordar uma oportunidade. |

## 6. Limites e controles

- RSS pode entregar somente manchete e nome do veículo. O sistema não obtém automaticamente uma evidência completa a partir disso.
- Tradução usa endpoints públicos externos, sujeitos a bloqueio, falha e erros linguísticos. Os originais são preservados.
- Completude do conteúdo não equivale a confiança estatística, veracidade ou probabilidade de venda. O score representa relevância segundo a configuração, não risco.
- Algumas camadas de filtro possuem fallback quando zeram a seleção. A presença no relatório não garante aderência estrita a todos os critérios.
- Valores são extraídos literalmente, sem conversão, soma ou estimativa de tamanho da oportunidade.
- O histórico local registra metadados de execuções, não uma base de eventos para comparação temporal. Não há detecção validada de aceleração de tendências.
- Imagens podem vir do feed ou de fallback ilustrativo; não são evidência do evento.
- Sucesso na geração não confirma persistência remota. O binário portátil anterior não foi atualizado pela publicação web.

## 7. Benefícios esperados e medição proposta

Espera-se reduzir o esforço de consolidação e tornar a revisão mais consistente. Não foi apresentada medição de antes/depois que quantifique esses benefícios.

Para avaliá-los, recomenda-se registrar tempo de preparação e revisão por relatório, percentual de itens considerados relevantes pela equipe, falhas por fonte, traduções que exigiram correção e oportunidades confirmadas após consulta à fonte. Esses indicadores são propostas de acompanhamento; não estão implementados como um painel nesta versão.

## 8. Referências

- [Aplicação publicada](https://weekly-strategic-intelligence-nexus.onrender.com/)
- [Análise sem LLM](docs/ANALISE_SEM_LLM.md)
- [Arquitetura, persistência e operação](docs/ARQUITETURA_E_OPERACAO.md)
- [Estado da migração](docs/NEXUS_MIGRATION_STATUS.md)
