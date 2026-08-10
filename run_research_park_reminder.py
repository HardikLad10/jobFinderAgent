#!/usr/bin/env python3
"""Research Park careers within-1-day reminder — personal tracking only.

Logic: if X > 0 jobs posted within ~1 day, email a minimal nudge.
"""

from __future__ import annotations

import argparse
import logging

from alerts.research_park import count_keyword_hits, fetch_postings_within_one_day
from delivery import deliver_research_park_reminder


def main() -> int:
    parser = argparse.ArgumentParser(description="Research Park daily reminder")
    parser.add_argument(
        "--dry-run-email",
        action="store_true",
        help="Print the reminder email; do not send",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send the reminder via Resend if count > 0",
    )
    args = parser.parse_args()

    if args.dry_run_email and args.send_email:
        parser.error("use only one of --dry-run-email or --send-email")
    if not args.dry_run_email and not args.send_email:
        args.dry_run_email = True

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    snapshot = fetch_postings_within_one_day()
    software_n, intern_n = count_keyword_hits(snapshot.titles)

    print(f"Research Park within-1-day: {snapshot.count} job(s)")
    print(f"  software/eng/dev titles: {software_n}")
    print(f"  intern titles: {intern_n}")
    for title in snapshot.titles:
        print(f"  - {title}")

    deliver_research_park_reminder(
        count=snapshot.count,
        software_count=software_n,
        intern_count=intern_n,
        board_url=snapshot.board_url,
        dry_run=args.dry_run_email,
        send=args.send_email,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
