"""Supabase implementation of the Database interface.

Same interface as SQLiteDatabase — switch by setting env vars:

    YC_TRACKER_DB_BACKEND=supabase
    SUPABASE_URL=https://<project>.supabase.co
    SUPABASE_KEY=<service-role-or-anon-key>

Requires `pip install supabase`. Table DDL for Supabase (run once in the
SQL editor) lives in DESIGN.md §4 — it matches the columns used here.
"""

from __future__ import annotations

from yc_tracker.db.base import Database
from yc_tracker.models import Company, HealthCheck, NewsEvent, utcnow


class SupabaseDatabase(Database):
    def __init__(self, url: str, key: str):
        try:
            from supabase import create_client
        except ImportError as exc:
            raise ImportError(
                "Supabase backend requires the `supabase` package: pip install supabase"
            ) from exc
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        self.client = create_client(url, key)

    def init_schema(self) -> None:
        # Supabase tables are created via the dashboard / SQL editor
        # (see DESIGN.md §4); the client API cannot run DDL.
        pass

    def close(self) -> None:
        pass

    # -- companies -----------------------------------------------------
    def upsert_company(self, company: Company) -> None:
        row = company.to_row()
        row["updated_at"] = utcnow()
        row.pop("created_at", None)  # let the DB default stand on insert
        self.client.table("companies").upsert(row, on_conflict="id").execute()

    def get_company(self, company_id: str) -> Company | None:
        res = self.client.table("companies").select("*").eq("id", company_id).limit(1).execute()
        return Company.from_row(res.data[0]) if res.data else None

    def get_company_by_slug(self, slug: str) -> Company | None:
        res = self.client.table("companies").select("*").eq("slug", slug).limit(1).execute()
        return Company.from_row(res.data[0]) if res.data else None

    def list_companies(
        self,
        batch: str | None = None,
        status: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Company]:
        q = self.client.table("companies").select("*")
        if batch:
            q = q.eq("batch", batch)
        if status:
            q = q.eq("status", status)
        if query:
            q = q.or_(f"name.ilike.%{query}%,description.ilike.%{query}%")
        res = q.order("batch", desc=True).order("name").range(offset, offset + limit - 1).execute()
        return [Company.from_row(r) for r in res.data]

    def count_companies(
        self,
        batch: str | None = None,
        status: str | None = None,
        query: str | None = None,
    ) -> int:
        q = self.client.table("companies").select("id", count="exact")
        if batch:
            q = q.eq("batch", batch)
        if status:
            q = q.eq("status", status)
        if query:
            q = q.or_(f"name.ilike.%{query}%,description.ilike.%{query}%")
        return q.execute().count or 0

    def list_batches(self) -> list[str]:
        res = self.client.table("companies").select("batch").execute()
        return sorted({r["batch"] for r in res.data if r.get("batch")})

    # -- news events ---------------------------------------------------
    def add_news_event(self, event: NewsEvent) -> NewsEvent:
        payload = event.to_dict()
        payload.pop("id", None)
        res = self.client.table("news_events").insert(payload).execute()
        if res.data:
            event.id = res.data[0].get("id")
        return event

    def list_news_events(self, company_id: str | None = None, limit: int = 100) -> list[NewsEvent]:
        q = self.client.table("news_events").select("*")
        if company_id:
            q = q.eq("company_id", company_id)
        res = q.order("published_at", desc=True).limit(limit).execute()
        return [NewsEvent(**r) for r in res.data]

    # -- health checks ---------------------------------------------------
    def add_health_check(self, check: HealthCheck) -> HealthCheck:
        payload = check.to_dict()
        payload.pop("id", None)
        res = self.client.table("health_checks").insert(payload).execute()
        if res.data:
            check.id = res.data[0].get("id")
        return check

    def latest_health_check(self, company_id: str) -> HealthCheck | None:
        res = (
            self.client.table("health_checks").select("*")
            .eq("company_id", company_id)
            .order("checked_at", desc=True).limit(1).execute()
        )
        return HealthCheck(**res.data[0]) if res.data else None
