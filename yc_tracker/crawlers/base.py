"""Crawler interface + registry.

To integrate a new crawler (e.g. a16z, Sequoia, Product Hunt):

    from yc_tracker.crawlers.base import BaseCrawler, register

    @register
    class MyCrawler(BaseCrawler):
        name = "my-source"

        def crawl(self, **kwargs):
            yield Company(...)

It then shows up in `list_crawlers()` and `python -m yc_tracker crawl --source my-source`.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Iterator, Type

import httpx

from yc_tracker import config
from yc_tracker.models import Company

_REGISTRY: dict[str, Type["BaseCrawler"]] = {}


def register(cls: Type["BaseCrawler"]) -> Type["BaseCrawler"]:
    if not cls.name:
        raise ValueError(f"{cls.__name__} must define a `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get_crawler(name: str) -> "BaseCrawler":
    if name not in _REGISTRY:
        raise KeyError(f"Unknown crawler {name!r}. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[name]()


def list_crawlers() -> list[str]:
    return sorted(_REGISTRY)


class BaseCrawler(ABC):
    """A crawler produces Company records from some external source."""

    name: str = ""

    def __init__(self):
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=config.HTTP_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": random.choice(config.USER_AGENTS)},
            )
        return self._client

    def rotate_user_agent(self) -> None:
        self.client.headers["User-Agent"] = random.choice(config.USER_AGENTS)

    @abstractmethod
    def crawl(self, **kwargs) -> Iterator[Company]:
        """Yield Company records from the source."""

    def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            self._client.close()

    def __enter__(self) -> "BaseCrawler":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
