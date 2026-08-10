"""Email delivery via Resend API.

Why Resend (not Hotmail SMTP): one API key, reliable from GitHub Actions,
no Microsoft app-password / IP-block friction.

To: hardik.lad773@gmail.com (Resend account email). Hotmail blocked until a
domain is verified at resend.com/domains.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_TO_EMAIL = "hardik.lad773@gmail.com"
DEFAULT_FROM_EMAIL = "Job Finder Agent <onboarding@resend.dev>"
DEFAULT_ILLINOIS_TO_EMAILS = (
    "hardik.lad773@gmail.com",
)
NOTIFY_FITS = frozenset({"strong", "maybe"})
REASON_MAX_CHARS = 120


def load_env_var(name: str, *, default: str | None = None) -> str:
    existing = os.environ.get(name, "").strip()
    if existing:
        return existing

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == name:
                token = value.strip().strip('"').strip("'")
                if token:
                    return token

    if default is not None:
        return default
    raise RuntimeError(f"{name} not set. Add it to .env or export it in the shell.")


def selectable_matches(matches: Sequence[Any]) -> list[Any]:
    """Only strong + maybe go in the email (locked product choice)."""
    return [m for m in matches if getattr(m, "fit", "").lower() in NOTIFY_FITS]


def build_email(matches: Sequence[Any]) -> tuple[str, str, str] | None:
    """Return (subject, text, html) or None when there is nothing worth sending.

    Header counts, then separate Strong / Maybe sections. Each match is one
    compact line: Title — Company — Posted date — one-line reasoning — link.
    """
    chosen = selectable_matches(matches)
    if not chosen:
        return None

    strong = [m for m in chosen if m.fit.lower() == "strong"]
    maybe = [m for m in chosen if m.fit.lower() == "maybe"]

    subject = (
        f"Job matches: {len(strong)} strong, {len(maybe)} maybe"
        if strong or maybe
        else "Job matches"
    )

    text_parts = [
        f"{len(strong)} strong · {len(maybe)} maybe",
        "",
    ]
    html_parts = [
        f"<p><strong>{len(strong)}</strong> strong · <strong>{len(maybe)}</strong> maybe</p>",
    ]

    def _append_section(label: str, rows: list[Any]) -> None:
        if not rows:
            return
        text_parts.append(label)
        html_parts.append(f"<p><strong>{_escape(label)}</strong></p><ul>")
        for m in rows:
            text_parts.append(f"• {format_match_line(m)}")
            html_parts.append(
                f"<li>{_escape(m.title)} — {_escape(m.company)} — "
                f"{_escape(_posted_display(m))} — {_escape(_short_reason(m))} — "
                f'<a href="{m.url}">{_escape(m.url)}</a></li>'
            )
        text_parts.append("")
        html_parts.append("</ul>")

    _append_section("Strong", strong)
    _append_section("Maybe", maybe)

    return subject, "\n".join(text_parts).strip() + "\n", "\n".join(html_parts)


def format_match_line(match: Any) -> str:
    """One compact email line per match (reasons capped for display)."""
    return (
        f"{match.title} — {match.company} — {_posted_display(match)} — "
        f"{_short_reason(match)} — {match.url}"
    )


def _posted_display(match: Any) -> str:
    posted = getattr(match, "posted_date", "") or ""
    posted = str(posted).strip()
    return posted if posted else "unknown"


def _short_reason(match: Any) -> str:
    reason = " ".join(str(getattr(match, "reasoning", "") or "").split())
    if len(reason) <= REASON_MAX_CHARS:
        return reason
    return reason[: REASON_MAX_CHARS - 1].rstrip() + "…"


def send_email(
    *,
    subject: str,
    text: str,
    html: str,
    api_key: str | None = None,
    to_email: str | Sequence[str] | None = None,
    from_email: str | None = None,
) -> dict[str, Any]:
    key = api_key or load_env_var("RESEND_API_KEY")
    if to_email is None:
        recipients = [load_env_var("TO_EMAIL", default=DEFAULT_TO_EMAIL)]
    elif isinstance(to_email, str):
        recipients = [to_email]
    else:
        recipients = [addr for addr in to_email if addr]
    if not recipients:
        raise RuntimeError("no email recipients configured")
    from_addr = from_email or load_env_var("FROM_EMAIL", default=DEFAULT_FROM_EMAIL)

    payload = {
        "from": from_addr,
        "to": recipients,
        "subject": subject,
        "text": text,
        "html": html,
    }
    request = urllib.request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "jobFinderAgent/0.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend HTTP {exc.code}: {detail[:500]}") from exc

    logger.info("email sent to %s via Resend id=%s", recipients, body.get("id"))
    return body


def illinois_recipients() -> list[str]:
    """Recipients for the separate Illinois reminder email."""
    raw = None
    try:
        raw = load_env_var("ILLINOIS_TO_EMAILS")
    except RuntimeError:
        raw = None
    if raw:
        return [part.strip() for part in raw.split(",") if part.strip()]
    return list(DEFAULT_ILLINOIS_TO_EMAILS)


def deliver_matches(
    matches: Sequence[Any],
    *,
    dry_run: bool = False,
    send: bool = False,
) -> bool:
    """Build and optionally send. Returns True if an email was produced."""
    if dry_run and send:
        raise ValueError("pass only one of dry_run or send")

    built = build_email(matches)
    if built is None:
        logger.info("no strong/maybe matches — skipping email")
        print("No strong/maybe matches — email skipped.")
        return False

    subject, text, html = built
    to_addr = load_env_var("TO_EMAIL", default=DEFAULT_TO_EMAIL)

    if dry_run:
        print("=== DRY RUN EMAIL ===")
        print(f"To: {to_addr}")
        print(f"Subject: {subject}")
        print()
        print(text)
        print("=== END DRY RUN (not sent) ===")
        return True

    if send:
        send_email(subject=subject, text=text, html=html, to_email=to_addr)
        print(f"Email sent to {to_addr}: {subject}")
        return True

    return False


def deliver_illinois_reminder(
    *,
    count: int,
    software_count: int,
    analyst_count: int,
    board_url: str,
    dry_run: bool = False,
    send: bool = False,
) -> bool:
    """If count > 0, send a minimal separate reminder (not fit-matching)."""
    if dry_run and send:
        raise ValueError("pass only one of dry_run or send")
    if count <= 0:
        logger.info("Illinois CSOD: 0 postings within 1 day — reminder skipped")
        print("Illinois CSOD: 0 jobs today — reminder skipped.")
        return False

    subject = f"Illinois careers: {count} new job(s) today"
    text = (
        f"{count} new jobs found today.\n"
        f"a software jobs: {software_count}\n"
        f"b analyst jobs: {analyst_count}\n"
        f"\nBoard: {board_url}\n"
    )
    html = (
        f"<p><strong>{count} new jobs found today.</strong></p>"
        f"<p>a software jobs: {software_count}<br>"
        f"b analyst jobs: {analyst_count}</p>"
        f'<p><a href="{board_url}">Open Illinois career board</a></p>'
    )
    recipients = illinois_recipients()

    if dry_run:
        print("=== DRY RUN ILLINOIS REMINDER ===")
        print(f"To: {', '.join(recipients)}")
        print(f"Subject: {subject}")
        print()
        print(text)
        print("=== END DRY RUN (not sent) ===")
        return True

    if send:
        send_email(subject=subject, text=text, html=html, to_email=recipients)
        print(f"Illinois reminder sent to {', '.join(recipients)}: {subject}")
        return True

    return False


def deliver_research_park_reminder(
    *,
    count: int,
    software_count: int,
    intern_count: int,
    board_url: str,
    dry_run: bool = False,
    send: bool = False,
) -> bool:
    """If count > 0, send a minimal Research Park reminder (not fit-matching)."""
    if dry_run and send:
        raise ValueError("pass only one of dry_run or send")
    if count <= 0:
        logger.info("Research Park: 0 postings within 1 day — reminder skipped")
        print("Research Park: 0 jobs today — reminder skipped.")
        return False

    subject = f"Research Park careers: {count} new job(s) today"
    text = (
        f"{count} new Research Park job(s) found today.\n"
        f"software/eng/dev titles: {software_count}\n"
        f"intern titles: {intern_count}\n"
        f"\nBoard: {board_url}\n"
    )
    html = (
        f"<p><strong>{count} new Research Park job(s) found today.</strong></p>"
        f"<p>software/eng/dev titles: {software_count}<br>"
        f"intern titles: {intern_count}</p>"
        f'<p><a href="{board_url}">Open Research Park job board</a></p>'
    )
    to_addr = load_env_var("TO_EMAIL", default=DEFAULT_TO_EMAIL)

    if dry_run:
        print("=== DRY RUN RESEARCH PARK REMINDER ===")
        print(f"To: {to_addr}")
        print(f"Subject: {subject}")
        print()
        print(text)
        print("=== END DRY RUN (not sent) ===")
        return True

    if send:
        send_email(subject=subject, text=text, html=html, to_email=to_addr)
        print(f"Research Park reminder sent to {to_addr}: {subject}")
        return True

    return False


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
