"""Database factory — the only place backend selection happens."""

from __future__ import annotations

from yc_tracker import config
from yc_tracker.db.base import Database


def get_database(backend: str | None = None) -> Database:
    backend = backend or config.DB_BACKEND
    if backend == "sqlite":
        from yc_tracker.db.sqlite import SQLiteDatabase
        return SQLiteDatabase(config.SQLITE_PATH)
    if backend == "supabase":
        from yc_tracker.db.supabase import SupabaseDatabase
        return SupabaseDatabase(config.SUPABASE_URL, config.SUPABASE_KEY)
    raise ValueError(f"Unknown DB backend: {backend!r} (expected 'sqlite' or 'supabase')")


__all__ = ["Database", "get_database"]
