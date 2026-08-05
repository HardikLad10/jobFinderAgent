"""Claude Haiku fit-matching — the one agentic step.

Deterministic filters already ran. This module only answers: does this
posting fit the candidate profile, and why.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from filtering import FilteredJob

logger = logging.getLogger(__name__)

DEFAULT_RESUME_PATH = Path(__file__).resolve().parent.parent / "config" / "resume_profile.md"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
# Alias resolves to the current Haiku 4.5 snapshot (PROJECT_BRIEF model choice).
DEFAULT_MODEL = "claude-haiku-4-5"
MAX_DESCRIPTION_CHARS = 6000


@dataclass(frozen=True)
class MatchResult:
    title: str
    company: str
    location: str
    url: str
    posted_date: str
    sponsorship_flag: str
    fit: str  # strong | maybe | no
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
    limit: int | None = None,
) -> list[MatchResult]:
    profile = resume if resume is not None else load_resume()
    key = api_key if api_key is not None else load_api_key()

    targets = jobs if limit is None else jobs[:limit]
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
        try:
            fit, reasoning = _call_claude(
                api_key=key,
                model=model,
                resume=profile,
                posting=posting,
            )
        except Exception as exc:  # noqa: BLE001 — one bad call must not kill the run
            logger.error("match failed for %s (%s): %s", posting.title, posting.url, exc)
            fit, reasoning = "error", f"match call failed: {exc}"

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
            )
        )

    return results


def _call_claude(
    *,
    api_key: str,
    model: str,
    resume: str,
    posting: Any,
) -> tuple[str, str]:
    description = posting.description[:MAX_DESCRIPTION_CHARS]
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
        "max_tokens": 300,
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
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic HTTP {exc.code}: {detail[:500]}") from exc

    text = _extract_text(body)
    return _parse_fit_json(text)


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
    # Model sometimes wraps JSON in fences; pull the first object.
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    raw = match.group(0) if match else text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return "maybe", text.strip()[:500]

    fit = str(data.get("fit", "maybe")).strip().lower()
    if fit not in {"strong", "maybe", "no"}:
        fit = "maybe"
    reasoning = str(data.get("reasoning", "")).strip() or text.strip()[:500]
    return fit, reasoning
