"""SQLite implementation of the Database interface."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from yc_tracker.db.base import Database
from yc_tracker.models import Company, HealthCheck, NewsEvent, utcnow

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT,
    batch TEXT,
    description TEXT,
    one_liner TEXT,
    industry TEXT,
    location TEXT,
    website TEXT,
    yc_url TEXT,
    linkedin_url TEXT,
    founders TEXT,
    tags TEXT,
    team_size INTEGER,
    total_funding_usd INTEGER,
    last_funding_round TEXT,
    last_funding_date TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT REFERENCES companies(id),
    title TEXT,
    url TEXT,
    source TEXT,
    published_at TIMESTAMP,
    summary TEXT,
    event_type TEXT,
    funding_amount_usd INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS health_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT REFERENCES companies(id),
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    website_reachable BOOLEAN,
    website_status_code INTEGER,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_companies_batch ON companies(batch);
CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status);
CREATE INDEX IF NOT EXISTS idx_news_company ON news_events(company_id);
CREATE INDEX IF NOT EXISTS idx_health_company ON health_checks(company_id);
"""

COMPANY_COLUMNS = [
    "id", "name", "slug", "batch", "description", "one_liner", "industry",
    "location", "website", "yc_url", "linkedin_url", "founders", "tags",
    "team_size", "total_funding_usd", "last_funding_round",
    "last_funding_date", "status", "created_at", "updated_at",
]


class SQLiteDatabase(Database):
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # -- companies -----------------------------------------------------
    def upsert_company(self, company: Company) -> None:
        row = company.to_row()
        row["updated_at"] = utcnow()
        placeholders = ", ".join(f":{c}" for c in COMPANY_COLUMNS)
        updates = ", ".join(
            f"{c} = excluded.{c}" for c in COMPANY_COLUMNS if c not in ("id", "created_at")
        )
        self.conn.execute(
            f"INSERT INTO companies ({', '.join(COMPANY_COLUMNS)}) VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}",
            row,
        )

    def upsert_companies(self, companies: list[Company]) -> int:
        for company in companies:
            self.upsert_company(company)
        self.conn.commit()
        return len(companies)

    def get_company(self, company_id: str) -> Company | None:
        row = self.conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
        return Company.from_row(dict(row)) if row else None

    def get_company_by_slug(self, slug: str) -> Company | None:
        row = self.conn.execute("SELECT * FROM companies WHERE slug = ?", (slug,)).fetchone()
        return Company.from_row(dict(row)) if row else None

    def list_companies(
        self,
        batch: str | None = None,
        status: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Company]:
        sql, params = "SELECT * FROM companies WHERE 1=1", []
        if batch:
            sql += " AND batch = ?"
            params.append(batch)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if query:
            sql += " AND (name LIKE ? OR description LIKE ? OR one_liner LIKE ?)"
            params += [f"%{query}%"] * 3
        sql += " ORDER BY batch DESC, name LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = self.conn.execute(sql, params).fetchall()
        return [Company.from_row(dict(r)) for r in rows]

    def count_companies(
        self,
        batch: str | None = None,
        status: str | None = None,
        query: str | None = None,
    ) -> int:
        sql, params = "SELECT COUNT(*) FROM companies WHERE 1=1", []
        if batch:
            sql += " AND batch = ?"
            params.append(batch)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if query:
            sql += " AND (name LIKE ? OR description LIKE ? OR one_liner LIKE ?)"
            params += [f"%{query}%"] * 3
        return self.conn.execute(sql, params).fetchone()[0]

    def list_batches(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT batch FROM companies WHERE batch != '' ORDER BY batch"
        ).fetchall()
        return [r[0] for r in rows]

    # -- news events ---------------------------------------------------
    def add_news_event(self, event: NewsEvent) -> NewsEvent:
        cur = self.conn.execute(
            "INSERT INTO news_events (company_id, title, url, source, published_at, "
            "summary, event_type, funding_amount_usd, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (event.company_id, event.title, event.url, event.source, event.published_at,
             event.summary, event.event_type, event.funding_amount_usd, event.created_at),
        )
        self.conn.commit()
        event.id = cur.lastrowid
        return event

    def list_news_events(self, company_id: str | None = None, limit: int = 100) -> list[NewsEvent]:
        sql, params = "SELECT * FROM news_events", []
        if company_id:
            sql += " WHERE company_id = ?"
            params.append(company_id)
        sql += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [NewsEvent(**dict(r)) for r in rows]

    # -- health checks ---------------------------------------------------
    def add_health_check(self, check: HealthCheck) -> HealthCheck:
        cur = self.conn.execute(
            "INSERT INTO health_checks (company_id, checked_at, website_reachable, "
            "website_status_code, notes) VALUES (?, ?, ?, ?, ?)",
            (check.company_id, check.checked_at, check.website_reachable,
             check.website_status_code, check.notes),
        )
        self.conn.commit()
        check.id = cur.lastrowid
        return check

    def latest_health_check(self, company_id: str) -> HealthCheck | None:
        row = self.conn.execute(
            "SELECT * FROM health_checks WHERE company_id = ? ORDER BY checked_at DESC LIMIT 1",
            (company_id,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["website_reachable"] = bool(data["website_reachable"])
        return HealthCheck(**data)
