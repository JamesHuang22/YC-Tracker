"""Crawler package — importing it registers all built-in crawlers."""

from yc_tracker.crawlers.base import BaseCrawler, get_crawler, list_crawlers, register
from yc_tracker.crawlers.yc_directory import YCDirectoryCrawler
from yc_tracker.crawlers.company_page import CompanyPageCrawler

__all__ = [
    "BaseCrawler",
    "get_crawler",
    "list_crawlers",
    "register",
    "YCDirectoryCrawler",
    "CompanyPageCrawler",
]
