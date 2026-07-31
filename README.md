# YC Tracker

YC startup tracker — automatically monitors funding, team changes, and status of Y Combinator companies.

## Why

Crunchbase is too expensive and too general. YC's official directory is static. I built this to track the startups I care about in one place.

## Stack

Python + SQLite (Supabase-ready) + FastAPI + Hermes cron + DeepSeek LLM

## Quick start

```bash
python3.13 -m venv .venv          # needs Python 3.10+
.venv/bin/pip install -r requirements.txt

# Phase 1: pull the YC directory into SQLite (data/yc_tracker.db)
.venv/bin/python -m yc_tracker crawl --batch "Winter 2025"   # one batch
.venv/bin/python -m yc_tracker crawl                          # all ~6,100 companies

# Explore
.venv/bin/python -m yc_tracker list --q "ai agent"
.venv/bin/python -m yc_tracker show afterquery
.venv/bin/python -m yc_tracker enrich afterquery    # founders + LinkedIn from the company's YC page
.venv/bin/python -m yc_tracker website afterquery   # live-query the company's main URL
.venv/bin/python -m yc_tracker health --limit 20    # weekly website health check
.venv/bin/python -m yc_tracker stats

# HTTP API (docs at http://127.0.0.1:8000/docs)
.venv/bin/python -m yc_tracker serve
```

## Architecture

```
yc_tracker/
├── models.py            # Company / NewsEvent / HealthCheck / WebsiteSnapshot
├── config.py            # env-driven settings
├── db/
│   ├── base.py          # Database interface (backend-agnostic)
│   ├── sqlite.py        # SQLite backend (default)
│   └── supabase.py      # Supabase backend — set YC_TRACKER_DB_BACKEND=supabase
├── crawlers/
│   ├── base.py          # BaseCrawler + @register registry for new crawlers
│   ├── yc_directory.py  # YC directory via yc-oss public API (official Algolia mirror)
│   └── company_page.py  # per-company: YC page detail JSON + main-URL query / health check
├── api/app.py           # FastAPI: /companies, /companies/{slug}/website, /crawl, /stats
└── cli.py               # python -m yc_tracker <command>
```

**Data sources**
- Directory: [yc-oss/api](https://github.com/yc-oss/api) — a daily-updated JSON mirror of YC's official Algolia index (no key, no scraping-ban risk; the live directory page is a React app so plain HTML scraping sees nothing).
- Per-company: `ycombinator.com/companies/<slug>` embeds a JSON payload with founders, LinkedIn/GitHub/Twitter URLs, and YC-listed news items.
- Company website: fetched directly for the live snapshot / health check.

**Swapping the database**: all storage goes through `db/base.py`'s `Database` interface. `YC_TRACKER_DB_BACKEND=supabase SUPABASE_URL=... SUPABASE_KEY=...` switches backends without code changes (`pip install supabase` first).

**Adding a crawler**: subclass `BaseCrawler`, set a `name`, decorate with `@register` — it becomes available as `crawl --source <name>`.

## Status

✅ Phase 1 (directory crawl, DB, per-company queries, API) — done
⬜ Phase 2 — Google News RSS + DeepSeek funding extraction
⬜ Phase 3 — Telegram weekly report + README badges

See [DESIGN.md](DESIGN.md) for the full plan.
