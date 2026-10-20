# Análise por regras — versão 1

## Correção v2 — tradução e matriz contextual

O resumo e a matriz usam título e conteúdo traduzidos para português quando disponíveis; o texto original é mantido nos dados e na evidência expandida. Notícias já detectadas como português não consomem requisições de tradução. O tradutor usa requisições com timeout, cache por execução, rota de contingência e interrupção após falhas consecutivas. Endpoints públicos de tradução não têm SLA: indisponibilidade é exibida no relatório e nos avisos da execução, nunca confundida com tradução bem-sucedida.

A matriz diferencia frota/recarga, portos/logística, saneamento, energia, infraestrutura digital, instalações/facilities, infraestrutura física e mercado imobiliário. Distingue investimentos citados, indicadores, debate/diagnóstico, implantação, entrega e estudos; textos institucionais/treinamento sem objeto comercial e itens sem enquadramento são mantidos nos cards, sem uma linha genérica na matriz. Um assunto reconhecido não é oportunidade confirmada. Perguntas setoriais são verificações, não fatos nem riscos comprovados. Interpretações podem se repetir legitimamente para o mesmo assunto/evento; não há variação de palavras para simular análise.

Valores e percentuais são citados literalmente do material ORIGINAL, com magnitude preservada; não são somados, convertidos, associados automaticamente a um contrato nem usados como tamanho da oportunidade. Magnitudes não reconhecidas são omitidas da extração. Entrega de estudo, curso ou financiamento não é entrega de ativo operacional. A negação é aplicada ao trecho que sustenta o evento, e não apenas ao título.

Em RSS agregados, o veículo informado pelo item passa a ser usado como fonte editorial quando disponível, preservando o ID e nome do feed em metadados. Essa identificação não certifica autoria ou independência.

O cabeçalho HTTP `X-Nexus-Analysis-Version: rules-v2` identifica o código instalado. Relatórios já salvos conservam o conteúdo anterior; gerar um relatório novo para aplicar a correção.

O fluxo de coleta, normalização, filtros, deduplicação, score, perfis, persistência e exportação continua existente. A fachada Nexus utiliza o mesmo pipeline. A nova análise é Python puro, sem chamadas a LLM, sem chave adicional e sem dependência nova. A tradução já existente permanece como antes.

## Ativação e retorno

O padrão é `rules`. Para usar o conteúdo anterior, incluir na seção `project` do YAML efetivamente carregado:

```yaml
project:
  analysis_mode: legacy
```

Para reativar: `analysis_mode: rules`, ou remover essa chave. A configuração não foi adicionada ao formulário de perfis nesta versão. A seleção é feita no arquivo de configuração. A mudança não recalcula relatórios já armazenados.

## Regras implementadas

- Estágio: contratação aberta, contrato adjudicado/assinado, obras, operação/inauguração, anúncio/intenção, suspensão/cancelamento, múltiplos estágios ou não identificado.
- Sinais comerciais: editais publicados/abertos de manutenção/facilities, construção/ampliação de ativos e ativos em operação. Isso não confirma elegibilidade, demanda contratável nem venda.
- Negativas e condicionais: tratamento conservador; palavras como não, sem, poderá e será impedem afirmar evento realizado. Pronome reflexivo ligado por hífen não é tratado como condicional.
- Risco: só há sinal explicitamente descrito de suspensão, cancelamento, atraso ou paralisação; score não é risco. Prevenção de atraso não confirma atraso.
- Eixo: ao menos duas publicações com links válidos e o mesmo tipo de sinal. URLs repetidas ou título+conteúdo idênticos não multiplicam sinais. O vínculo é temático, não prova causalidade ou independência de fontes.
- Completude: limitada para manchete/trecho curto; parcial a partir de 180 caracteres de corpo, data e link; detalhada a partir de 500 caracteres, data e link. Os dois últimos níveis exigem também pelo menos 12 palavras distintas no corpo que não estejam no título (heurística conservadora para não contar uma manchete longa repetida como conteúdo detalhado). Não é confiança estatística ou veracidade.
- Rastreabilidade: título, fonte, data, trecho de suporte e link; lacunas e próximos passos acompanham a interpretação.

Os padrões cobrem sobretudo português, com algumas expressões inglesas. Não compreendem linguagem livre como um leitor humano; casos desconhecidos devem resultar em informação insuficiente. As frases extraídas podem continuar no idioma original. Regras novas exigem exemplos positivos e negativos.

## Limites e preservação

Não há comparação histórica de eventos nesta entrega; não se afirmam aceleração ou tendências. Valores, prazos e elegibilidade não são estimados nem normalizados automaticamente; precisam de confirmação na fonte. O resumo curto e os cards individuais continuam usando o fluxo anterior; foram melhorados o resumo semanal, a matriz, a leitura transversal e o eixo.

O modo legado mantém a composição anterior; escape HTML e saneamento de links passam a valer nos dois modos. Ao desativar imagens, elementos vazios de imagem deixam de ser renderizados.

Testes: `.venv311_portable/Scripts/python.exe -m unittest discover -s tests -v`.
Os testes de integração substituem somente coleta, tradução externa, cotações e persistência remota por fixtures; não fazem gravações em produção.

O executável existente, banco remoto e configurações privadas não são alterados por esta mudança. O modo normal mantém imagens do feed e o fallback conforme `include_images`; a ausência de imagens nas comparações locais é uma opção exclusiva do teste. Relatórios históricos não são recalculados. A publicação do código atualiza apenas as novas gerações. Um novo build portátil deve ser realizado separadamente para distribuir esta versão em `.exe`. Não afirmar validação de produção a partir dos testes locais.
