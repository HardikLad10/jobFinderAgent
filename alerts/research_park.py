"""UIUC Research Park job board — reminder-only check.

Personal tracking helper (not part of Greenhouse/Lever/Ashby matching).
Uses the public WordPress REST endpoint for job_listing posts.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape

logger = logging.getLogger(__name__)

BOARD_URL = "https://researchpark.illinois.edu/work-here/careers/"
LISTINGS_API = (
    "https://researchpark.illinois.edu/wp-json/wp/v2/job-listings"
)
USER_AGENT = "jobFinderAgent/0.1 (research-park-reminder)"


@dataclass(frozen=True)
class ResearchParkSnapshot:
    count: int
    titles: tuple[str, ...]
    board_url: str = BOARD_URL


def count_keyword_hits(titles: tuple[str, ...] | list[str]) -> tuple[int, int]:
    """Case-insensitive substring counts: (software_count, intern_count)."""
    software = 0
    intern = 0
    for title in titles:
        lower = title.lower()
        if "software" in lower or "engineer" in lower or "developer" in lower:
            software += 1
        if "intern" in lower:
            intern += 1
    return software, intern


def fetch_postings_within_one_day() -> ResearchParkSnapshot:
    """Return Research Park listings with date_gmt in the last ~24 hours."""
    after = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    query = urllib.parse.urlencode(
        {
            "per_page": "100",
            "orderby": "date",
            "order": "desc",
            "after": after,
        }
    )
    url = f"{LISTINGS_API}?{query}"
    jobs = _get_json(url)

    titles: list[str] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        title_obj = job.get("title") or {}
        raw = title_obj.get("rendered") if isinstance(title_obj, dict) else None
        if isinstance(raw, str) and raw.strip():
            titles.append(_clean_title(raw))

    count = len(titles)
    logger.info("Research Park within-1-day count=%d", count)
    return ResearchParkSnapshot(count=count, titles=tuple(titles))


def _clean_title(raw: str) -> str:
    text = unescape(raw)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _get_json(url: str) -> list:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(
            f"Research Park API HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Research Park API network error: {exc.reason}"
        ) from exc

    if not isinstance(data, list):
        raise RuntimeError(
            f"Research Park API expected list, got {type(data).__name__}"
        )
    return data
