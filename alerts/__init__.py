"""Lightweight board reminders (separate from fit-matching)."""

from .illinois_csod import IllinoisBoardSnapshot, fetch_postings_within_one_day

__all__ = [
    "IllinoisBoardSnapshot",
    "fetch_postings_within_one_day",
]
