"""Tiny HTTP helper shared by ATS clients. Stdlib only — one GET each."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .errors import IngestionError

REQUEST_TIMEOUT_SECONDS = 30
USER_AGENT = "jobFinderAgent/0.1"


def get_json(url: str, *, company_name: str) -> Any:
    body = get_text(url, company_name=company_name, accept="application/json")
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise IngestionError(
            f"{company_name}: malformed JSON from {url}: {exc}"
        ) from exc


def get_text(url: str, *, company_name: str, accept: str = "text/html,*/*") -> str:
    request = urllib.request.Request(
        url,
        headers={"Accept": accept, "User-Agent": USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = getattr(response, "status", None) or response.getcode()
    except urllib.error.HTTPError as exc:
        raise IngestionError(
            f"{company_name}: HTTP {exc.code} for {url}"
        ) from exc
    except urllib.error.URLError as exc:
        raise IngestionError(
            f"{company_name}: network error fetching {url}: {exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise IngestionError(f"{company_name}: timed out fetching {url}") from exc

    if status != 200:
        raise IngestionError(f"{company_name}: unexpected HTTP {status} for {url}")
    return body
