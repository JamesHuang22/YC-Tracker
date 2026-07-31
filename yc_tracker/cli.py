"""Command-line interface.

    python -m yc_tracker crawl [--batch "Winter 2025"] [--source yc-directory]
    python -m yc_tracker list [--batch ...] [--status ...] [--q ...]
    python -m yc_tracker show <slug>
    python -m yc_tracker enrich <slug>
    python -m yc_tracker website <slug>
    python -m yc_tracker health [--batch ...] [--limit N]
    python -m yc_tracker batches
    python -m yc_tracker stats
    python -m yc_tracker serve [--port 8000]
"""

from __future__ import annotations

import argparse
import json
import sys

from yc_tracker.crawlers import CompanyPageCrawler, YCDirectoryCrawler, get_crawler, list_crawlers
from yc_tracker.db import get_database


def cmd_crawl(args):
    with get_database() as db, get_crawler(args.source) as crawler:
        companies = list(crawler.crawl(batch=args.batch))
        count = db.upsert_companies(companies)
        print(f"Upserted {count} companies from {args.source}"
              + (f" (batch: {args.batch})" if args.batch else " (all batches)"))


def cmd_list(args):
    with get_database() as db:
        companies = db.list_companies(batch=args.batch, status=args.status,
                                      query=args.q, limit=args.limit)
        for c in companies:
            print(f"{c.batch:14} {c.status:9} {c.name:30} {c.website}")
        print(f"-- {len(companies)} shown / "
              f"{db.count_companies(batch=args.batch, status=args.status, query=args.q)} matching")


def cmd_show(args):
    with get_database() as db:
        c = db.get_company_by_slug(args.slug) or db.get_company(args.slug)
        if not c:
            sys.exit(f"Company {args.slug!r} not found — run `crawl` first?")
        print(json.dumps(c.to_dict(), indent=2, ensure_ascii=False))


def cmd_enrich(args):
    with get_database() as db, CompanyPageCrawler() as crawler:
        c = db.get_company_by_slug(args.slug) or db.get_company(args.slug)
        if not c:
            sys.exit(f"Company {args.slug!r} not found — run `crawl` first?")
        c = crawler.enrich(c)
        db.upsert_companies([c])
        print(json.dumps(c.to_dict(), indent=2, ensure_ascii=False))


def cmd_website(args):
    with get_database() as db, CompanyPageCrawler() as crawler:
        c = db.get_company_by_slug(args.slug) or db.get_company(args.slug)
        if not c:
            sys.exit(f"Company {args.slug!r} not found — run `crawl` first?")
        snapshot = crawler.fetch_website(c.website)
        db.add_health_check(crawler.check_health(c))
        print(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False))


def cmd_health(args):
    with get_database() as db, CompanyPageCrawler() as crawler:
        companies = db.list_companies(batch=args.batch, limit=args.limit)
        for c in companies:
            check = crawler.check_health(c)
            db.add_health_check(check)
            mark = "OK " if check.website_reachable else "DOWN"
            print(f"{mark:5} {check.website_status_code or '---':>4} {c.name:30} {c.website}")


def cmd_batches(args):
    with YCDirectoryCrawler() as crawler:
        for name in crawler.list_batches():
            print(name)


def cmd_stats(args):
    with get_database() as db:
        print(f"companies: {db.count_companies()}")
        for status in ("active", "acquired", "dead", "public", "unknown"):
            print(f"  {status:9}: {db.count_companies(status=status)}")
        print(f"batches:   {len(db.list_batches())}")


def cmd_serve(args):
    import uvicorn
    uvicorn.run("yc_tracker.api.app:app", host=args.host, port=args.port)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="yc_tracker", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("crawl", help="crawl a source and upsert into the DB")
    p.add_argument("--batch", help='e.g. "Winter 2025" or "winter-2025"')
    p.add_argument("--source", default="yc-directory", choices=list_crawlers())
    p.set_defaults(func=cmd_crawl)

    p = sub.add_parser("list", help="list companies in the DB")
    p.add_argument("--batch")
    p.add_argument("--status")
    p.add_argument("--q")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="show one company as JSON")
    p.add_argument("slug")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("enrich", help="pull founders/linkedin from the company's YC page")
    p.add_argument("slug")
    p.set_defaults(func=cmd_enrich)

    p = sub.add_parser("website", help="query the company's main URL live")
    p.add_argument("slug")
    p.set_defaults(func=cmd_website)

    p = sub.add_parser("health", help="health-check company websites")
    p.add_argument("--batch")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_health)

    p = sub.add_parser("batches", help="list batches known to the YC source")
    p.set_defaults(func=cmd_batches)

    p = sub.add_parser("stats", help="database summary")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("serve", help="run the HTTP API")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
