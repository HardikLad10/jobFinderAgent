"""Ashby public job board API client.

Endpoint: GET https://api.ashbyhq.com/posting-api/job-board/{board_name}
Only works when the org has enabled Ashby's public posting API (HTML career
pages alone are not enough — some boards 404 here even if jobs.ashbyhq.com loads).
"""

from __future__ import annotations

import logging
from typing import Any

from .errors import IngestionError
from .http import get_json
from .schema import JobPosting
from .textutil import html_to_text

logger = logging.getLogger(__name__)

ASHBY_BOARD_URL = "https://api.ashbyhq.com/posting-api/job-board/{board_token}"


def fetch_ashby_jobs(company_name: str, board_token: str) -> list[JobPosting]:
    url = ASHBY_BOARD_URL.format(board_token=board_token)
    raw = get_json(url, company_name=company_name)

    if not isinstance(raw, dict):
        raise IngestionError(
            f"{company_name}: expected JSON object from Ashby, got {type(raw).__name__}"
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
    url = _require_str(job.get("jobUrl") or job.get("applyUrl"), field="jobUrl")
    posted_date = _require_str(job.get("publishedAt"), field="publishedAt")

    location = job.get("location")
    if not isinstance(location, str) or not location.strip():
        location = "Remote" if job.get("isRemote") else "Unknown"
    else:
        location = location.strip()

    description = ""
    plain = job.get("descriptionPlain")
    html = job.get("descriptionHtml")
    if isinstance(plain, str) and plain.strip():
        description = plain.strip()
    elif isinstance(html, str) and html.strip():
        description = html_to_text(html)

    return JobPosting(
        title=title,
        company=company_name,
        location=location,
        posted_date=posted_date,
        url=url,
        description=description,
    )


def _require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or empty '{field}'")
    return value.strip()
