"""Domain models shared by crawlers, database backends, and the API."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class Company:
    id: str  # "yc-{slug}"
    name: str
    slug: str = ""
    batch: str = ""                     # "Winter 2025", "Summer 2012", ...
    description: str = ""
    one_liner: str = ""
    industry: str = ""
    location: str = ""
    website: str = ""
    yc_url: str = ""
    linkedin_url: str = ""
    founders: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    team_size: int | None = None
    total_funding_usd: int | None = None
    last_funding_round: str = ""
    last_funding_date: str = ""
    status: str = "active"              # active, acquired, dead, public, unknown
    created_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_row(self) -> dict:
        """Flatten list fields to JSON strings for relational storage."""
        row = self.to_dict()
        row["founders"] = json.dumps(self.founders, ensure_ascii=False)
        row["tags"] = json.dumps(self.tags, ensure_ascii=False)
        return row

    @classmethod
    def from_row(cls, row: dict) -> "Company":
        data = dict(row)
        for key in ("founders", "tags"):
            value = data.get(key)
            if isinstance(value, str):
                data[key] = json.loads(value) if value else []
            elif value is None:
                data[key] = []
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known and v is not None})


@dataclass
class NewsEvent:
    company_id: str
    title: str = ""
    url: str = ""
    source: str = ""
    published_at: str = ""
    summary: str = ""
    event_type: str = ""                # funding, acquisition, product_launch, ...
    funding_amount_usd: int | None = None
    id: int | None = None
    created_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HealthCheck:
    company_id: str
    website_reachable: bool = False
    website_status_code: int | None = None
    notes: str = ""
    id: int | None = None
    checked_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WebsiteSnapshot:
    """Result of querying a company's main URL."""
    url: str
    final_url: str = ""
    reachable: bool = False
    status_code: int | None = None
    title: str = ""
    meta_description: str = ""
    error: str = ""
    fetched_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return asdict(self)
