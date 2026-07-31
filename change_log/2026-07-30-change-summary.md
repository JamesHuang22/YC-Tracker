# Change Summary — 2026-07-30

## MVP implementation (Phase 1 of DESIGN.md)

Built and tested the YC Tracker MVP end-to-end against live data.

## What was built

```
yc_tracker/
├── models.py            # Company / NewsEvent / HealthCheck / WebsiteSnapshot dataclasses
├── config.py            # env-driven settings (DB backend, timeouts, UA rotation)
├── db/
│   ├── base.py          # Database ABC — common backend-agnostic interface
│   ├── sqlite.py        # default backend (data/yc_tracker.db, WAL mode)
│   └── supabase.py      # same interface; switch via YC_TRACKER_DB_BACKEND=supabase
├── crawlers/
│   ├── base.py          # BaseCrawler + @register registry → new crawlers plug in with one decorator
│   ├── yc_directory.py  # full YC directory
│   └── company_page.py  # per-company: fetch_detail(), enrich(), fetch_website(), check_health()
├── api/app.py           # FastAPI
└── cli.py               # python -m yc_tracker crawl / list / show / enrich / website / health / stats / serve
```

Also added `requirements.txt`, updated `README.md` with quick-start and architecture docs, and added `data/` to `.gitignore`.

## Key decision on the data source

The YC directory page is a React app, so BeautifulSoup on the HTML sees no
companies, and the old public Algolia key is dead (403). The directory
crawler instead uses the **yc-oss public API** — a daily-updated JSON mirror
of YC's official Algolia index (no API key, no ban risk).

It's complemented by two dedicated per-company query methods:

- `fetch_detail(slug)` — parses the embedded JSON on each company's own YC
  page (founders, LinkedIn, GitHub, news items)
- `fetch_website(url)` — hits the company's main URL and returns
  status/title/description; doubles as the weekly health check

## Verified live

- Crawled Winter 2025 (167 companies) + Summer 2025 (166) into SQLite —
  statuses mapped (active/acquired/dead)
- `enrich afterquery` pulled real founders ("Carlos Georgescu",
  "Spencer Mateega") and LinkedIn from the YC page
- `website afterquery` returned 200 with the site's title and meta description
- API endpoints all tested: `/stats`, `/companies?q=`,
  `/companies/{slug}/website`, `POST /crawl?batch=`
- Fixed a bug where search counts ignored the query filter

## Environment note

The system default `python3` is 3.9, which FastAPI's modern type syntax
doesn't support — the project venv is built with Homebrew **Python 3.13**
(documented in the README).

## Next steps

- Phase 2 — Google News RSS + DeepSeek funding extraction
- Phase 3 — Telegram weekly report + README badges
- Nothing committed to git yet
