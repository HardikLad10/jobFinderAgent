"""Rippling public job-board client.

List: GET https://api.rippling.com/platform/api/ats/v2/board/{slug}/jobs
Detail: GET https://api.rippling.com/platform/api/ats/v1/board/{slug}/jobs/{id}

Unknown slugs return HTTP 404. The list has no description and no posted
date, so a detail call runs only for software-looking titles.
"""

from __future__ import annotations

import logging
from typing import Any

from .errors import IngestionError
from .http import get_json
from .schema import JobPosting
from .textutil import html_to_text

logger = logging.getLogger(__name__)

LIST_URL = (
    "https://api.rippling.com/platform/api/ats/v2/board/{board_token}/jobs"
    "?page={page}&pageSize=100"
)
DETAIL_URL = (
    "https://api.rippling.com/platform/api/ats/v1/board/{board_token}/jobs/{job_id}"
)
PAGE_SIZE_CAP = 50
SWE_TITLE_HINTS = (
    "software",
    "developer",
    "engineer",
    "swe",
    "full stack",
    "fullstack",
    "backend",
    "frontend",
    "front-end",
    "devops",
    "sre",
    "programmer",
    "data engineer",
    "machine learning",
    "ml engineer",
)


def fetch_rippling_jobs(company_name: str, board_token: str) -> list[JobPosting]:
    rows = _list_jobs(company_name, board_token)
    postings: list[JobPosting] = []
    for index, job in enumerate(rows):
        title = job.get("name")
        if not _title_looks_swe(title):
            continue
        try:
            postings.append(
                _normalize_job(job, company_name=company_name, board_token=board_token)
            )
        except ValueError as exc:
            logger.warning("%s: skipping job[%s]: %s", company_name, index, exc)
    return postings


def _list_jobs(company_name: str, board_token: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 0
    total_pages = 1
    while page < total_pages and page < PAGE_SIZE_CAP:
        url = LIST_URL.format(board_token=board_token, page=page)
        raw = get_json(url, company_name=company_name)
        if not isinstance(raw, dict):
            raise IngestionError(
                f"{company_name}: expected JSON object from Rippling, "
                f"got {type(raw).__name__}"
            )
        items = raw.get("items")
        if not isinstance(items, list):
            raise IngestionError(
                f"{company_name}: Rippling missing items list (keys={list(raw.keys())})"
            )
        rows.extend(item for item in items if isinstance(item, dict))
        total = raw.get("totalPages")
        if isinstance(total, int) and total > 0:
            total_pages = total
        if not items:
            break
        page += 1
    return rows


def _title_looks_swe(title: Any) -> bool:
    if not isinstance(title, str) or not title.strip():
        return False
    lower = title.lower()
    return any(hint in lower for hint in SWE_TITLE_HINTS)


def _normalize_job(
    job: dict[str, Any], *, company_name: str, board_token: str
) -> JobPosting:
    title = _require_str(job.get("name"), field="name")
    job_id = _require_str(job.get("id"), field="id")
    raw_url = job.get("url")
    if isinstance(raw_url, str) and raw_url.strip():
        url = raw_url.strip()
    else:
        url = f"https://ats.rippling.com/{board_token}/jobs/{job_id}"
    posted_date, description = _detail(board_token, job_id, company_name=company_name)
    return JobPosting(
        title=title,
        company=company_name,
        location=_location(job.get("locations")),
        posted_date=posted_date,
        url=url,
        description=description,
    )


def _location(locations: Any) -> str:
    if not isinstance(locations, list):
        return "Unknown"
    parts: list[str] = []
    for loc in locations:
        if not isinstance(loc, dict):
            continue
        name = loc.get("name")
        text = name.strip() if isinstance(name, str) else ""
        if not text:
            bits = [
                loc.get("city"),
                loc.get("state"),
                loc.get("country"),
            ]
            text = ", ".join(
                bit.strip() for bit in bits if isinstance(bit, str) and bit.strip()
            )
        if not text:
            continue
        workplace = loc.get("workplaceType")
        if (
            isinstance(workplace, str)
            and workplace.upper() == "REMOTE"
            and "remote" not in text.lower()
        ):
            text = f"Remote - {text}"
        parts.append(text)
    return "; ".join(parts) if parts else "Unknown"


def _detail(board_token: str, job_id: str, *, company_name: str) -> tuple[str, str]:
    url = DETAIL_URL.format(board_token=board_token, job_id=job_id)
    try:
        raw = get_json(url, company_name=company_name)
    except IngestionError as exc:
        logger.warning("%s: Rippling detail failed: %s", company_name, exc)
        return "", ""
    if not isinstance(raw, dict):
        return "", ""
    created = raw.get("createdOn")
    posted = created.strip() if isinstance(created, str) else ""
    description = raw.get("description")
    chunks: list[str] = []
    if isinstance(description, dict):
        for key in ("role", "company"):
            value = description.get(key)
            if isinstance(value, str) and value.strip():
                chunks.append(html_to_text(value))
    return posted, "\n\n".join(chunk for chunk in chunks if chunk)


def _require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or empty '{field}'")
    return value.strip()
