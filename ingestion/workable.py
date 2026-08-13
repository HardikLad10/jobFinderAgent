"""Workable public widget API client.

GET https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true

Unknown slugs often return HTTP 200 with an empty jobs list — discovery must
require at least one job.
"""

from __future__ import annotations

import logging
from typing import Any

from .errors import IngestionError
from .http import get_json
from .schema import JobPosting
from .textutil import html_to_text

logger = logging.getLogger(__name__)

WORKABLE_URL = (
    "https://apply.workable.com/api/v1/widget/accounts/{board_token}?details=true"
)


def fetch_workable_jobs(company_name: str, board_token: str) -> list[JobPosting]:
    url = WORKABLE_URL.format(board_token=board_token)
    raw = get_json(url, company_name=company_name)
    if not isinstance(raw, dict):
        raise IngestionError(
            f"{company_name}: expected JSON object from Workable, got {type(raw).__name__}"
        )
    jobs = raw.get("jobs")
    if not isinstance(jobs, list):
        raise IngestionError(
            f"{company_name}: Workable missing jobs list (keys={list(raw.keys())})"
        )

    postings: list[JobPosting] = []
    for index, job in enumerate(jobs):
        try:
            postings.append(_normalize_job(job, company_name=company_name))
        except ValueError as exc:
            logger.warning("%s: skipping job[%s]: %s", company_name, index, exc)
    return postings


def _normalize_job(job: Any, *, company_name: str) -> JobPosting:
    if not isinstance(job, dict):
        raise ValueError(f"expected job object, got {type(job).__name__}")
    title = _require_str(job.get("title"), field="title")
    shortcode = job.get("shortcode")
    url = job.get("url") or job.get("application_url")
    if not isinstance(url, str) or not url.strip():
        if isinstance(shortcode, str) and shortcode.strip():
            url = f"https://apply.workable.com/j/{shortcode.strip()}/"
        else:
            raise ValueError("missing url/shortcode")
    posted_date = job.get("published_on")
    posted_date = posted_date.strip() if isinstance(posted_date, str) else ""
    location = _extract_location(job)
    description = ""
    for key in ("description", "full_description", "description_html"):
        value = job.get(key)
        if isinstance(value, str) and value.strip():
            description = html_to_text(value)
            break
    return JobPosting(
        title=title,
        company=company_name,
        location=location,
        posted_date=posted_date,
        url=url.strip(),
        description=description,
    )


def _extract_location(job: dict[str, Any]) -> str:
    parts = [
        p
        for p in (job.get("city"), job.get("state"), job.get("country"))
        if isinstance(p, str) and p.strip()
    ]
    loc = ", ".join(parts)
    if job.get("telecommuting"):
        return f"Remote, {loc}" if loc else "Remote"
    return loc or "Unknown"


def _require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or empty '{field}'")
    return value.strip()
