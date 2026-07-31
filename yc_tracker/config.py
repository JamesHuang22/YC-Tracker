"""Central configuration, all overridable via environment variables."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("YC_TRACKER_DATA_DIR", PROJECT_ROOT / "data"))

# Database backend: "sqlite" (default) or "supabase"
DB_BACKEND = os.getenv("YC_TRACKER_DB_BACKEND", "sqlite")
SQLITE_PATH = Path(os.getenv("YC_TRACKER_SQLITE_PATH", DATA_DIR / "yc_tracker.db"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# yc-oss: daily-updated public mirror of YC's official Algolia index (no API key).
YC_OSS_BASE = "https://yc-oss.github.io/api"
YC_COMPANY_PAGE = "https://www.ycombinator.com/companies/{slug}"

HTTP_TIMEOUT = float(os.getenv("YC_TRACKER_HTTP_TIMEOUT", "20"))
REQUEST_DELAY_SECONDS = float(os.getenv("YC_TRACKER_REQUEST_DELAY", "1.0"))

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
]
