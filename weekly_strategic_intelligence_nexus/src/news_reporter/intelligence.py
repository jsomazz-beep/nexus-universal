"""Análise determinística: evidências explícitas e hipóteses, sem geração por LLM.

As regras classificam o material coletado; não verificam a verdade da publicação.
Não inferem risco a partir de score nem confirmam independência de fontes.
"""
from __future__ import annotations

import html
import re
import unicodedata
from collections import Counter
from urllib.parse import urlsplit, urlunsplit

from news_reporter.models import NewsItem

ANALYSIS_VERSION = 'rules-v1'
METHOD = 'Regras determinísticas v1; sem LLM. Evidência = material publicado, não verificação independente.'


def _clean(value: str | None) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', value or ''))).strip()


def _norm(value: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', value.lower()) if not unicodedata.combining(c))


def _has(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, _norm(text)))


def safe_url(value: str) -> str:
    """Só links navegáveis HTTP(S); nunca javascript/data ou links relativos."""
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme.lower() in {'https', 'http'} and parsed.hostname and not parsed.username:
            return urlunsplit(parsed)
    except ValueError:
        pass
    return ''


def _uncertain(sentence: str) -> bool:
    return (_denied(sentence) or
            _has(sentence, r'\b(podera|poderia|pode|may|might|could|would|will|sera|serao|if|caso|pretende|planeja|previsto|prevista|estuda|planejada|planejado)\b') or
            _has(sentence, r'(?<![-\w])se\b'))


def _denied(sentence: str) -> bool:
    return _has(sentence, r'\b(nao|not|never|sem|without|nenhum|nenhuma)\b')


def _sentences(item: NewsItem) -> list[str]:
    # Campos separados evitam ligar o título a uma ressalva como se fossem uma frase.
    result = []
    for field in (item.title, item.description, item.content):
        for sentence in re.split(r'(?<=[.!?;])\s+|\n+', _clean(field)):
            if sentence and sentence not in result:
                result.append(sentence)
    return result


def inspect_item(item: NewsItem) -> dict:
    sentences = _sentences(item)
    factual = [s for s in sentences if not _uncertain(s)]
    gaps = []
    if len(factual) < len(sentences):
        gaps.append('Há linguagem condicional ou negativa; o trecho não confirma o evento positivo.')
    body = _clean(item.content or item.description)
    title_words = set(re.findall(r'\w+', _norm(_clean(item.title))))
    novel_words = set(re.findall(r'\w+', _norm(body))) - title_words
    has_body_detail = len(novel_words) >= 12
    url = safe_url(item.url)
    if len(body) < 180 or not has_body_detail:
        gaps.append('Conteúdo curto ou apenas manchete; confirmar detalhes na publicação original.')
    if not item.published_at:
        gaps.append('Data de publicação não informada.')
    if not url:
        gaps.append('Link HTTP(S) válido da publicação não disponível.')

    cancelled = [s for s in factual if _has(s, r'\b(cancelad[ao]s?|suspens[ao]s?|cancelled|canceled|suspended)\b')]
    procurement = [s for s in factual if _has(s, r'\b(edital|licitac[aã]o|tender|bidding)\b') and
                   _has(s, r'\b(publicad[ao]s?|abert[ao]s?|abriu|lancad[ao]s?|publica|abre|opened|published)\b')]
    awarded = [s for s in factual if _has(s, r'\b(contrato|contract|licitacao)\b') and
               _has(s, r'\b(assinad[ao]|adjudicad[ao]|homologad[ao]|signed|awarded)\b')]
    operating = [s for s in factual if _has(s, r'\b(inauguracao|inaugurad[ao]|entrou em operacao|iniciou as operacoes|began operations|opened facility)\b')]
    works = [s for s in factual if _has(s, r'\b(obras? iniciad[ao]s?|iniciou a construcao|em construcao|under construction)\b')]
    announced = [s for s in sentences if not _denied(s) and
                 _has(s, r'\b(anuncia|anunciou|anunciad[ao]|preve|pretende|planeja|announces|plans)\b')]
    stages = [(name, evidence) for name, evidence in (
        ('Contratação aberta', procurement), ('Contrato adjudicado/assinado', awarded),
        ('Operação/inauguração', operating), ('Obras em andamento', works)) if evidence]
    if cancelled:
        stage = 'Suspenso/cancelado'
    elif len(stages) > 1:
        stage = 'Múltiplos estágios mencionados'
        gaps.append('O texto cita estágios diferentes; confirmar a qual projeto/contrato cada um se refere.')
    elif stages:
        stage = stages[0][0]
    elif announced:
        stage = 'Anúncio/intenção'
    else:
        stage = 'Não identificado'
        gaps.append('Estágio não confirmado por expressão explícita nas regras disponíveis.')

    maintenance_pattern = r'\b(manutencao|facilities|limpeza|maintenance|facility management|operacao e manutencao)\b'
    asset_pattern = r'\b(hospital|fabrica|planta|terminal|instalac[aoe]+s?|infraestrutura|saneamento|facility|plant)\b'
    expansion_pattern = r'\b(construcao|expansao|ampliacao|construction|expansion)\b'
    signals = []
    matched = []
    if stage == 'Contratação aberta' and any(_has(s, maintenance_pattern) for s in procurement):
        signals.append('services_procurement')
        matched.extend(s for s in procurement if _has(s, maintenance_pattern))
    if stage not in {'Suspenso/cancelado', 'Múltiplos estágios mencionados'}:
        expansion = [s for s in sentences if not _denied(s) and (s in factual or s in announced) and
                     _has(s, asset_pattern) and _has(s, expansion_pattern)]
        if expansion:
            signals.append('asset_expansion')
            matched.extend(expansion)
        if operating and any(_has(s, asset_pattern) for s in operating):
            signals.append('asset_operation')
            matched.extend(s for s in operating if _has(s, asset_pattern))
    delays = [s for s in factual if _has(s, r'\b(atraso|atrasos|paralisacao|delay|delays)\b') and
              not _has(s, r'\b(evitar|prevenir|reduzir|mitigar|risco de|possibilidade de|prevent|avoid|risk of)\b')]
    risks = cancelled + delays
    if risks:
        risk = 'Sinal explícito no material: ' + ' | '.join(risks[:2])
    else:
        risk = 'Não identificado no material pelas regras atuais; isso não indica ausência de risco.'
    if stage == 'Suspenso/cancelado':
        implication = 'Inferência: a suspensão/cancelamento pode restringir a oportunidade; verificar alcance e vigência.'
        action = 'Verificar o ato oficial e eventual reabertura antes de prospectar.'
    elif 'services_procurement' in signals:
        implication = 'Hipótese comercial: o objeto pode ser aderente a serviços de manutenção/facilities; não comprova elegibilidade nem venda.'
        action = 'Verificar edital, prazo, requisitos, objeto e capacidade de atendimento antes de decidir participar.'
    elif 'asset_expansion' in signals:
        implication = 'Hipótese: a expansão do ativo pode gerar demanda futura por serviços; anúncio não equivale a contratação disponível.'
        action = 'Identificar responsável, estágio real, escopo e canal de compras; acompanhar confirmação do investimento.'
    elif 'asset_operation' in signals:
        implication = 'Hipótese: o ativo em operação pode demandar serviços recorrentes; verificar contratos já existentes e acesso comercial.'
        action = 'Mapear operador e contratos vigentes antes de avaliar prospecção.'
    else:
        implication = 'Não há base suficiente nas regras atuais para atribuir uma implicação comercial específica.'
        action = 'Revisar a fonte e confirmar aderência ao negócio antes de priorizar.'
    gaps.append('Prazo comercial e dimensão da oportunidade exigem confirmação na fonte; não estimados automaticamente.')
    quality = 'Detalhada' if len(body) >= 500 and has_body_detail and url and item.published_at else (
        'Parcial' if len(body) >= 180 and has_body_detail and url and item.published_at else 'Limitada')
    excerpt = (matched or cancelled or [s for _, ev in stages for s in ev] or sentences or ['Conteúdo indisponível.'])[0]
    evidence = {'title': _clean(item.translated_title_pt or item.title), 'source': _clean(item.source_name),
                'url': url, 'date': item.published_at.strftime('%d/%m/%Y') if item.published_at else 'N/D',
                'excerpt': excerpt[:600]}
    return {'region': item.region, 'vector': evidence['title'], 'stage': stage, 'risk': risk,
            'implication': implication, 'action': action, 'evidence_quality': quality,
            'gaps': gaps, 'evidence': [evidence], 'signal_types': signals,
            'horizon': 'A confirmar na fonte', 'score': item.score}


def analyze(items: list[NewsItem], expected_regions: list[str] | None = None) -> dict:
    signals = []
    seen = set()
    seen_content = set()
    for item in sorted(items, key=lambda i: i.score, reverse=True):
        key = safe_url(item.url).rstrip('/') or (item.region, _norm(_clean(item.title)))
        content_key = (_norm(_clean(item.title)), _norm(_clean(item.content or item.description)))
        if key in seen or content_key in seen_content:
            continue
        seen.add(key)
        seen_content.add(content_key)
        signals.append(inspect_item(item))
    expected = list(dict.fromkeys(expected_regions or [s['region'] for s in signals]))
    uncovered = [region for region in expected if not any(s['region'] == region for s in signals)]
    qualified = [s for s in signals if s['signal_types']]
    counts = Counter(s['stage'] for s in signals)
    summary = 'Material insuficiente para uma síntese estratégica nesta janela.'
    if signals:
        distribution = '; '.join(f'{stage}: {number}' for stage, number in counts.items())
        summary = f'Nesta janela, {len(signals)} publicações distintas por URL/título foram analisadas. Estágios identificados: {distribution}. '
        if qualified:
            top = qualified[0]
            summary += f"Sinal para verificação: {top['vector']} ({top['region']}). {top['implication']} {top['action']}"
        else:
            summary += 'Não foi identificada combinação suficiente de sinais para uma implicação comercial específica; revisar as fontes antes de decidir.'
    groups = {
        'services_procurement': ('Contratação de serviços', 'Editais citam serviços de manutenção/facilities.',
                                 'Hipótese: há objetos potencialmente aderentes em mais de uma publicação; verificar elegibilidade e prazos individualmente.'),
        'asset_expansion': ('Expansão de ativos', 'As publicações mencionam construção/ampliação de ativos.',
                            'Hipótese: a expansão pode abrir demanda futura por serviços; depende de investimento efetivado, cronograma e modelo de contratação.'),
        'asset_operation': ('Ativos em operação', 'As publicações mencionam inauguração ou início de operação.',
                            'Hipótese: os ativos podem demandar serviços recorrentes; a oportunidade depende dos contratos e operadores existentes.'),
    }
    connector = {'supported': False, 'left': 'Evidências insuficientes para um eixo comum.',
                 'right': 'Não forçar uma relação entre notícias sem sinais compatíveis.',
                 'bottom': 'Revisar fontes e ampliar o material coletado.',
                 'center': 'Não foi identificado eixo comum suficientemente sustentado nesta edição.', 'evidence': []}
    best = max(groups, key=lambda g: sum(g in s['signal_types'] and bool(s['evidence'][0]['url']) for s in signals))
    related = [s for s in signals if best in s['signal_types'] and s['evidence'][0]['url']]
    if len(related) >= 2:
        label, mechanism, implication = groups[best]
        connector = {'supported': True, 'left': f'{label}: {len(related)} publicações distintas por URL.',
                     'right': mechanism, 'bottom': 'Conexão temática por regra; não comprova causalidade nem confirmação por fontes independentes.',
                     'center': implication, 'evidence': [s['evidence'][0] for s in related[:6]]}
    attention = ['Sem comparação com histórico estruturado: não se infere aceleração, crescimento ou tendência temporal.',
                 'Qualidade da evidência descreve completude do material; não é probabilidade nem verificação de veracidade.']
    if uncovered:
        attention.append('Sem cobertura aderente no recorte: ' + ', '.join(uncovered) + '; não significa ausência de atividade nesses mercados.')
    if any(s['evidence_quality'] == 'Limitada' for s in signals):
        attention.append('Há notícias com informação limitada; as hipóteses precisam de confirmação na fonte.')
    return {'method': METHOD, 'signals': signals, 'executive_summary': summary,
            'comparative_rows': signals, 'connector': connector, 'attention': attention,
            'uncovered_regions': uncovered}
