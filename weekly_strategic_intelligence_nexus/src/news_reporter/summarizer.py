from __future__ import annotations

import logging

from news_reporter.models import NewsItem
from news_reporter.intelligence import analyze, _clean
from news_reporter.translation import ReportTranslator
from news_reporter.utils.text import detect_language_safe
import re

logger = logging.getLogger(__name__)

class Summarizer:
    def __init__(self, output_language: str = "pt") -> None:
        self.output_language = output_language
        self._translator = ReportTranslator(target=output_language)
        self._translation_cache = {}

    def summarize(self, items: list[NewsItem]) -> list[NewsItem]:
        for item in items:
            title = _clean(item.title)
            body = _clean(item.content or item.description or item.normalized_text or item.title)
            language = (item.normalized_language or item.raw_language or '').lower()
            if language in {'', 'unknown', 'any'}:
                language = (detect_language_safe(title + ' ' + body) or 'unknown').lower()
            if language.startswith('pt'):
                item.translated_title_pt, item.translated_content_pt = title, body
                item.translation_status = 'original_pt'
            else:
                item.translated_title_pt = self._translate(title)
                same_words = lambda value: re.sub(r'\W+', '', value.casefold())
                item.translated_content_pt = (item.translated_title_pt if same_words(body) == same_words(title)
                                               else self._translate(body))
                title_ok = same_words(item.translated_title_pt) != same_words(title)
                body_ok = same_words(item.translated_content_pt) != same_words(body)
                item.translation_status = 'translated' if title_ok and body_ok else 'partial' if title_ok or body_ok else 'failed'
                item.metadata['translation'] = {'title_ok': title_ok, 'body_ok': body_ok, 'target': 'pt-BR'}
            base_text_pt = item.translated_content_pt or item.translated_title_pt
            sentences = self._split_sentences(base_text_pt)

            item.short_summary_pt = self._short_summary(sentences)
            item.executive_summary_pt = self._executive_summary(sentences, item)
        return items

    def weekly_synthesis(self, items: list[NewsItem], expected_regions: list[str] | None = None,
                         analysis_mode: str = 'rules') -> dict:
        result = self._legacy_weekly_synthesis(items, expected_regions)
        if analysis_mode != 'legacy':
            analysis = analyze(items, expected_regions)
            result.update(executive_summary=analysis['executive_summary'], analysis=analysis,
                          attention=analysis['attention'],
                          trends=['Conexão temática: ' + analysis['connector']['center']]
                          if analysis['connector']['supported'] else [],
                          opportunities=[s['vector'] + ' — ' + s['implication']
                                         for s in analysis['signals'] if s['signal_types']][:5])
        return result

    def _legacy_weekly_synthesis(self, items: list[NewsItem], expected_regions: list[str] | None = None) -> dict:
        top = sorted(items, key=lambda i: i.score, reverse=True)[:8]

        highlights = [f"{i.translated_title_pt} (score {i.score})" for i in top[:5]]
        opportunities = [
            f"{i.translated_title_pt} -> {', '.join(i.opportunity_types[:2])}"
            for i in top
            if i.opportunity_exists
        ][:5]

        by_region: dict[str, int] = {}
        for item in items:
            by_region[item.region] = by_region.get(item.region, 0) + 1

        expected = expected_regions or sorted(by_region.keys())
        regional_highlights: list[str] = []
        for region in expected:
            region_items = sorted([i for i in items if i.region == region], key=lambda i: i.score, reverse=True)
            if region_items:
                top_item = region_items[0]
                regional_highlights.append(f"{region}: {top_item.translated_title_pt} (score {top_item.score})")
            else:
                regional_highlights.append(f"{region}: sem item aderente nesta janela")

        trends = []
        recurring_terms = self._top_terms(items)
        if recurring_terms:
            trends.append("Assuntos recorrentes: " + ", ".join(recurring_terms))
        if opportunities:
            trends.append("Alta incidência de sinais de oportunidade em contratos, investimento e infraestrutura.")

        attention = []
        if any(item.score < 45 for item in items):
            attention.append("Parte dos itens apresenta baixa densidade informacional; manter revisão humana rápida.")
        if not opportunities:
            attention.append("Não houve sinais fortes de oportunidade nesta janela.")

        return {
            "executive_summary": (
                f"Na semana analisada, {len(items)} notícias aderentes foram selecionadas para "
                f"{', '.join(expected)}. Os maiores sinais estratégicos concentram-se em economia aplicada "
                f"e oportunidades regionais."
            ),
            "highlights": highlights,
            "opportunities": opportunities,
            "trends": trends,
            "attention": attention,
            "regional_movements": [f"{region}: {by_region.get(region, 0)} item(ns)" for region in expected],
            "regional_highlights": regional_highlights,
            "recurring_topics": recurring_terms,
        }

    def _translate(self, text: str) -> str:
        payload = (text or "").strip()
        if not payload:
            return ""

        if self._translator:
            try:
                if not hasattr(self, '_translation_cache'):
                    self._translation_cache = {}
                if payload not in self._translation_cache:
                    translated = self._translator.translate(payload)
                    if not isinstance(translated, str) or not translated.strip():
                        raise ValueError('Invalid translation response')
                    self._translation_cache[payload] = translated.strip()
                return self._translation_cache[payload]
            except Exception as exc:  # noqa: BLE001
                logger.warning("Tradução indisponível (%s); relatório deve sinalizar o trecho original.", type(exc).__name__)
        return payload

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        chunks = [s.strip().rstrip('.!?') for s in re.split(r'(?<=[.!?])\s+', text.replace('\n', ' ')) if s.strip()]
        return chunks

    @staticmethod
    def _short_summary(sentences: list[str]) -> str:
        if not sentences:
            return "Resumo indisponível."
        return (sentences[0] + ".")[:340]

    @staticmethod
    def _executive_summary(sentences: list[str], item: NewsItem) -> str:
        if not sentences:
            return "Resumo executivo indisponível."
        core = ". ".join(sentences[:3])
        anchor = f" Relevância: score {item.score}, região {item.region}, tema(s): {', '.join(item.themes) or 'N/D'}."
        return (core + "." + anchor)[:820]

    @staticmethod
    def _top_terms(items: list[NewsItem]) -> list[str]:
        from collections import Counter

        blacklist = {"de", "da", "do", "e", "em", "para", "com", "na", "no", "a", "o", "as", "os"}
        counter: Counter[str] = Counter()
        for item in items:
            words = [w.lower() for w in item.normalized_text.split() if len(w) > 4]
            for w in words:
                if w not in blacklist:
                    counter[w] += 1
        return [word for word, _ in counter.most_common(6)]
