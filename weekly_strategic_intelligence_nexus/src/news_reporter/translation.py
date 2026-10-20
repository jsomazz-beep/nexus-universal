"""Bounded, cached translation of public news; no LLM or API key.

The public Google endpoints have no availability/quality guarantee. Failure is
propagated to the report instead of pretending the original is a translation.
"""
from __future__ import annotations

import re
import requests
from bs4 import BeautifulSoup


class TranslationUnavailable(RuntimeError):
    pass


class ReportTranslator:
    def __init__(self, target='pt', fallback=None, timeout=(4, 8)):
        self.target = 'pt' if target.lower().replace('_', '-') in {'pt', 'pt-br'} else target
        self.fallback = fallback
        self.timeout = timeout
        self.cache = {}
        self.failures = 0

    def translate(self, text: str) -> str:
        if text in self.cache:
            return self.cache[text]
        if self.failures >= 2:
            raise TranslationUnavailable('Translation temporarily unavailable for this report')
        chunks = re.findall(r'.{1,3500}(?:\s+|$)|.{1,3500}', text, flags=re.S)
        try:
            translated = ' '.join(self._translate_chunk(chunk.strip()) for chunk in chunks if chunk.strip())
            if not translated or translated.casefold() == text.strip().casefold():
                raise TranslationUnavailable('Service returned unchanged content')
        except Exception:
            self.failures += 1
            raise
        self.failures = 0
        self.cache[text] = translated
        return translated

    def _translate_chunk(self, text: str) -> str:
        try:
            response = requests.get('https://translate.googleapis.com/translate_a/single',
                params={'client':'gtx','sl':'auto','tl':self.target,'hl':'pt-BR','dt':'t','q':text},
                timeout=self.timeout)
            if response.status_code != 200:
                raise TranslationUnavailable('Translation HTTP ' + str(response.status_code))
            payload = response.json()
            result = ''.join(segment[0] or '' for segment in payload[0])
            if result and result.casefold() != text.casefold():
                return result
        except (requests.RequestException, ValueError, TypeError, IndexError, TranslationUnavailable):
            pass
        if self.fallback is not None:
            return self.fallback.translate(text)
        response = requests.get('https://translate.google.com/m',
            params={'sl':'auto','tl':self.target,'hl':'pt-BR','q':text}, timeout=self.timeout)
        if response.status_code != 200:
            raise TranslationUnavailable('Fallback translation HTTP ' + str(response.status_code))
        soup = BeautifulSoup(response.text, 'html.parser')
        element = soup.select_one('.result-container, .t0')
        if element is None:
            raise TranslationUnavailable('Fallback translation not found')
        return element.get_text(' ', strip=True)
