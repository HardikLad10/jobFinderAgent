"""Claude Opus fit-matching — the one agentic step.

Deterministic filters already ran. This module only answers: does this
posting fit the candidate profile, and why.

Guardrails (PROJECT_BRIEF §7a):
- Fail-closed: malformed/unknown fit → invalid; API failures → error.
- One in-run retry with backoff on transient Anthropic errors.
- Quarantine after 3 invalid/error attempts (data/quarantine.json).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from filtering import FilteredJob
from matching.quarantine import (
    clear_failure,
    load_quarantine,
    quarantined_urls,
    record_failure,
    save_quarantine,
)

logger = logging.getLogger(__name__)

DEFAULT_RESUME_PATH = Path(__file__).resolve().parent.parent / "config" / "resume_profile.md"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_EFFORT = "medium"
DEFAULT_MAX_TOKENS = 4096
REQUEST_TIMEOUT_SECONDS = 120
VALID_FITS = frozenset({"strong", "maybe", "no"})
FAIL_CLOSED_FITS = frozenset({"invalid", "error"})
RETRY_WAIT_SECONDS = 2.0


@dataclass(frozen=True)
class MatchResult:
    title: str
    company: str
    location: str
    url: str
    posted_date: str
    sponsorship_flag: str
    fit: str  # strong | maybe | no | invalid | error
    reasoning: str
    model: str = DEFAULT_MODEL
    effort: str = DEFAULT_EFFORT
    input_tokens: int | None = None
    output_tokens: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_scored(self) -> bool:
        return self.fit in VALID_FITS

    @property
    def is_fail_closed(self) -> bool:
        return self.fit in FAIL_CLOSED_FITS


def load_resume(path: Path | None = None) -> str:
    resume_path = path or DEFAULT_RESUME_PATH
    text = resume_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"resume profile is empty: {resume_path}")
    return text


def load_api_key(env_path: Path | None = None) -> str:
    """Read ANTHROPIC_API_KEY from process env or local .env (no dotenv dep)."""
    existing = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if existing:
        return existing

    path = env_path or Path(__file__).resolve().parent.parent / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == "ANTHROPIC_API_KEY":
                token = value.strip().strip('"').strip("'")
                if token:
                    return token
    raise RuntimeError(
        "ANTHROPIC_API_KEY not set. Paste it into .env or export it in the shell."
    )


def match_jobs(
    jobs: list[FilteredJob],
    *,
    resume: str | None = None,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EFFORT,
    limit: int | None = None,
    persist_quarantine: bool = True,
) -> list[MatchResult]:
    profile = resume if resume is not None else load_resume()
    key = api_key if api_key is not None else load_api_key()

    qstore = load_quarantine()
    blocked = quarantined_urls(qstore)
    eligible = [item for item in jobs if item.posting.url not in blocked]
    skipped = len(jobs) - len(eligible)
    if skipped:
        logger.info("skipping %d quarantined URL(s)", skipped)

    targets = eligible if limit is None else eligible[:limit]
    results: list[MatchResult] = []

    for index, item in enumerate(targets, start=1):
        posting = item.posting
        logger.info(
            "matching %d/%d: %s — %s",
            index,
            len(targets),
            posting.company,
            posting.title,
        )
        fit, reasoning, usage = _score_with_retry(
            api_key=key,
            model=model,
            effort=effort,
            resume=profile,
            posting=posting,
        )
        if fit in FAIL_CLOSED_FITS:
            record_failure(qstore, posting.url, error=f"{fit}: {reasoning}")
        else:
            clear_failure(qstore, posting.url)

        results.append(
            MatchResult(
                title=posting.title,
                company=posting.company,
                location=posting.location,
                url=posting.url,
                posted_date=posting.posted_date,
                sponsorship_flag=item.sponsorship_flag,
                fit=fit,
                reasoning=reasoning,
                model=model,
                effort=effort,
                input_tokens=(usage or {}).get("input_tokens"),
                output_tokens=(usage or {}).get("output_tokens"),
            )
        )

    if persist_quarantine:
        save_quarantine(qstore)

    return results


def _score_with_retry(
    *,
    api_key: str,
    model: str,
    effort: str,
    resume: str,
    posting: Any,
) -> tuple[str, str, dict[str, int] | None]:
    """One retry with backoff on transport/API failures; parse is fail-closed."""
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            return _call_claude(
                api_key=api_key,
                model=model,
                effort=effort,
                resume=resume,
                posting=posting,
            )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.error(
                "match attempt %d failed for %s (%s): %s",
                attempt + 1,
                posting.title,
                posting.url,
                exc,
            )
            if attempt == 0:
                time.sleep(RETRY_WAIT_SECONDS)
    return "error", f"match call failed: {last_exc}", None


def _call_claude(
    *,
    api_key: str,
    model: str,
    effort: str,
    resume: str,
    posting: Any,
) -> tuple[str, str, dict[str, int] | None]:
    description = posting.description or ""
    user_prompt = f"""You are scoring fit between a candidate profile and one job posting.

Return ONLY valid JSON with this exact shape:
{{"fit":"strong"|"maybe"|"no","reasoning":"<2-4 sentences>"}}

Rules:
- strong: clear overlap on role level, stack, and domain; worth applying soon
- maybe: partial overlap or stretch; still worth a look
- no: clear mismatch on seniority, domain, or required skills
- Be concrete. Cite specific overlaps or gaps from the texts below.
- Do not invent experience the profile does not claim.

## Candidate profile
{resume}

## Job posting
Title: {posting.title}
Company: {posting.company}
Location: {posting.location}
Posted: {posting.posted_date}
URL: {posting.url}

Description:
{description}
"""

    payload = {
        "model": model,
        "max_tokens": DEFAULT_MAX_TOKENS,
        "output_config": {"effort": effort},
        "messages": [{"role": "user", "content": user_prompt}],
    }
    request = urllib.request.Request(
        ANTHROPIC_MESSAGES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "user-agent": "jobFinderAgent/0.1",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic HTTP {exc.code}: {detail[:500]}") from exc

    text = _extract_text(body)
    fit, reasoning = _parse_fit_json(text)
    usage = _extract_usage(body)
    return fit, reasoning, usage


def _extract_usage(body: dict[str, Any]) -> dict[str, int] | None:
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return None
    out: dict[str, int] = {}
    for key in ("input_tokens", "output_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            out[key] = value
    return out or None


def _extract_text(body: dict[str, Any]) -> str:
    content = body.get("content")
    if not isinstance(content, list):
        raise RuntimeError(f"unexpected Anthropic response: {body!r}"[:400])
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("Anthropic response contained no text blocks")
    return text


def _parse_fit_json(text: str) -> tuple[str, str]:
    """Fail-closed: bad JSON or unknown fit → invalid (never maybe)."""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    raw = match.group(0) if match else text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return "invalid", f"malformed model JSON: {text.strip()[:500]}"

    if not isinstance(data, dict):
        return "invalid", f"model JSON was not an object: {text.strip()[:500]}"

    fit = str(data.get("fit", "")).strip().lower()
    if fit not in VALID_FITS:
        return "invalid", f"unknown fit {fit!r}: {text.strip()[:500]}"

    reasoning = str(data.get("reasoning", "")).strip() or text.strip()[:500]
    return fit, reasoning
