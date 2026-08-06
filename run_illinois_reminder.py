#!/usr/bin/env python3
"""Illinois CSOD within-1-day reminder — separate from the main fit-matching agent.

Logic: if X > 0 jobs posted within ~1 day, email a minimal nudge.
Flags titles containing 'software' / 'analyst' (case-insensitive).
"""

from __future__ import annotations

import argparse
import logging

from alerts.illinois_csod import count_keyword_hits, fetch_postings_within_one_day
from delivery import deliver_illinois_reminder


def main() -> int:
    parser = argparse.ArgumentParser(description="Illinois CSOD daily reminder")
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
        # Default to dry-run locally so a bare invocation is safe.
        args.dry_run_email = True

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    snapshot = fetch_postings_within_one_day()
    software_n, analyst_n = count_keyword_hits(snapshot.titles)

    print(f"Illinois CSOD within-1-day: {snapshot.count} job(s)")
    print(f"  a software jobs: {software_n}")
    print(f"  b analyst jobs: {analyst_n}")
    for title in snapshot.titles:
        print(f"  - {title}")

    delivered = deliver_illinois_reminder(
        count=snapshot.count,
        software_count=software_n,
        analyst_count=analyst_n,
        board_url=snapshot.board_url,
        dry_run=args.dry_run_email,
        send=args.send_email,
    )
    if not delivered and snapshot.count <= 0:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
