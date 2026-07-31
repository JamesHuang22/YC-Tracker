"""YC directory crawler.

Source: the yc-oss public API (https://github.com/yc-oss/api) — a
daily-updated mirror of Y Combinator's official Algolia search index.
No API key, no HTML scraping, no ban risk.

The live YC directory page is a React app, so BeautifulSoup on
ycombinator.com/companies sees no data; this JSON mirror is the same
data YC's own directory search serves.
"""

from __future__ import annotations

from typing import Iterator

from yc_tracker import config
from yc_tracker.crawlers.base import BaseCrawler, register
from yc_tracker.models import Company

# yc-oss "status" → our status vocabulary
STATUS_MAP = {
    "Active": "active",
    "Acquired": "acquired",
    "Inactive": "dead",
    "Public": "public",
}


@register
class YCDirectoryCrawler(BaseCrawler):
    name = "yc-directory"

    def crawl(self, batch: str | None = None, **kwargs) -> Iterator[Company]:
        """Yield all YC companies, optionally restricted to one batch.

        `batch` accepts the display form ("Winter 2025") or the slug
        form ("winter-2025").
        """
        if batch:
            url = f"{config.YC_OSS_BASE}/batches/{self._batch_slug(batch)}.json"
        else:
            url = f"{config.YC_OSS_BASE}/companies/all.json"
        resp = self.client.get(url)
        resp.raise_for_status()
        for record in resp.json():
            yield self.to_company(record)

    def list_batches(self) -> list[str]:
        """Batch names known to the source, newest first."""
        resp = self.client.get(f"{config.YC_OSS_BASE}/meta.json")
        resp.raise_for_status()
        batches = resp.json().get("batches", {})
        return [info["name"] for info in batches.values()]

    @staticmethod
    def _batch_slug(batch: str) -> str:
        return batch.strip().lower().replace(" ", "-")

    @staticmethod
    def to_company(record: dict) -> Company:
        slug = record.get("slug") or ""
        return Company(
            id=f"yc-{slug}" if slug else f"yc-id-{record.get('id')}",
            name=record.get("name") or "",
            slug=slug,
            batch=record.get("batch") or "",
            description=record.get("long_description") or "",
            one_liner=record.get("one_liner") or "",
            industry=record.get("industry") or "",
            location=record.get("all_locations") or "",
            website=record.get("website") or "",
            yc_url=record.get("url") or config.YC_COMPANY_PAGE.format(slug=slug),
            tags=record.get("tags") or [],
            team_size=record.get("team_size"),
            status=STATUS_MAP.get(record.get("status", ""), "unknown"),
        )
