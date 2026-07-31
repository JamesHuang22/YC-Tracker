"""Backend-agnostic database interface.

Every storage backend (SQLite today, Supabase later) implements this
interface. Application code only ever imports `Database` and the
`get_database()` factory, so swapping backends is a config change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from yc_tracker.models import Company, HealthCheck, NewsEvent


class Database(ABC):
    # -- lifecycle -----------------------------------------------------
    @abstractmethod
    def init_schema(self) -> None:
        """Create tables if they don't exist."""

    @abstractmethod
    def close(self) -> None: ...

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- companies -----------------------------------------------------
    @abstractmethod
    def upsert_company(self, company: Company) -> None:
        """Insert or update by primary key, preserving created_at."""

    def upsert_companies(self, companies: list[Company]) -> int:
        for company in companies:
            self.upsert_company(company)
        return len(companies)

    @abstractmethod
    def get_company(self, company_id: str) -> Company | None: ...

    @abstractmethod
    def get_company_by_slug(self, slug: str) -> Company | None: ...

    @abstractmethod
    def list_companies(
        self,
        batch: str | None = None,
        status: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Company]: ...

    @abstractmethod
    def count_companies(
        self,
        batch: str | None = None,
        status: str | None = None,
        query: str | None = None,
    ) -> int: ...

    @abstractmethod
    def list_batches(self) -> list[str]: ...

    # -- news events ---------------------------------------------------
    @abstractmethod
    def add_news_event(self, event: NewsEvent) -> NewsEvent: ...

    @abstractmethod
    def list_news_events(self, company_id: str | None = None, limit: int = 100) -> list[NewsEvent]: ...

    # -- health checks ---------------------------------------------------
    @abstractmethod
    def add_health_check(self, check: HealthCheck) -> HealthCheck: ...

    @abstractmethod
    def latest_health_check(self, company_id: str) -> HealthCheck | None: ...
