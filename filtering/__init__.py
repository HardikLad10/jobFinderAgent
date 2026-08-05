"""Deterministic filters — no LLM.

Order matters: cheap title/location checks first, then sponsorship on body
text, then dedupe against the seen-jobs store.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
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
) -> list[FilteredJob]:
    """Apply title → location → sponsorship → dedupe. Returns survivors only."""
    cfg = filter_config if filter_config is not None else load_filter_config()
    seen = seen_urls if seen_urls is not None else load_seen_urls()

    title_include = _lower_list(cfg.get("title_include_any", []))
    title_exclude = _lower_list(cfg.get("title_exclude_any", []))
    location_include = _lower_list(cfg.get("location_include_any", []))
    phrases = _lower_list(cfg.get("sponsorship_exclusion_phrases", []))

    kept: list[FilteredJob] = []
    stats = {
        "input": len(postings),
        "title_drop": 0,
        "location_drop": 0,
        "sponsorship_drop": 0,
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
        if location_include and not any(k.strip() in location_l for k in location_include):
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

        if posting.url in seen:
            stats["dedupe_drop"] += 1
            continue

        kept.append(FilteredJob(posting=posting, sponsorship_flag=flag))

    stats["kept"] = len(kept)
    logger.info(
        "filter stats: input=%d title_drop=%d location_drop=%d "
        "sponsorship_drop=%d dedupe_drop=%d kept=%d",
        stats["input"],
        stats["title_drop"],
        stats["location_drop"],
        stats["sponsorship_drop"],
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


def _phrase_in_text(phrase: str, text: str) -> bool:
    # Prefer substring for multi-word phrases. For short tokens like "itar",
    # require a word boundary so we don't match random substrings.
    if " " in phrase or "." in phrase:
        return phrase in text
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def _lower_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(v).lower().strip() for v in values if str(v).strip()]
