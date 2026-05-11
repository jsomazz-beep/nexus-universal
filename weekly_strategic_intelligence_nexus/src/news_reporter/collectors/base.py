from __future__ import annotations

from abc import ABC, abstractmethod

from news_reporter.models import NewsItem


class Collector(ABC):
    def __init__(self, source_config: dict, runtime_config: dict, env: dict[str, str]) -> None:
        self.source_config = source_config
        self.runtime_config = runtime_config
        self.env = env

    @abstractmethod
    def collect(self) -> list[NewsItem]:
        raise NotImplementedError
