"""UIUC / Illinois CSOD board — reminder-only check.

Not part of Greenhouse/Lever/Ashby matching. One job: count postings
within the last day; if count > 0, the pipeline can email a reminder to
open the career site (no built-in email alerts on that board).

Tradeoff vs full CSOD ingestion: we reuse the same anonymous JWT the
career page embeds (short-lived), but we only need totalCount + titles.
If bootstrap HTML or the search endpoint changes, this alert may break —
logged as acceptable for a single high-value university board.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CAREER_URL = (
    "https://illinois.csod.com/ux/ats/careersite/1/home"
    "?c=illinois&date=WithinOneDay"
)
CAREER_HOME = "https://illinois.csod.com/ux/ats/careersite/1/home?c=illinois"
DEFAULT_API_HOST = "https://us.api.csod.com"
SEARCH_PATH = "/rec-job-search/external/jobs"
USER_AGENT = "jobFinderAgent/0.1 (illinois-board-reminder)"


@dataclass(frozen=True)
class IllinoisBoardSnapshot:
    count: int
    titles: tuple[str, ...]
    board_url: str = CAREER_URL


def fetch_postings_within_one_day() -> IllinoisBoardSnapshot:
    """Return how many Illinois CSOD jobs were posted within ~1 day."""
    html = _get_text(CAREER_URL)
    token = _extract_jwt(html)
    api_host = _extract_api_host(html) or DEFAULT_API_HOST

    payload = {
        "careerSiteId": 1,
        "careerSitePageId": 1,
        "pageNumber": 1,
        "pageSize": 25,
        "cultureId": 1,
        "searchText": "",
        "states": [],
        "countryCodes": [],
        "cities": [],
        "placeID": "",
        "radius": None,
        "postingsWithinDays": 1,
        "customFieldCheckboxKeys": [],
        "customFieldDropdowns": [],
        "customFieldRadios": [],
    }
    body = _post_json(
        f"{api_host}{SEARCH_PATH}",
        payload=payload,
        token=token,
    )
    if body.get("status") != "Success":
        raise RuntimeError(f"Illinois CSOD search failed: {body.get('status')!r}")

    data = body.get("data") or {}
    count = int(data.get("totalCount") or 0)
    titles: list[str] = []
    for req in data.get("requisitions") or []:
        if not isinstance(req, dict):
            continue
        title = req.get("displayJobTitle")
        if isinstance(title, str) and title.strip():
            titles.append(title.strip())

    logger.info("Illinois CSOD within-1-day count=%d", count)
    return IllinoisBoardSnapshot(count=count, titles=tuple(titles))


def _get_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Illinois CSOD page HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Illinois CSOD page network error: {exc.reason}") from exc


def _post_json(url: str, *, payload: dict, token: str) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://illinois.csod.com",
            "Referer": CAREER_HOME,
            "User-Agent": USER_AGENT,
            "Csod-Accept-Language": "en-US",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Illinois CSOD API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Illinois CSOD API network error: {exc.reason}") from exc


def _extract_jwt(html: str) -> str:
    match = re.search(r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+", html)
    if not match:
        raise RuntimeError("Illinois CSOD page missing embedded JWT")
    return match.group(0)


def _extract_api_host(html: str) -> str | None:
    match = re.search(r"https://(?:us|eu|ap)\.api\.csod\.com", html)
    return match.group(0) if match else None
