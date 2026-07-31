"""HTTP API. Run with: python -m yc_tracker serve"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query

from yc_tracker.crawlers import CompanyPageCrawler, YCDirectoryCrawler
from yc_tracker.db import Database, get_database
from yc_tracker.models import Company

app = FastAPI(title="YC Tracker", version="0.1.0")


def db() -> Database:
    database = get_database()
    try:
        yield database
    finally:
        database.close()


def _find(database: Database, id_or_slug: str) -> Company:
    company = database.get_company(id_or_slug) or database.get_company_by_slug(id_or_slug)
    if not company:
        raise HTTPException(404, f"Company {id_or_slug!r} not found")
    return company


@app.get("/stats")
def stats(database: Database = Depends(db)):
    return {
        "total": database.count_companies(),
        "by_status": {
            s: database.count_companies(status=s)
            for s in ("active", "acquired", "dead", "public", "unknown")
        },
        "batches": len(database.list_batches()),
    }


@app.get("/batches")
def batches(database: Database = Depends(db)):
    return database.list_batches()


@app.get("/companies")
def list_companies(
    batch: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    database: Database = Depends(db),
):
    companies = database.list_companies(batch=batch, status=status, query=q,
                                        limit=limit, offset=offset)
    return {
        "count": database.count_companies(batch=batch, status=status, query=q),
        "results": [c.to_dict() for c in companies],
    }


@app.get("/companies/{id_or_slug}")
def get_company(id_or_slug: str, database: Database = Depends(db)):
    return _find(database, id_or_slug).to_dict()


@app.get("/companies/{id_or_slug}/website")
def query_company_website(id_or_slug: str, database: Database = Depends(db)):
    """Dedicated query: hit the company's main URL live and report back."""
    company = _find(database, id_or_slug)
    with CompanyPageCrawler() as crawler:
        snapshot = crawler.fetch_website(company.website)
        database.add_health_check(crawler.check_health(company))
    return snapshot.to_dict()


@app.post("/companies/{id_or_slug}/enrich")
def enrich_company(id_or_slug: str, database: Database = Depends(db)):
    """Pull founders / linkedin / news from the company's YC page."""
    company = _find(database, id_or_slug)
    with CompanyPageCrawler() as crawler:
        company = crawler.enrich(company)
        database.upsert_companies([company])
    return company.to_dict()


@app.post("/crawl")
def crawl(batch: str | None = None, database: Database = Depends(db)):
    """Run the YC directory crawler and upsert results."""
    with YCDirectoryCrawler() as crawler:
        count = database.upsert_companies(list(crawler.crawl(batch=batch)))
    return {"upserted": count, "batch": batch or "all"}
