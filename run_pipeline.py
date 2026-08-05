#!/usr/bin/env python3
"""Full pipeline: ingest → filter → match.

Email delivery and GitHub Actions scheduling are still out of scope here.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from filtering import filter_postings, load_seen_urls, save_seen_urls
from ingestion.runner import ingest_companies
from matching import match_jobs

DATA_DIR = Path(__file__).resolve().parent / "data"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run jobFinderAgent pipeline")
    parser.add_argument(
        "--skip-match",
        action="store_true",
        help="Ingest + filter only (no Claude calls)",
    )
    parser.add_argument(
        "--match-limit",
        type=int,
        default=None,
        help="Max jobs to send to Claude (useful for cheap smoke tests)",
    )
    parser.add_argument(
        "--mark-seen",
        action="store_true",
        help="Add filtered job URLs to data/seen_jobs.json after the run",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    postings = ingest_companies()
    (DATA_DIR / "latest_ingestion.json").write_text(
        json.dumps([p.to_dict() for p in postings], indent=2) + "\n",
        encoding="utf-8",
    )
    logging.info("ingested %d postings", len(postings))

    filtered = filter_postings(postings)
    (DATA_DIR / "latest_filtered.json").write_text(
        json.dumps(
            [
                {
                    **item.posting.to_dict(),
                    "sponsorship_flag": item.sponsorship_flag,
                }
                for item in filtered
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    logging.info("filtered down to %d postings", len(filtered))

    if args.skip_match:
        print(f"\nSkipped matching. {len(filtered)} filtered posting(s) ready.")
        _maybe_mark_seen(filtered, args.mark_seen)
        return 0

    results = match_jobs(filtered, limit=args.match_limit)
    out_path = DATA_DIR / "latest_matches.json"
    out_path.write_text(
        json.dumps([r.to_dict() for r in results], indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n=== Match results ===")
    for result in results:
        print(f"[{result.fit.upper()}] {result.company} — {result.title}")
        print(f"  {result.location} | {result.url}")
        print(f"  {result.reasoning}\n")

    print(f"Wrote {len(results)} match result(s) to {out_path}", file=sys.stderr)
    _maybe_mark_seen(filtered, args.mark_seen)
    return 0


def _maybe_mark_seen(filtered: list, mark: bool) -> None:
    if not mark:
        return
    seen = load_seen_urls()
    for item in filtered:
        seen.add(item.posting.url)
    save_seen_urls(seen)
    logging.info("updated seen store (%d urls)", len(seen))


if __name__ == "__main__":
    raise SystemExit(main())
