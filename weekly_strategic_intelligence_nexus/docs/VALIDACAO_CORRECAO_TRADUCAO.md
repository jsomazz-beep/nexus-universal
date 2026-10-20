# Correção de tradução e repetição da matriz — 20/10/2026

## Reprodução

O relatório servido por `/report/current` na versão rules-v1 continha títulos em inglês e linhas da matriz com a mesma interpretação/pedido de revisão. O caminho de tradução anterior retornou `TooManyRequests` em uma chamada real local. A versão v1 mantinha o texto original silenciosamente quando havia erro. Além disso, a análise lia `title/description/content` originais e não o conteúdo traduzido.

## Correção

- Tradutor HTTP com timeout, rota de contingência, cache por execução e interrupção de tentativas após falhas consecutivas; português detectado não é enviado para retradução.
- `translated_content_pt` e `translation_status` em NewsItem, com valores padrão compatíveis com registros anteriores.
- Títulos e trechos traduzidos alimentam as regras; originais permanecem disponíveis. Falhas de tradução são visíveis nos cards, no resumo e nos avisos da execução.
- Matriz por assunto/evento, com perguntas setoriais e dados numéricos citados literalmente do original, sem conversões ou soma.
- Itens sem enquadramento e conteúdo institucional/treinamento sem objeto comercial continuam nos cards, sem uma linha genérica de oportunidade na matriz.
- Estudo/curso/financiamento concluído não é ativo em operação; negação no corpo impede afirmar investimento mesmo com título neutro. Magnitudes monetárias são preservadas ou omitidas quando não reconhecidas.
- RSS usa o veículo informado pelo item e conserva identificação do feed.

## Evidência local

41 testes passam, com regressões primeiro reproduzidas e depois corrigidas. Revisão independente encontrou três casos (magnitude monetária, conclusão de estudo/curso e investimento negado); todos receberam testes e correções.

Na mesma amostra real anterior de 50 notícias: 42 originais em português e 8 em inglês; as 8 foram traduzidas em chamadas reais ao serviço. A matriz contém 31 linhas em 8 assuntos, com 18 interpretações textualmente distintas e 8 ações setoriais; 19 itens continuam nos cards sem linha de análise específica. Diversidade textual não comprova acurácia: esse indicador apenas verifica que não há mais a mesma resposta em todos os casos.

## Limites

Endpoints públicos de tradução podem bloquear ou falhar; não há SLA nem garantia de qualidade linguística. A evidência original continua acessível, incluindo nomes e valores. Sem LLM, o sistema segue um conjunto finito de regras; mesmos assuntos/eventos podem ter as mesmas perguntas. Não interpretar automaticamente uma notícia setorial como compra disponível. Essa validação não confirma a verdade dos fatos jornalísticos nem corrige todas as limitações dos feeds ou da classificação geográfica.

Relatórios históricos são imutáveis; é necessário gerar um novo relatório após atualizar o código para aplicar a correção.
