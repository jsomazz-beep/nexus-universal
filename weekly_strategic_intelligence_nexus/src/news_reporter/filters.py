from __future__ import annotations

import re
from datetime import timedelta

from news_reporter.models import NewsItem
from news_reporter.utils.text import normalize_for_match, now_utc


class FilterEngine:
    def __init__(self, filters_cfg: dict, monitoring_cfg: dict) -> None:
        self.filters_cfg = filters_cfg
        self.monitoring_cfg = monitoring_cfg

    def apply(self, items: list[NewsItem]) -> tuple[list[NewsItem], list[str]]:
        logs: list[str] = []
        current = items
        strict_priority = bool(self.filters_cfg.get("strict_priority_keyword_match", False))

        current = self._layer_time_language_integrity(current, logs)
        current = self._with_fallback(current, self._layer_region, logs, "região")
        current = self._with_fallback(current, self._layer_theme, logs, "tema")
        if strict_priority:
            current = self._layer_keyword_or_opportunity(current, logs)
        else:
            current = self._with_fallback(current, self._layer_keyword_or_opportunity, logs, "keywords/oportunidade")
        current = self._layer_negative_keywords(current, logs)

        return current, logs

    @staticmethod
    def _with_fallback(
        items: list[NewsItem],
        layer_fn,
        logs: list[str],
        layer_name: str,
    ) -> list[NewsItem]:
        filtered = layer_fn(items, logs)
        if items and not filtered:
            logs.append(
                f"Fallback camada {layer_name}: resultado zerado; mantendo {len(items)} item(ns) da camada anterior."
            )
            return items
        return filtered

    def _layer_time_language_integrity(self, items: list[NewsItem], logs: list[str]) -> list[NewsItem]:
        days = int(self.filters_cfg.get("time_window_days", 7))
        accepted_languages = [lang.lower() for lang in self.filters_cfg.get("accepted_languages", ["any"])]
        min_text_len = int(self.filters_cfg.get("min_text_length", 80))
        min_fields = self.filters_cfg.get("minimum_fields", ["title", "url", "published_at"])

        limit = now_utc() - timedelta(days=days)
        output: list[NewsItem] = []

        for item in items:
            if "title" in min_fields and not item.title:
                continue
            if "url" in min_fields and not item.url:
                continue
            if "published_at" in min_fields and not item.published_at:
                continue
            if item.published_at and item.published_at < limit:
                continue

            if "any" not in accepted_languages and item.normalized_language not in accepted_languages:
                continue

            if len(item.normalized_text) < min_text_len:
                continue

            output.append(item)

        logs.append(f"Camada1(time/lang/integridade): {len(items)} -> {len(output)}")
        return output

    def _layer_region(self, items: list[NewsItem], logs: list[str]) -> list[NewsItem]:
        regions = [str(r).strip() for r in self.monitoring_cfg.get("regions", []) if str(r).strip()]
        regions_set = set(regions)
        region_aliases_cfg = self.monitoring_cfg.get("region_aliases", {})
        subregion_terms = [
            normalize_for_match(str(t).strip())
            for t in self.monitoring_cfg.get("subregion_terms", [])
            if str(t).strip()
        ]

        expanded_aliases_by_region: dict[str, list[str]] = {}
        for region in regions:
            aliases: list[str] = [region]
            aliases.extend(region_aliases_cfg.get(region, []))
            expanded_aliases_by_region[region] = [
                normalize_for_match(str(a).strip())
                for a in aliases
                if str(a).strip()
            ]

        output: list[NewsItem] = []
        for item in items:
            if item.region in regions_set:
                output.append(item)
                continue

            blob = normalize_for_match(
                " ".join(
                    [
                        item.title or "",
                        item.description or "",
                        item.content or "",
                        item.url or "",
                        str(item.metadata.get("region_hint", "")),
                    ]
                )
            )

            matched_region = False
            for aliases in expanded_aliases_by_region.values():
                for alias in aliases:
                    if not alias:
                        continue
                    if len(alias) <= 3:
                        if re.search(rf"\b{re.escape(alias)}\b", blob):
                            matched_region = True
                            break
                    elif alias in blob:
                        matched_region = True
                        break
                if matched_region:
                    break

            if matched_region:
                output.append(item)
                continue

            if subregion_terms and any(term and term in blob for term in subregion_terms):
                output.append(item)

        logs.append(f"Camada2(região): {len(items)} -> {len(output)}")
        return output

    def _layer_theme(self, items: list[NewsItem], logs: list[str]) -> list[NewsItem]:
        valid_themes = set(self.monitoring_cfg.get("themes", {}).keys())
        output = [
            i
            for i in items
            if any(theme in valid_themes for theme in i.themes)
            or i.detected_keywords
            or i.detected_associated_keywords
            or i.opportunity_types
        ]
        logs.append(f"Camada3(tema): {len(items)} -> {len(output)}")
        return output

    def _layer_keyword_or_opportunity(self, items: list[NewsItem], logs: list[str]) -> list[NewsItem]:
        strict_priority = bool(self.filters_cfg.get("strict_priority_keyword_match", False))
        if strict_priority:
            output = [i for i in items if i.detected_keywords]
            logs.append(f"Camada4(keywords estritas): {len(items)} -> {len(output)}")
            return output

        output = [i for i in items if i.detected_keywords or i.detected_associated_keywords or i.opportunity_types]
        logs.append(f"Camada4(keywords/oportunidade): {len(items)} -> {len(output)}")
        return output

    def _layer_negative_keywords(self, items: list[NewsItem], logs: list[str]) -> list[NewsItem]:
        negatives = [k.lower() for k in self.monitoring_cfg.get("negative_keywords", [])]
        if not negatives:
            logs.append(f"Camada5(negativas): {len(items)} -> {len(items)}")
            return items

        output: list[NewsItem] = []
        for item in items:
            text = item.normalized_text.lower()
            if any(neg in text for neg in negatives):
                continue
            output.append(item)

        logs.append(f"Camada5(negativas): {len(items)} -> {len(output)}")
        return output
