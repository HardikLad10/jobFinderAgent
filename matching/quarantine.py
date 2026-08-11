"""Persistent quarantine for URLs that repeatedly fail scoring.

After QUARANTINE_AFTER failed attempts (invalid/error), the URL is set aside
so it stops burning Opus calls. Tracked separately from seen_jobs.json.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_QUARANTINE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "quarantine.json"
)
QUARANTINE_AFTER = 3


@dataclass
class QuarantineEntry:
    url: str
    attempts: int
    last_error: str
    quarantined: bool
    updated_at: str
    note: str = ""


def load_quarantine(path: Path | None = None) -> dict[str, QuarantineEntry]:
    qpath = path or DEFAULT_QUARANTINE_PATH
    if not qpath.exists():
        return {}
    data = json.loads(qpath.read_text(encoding="utf-8"))
    entries = data.get("entries", data) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise ValueError(f"unrecognized quarantine format in {qpath}")
    out: dict[str, QuarantineEntry] = {}
    for row in entries:
        if not isinstance(row, dict) or not row.get("url"):
            continue
        url = str(row["url"])
        out[url] = QuarantineEntry(
            url=url,
            attempts=int(row.get("attempts", 0)),
            last_error=str(row.get("last_error", "")),
            quarantined=bool(row.get("quarantined", False)),
            updated_at=str(row.get("updated_at", "")),
            note=str(row.get("note", "")),
        )
    return out


def save_quarantine(
    store: dict[str, QuarantineEntry],
    path: Path | None = None,
) -> None:
    qpath = path or DEFAULT_QUARANTINE_PATH
    qpath.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "url": e.url,
            "attempts": e.attempts,
            "last_error": e.last_error,
            "quarantined": e.quarantined,
            "updated_at": e.updated_at,
            "note": e.note,
        }
        for e in sorted(store.values(), key=lambda x: x.url)
    ]
    payload = {"entries": entries}
    qpath.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def quarantined_urls(store: dict[str, QuarantineEntry] | None = None) -> set[str]:
    data = store if store is not None else load_quarantine()
    return {url for url, e in data.items() if e.quarantined}


def record_failure(
    store: dict[str, QuarantineEntry],
    url: str,
    *,
    error: str,
    now: datetime | None = None,
) -> QuarantineEntry:
    """Increment attempt count; quarantine at QUARANTINE_AFTER failures."""
    clock = now or datetime.now(timezone.utc)
    stamp = clock.isoformat()
    entry = store.get(url)
    if entry is None:
        entry = QuarantineEntry(
            url=url,
            attempts=0,
            last_error="",
            quarantined=False,
            updated_at=stamp,
        )
    entry.attempts += 1
    entry.last_error = error[:500]
    entry.updated_at = stamp
    if entry.attempts >= QUARANTINE_AFTER and not entry.quarantined:
        entry.quarantined = True
        entry.note = (
            f"Quarantined after {entry.attempts} failed scoring attempts "
            f"(invalid/error). Last error: {entry.last_error}"
        )
        logger.warning("quarantined %s after %d failures", url, entry.attempts)
    store[url] = entry
    return entry


def clear_failure(store: dict[str, QuarantineEntry], url: str) -> None:
    """Successful score clears the failure streak (does not un-quarantine)."""
    entry = store.get(url)
    if entry is None or entry.quarantined:
        return
    if entry.attempts:
        entry.attempts = 0
        entry.last_error = ""
        entry.updated_at = datetime.now(timezone.utc).isoformat()
        store[url] = entry


def to_public_dict(store: dict[str, QuarantineEntry]) -> dict[str, Any]:
    return {
        "entries": [
            {
                "url": e.url,
                "attempts": e.attempts,
                "last_error": e.last_error,
                "quarantined": e.quarantined,
                "updated_at": e.updated_at,
                "note": e.note,
            }
            for e in sorted(store.values(), key=lambda x: x.url)
        ]
    }
