"""Deterministic filters — no LLM.

Order matters: cheap title/location checks first, then sponsorship on body
text, then posted-date freshness, then dedupe against the seen-jobs store.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ingestion.schema import JobPosting

logger = logging.getLogger(__name__)

DEFAULT_FILTERS_PATH = Path(__file__).resolve().parent.parent / "config" / "filters.json"
DEFAULT_SEEN_PATH = Path(__file__).resolve().parent.parent / "data" / "seen_jobs.json"

SponsorshipFlag = str  # "exclusion_found" | "none_found"


@dataclass(frozen=True)
class FilteredJob:
    posting: JobPosting
    sponsorship_flag: SponsorshipFlag


def load_filter_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_FILTERS_PATH
    with config_path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("filters.json must be a JSON object")
    return data


def load_seen_urls(path: Path | None = None) -> set[str]:
    seen_path = path or DEFAULT_SEEN_PATH
    if not seen_path.exists():
        return set()
    with seen_path.open(encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {str(u) for u in data}
    if isinstance(data, dict) and isinstance(data.get("urls"), list):
        return {str(u) for u in data["urls"]}
    raise ValueError(f"unrecognized seen-jobs format in {seen_path}")


def save_seen_urls(urls: set[str], path: Path | None = None) -> None:
    seen_path = path or DEFAULT_SEEN_PATH
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"urls": sorted(urls)}
    seen_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def filter_postings(
    postings: list[JobPosting],
    *,
    filter_config: dict[str, Any] | None = None,
    seen_urls: set[str] | None = None,
    now: datetime | None = None,
) -> list[FilteredJob]:
    """Apply title → location → sponsorship → freshness → dedupe.

    Freshness sits after sponsorship and before URL-based seen dedupe so
    stale postings never consume a Claude call or a seen-store slot.
    """
    cfg = filter_config if filter_config is not None else load_filter_config()
    seen = seen_urls if seen_urls is not None else load_seen_urls()
    clock = now if now is not None else datetime.now(timezone.utc)

    title_include = _lower_list(cfg.get("title_include_any", []))
    title_exclude = _lower_list(cfg.get("title_exclude_any", []))
    location_include = _lower_list(cfg.get("location_include_any", []))
    remote_us = _lower_list(cfg.get("remote_us_include_any", []))
    remote_non_us = _lower_list(cfg.get("remote_non_us_exclude_any", []))
    phrases = _lower_list(cfg.get("sponsorship_exclusion_phrases", []))
    max_age_days = _max_age_days(cfg.get("max_age_days", 7))

    kept: list[FilteredJob] = []
    stats = {
        "input": len(postings),
        "title_drop": 0,
        "location_drop": 0,
        "sponsorship_drop": 0,
        "freshness_drop": 0,
        "dedupe_drop": 0,
        "kept": 0,
    }

    for posting in postings:
        title_l = posting.title.lower()
        if title_include and not any(k in title_l for k in title_include):
            stats["title_drop"] += 1
            continue
        if title_exclude and any(k in title_l for k in title_exclude):
            stats["title_drop"] += 1
            continue

        location_l = posting.location.lower()
        if not _location_allowed(
            location_l,
            geo_include=location_include,
            remote_us_include=remote_us,
            remote_non_us_exclude=remote_non_us,
        ):
            stats["location_drop"] += 1
            continue

        flag, matched_phrase = sponsorship_flag(posting.description, phrases)
        if flag == "exclusion_found":
            stats["sponsorship_drop"] += 1
            logger.info(
                "sponsorship exclusion: %s — %s (%s)",
                posting.company,
                posting.title,
                matched_phrase,
            )
            continue

        if _is_stale(posting.posted_date, max_age_days=max_age_days, now=clock):
            stats["freshness_drop"] += 1
            continue

        if posting.url in seen:
            stats["dedupe_drop"] += 1
            continue

        kept.append(FilteredJob(posting=posting, sponsorship_flag=flag))

    stats["kept"] = len(kept)
    logger.info(
        "filter stats: input=%d title_drop=%d location_drop=%d "
        "sponsorship_drop=%d freshness_drop=%d dedupe_drop=%d kept=%d",
        stats["input"],
        stats["title_drop"],
        stats["location_drop"],
        stats["sponsorship_drop"],
        stats["freshness_drop"],
        stats["dedupe_drop"],
        stats["kept"],
    )
    return kept


def sponsorship_flag(
    description: str,
    phrases: list[str],
) -> tuple[SponsorshipFlag, str | None]:
    """Red-flag only. none_found ≠ confirmed sponsorship available."""
    text = description.lower()
    for phrase in phrases:
        if _phrase_in_text(phrase, text):
            return "exclusion_found", phrase
    return "none_found", None


def _location_allowed(
    location_l: str,
    *,
    geo_include: list[str],
    remote_us_include: list[str],
    remote_non_us_exclude: list[str],
) -> bool:
    """Midwest/geo hit OR US-remote (not global remote).

    - Geo tokens (Chicago, IL, Champaign, …) pass as before.
    - Bare `remote` alone is no longer a geo include token.
    - Remote path: drop if a non-US country/region token appears; keep if a
      US signal appears; bare \"Remote\" with neither still kept (residual noise).
    """
    if any(token and token in location_l for token in geo_include):
        return True

    if "remote" not in location_l:
        return False

    if any(token and token in location_l for token in remote_non_us_exclude):
        return False

    if any(token and token in location_l for token in remote_us_include):
        return True

    # Ambiguous remote-only location strings — keep for recall; expect some noise.
    return True


def _is_stale(posted_date: str | None, *, max_age_days: int, now: datetime) -> bool:
    """True only when posted_date parses and is older than max_age_days.

    Missing / empty / unparseable dates are kept (return False).
    """
    parsed = _parse_posted_date(posted_date)
    if parsed is None:
        return False
    cutoff = now - timedelta(days=max_age_days)
    return parsed < cutoff


def _parse_posted_date(value: str | None) -> datetime | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    # ATS feeds use ISO-8601; accept trailing Z and naive timestamps as UTC.
    normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _max_age_days(value: Any) -> int:
    try:
        days = int(value)
    except (TypeError, ValueError):
        return 7
    return days if days > 0 else 7


def _phrase_in_text(phrase: str, text: str) -> bool:
    # Prefer substring for multi-word phrases. For short tokens like "itar",
    # require a word boundary so we don't match random substrings.
    if " " in phrase or "." in phrase:
        return phrase in text
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def _lower_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    # Do not strip: tokens like " il " / ", il" need surrounding spaces/commas.
    return [str(v).lower() for v in values if str(v).strip()]
