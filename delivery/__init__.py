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
NOTIFY_FITS = frozenset({"strong", "maybe"})


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
    """Return (subject, text, html) or None when there is nothing worth sending."""
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
        "Daily job search summary",
        f"{len(strong)} strong · {len(maybe)} maybe",
        "",
    ]
    html_parts = [
        "<h2>Daily job search summary</h2>",
        f"<p><strong>{len(strong)}</strong> strong · <strong>{len(maybe)}</strong> maybe</p>",
    ]

    def add_section(label: str, items: list[Any]) -> None:
        if not items:
            return
        text_parts.append(f"== {label} ==")
        html_parts.append(f"<h3>{label}</h3><ul>")
        for m in items:
            posted = getattr(m, "posted_date", "") or "unknown"
            text_parts.extend(
                [
                    f"[{m.fit.upper()}] {m.company} — {m.title}",
                    f"  Posted: {posted}",
                    f"  {m.location}",
                    f"  {m.url}",
                    f"  {m.reasoning}",
                    "",
                ]
            )
            html_parts.append(
                "<li>"
                f"<p><strong>[{m.fit.upper()}] {m.company} — {m.title}</strong><br>"
                f"Posted: {_escape(posted)}<br>"
                f"{_escape(m.location)}<br>"
                f'<a href="{m.url}">{m.url}</a></p>'
                f"<p>{_escape(m.reasoning)}</p>"
                "</li>"
            )
        html_parts.append("</ul>")

    add_section("STRONG", strong)
    add_section("MAYBE", maybe)

    return subject, "\n".join(text_parts).strip() + "\n", "\n".join(html_parts)


def send_email(
    *,
    subject: str,
    text: str,
    html: str,
    api_key: str | None = None,
    to_email: str | None = None,
    from_email: str | None = None,
) -> dict[str, Any]:
    key = api_key or load_env_var("RESEND_API_KEY")
    to_addr = to_email or load_env_var("TO_EMAIL", default=DEFAULT_TO_EMAIL)
    from_addr = from_email or load_env_var("FROM_EMAIL", default=DEFAULT_FROM_EMAIL)

    payload = {
        "from": from_addr,
        "to": [to_addr],
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

    logger.info("email sent to %s via Resend id=%s", to_addr, body.get("id"))
    return body


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
    titles: Sequence[str],
    board_url: str,
    dry_run: bool = False,
    send: bool = False,
) -> bool:
    """If count > 0, remind the user to check the Illinois CSOD board."""
    if dry_run and send:
        raise ValueError("pass only one of dry_run or send")
    if count <= 0:
        logger.info("Illinois CSOD: 0 postings within 1 day — reminder skipped")
        print("Illinois CSOD: 0 jobs today — reminder skipped.")
        return False

    subject = f"Illinois careers: {count} job(s) posted within 1 day"
    title_lines = "\n".join(f"- {t}" for t in titles) or "- (titles unavailable)"
    text = (
        f"{count} jobs found from this page (posted within ~1 day).\n"
        f"Open the board and review manually:\n{board_url}\n\n"
        f"Titles returned by the board:\n{title_lines}\n"
    )
    html_titles = "".join(f"<li>{_escape(t)}</li>" for t in titles) or "<li>(titles unavailable)</li>"
    html = (
        f"<p><strong>{count} jobs found from this page</strong> "
        f"(posted within ~1 day).</p>"
        f'<p><a href="{board_url}">Open the Illinois career board</a></p>'
        f"<p>Titles:</p><ul>{html_titles}</ul>"
    )
    to_addr = load_env_var("TO_EMAIL", default=DEFAULT_TO_EMAIL)

    if dry_run:
        print("=== DRY RUN ILLINOIS REMINDER ===")
        print(f"To: {to_addr}")
        print(f"Subject: {subject}")
        print()
        print(text)
        print("=== END DRY RUN (not sent) ===")
        return True

    if send:
        send_email(subject=subject, text=text, html=html, to_email=to_addr)
        print(f"Illinois reminder sent to {to_addr}: {subject}")
        return True

    return False


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
