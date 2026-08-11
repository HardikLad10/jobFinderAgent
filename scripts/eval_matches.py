#!/usr/bin/env python3
"""Offline gold eval — re-score snapshotted postings and apply pass rule.

Usage:
  python scripts/eval_matches.py              # live Claude calls (costs $)
  python scripts/eval_matches.py --dry-labels # validate fixtures only
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from filtering import FilteredJob
from ingestion.schema import JobPosting
from matching import match_jobs

GOLD_DIR = ROOT / "evals" / "gold"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run snapshotted gold match eval")
    parser.add_argument(
        "--dry-labels",
        action="store_true",
        help="Only validate gold fixtures/manifest; no Claude calls",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    manifest = json.loads((GOLD_DIR / "manifest.json").read_text(encoding="utf-8"))
    items = manifest["items"]
    rule = manifest.get("pass_rule", {})
    min_exact = int(rule.get("min_exact", 10))

    if len(items) != 12:
        print(f"FAIL: expected 12 gold items, found {len(items)}")
        return 1

    if args.dry_labels:
        fits = [i["expected_fit"] for i in items]
        print("Gold fixtures OK:", fits)
        print("Boundary count:", sum(1 for i in items if i.get("boundary")))
        return 0

    jobs: list[FilteredJob] = []
    expected: dict[str, str] = {}
    for item in items:
        snap = json.loads((GOLD_DIR / item["path"]).read_text(encoding="utf-8"))
        p = snap["posting"]
        posting = JobPosting(
            title=p["title"],
            company=p["company"],
            location=p["location"],
            posted_date=p["posted_date"],
            url=p["url"],
            description=p.get("description", ""),
        )
        jobs.append(
            FilteredJob(
                posting=posting,
                sponsorship_flag=snap.get("sponsorship_flag", "none_found"),
            )
        )
        expected[p["url"]] = snap["expected_fit"]

    results = match_jobs(jobs, persist_quarantine=False)
    exact = 0
    soft = 0
    hard_flip = 0
    rows = []
    for result in results:
        exp = expected[result.url]
        got = result.fit
        if got == exp:
            exact += 1
            status = "exact"
        elif {got, exp} <= {"strong", "maybe"}:
            soft += 1
            status = "soft"
        elif {got, exp} == {"no", "strong"} or (
            got in {"invalid", "error"} and exp in {"strong", "maybe", "no"}
        ):
            if {got, exp} == {"no", "strong"}:
                hard_flip += 1
            status = "hard" if {got, exp} == {"no", "strong"} else "fail_closed"
        else:
            status = "mismatch"
        rows.append((status, exp, got, result.company, result.title[:40]))

    print("=== Gold eval results ===")
    for status, exp, got, company, title in rows:
        print(f"[{status}] expected={exp} got={got} | {company} — {title}")

    print(
        f"\nexact={exact}/12 soft_strong_maybe={soft} no_strong_flips={hard_flip}"
    )
    passed = exact >= min_exact and hard_flip == 0
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
