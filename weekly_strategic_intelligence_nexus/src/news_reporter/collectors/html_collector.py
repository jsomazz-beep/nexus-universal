from __future__ import annotations

from bs4 import BeautifulSoup

from news_reporter.collectors.base import Collector
from news_reporter.models import NewsItem
from news_reporter.utils.http import http_get_text
from news_reporter.utils.text import clean_html_text, now_utc


class HTMLCollector(Collector):
    """Coletor genérico para páginas estáveis com seletores CSS configuráveis."""

    def collect(self) -> list[NewsItem]:
        source_url = self.source_config["url"]
        timeout = int(self.runtime_config.get("per_source_timeout_seconds", 20))
        retries = int(self.runtime_config.get("retries", 2))
        backoff = int(self.runtime_config.get("retry_backoff_seconds", 2))

        html = http_get_text(
            source_url,
            headers={"User-Agent": self.env.get("HTTP_USER_AGENT", "WeeklyNewsReporter/1.0")},
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff,
        )

        soup = BeautifulSoup(html, "html.parser")
        article_selector = self.source_config.get("article_selector", "article")
        title_selector = self.source_config.get("title_selector", "h1, h2, h3")
        link_selector = self.source_config.get("link_selector", "a")

        base_url = self.source_config.get("base_url", "")
        source_name = self.source_config.get("name", self.source_config.get("id", "html"))

        items: list[NewsItem] = []
        for article in soup.select(article_selector):
            title_node = article.select_one(title_selector)
            link_node = article.select_one(link_selector)
            if not title_node or not link_node:
                continue

            href = (link_node.get("href") or "").strip()
            if href and href.startswith("/") and base_url:
                href = base_url.rstrip("/") + href

            content_text = clean_html_text(str(article))
            items.append(
                NewsItem(
                    source_id=self.source_config.get("id", "html"),
                    source_name=source_name,
                    title=clean_html_text(str(title_node)),
                    subtitle=None,
                    url=href,
                    published_at=None,
                    collected_at=now_utc(),
                    raw_language=None,
                    description=content_text[:500],
                    content=content_text,
                    image_url=None,
                    tags=[],
                    metadata={
                        "source_type": "html",
                        "region_hint": self.source_config.get("region_hint", ""),
                    },
                )
            )

        return items
