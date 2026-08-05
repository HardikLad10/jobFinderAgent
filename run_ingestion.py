#!/usr/bin/env python3
"""Fetch + normalize configured companies, print a summary.

Full normalized JSON is written to data/latest_ingestion.json (gitignored)
so a large board list does not flood the console.
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path

from ingestion.runner import ingest_companies

OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "latest_ingestion.json"


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    postings = ingest_companies()
    by_company = Counter(p.company for p in postings)

    print("\n=== Ingestion summary ===")
    for company, count in sorted(by_company.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {company}: {count}")
    print(f"\nTotal normalized postings: {len(postings)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps([p.to_dict() for p in postings], indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Full JSON written to {OUTPUT_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
