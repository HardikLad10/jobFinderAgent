"""Lever public postings API client.

Endpoint: GET https://api.lever.co/v0/postings/{site}?mode=json
Returns a JSON array (not an object wrapper).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .errors import IngestionError
from .http import get_json
from .schema import JobPosting

logger = logging.getLogger(__name__)

LEVER_POSTINGS_URL = "https://api.lever.co/v0/postings/{board_token}?mode=json"


def fetch_lever_jobs(company_name: str, board_token: str) -> list[JobPosting]:
    url = LEVER_POSTINGS_URL.format(board_token=board_token)
    raw = get_json(url, company_name=company_name)

    if not isinstance(raw, list):
        raise IngestionError(
            f"{company_name}: expected JSON array from Lever, got {type(raw).__name__}"
        )

    postings: list[JobPosting] = []
    for index, job in enumerate(raw):
        try:
            postings.append(_normalize_job(job, company_name=company_name))
        except ValueError as exc:
            logger.warning("%s: skipping job[%s]: %s", company_name, index, exc)

    return postings


def _normalize_job(job: Any, *, company_name: str) -> JobPosting:
    if not isinstance(job, dict):
        raise ValueError(f"expected job object, got {type(job).__name__}")

    title = _require_str(job.get("text"), field="text")
    url = _require_str(job.get("hostedUrl"), field="hostedUrl")
    posted_date = _format_created_at(job.get("createdAt"))
    location = _extract_location(job.get("categories"))

    # Prefer plain text; fall back to HTML fields stripped later if needed.
    description = ""
    for key in ("descriptionPlain", "descriptionBodyPlain", "description", "descriptionBody"):
        value = job.get(key)
        if isinstance(value, str) and value.strip():
            description = value.strip()
            break

    return JobPosting(
        title=title,
        company=company_name,
        location=location,
        posted_date=posted_date,
        url=url,
        description=description,
    )


def _format_created_at(value: Any) -> str:
    # Lever emits createdAt as epoch milliseconds.
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc).isoformat()
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError("missing or empty 'createdAt'")


def _extract_location(categories: Any) -> str:
    if isinstance(categories, dict):
        location = categories.get("location")
        if isinstance(location, str) and location.strip():
            return location.strip()
        all_locations = categories.get("allLocations")
        if isinstance(all_locations, list) and all_locations:
            first = all_locations[0]
            if isinstance(first, str) and first.strip():
                return first.strip()
    return "Unknown"


def _require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or empty '{field}'")
    return value.strip()
