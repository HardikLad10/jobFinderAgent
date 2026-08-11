#!/usr/bin/env python3
"""Full pipeline: ingest → filter → ceiling → match → optional email.

Illinois CSOD reminder is intentionally NOT here — see run_illinois_reminder.py
and .github/workflows/illinois_csod_reminder.yml.

Seen-state (PROJECT_BRIEF §7a):
- `no` marked seen after successful score
- `strong` / `maybe` marked seen only after successful email send
- `invalid` / `error` never marked seen (quarantine handles repeats)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from delivery import deliver_matches, send_email, load_env_var, DEFAULT_TO_EMAIL, DEFAULT_FROM_EMAIL
from filtering import (
    apply_survivor_ceiling,
    filter_postings,
    load_seen_urls,
    save_seen_urls,
)
from ingestion.runner import ingest_companies
from matching import VALID_FITS, match_jobs
from matching.quarantine import quarantined_urls

DATA_DIR = Path(__file__).resolve().parent / "data"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run jobFinderAgent pipeline")
    parser.add_argument(
        "--reuse-ingest",
        action="store_true",
        help="Skip ATS fetch; reload data/latest_ingestion.json (filter/match iteration)",
    )
    parser.add_argument(
        "--skip-match",
        action="store_true",
        help="Ingest + filter only (no Claude calls)",
    )
    parser.add_argument(
        "--match-limit",
        type=int,
        default=None,
        help="Max jobs to send to Claude (smoke tests only; not used on daily cron)",
    )
    parser.add_argument(
        "--mark-seen",
        action="store_true",
        help="Update seen_jobs using split seen-state rules after the run",
    )
    parser.add_argument(
        "--dry-run-email",
        action="store_true",
        help="Print the email body for strong/maybe matches; do not send",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send strong/maybe summary via Resend (requires RESEND_API_KEY)",
    )
    args = parser.parse_args()

    if args.dry_run_email and args.send_email:
        parser.error("use only one of --dry-run-email or --send-email")

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.reuse_ingest:
        ingest_path = DATA_DIR / "latest_ingestion.json"
        if not ingest_path.exists():
            logging.error("no %s — run without --reuse-ingest first", ingest_path)
            return 1
        from ingestion.schema import JobPosting

        raw = json.loads(ingest_path.read_text(encoding="utf-8"))
        postings = [
            JobPosting(
                title=str(row.get("title", "")),
                company=str(row.get("company", "")),
                location=str(row.get("location", "")),
                posted_date=str(row.get("posted_date", "")),
                url=str(row.get("url", "")),
                description=str(row.get("description", "")),
            )
            for row in raw
        ]
        logging.info("reused %d postings from %s", len(postings), ingest_path)
    else:
        postings = ingest_companies()
        (DATA_DIR / "latest_ingestion.json").write_text(
            json.dumps([p.to_dict() for p in postings], indent=2) + "\n",
            encoding="utf-8",
        )
        logging.info("ingested %d postings", len(postings))

    if len(postings) == 0:
        _alert_ingest_empty()
        logging.error("ingested == 0 — aborting pipeline (ingest-health alert)")
        return 2

    filtered = filter_postings(
        postings,
        extra_skip_urls=quarantined_urls(),
    )
    filtered, ceiling_drop = apply_survivor_ceiling(filtered)
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
    logging.info(
        "filtered down to %d postings (ceiling_drop=%d)",
        len(filtered),
        ceiling_drop,
    )

    if args.skip_match:
        print(f"\nSkipped matching. {len(filtered)} filtered posting(s) ready.")
        return 0

    results = match_jobs(filtered, limit=args.match_limit)
    _log_spend(results)
    out_path = DATA_DIR / "latest_matches.json"
    out_path.write_text(
        json.dumps([r.to_dict() for r in results], indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n=== Match results ===")
    for result in results:
        print(f"[{result.fit.upper()}] {result.company} — {result.title}")
        print(f"  Posted: {result.posted_date}")
        print(f"  {result.location} | {result.url}")
        print(f"  {result.reasoning}\n")

    print(f"Wrote {len(results)} match result(s) to {out_path}", file=sys.stderr)

    email_sent = False
    if args.dry_run_email or args.send_email:
        email_sent = deliver_matches(
            results,
            dry_run=args.dry_run_email,
            send=args.send_email,
        )

    if args.mark_seen:
        _apply_split_seen(results, email_sent=email_sent and args.send_email)

    return 0


def _apply_split_seen(results: list, *, email_sent: bool) -> None:
    """Mark no after score; strong/maybe only after successful send."""
    seen = load_seen_urls()
    before = len(seen)
    for result in results:
        fit = result.fit.lower()
        if fit == "no":
            seen.add(result.url)
        elif fit in {"strong", "maybe"} and email_sent:
            seen.add(result.url)
        # invalid/error: never ordinary seen
    save_seen_urls(seen)
    logging.info(
        "updated seen store (%d → %d urls; email_sent=%s)",
        before,
        len(seen),
        email_sent,
    )


def _log_spend(results: list) -> None:
    input_tokens = sum(r.input_tokens or 0 for r in results)
    output_tokens = sum(r.output_tokens or 0 for r in results)
    scored = sum(1 for r in results if r.fit in VALID_FITS)
    fail = sum(1 for r in results if r.fit in {"invalid", "error"})
    logging.info(
        "match spend: scored=%d fail_closed=%d input_tokens=%d output_tokens=%d",
        scored,
        fail,
        input_tokens,
        output_tokens,
    )
    print(
        f"Match spend: scored={scored} fail_closed={fail} "
        f"input_tokens={input_tokens} output_tokens={output_tokens}",
        file=sys.stderr,
    )


def _alert_ingest_empty() -> None:
    """Same-day alert when ATS fan-out produced zero postings."""
    subject = "ALERT: jobFinderAgent ingested 0 jobs"
    text = (
        "Daily pipeline ingested 0 postings from resolved ATS boards.\n"
        "This is treated as an outage (not a quiet filter day).\n"
        "Check GitHub Actions logs and ATS board health.\n"
    )
    html = (
        "<p><strong>Daily pipeline ingested 0 postings.</strong></p>"
        "<p>This is treated as an outage (not a quiet filter day). "
        "Check GitHub Actions logs and ATS board health.</p>"
    )
    print(text)
    try:
        to_addr = load_env_var("TO_EMAIL", default=DEFAULT_TO_EMAIL)
        send_email(
            subject=subject,
            text=text,
            html=html,
            to_email=to_addr,
            from_email=load_env_var("FROM_EMAIL", default=DEFAULT_FROM_EMAIL),
        )
        print(f"Ingest-empty alert emailed to {to_addr}")
    except Exception as exc:  # noqa: BLE001
        logging.error("failed to send ingest-empty alert: %s", exc)


if __name__ == "__main__":
    raise SystemExit(main())
