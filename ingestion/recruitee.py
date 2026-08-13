"""Recruitee public offers API client.

GET https://{board_token}.recruitee.com/api/offers/
Unknown slugs typically 404.
"""

from __future__ import annotations

import logging
from typing import Any

from .errors import IngestionError
from .http import get_json
from .schema import JobPosting
from .textutil import html_to_text

logger = logging.getLogger(__name__)

RECRUITEE_URL = "https://{board_token}.recruitee.com/api/offers/"


def fetch_recruitee_jobs(company_name: str, board_token: str) -> list[JobPosting]:
    url = RECRUITEE_URL.format(board_token=board_token)
    raw = get_json(url, company_name=company_name)
    if not isinstance(raw, dict):
        raise IngestionError(
            f"{company_name}: expected JSON object from Recruitee, got {type(raw).__name__}"
        )
    offers = raw.get("offers")
    if not isinstance(offers, list):
        raise IngestionError(
            f"{company_name}: Recruitee missing offers list (keys={list(raw.keys())})"
        )

    postings: list[JobPosting] = []
    for index, job in enumerate(offers):
        try:
            postings.append(
                _normalize_job(job, company_name=company_name, board_token=board_token)
            )
        except ValueError as exc:
            logger.warning("%s: skipping job[%s]: %s", company_name, index, exc)
    return postings


def _normalize_job(
    job: Any, *, company_name: str, board_token: str
) -> JobPosting:
    if not isinstance(job, dict):
        raise ValueError(f"expected job object, got {type(job).__name__}")
    title = _require_str(job.get("title"), field="title")
    slug = job.get("slug") or job.get("guid") or job.get("id")
    careers_url = job.get("careers_url") or job.get("url")
    if isinstance(careers_url, str) and careers_url.strip():
        url = careers_url.strip()
    elif slug is not None:
        url = f"https://{board_token}.recruitee.com/o/{slug}"
    else:
        raise ValueError("missing careers_url/slug")
    posted_date = job.get("published_at") or job.get("created_at") or ""
    if not isinstance(posted_date, str):
        posted_date = str(posted_date) if posted_date else ""
    location = _extract_location(job)
    description = ""
    for key in ("description", "requirements", "description_html"):
        value = job.get(key)
        if isinstance(value, str) and value.strip():
            description = html_to_text(value)
            break
    return JobPosting(
        title=title,
        company=company_name,
        location=location,
        posted_date=posted_date.strip(),
        url=url,
        description=description,
    )


def _extract_location(job: dict[str, Any]) -> str:
    locations = job.get("locations")
    if isinstance(locations, list) and locations and isinstance(locations[0], dict):
        loc = locations[0]
        parts = [
            p
            for p in (loc.get("city"), loc.get("state"), loc.get("country"))
            if isinstance(p, str) and p.strip()
        ]
        if parts:
            return ", ".join(parts)
        name = loc.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    city = job.get("city")
    if isinstance(city, str) and city.strip():
        return city.strip()
    if job.get("remote"):
        return "Remote"
    return "Unknown"


def _require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or empty '{field}'")
    return value.strip()
