"""BreezyHR public board client.

List feed: GET https://{board_token}.breezy.hr/json
That list has title/location/url/date but no description. Sponsorship
filtering needs body text, so each posting's HTML page is fetched and the
JobPosting JSON-LD `description` is used (same public careers page).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .errors import IngestionError
from .http import get_json, get_text
from .schema import JobPosting
from .textutil import html_to_text

logger = logging.getLogger(__name__)

BREEZY_LIST_URL = "https://{board_token}.breezy.hr/json"
JOBPOSTING_LD_RE = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>',
    re.I | re.S,
)


def fetch_breezy_jobs(company_name: str, board_token: str) -> list[JobPosting]:
    url = BREEZY_LIST_URL.format(board_token=board_token)
    raw = get_json(url, company_name=company_name)
    if not isinstance(raw, list):
        raise IngestionError(
            f"{company_name}: expected JSON array from Breezy, got {type(raw).__name__}"
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

    title = _require_str(job.get("name"), field="name")
    url = _require_str(job.get("url"), field="url")
    posted_date = job.get("published_date")
    if not isinstance(posted_date, str) or not posted_date.strip():
        posted_date = ""
    else:
        posted_date = posted_date.strip()

    location = _extract_location(job)
    description = _description_from_detail(url, company_name=company_name)
    if not description:
        logger.warning("%s: job %r missing description body", company_name, title)

    return JobPosting(
        title=title,
        company=company_name,
        location=location,
        posted_date=posted_date,
        url=url,
        description=description,
    )


def _extract_location(job: dict[str, Any]) -> str:
    loc = job.get("location")
    if isinstance(loc, dict):
        name = loc.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
        city = loc.get("city") if isinstance(loc.get("city"), str) else ""
        country = ""
        country_obj = loc.get("country")
        if isinstance(country_obj, dict) and isinstance(country_obj.get("name"), str):
            country = country_obj["name"]
        if loc.get("is_remote"):
            remote = "Remote"
            extra = ", ".join(p for p in (city, country) if p)
            return f"{remote}" + (f" ({extra})" if extra else "")
        joined = ", ".join(p for p in (city, country) if p)
        if joined:
            return joined
    locations = job.get("locations")
    if isinstance(locations, list) and locations and isinstance(locations[0], dict):
        return _extract_location({"location": locations[0]})
    return "Unknown"


def _description_from_detail(url: str, *, company_name: str) -> str:
    try:
        html = get_text(url, company_name=company_name)
    except IngestionError as exc:
        logger.warning("%s: breezy detail fetch failed for %s: %s", company_name, url, exc)
        return ""

    for block in JOBPOSTING_LD_RE.findall(html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        if str(data.get("@type") or "") != "JobPosting":
            continue
        raw = data.get("description")
        if isinstance(raw, str) and raw.strip():
            return html_to_text(raw)
    return ""


def _require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or empty '{field}'")
    return value.strip()
