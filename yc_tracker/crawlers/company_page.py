"""Per-company crawler.

Two dedicated query methods per company:

1. `fetch_detail(slug)` — hits the company's own YC page
   (ycombinator.com/companies/<slug>) and parses the embedded JSON
   payload: founders, linkedin/github/twitter URLs, year founded,
   and recent news items YC lists for the company.

2. `fetch_website(url)` — queries the company's main URL directly and
   returns a WebsiteSnapshot (status code, reachability, <title>, meta
   description). Doubles as the weekly health check.
"""

from __future__ import annotations

import html as html_lib
import json
import re
import time
from typing import Iterator

from bs4 import BeautifulSoup

from yc_tracker import config
from yc_tracker.crawlers.base import BaseCrawler, register
from yc_tracker.models import Company, HealthCheck, NewsEvent, WebsiteSnapshot

_DATA_PAGE_RE = re.compile(r'data-page="([^"]+)"')


@register
class CompanyPageCrawler(BaseCrawler):
    name = "yc-company-page"

    # -- YC company detail page ---------------------------------------
    def fetch_detail(self, slug: str) -> dict:
        """Fetch and parse the embedded JSON on a company's YC page."""
        url = config.YC_COMPANY_PAGE.format(slug=slug)
        self.rotate_user_agent()
        resp = self.client.get(url)
        resp.raise_for_status()
        match = _DATA_PAGE_RE.search(resp.text)
        if not match:
            raise ValueError(f"No embedded data-page JSON found at {url}")
        return json.loads(html_lib.unescape(match.group(1))).get("props", {})

    def enrich(self, company: Company) -> Company:
        """Fill fields the directory listing doesn't carry."""
        props = self.fetch_detail(company.slug)
        detail = props.get("company", {})
        company.linkedin_url = detail.get("linkedin_url") or company.linkedin_url
        founders = detail.get("founders") or []
        names = [f.get("full_name") or f.get("first_name", "") for f in founders]
        company.founders = [n for n in names if n] or company.founders
        company.team_size = detail.get("team_size") or company.team_size
        company.location = detail.get("location") or company.location
        company.website = detail.get("website") or company.website
        return company

    def fetch_news_items(self, company: Company) -> list[NewsEvent]:
        """News links YC itself lists on the company page."""
        props = self.fetch_detail(company.slug)
        events = []
        for item in props.get("newsItems") or []:
            events.append(NewsEvent(
                company_id=company.id,
                title=item.get("title") or "",
                url=item.get("url") or "",
                source="yc-company-page",
                published_at=item.get("date") or "",
            ))
        return events

    # -- company's main URL --------------------------------------------
    def fetch_website(self, url: str) -> WebsiteSnapshot:
        """Query a company's main URL and describe what's there."""
        snapshot = WebsiteSnapshot(url=url)
        if not url:
            snapshot.error = "no website on record"
            return snapshot
        try:
            self.rotate_user_agent()
            resp = self.client.get(url)
            snapshot.status_code = resp.status_code
            snapshot.final_url = str(resp.url)
            snapshot.reachable = resp.status_code < 400
            if snapshot.reachable and "text/html" in resp.headers.get("content-type", ""):
                soup = BeautifulSoup(resp.text, "html.parser")
                if soup.title and soup.title.string:
                    snapshot.title = soup.title.string.strip()
                meta = soup.find("meta", attrs={"name": "description"})
                if meta and meta.get("content"):
                    snapshot.meta_description = meta["content"].strip()
        except Exception as exc:
            snapshot.error = f"{type(exc).__name__}: {exc}"
        return snapshot

    def check_health(self, company: Company) -> HealthCheck:
        snapshot = self.fetch_website(company.website)
        return HealthCheck(
            company_id=company.id,
            website_reachable=snapshot.reachable,
            website_status_code=snapshot.status_code,
            notes=snapshot.error or snapshot.title,
        )

    # -- BaseCrawler interface ------------------------------------------
    def crawl(self, companies: list[Company] | None = None, **kwargs) -> Iterator[Company]:
        """Enrich a list of companies via their YC pages (rate-limited)."""
        for company in companies or []:
            try:
                yield self.enrich(company)
            except Exception:
                yield company  # keep directory data if the page fails
            time.sleep(config.REQUEST_DELAY_SECONDS)
