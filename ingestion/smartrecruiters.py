"""SmartRecruiters public posting API client.

List: GET https://api.smartrecruiters.com/v1/companies/{id}/postings
Detail (description): GET .../postings/{postingId}

List responses are 200 even for unknown identifiers (totalFound=0). Callers
must treat empty boards as a miss during discovery.
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
    "https://api.smartrecruiters.com/v1/companies/{board_token}/postings"
    "?limit={limit}&offset={offset}"
)
DETAIL_URL = (
    "https://api.smartrecruiters.com/v1/companies/{board_token}/postings/{posting_id}"
)
PAGE_SIZE = 100
# Detail fetch is 1 HTTP/job. Only pull descriptions for SWE-ish titles;
# others never survive the title filter anyway.
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


def fetch_smartrecruiters_jobs(company_name: str, board_token: str) -> list[JobPosting]:
    rows: list[dict[str, Any]] = []
    offset = 0
    total = None
    while True:
        url = LIST_URL.format(board_token=board_token, limit=PAGE_SIZE, offset=offset)
        raw = get_json(url, company_name=company_name)
        if not isinstance(raw, dict):
            raise IngestionError(
                f"{company_name}: expected JSON object from SmartRecruiters, "
                f"got {type(raw).__name__}"
            )
        content = raw.get("content")
        if not isinstance(content, list):
            raise IngestionError(
                f"{company_name}: SmartRecruiters missing content list "
                f"(keys={list(raw.keys())})"
            )
        if total is None:
            total = raw.get("totalFound")
        rows.extend(item for item in content if isinstance(item, dict))
        offset += len(content)
        if not content:
            break
        if isinstance(total, int) and offset >= total:
            break
        if len(content) < PAGE_SIZE:
            break

    postings: list[JobPosting] = []
    for index, job in enumerate(rows):
        title = job.get("name") if isinstance(job, dict) else None
        if not _title_looks_swe(title):
            continue
        try:
            postings.append(
                _normalize_job(job, company_name=company_name, board_token=board_token)
            )
        except ValueError as exc:
            logger.warning("%s: skipping job[%s]: %s", company_name, index, exc)
    return postings


def _title_looks_swe(title: Any) -> bool:
    if not isinstance(title, str) or not title.strip():
        return False
    lower = title.lower()
    return any(hint in lower for hint in SWE_TITLE_HINTS)


def _normalize_job(
    job: dict[str, Any], *, company_name: str, board_token: str
) -> JobPosting:
    title = _require_str(job.get("name"), field="name")
    posting_id = _require_str(job.get("id"), field="id")
    url = (
        f"https://jobs.smartrecruiters.com/{board_token}/{posting_id}"
    )
    posted_date = job.get("releasedDate")
    posted_date = posted_date.strip() if isinstance(posted_date, str) else ""
    location = _extract_location(job.get("location"))
    description = _detail_description(
        board_token, posting_id, company_name=company_name
    )
    return JobPosting(
        title=title,
        company=company_name,
        location=location,
        posted_date=posted_date,
        url=url,
        description=description,
    )


def _extract_location(location: Any) -> str:
    if not isinstance(location, dict):
        return "Unknown"
    full = location.get("fullLocation")
    if isinstance(full, str) and full.strip():
        if location.get("remote"):
            return f"Remote, {full.strip()}"
        return full.strip()
    parts = [
        p
        for p in (location.get("city"), location.get("region"), location.get("country"))
        if isinstance(p, str) and p.strip()
    ]
    if location.get("remote"):
        parts.insert(0, "Remote")
    return ", ".join(parts) if parts else ("Remote" if location.get("remote") else "Unknown")


def _detail_description(board_token: str, posting_id: str, *, company_name: str) -> str:
    url = DETAIL_URL.format(board_token=board_token, posting_id=posting_id)
    try:
        raw = get_json(url, company_name=company_name)
    except IngestionError as exc:
        logger.warning("%s: SmartRecruiters detail failed: %s", company_name, exc)
        return ""
    if not isinstance(raw, dict):
        return ""
    job_ad = raw.get("jobAd")
    if isinstance(job_ad, dict):
        sections = job_ad.get("sections")
        if isinstance(sections, dict):
            chunks: list[str] = []
            for key in ("companyDescription", "jobDescription", "qualifications", "additionalInformation"):
                block = sections.get(key)
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    chunks.append(html_to_text(block["text"]))
            if chunks:
                return "\n\n".join(c for c in chunks if c)
    for key in ("description", "jobDescription"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return html_to_text(value)
    return ""


def _require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or empty '{field}'")
    return value.strip()
