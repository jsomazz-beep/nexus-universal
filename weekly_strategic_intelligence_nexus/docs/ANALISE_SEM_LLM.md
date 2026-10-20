# Análise sem LLM — rules-v2

Atualizado em 20/10/2026. O objetivo é produzir uma leitura rastreável do material disponível, sem inventar fatos nem preencher lacunas com respostas genéricas. O motor é um conjunto finito de regras Python; não compreende linguagem livre como um analista humano.

## Ativação

O padrão é `rules`. No bloco `project` do YAML efetivamente carregado, use `analysis_mode: legacy` para recuperar a composição anterior; use `analysis_mode: rules`, ou remova a chave, para a atual. A opção não está no formulário de perfis. Tradução corrigida, escape HTML e links saneados permanecem nos dois modos.

Relatórios salvos conservam seu conteúdo. Gere novamente após uma atualização. `X-Nexus-Analysis-Version: rules-v2` identifica o código instalado no WebApp.

## Tradução antes da análise

O resumo e as regras usam título e corpo traduzidos quando disponíveis. Os originais permanecem nos dados e na evidência expandida. Português detectado não é enviado para retradução. Em tradução parcial, cada campo utiliza o texto disponível; falhas são sinalizadas no relatório e nos avisos da execução.

O fluxo externo de tradução foi corrigido na v2: timeout, cache por execução, rota de contingência e interrupção após falhas consecutivas. Endpoints públicos podem bloquear ou falhar, sem SLA. A identificação de idioma e a qualidade linguística também têm limites. Consulte [operação](ARQUITETURA_E_OPERACAO.md#tradução-e-fontes).

## Resumo, matriz e eixo

| Parte | Critério e interpretação |
| --- | --- |
| Resumo semanal | Consolida sinais e lacunas do conjunto selecionado, com referências; não prevê mercado. |
| Matriz comparativa | Usa assunto, evento, trecho de suporte e perguntas de verificação adequadas ao contexto. |
| Eixo conector | Exige ao menos duas publicações distintas, links válidos e sinal compatível; conexão temática, sem prova causal. |
| Cards | Preservam também itens sem enquadramento específico na matriz, respeitando a seleção do pipeline. |

A matriz diferencia frota/recarga, infraestrutura digital, portos/logística, saneamento, energia, mercado imobiliário, instalações/facilities e infraestrutura física. Distingue entrega de ativo, aprovação citada, investimento com fase não confirmada, indicador setorial, implantação, estudo e debate/diagnóstico.

Conteúdo institucional, premiações e treinamento sem objeto comercial não recebem uma linha genérica de oportunidade. Reconhecer um assunto não confirma demanda contratável. Perguntas setoriais são verificações, não fatos ou riscos comprovados. Mesmo assunto/evento pode legitimamente produzir a mesma orientação; não se variam palavras para simular inteligência.

## Evidência e regras conservadoras

- Estágios: contratação aberta, adjudicação/assinatura, obras, operação/inauguração, anúncio/intenção, suspensão/cancelamento, múltiplos estágios ou não identificado.
- Sinais: editais de manutenção/facilities, expansão/construção e ativos em operação, conforme expressões explícitas. Não confirmam elegibilidade ou venda.
- Negação e condicionais impedem afirmar como realizado um evento não sustentado. O trecho do corpo também importa; título neutro não anula investimento negado no conteúdo.
- Risco exige indicação explícita de suspensão, cancelamento, atraso ou paralisação. Score e prevenção de atraso não comprovam risco ocorrido.
- Entrega de estudo, curso ou financiamento não equivale à entrega de um ativo operacional.
- Valores e percentuais são extraídos literalmente do ORIGINAL. Magnitude deve ser preservada; se não reconhecida, a extração é omitida. Não há conversão, soma nem estimativa de tamanho da oportunidade.
- Evidência inclui título, fonte, data, link, trecho, original e estado de tradução. URLs repetidas ou título e corpo idênticos não multiplicam sinais do eixo.

## Completude do material

“Limitada”, “parcial” e “detalhada” descrevem material recebido, não verdade, confiança estatística ou probabilidade comercial. Manchete repetida no corpo não passa a ser evidência detalhada.

Para “parcial”, a heurística exige corpo com pelo menos 180 caracteres, data, link HTTP(S) válido e ao menos 12 palavras distintas do corpo ausentes do título. “Detalhada” exige pelo menos 500 caracteres, além desses critérios. Conteúdo aquém disso fica limitado. Mesmo material extenso pode estar errado ou ser insuficiente para decisão.

## Limites preservados

Não há comparação histórica estruturada de eventos, cálculo de aceleração nem garantia de cobertura. Regras dependem dos textos disponíveis e têm cobertura finita de expressões. Traduções e inferência geográfica podem errar. Alguns filtros possuem fallback quando zeram a seleção. O histórico local contém metadados de execução, não uma base completa de fatos.

Imagens do feed são exibidas quando disponíveis e habilitadas. O fallback Picsum é ilustrativo e pode não representar a notícia; imagens não sustentam a análise. A ausência de imagens em comparações locais anteriores foi uma opção dos testes.

A publicação web não atualiza o `.exe` já distribuído. A [validação v2](VALIDACAO_CORRECAO_TRADUCAO.md) registra o que foi efetivamente testado e distingue amostras locais de produção.
