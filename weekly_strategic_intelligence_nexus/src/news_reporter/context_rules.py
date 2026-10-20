"""Sector-specific questions and conditional readings, never inferred facts."""
from __future__ import annotations
import re
import unicodedata


def norm(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


# pattern, label, conditional business mechanism, concrete checks
TOPICS = {
    'fleet': (r'\b(frota|recarga|carregamento|eletrificad\w*|fleet|charging|electric vehicles|veiculos eletricos)\b',
        'Frota e recarga', 'manutenção de veículos, disponibilidade da frota e operação dos pontos de recarga',
        'Identificar operador da frota e da recarga, plano de implantação e contratos de manutenção; confirmar se há compras acessíveis.'),
    'digital': (r'\b(data centers?|datacenters?|centros? de dados|infraestrutura de ia|ai infrastructure|gpt|openai|hiperescala|hyperfusion)\b',
        'Infraestrutura digital', 'infraestrutura elétrica, climatização, disponibilidade e suporte das instalações de TI',
        'Confirmar localização e fase da infraestrutura digital, operador e escopo físico; distinguir contratação de software de serviços de facilities.'),
    'logistics': (r'\b(portos?|portuario\w*|ferrovi\w*|railway|railroad|logistic\w*|terminal|terminais)\b',
        'Portos e logística', 'manutenção de ativos portuários/logísticos e continuidade operacional',
        'Identificar porto, terminal ou ferrovia, dono do ativo e modelo de concessão; consultar cronograma e canal de compras do projeto.'),
    'water': (r'\b(saneamento|sanitation|wastewater|water|agua|aguas|drenagem|tarifa social)\b',
        'Saneamento e água', 'operação de redes/instalações, manutenção e acompanhamento de metas de saneamento',
        'Identificar concessionária ou órgão de saneamento, obrigação ou ativo citado; procurar plano de obras, contrato ou edital específico.'),
    'energy': (r'\b(energia|energetic\w*|energy|petroleo|oil|gas|solar|power)\b',
        'Energia', 'manutenção de instalações energéticas, segurança e continuidade de fornecimento',
        'Identificar instalação energética, operador, fase e requisitos de segurança; confirmar escopo e contratos antes de prospectar.'),
    'property': (r'\b(imobiliari\w*|real estate|imoveis|imovel)\b',
        'Mercado imobiliário', 'gestão e manutenção dos imóveis associados a transações efetivas',
        'Verificar quais imóveis, gestores e transações compõem o dado; volume de investimento imobiliário não equivale a orçamento disponível para facilities.'),
    'facilities': (r'\b(hospital\w*|manutencao|maintenance|facilities|facility|predial|edific\w*|fabrica|plant|instalac\w*|praias|parques|beaches|parks)\b',
        'Instalações e facilities', 'manutenção predial, operação e conservação dos ativos mencionados',
        'Identificar instalações e operador, contratos vigentes e modelo de conservação; confirmar escopo técnico e possibilidade de contratação.'),
    'infrastructure': (r'\b(infraestrutura|infrastructure|pavimentacao|encosta|rodovi\w*|estrada\w*|obras)\b',
        'Infraestrutura física', 'operação e conservação da infraestrutura física citada',
        'Identificar obra, local e órgão responsável, situação de entrega e obrigações de conservação; verificar contratos e licitações associados.'),
}


def quantities_from_text(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(
        r'(?:US\$|R\$|USD|EUR|\$|€)\s*\d+(?:[.,]\d+)*(?:\s*(?:(?:mil\s+)?milhões|milhão|bilhões|bilhão|trilhões|trilhão|milhoes|milhao|bilhoes|bilhao|trilhoes|trilhao|mil|thousand|billion|million|trillion|bn|tn|trn|mn|[kmb])\b)?(?!\w|[.,]\d)(?!\s+(?:\w*ilh[ãõa]\w*|\w*illion|bn|tn|trn|mn)\b)'
        r'|\b\d+(?:[.,]\d+)*\s*(?:(?:mil\s+)?milhões|milhão|bilhões|bilhão|trilhões|trilhão|milhoes|milhao|bilhoes|bilhao|trilhoes|trilhao|million|billion|trillion)\s+(?:de\s+)?(?:euros|dólares|dolares|reais)'
        r'|\b\d+(?:[.,]\d+)*\s*%', text, flags=re.I)))[:4]


def context_for(text: str, title: str, factual: list[str], stage: str, quantities: list[str] | None = None) -> dict:
    normalized = norm(text)
    topic_key = next((key for key, spec in TOPICS.items() if re.search(spec[0], normalized)), None)
    if quantities is None:
        quantities = quantities_from_text(text)
    if topic_key is None:
        return {'topic': 'Sem enquadramento específico', 'topic_key': None, 'quantities': quantities,
                'matrix_eligible': False, 'event': None, 'extra_signals': []}
    _, label, mechanism, action = TOPICS[topic_key]
    positive = ' '.join(factual)
    excluded_kind = bool(re.search(r'\b(melhor empregadora|best employer|premio|premiada|award|oferece novos cursos|cursos sobre|curso de)\b', normalized))
    investment_sentences = [s for s in factual if re.search(r'\b(investimento|investment|investments|investira|investir)\b', norm(s))]
    completion_sentences = [s for s in factual if re.search(r'\b(conclui|concluiu|concluid\w*|entrega|entregou|completes|completed|delivered)\b', norm(s))
        and re.search(r'\b(obras?|projetos?|projects?|instalac\w*|edific\w*|facilit\w*|parks?|parques?|terminal|ferrovia|railway)\b', norm(s))
        and not re.search(r'\b(estudo|estudos|curso|cursos|formacao|study|studies|report|relatorio|course|financiamento|acordo|deal|financing)\b', norm(s))]
    event = None
    extra_signals = []
    if stage == 'Não identificado':
        if completion_sentences:
            event = 'Entrega/conclusão citada'
        elif re.search(r'\b(aprova|aprovou|aprovad\w*|approves|approved)\b', norm(positive)):
            event = 'Aprovação citada'
        elif investment_sentences:
            event = 'Investimento citado; fase a confirmar'
        elif re.search(r'\b(cresce|crescimento|alta|atinge|triplica|growth|grows|increase|increases|supera|representam|concentram)\b', norm(positive)):
            event = 'Indicador setorial citado'
        elif re.search(r'\b(implantacao|deployment|implanta|implementacao)\b', norm(positive)):
            event = 'Implantação citada'
        elif re.search(r'\b(estudo|estudos|study|studies|levantamento|survey)\b', norm(positive)):
            event = 'Estudo/levantamento citado'
        elif re.search(r'\b(debate|debate\w*|cobra|pede|diz|insights|formacao|cursos|resiliencia)\b', normalized):
            event = 'Debate/diagnóstico setorial'
    effective_stage = event or stage
    observed = f'Leitura contextual — {label.lower()}: '
    # The mechanism is hypothetical even when the published event is affirmative.
    if effective_stage == 'Entrega/conclusão citada':
        implication = observed + f'a entrega citada sugere verificar o ciclo de {mechanism}; não confirma serviços disponíveis para contratação.'
        if topic_key in {'facilities', 'infrastructure', 'logistics', 'energy'}:
            extra_signals.append('asset_operation')
    elif effective_stage in {'Investimento citado; fase a confirmar', 'Aprovação citada', 'Anúncio/intenção'}:
        implication = observed + f'o investimento/anúncio pode afetar {mechanism}; a notícia não comprova orçamento comercial acessível.'
        if any(not re.search(r'\b(nao|not|sem|without|pode|podera|will|may|if)\b', norm(s)) and
               re.search(r'\b(investimento|investment|investments)\b', norm(s)) for s in factual):
            if topic_key in {'fleet', 'logistics', 'energy', 'digital'}:
                extra_signals.append(topic_key + '_investment')
    elif effective_stage == 'Indicador setorial citado':
        implication = observed + f'o indicador ajuda a monitorar o mercado de {mechanism}; crescimento agregado não identifica comprador nem contrato.'
    elif effective_stage == 'Debate/diagnóstico setorial':
        implication = observed + f'o diagnóstico orienta acompanhamento de {mechanism}; não caracteriza uma contratação ou projeto confirmado.'
    elif effective_stage == 'Implantação citada':
        implication = observed + f'a implantação pode envolver {mechanism}; confirmar o que é infraestrutura física e o que é apenas solução tecnológica.'
    elif effective_stage == 'Estudo/levantamento citado':
        implication = observed + 'o material apresenta um estudo/levantamento; não descreve entrega ou início de operação de um ativo.'
        action = f'Checar método, universo e período de referência do estudo de {label.lower()}; confrontar dados com fontes primárias antes de tomar decisões.'
    else:
        implication = observed + 'o tema foi identificado, mas o material não caracteriza um projeto ou compra; não é possível atribuir demanda por serviços a partir desse trecho.'
    if quantities:
        implication += ' Dados citados (como publicados): ' + '; '.join(quantities) + '.'
    if not factual and stage == 'Não identificado':
        event = 'Evento não confirmado (negativo/condicional)'
        implication = observed + 'o trecho contém linguagem negativa ou condicional e não confirma a realização do evento; verificar a condição descrita na fonte.'
        extra_signals = []
    if topic_key == 'property':
        question = 'A confirmar: identidade dos imóveis/gestores e relação do indicador com contratos de serviços.'
    else:
        question = f'A confirmar em {label.lower()}: operador/comprador, escopo acessível e estágio real; não é um risco já comprovado.'
    return {'topic': label, 'topic_key': topic_key, 'quantities': quantities, 'matrix_eligible': not excluded_kind,
            'event': event, 'extra_signals': extra_signals, 'implication': implication,
            'action': action, 'verification': question}
