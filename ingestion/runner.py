"""Run ingestion across the company config.

Per-company failures are logged and collected; they do not abort the run.
Unresolved ATS entries are skipped (expected until board tokens are found).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

from .ashby import fetch_ashby_jobs
from .breezy import fetch_breezy_jobs
from .errors import IngestionError
from .greenhouse import fetch_greenhouse_jobs
from .lever import fetch_lever_jobs
from .recruitee import fetch_recruitee_jobs
from .schema import JobPosting
from .smartrecruiters import fetch_smartrecruiters_jobs
from .workable import fetch_workable_jobs

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "companies.json"

FetchFn = Callable[[str, str], list[JobPosting]]

FETCHERS: dict[str, FetchFn] = {
    "greenhouse": fetch_greenhouse_jobs,
    "lever": fetch_lever_jobs,
    "ashby": fetch_ashby_jobs,
    "breezy": fetch_breezy_jobs,
    "smartrecruiters": fetch_smartrecruiters_jobs,
    "workable": fetch_workable_jobs,
    "recruitee": fetch_recruitee_jobs,
}


def load_companies(config_path: Path | None = None) -> list[dict[str, Any]]:
    path = config_path or DEFAULT_CONFIG_PATH
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"company config must be a JSON list, got {type(data).__name__}")
    return data


def ingest_companies(config_path: Path | None = None) -> list[JobPosting]:
    """Ingest all resolved companies. Continues past individual failures."""
    companies = load_companies(config_path)
    all_postings: list[JobPosting] = []
    skipped_unresolved = 0

    for company in companies:
        name = company.get("name", "<unnamed>")
        status = company.get("status", "resolved")
        ats = company.get("ats")
        board_token = company.get("board_token")

        if status == "unresolved" or ats is None or board_token is None:
            skipped_unresolved += 1
            logger.info("%s: unresolved ATS — skipping", name)
            continue

        fetch = FETCHERS.get(str(ats))
        if fetch is None:
            logger.error("%s: unsupported ats=%r (skipping)", name, ats)
            continue
        if not isinstance(board_token, str) or not board_token.strip():
            logger.error("%s: missing board_token (skipping)", name)
            continue

        try:
            postings = fetch(name, board_token.strip())
        except IngestionError as exc:
            logger.error("ingestion failed for %s: %s", name, exc)
            continue
        except Exception as exc:  # noqa: BLE001 — last-resort guard for scale-out
            logger.exception("unexpected error ingesting %s: %s", name, exc)
            continue

        logger.info("%s (%s/%s): fetched %d posting(s)", name, ats, board_token, len(postings))
        all_postings.extend(postings)

    logger.info(
        "ingestion complete: %d posting(s) from resolved boards; %d unresolved skipped",
        len(all_postings),
        skipped_unresolved,
    )
    return all_postings
