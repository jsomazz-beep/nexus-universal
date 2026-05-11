"""Nexus Intelligence — summarizer with optional Gemini AI."""
from __future__ import annotations

import logging
from collections import Counter

from nexus.models import NewsItem, TopicSynthesis, RegionalSynthesis

logger = logging.getLogger(__name__)

try:
    from deep_translator import GoogleTranslator  # type: ignore
except ImportError:
    GoogleTranslator = None  # type: ignore

try:
    import google.generativeai as genai  # type: ignore
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


class Summarizer:
    def __init__(self, output_language: str = "pt", gemini_api_key: str = "") -> None:
        self.output_language = output_language
        self._translator = None
        self._gemini = None

        if output_language != "en" and GoogleTranslator:
            try:
                self._translator = GoogleTranslator(source="auto", target=output_language)
            except Exception as exc:
                logger.warning("Translator init failed: %s", exc)

        if gemini_api_key and _GENAI_AVAILABLE:
            try:
                genai.configure(api_key=gemini_api_key)
                self._gemini = genai.GenerativeModel("gemini-1.5-flash")
                logger.info("Gemini AI summaries enabled")
            except Exception as exc:
                logger.warning("Gemini init failed: %s", exc)

    def summarize(self, items: list[NewsItem]) -> list[NewsItem]:
        for item in items:
            item.translated_title = self._translate(item.title)
            base_text = self._translate(item.normalized_text or item.title)
            sentences = [s.strip() for s in base_text.replace("\n", " ").split(".") if s.strip()]
            item.short_summary = self._short(sentences)
            if self._gemini:
                item.ai_summary = self._gemini_summary(item)
        return items

    def build_topic_syntheses(self, items: list[NewsItem], topics_cfg: dict) -> list[TopicSynthesis]:
        by_topic: dict[str, list[NewsItem]] = {}
        for item in items:
            for topic in item.topics:
                by_topic.setdefault(topic, []).append(item)

        syntheses: list[TopicSynthesis] = []
        for topic_name, topic_data in topics_cfg.items():
            topic_items = sorted(by_topic.get(topic_name, []), key=lambda x: x.score, reverse=True)
            if not topic_items:
                continue
            insight = self._topic_insight(topic_name, topic_items)
            syntheses.append(TopicSynthesis(
                topic=topic_name,
                icon=topic_data.get("icon", "📰"),
                color=topic_data.get("color", "#6366f1"),
                count=len(topic_items),
                top_items=topic_items[:5],
                key_insight=insight,
            ))

        return sorted(syntheses, key=lambda s: s.count, reverse=True)

    def build_regional_syntheses(self, items: list[NewsItem], regions: list[str]) -> list[RegionalSynthesis]:
        by_region: dict[str, list[NewsItem]] = {}
        for item in items:
            by_region.setdefault(item.region, []).append(item)

        syntheses: list[RegionalSynthesis] = []
        for region in regions:
            region_items = sorted(by_region.get(region, []), key=lambda x: x.score, reverse=True)
            count = len(region_items)
            signal = "low" if count < 3 else "moderate" if count < 10 else "high" if count < 20 else "critical"
            syntheses.append(RegionalSynthesis(
                region=region,
                count=count,
                top_items=region_items[:4],
                signal_strength=signal,
            ))
        return syntheses

    def _topic_insight(self, topic: str, items: list[NewsItem]) -> str:
        all_words: list[str] = []
        for item in items[:10]:
            words = [w.lower() for w in item.normalized_text.split() if len(w) > 5]
            all_words.extend(words)
        stopwords = {"de", "da", "do", "e", "em", "para", "com", "na", "no", "a", "o", "as", "os",
                     "the", "and", "for", "in", "of", "to", "is", "are", "that", "this"}
        counter = Counter(w for w in all_words if w not in stopwords)
        top = [w for w, _ in counter.most_common(4)]
        if top:
            return f"Termos recorrentes: {', '.join(top)}."
        return ""

    def _gemini_summary(self, item: NewsItem) -> str:
        prompt = (
            f"Resuma em 2 frases (max 200 chars) em português esta notícia:\n"
            f"Título: {item.title}\n"
            f"Texto: {item.normalized_text[:600]}"
        )
        try:
            resp = self._gemini.generate_content(prompt)
            return (resp.text or "").strip()[:300]
        except Exception as exc:
            logger.debug("Gemini summary failed: %s", exc)
            return ""

    def _translate(self, text: str) -> str:
        text = (text or "").strip()
        if not text or not self._translator:
            return text
        try:
            return self._translator.translate(text[:4000]) or text
        except Exception:
            return text

    @staticmethod
    def _short(sentences: list[str]) -> str:
        if not sentences:
            return "Resumo indisponível."
        return (sentences[0] + ".")[:320]
