"""Greenhouse public board API client.

Why Greenhouse list endpoint (not HTML scrape): structured JSON, no auth,
and Greenhouse is one of the three ATS sources locked in PROJECT_BRIEF.md.

Endpoint: GET /v1/boards/{board_token}/jobs?content=true
content=true is required so sponsorship filtering can scan body text.
"""

from __future__ import annotations

import logging
from typing import Any

from .errors import IngestionError
from .http import get_json
from .schema import JobPosting
from .textutil import html_to_text

logger = logging.getLogger(__name__)

GREENHOUSE_BOARD_URL = (
    "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
)


def fetch_greenhouse_jobs(company_name: str, board_token: str) -> list[JobPosting]:
    """Fetch one Greenhouse board and return normalized postings.

    Raises IngestionError on HTTP/network/JSON/shape failures so the caller
    can log and continue with other companies.
    """
    url = GREENHOUSE_BOARD_URL.format(board_token=board_token)
    raw = get_json(url, company_name=company_name)

    if not isinstance(raw, dict):
        raise IngestionError(
            f"{company_name}: expected JSON object from Greenhouse, got {type(raw).__name__}"
        )

    jobs = raw.get("jobs")
    if not isinstance(jobs, list):
        raise IngestionError(
            f"{company_name}: response missing a 'jobs' list "
            f"(got keys={list(raw.keys())})"
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
    url = _require_str(job.get("absolute_url"), field="absolute_url")

    # Prefer first_published (true post time) over updated_at (bumps on edits).
    posted_date = job.get("first_published") or job.get("updated_at")
    posted_date = _require_str(posted_date, field="first_published/updated_at")

    location = _extract_location(job.get("location"))
    company = job.get("company_name") or company_name
    company = _require_str(company, field="company")

    raw_content = job.get("content")
    if isinstance(raw_content, str) and raw_content.strip():
        description = html_to_text(raw_content)
    else:
        description = ""
        logger.warning("%s: job %r missing content body", company_name, title)

    return JobPosting(
        title=title,
        company=company,
        location=location,
        posted_date=posted_date,
        url=url,
        description=description,
    )


def _extract_location(location: Any) -> str:
    if isinstance(location, dict):
        name = location.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    if isinstance(location, str) and location.strip():
        return location.strip()
    return "Unknown"


def _require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or empty '{field}'")
    return value.strip()
