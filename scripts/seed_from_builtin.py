#!/usr/bin/env python3
"""Build Midwest tech employer seed from Built In public directories.

Pulls company listings via the public SearchResults handler (HTML partials),
then drops names already present in companies.json / prior seeds.

Supports Chicago software, Chicago all-types (`--all-chicago`), and adjacent
metros (Milwaukee, Indianapolis, Detroit). Not part of the daily pipeline.
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "config" / "builtin_chicago_software_seed.json"

# Chicago software directory — high G/L/A/Breezy hit-rate vs full 6k listing.
DEFAULT_BASES = (
    "https://www.builtinchicago.org/companies/type/software-companies",
)
CHICAGO_ALL_COMPANIES = "https://www.builtinchicago.org/companies"

# Neighbor metros with working builtin.com location filters.
ADJACENT_METRO_SOFTWARE = (
    "https://www.builtin.com/companies/location/milwaukee/type/software-companies",
    "https://www.builtin.com/companies/location/indianapolis/type/software-companies",
    "https://www.builtin.com/companies/location/detroit/type/software-companies",
)

H2_RE = re.compile(r"<h2[^>]*>\s*([^<]+?)\s*</h2>", re.I)
ALIAS_RE = re.compile(r'data-company-alias="(/company/[^"]+)"')

# Same body-shop / consult cut as LCA seed (full Chicago list is noisy).
CONSULT_NAME_RE = re.compile(
    r"\b("
    r"INFOSYS|TATA|WIPRO|COGNIZANT|HCL\b|TECH MAHINDRA|LTIMINDTREE|MINDTREE|"
    r"ACCENTURE|CAPGEMINI|DELOITTE|ERNST\s*&\s*YOUNG|\bEY\b|KPMG|PRICEWATER|PWC\b|"
    r"IBM\b|HTC GLOBAL|GLOBALLOGIC|HEXAWARE|YASH TECHNOLOGIES|COMPUNNEL|"
    r"PERSISTENT|MPHASIS|LARSEN|LTI\b|"
    r"CONSULTING|CONSULTANTS|STAFFING|GLOBAL SERVICES"
    r")\b",
    re.I,
)
LLC_RE = re.compile(r"\bL\.?L\.?C\.?\b", re.I)
LLP_RE = re.compile(r"\bL\.?L\.?P\.?\b", re.I)
LLC_NOISE_TOKENS = (
    "STAFFING",
    "CONSULTING",
    "CONSULTANT",
    "CONSULTANTS",
    "SOLUTIONS",
    "SERVICES",
    "TECHNOLOGIES",
    "TECHNOLOGY",
    "OUTSOURCE",
    "OUTSOURCING",
    "CONTRACTOR",
    "CONTRACTING",
    "RECRUIT",
    "TALENT",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        nargs="*",
        default=list(DEFAULT_BASES),
        help="One or more Built In directory URLs to paginate",
    )
    parser.add_argument(
        "--adjacent-metros",
        action="store_true",
        help="Use Milwaukee + Indianapolis + Detroit software directories",
    )
    parser.add_argument(
        "--all-chicago",
        action="store_true",
        help="Full Built In Chicago companies directory (all types, ~6.5k)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--sleep", type=float, default=0.35, help="Delay between pages")
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument(
        "--companies",
        type=Path,
        default=ROOT / "config" / "companies.json",
        help="Existing companies to exclude",
    )
    parser.add_argument(
        "--also-exclude",
        type=Path,
        nargs="*",
        default=[
            ROOT / "config" / "lca_midwest_swe_seed.json",
            ROOT / "config" / "midwest_seed.json",
            ROOT / "config" / "builtin_chicago_software_seed.json",
            ROOT / "config" / "builtin_adjacent_metros_software_seed.json",
        ],
        help="Extra name lists to exclude (LCA / prior seeds)",
    )
    args = parser.parse_args()

    if args.all_chicago:
        bases = [CHICAGO_ALL_COMPANIES]
        if args.max_pages == 200:
            args.max_pages = 400
    elif args.adjacent_metros:
        bases = list(ADJACENT_METRO_SOFTWARE)
    else:
        bases = list(args.base_url)
    if not bases:
        raise SystemExit("no --base-url provided")

    names: list[str] = []
    seen: set[str] = set()

    for base in bases:
        label = _label_for(base)
        print(f"\n=== Scraping {label} ===", flush=True)
        empty_streak = 0
        referer = base.split("?")[0]
        for page in range(1, args.max_pages + 1):
            url = f"{base}?handler=SearchResults&page={page}"
            body = _get(url, referer=referer)
            page_names = [
                html_lib.unescape(m.group(1)).strip() for m in H2_RE.finditer(body)
            ]
            page_names = [n for n in page_names if n]
            if len(page_names) <= 1:
                empty_streak += 1
                if empty_streak >= 2:
                    print(f"  stopping at page {page} (empty results)", flush=True)
                    break
            else:
                empty_streak = 0

            added = 0
            for name in page_names:
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                names.append(name)
                added += 1
            print(f"  page {page}: +{added} (total {len(names)})", flush=True)
            time.sleep(args.sleep)

    exclude = _load_exclude_names(args.companies, args.also_exclude)
    dropped_noise = 0
    fresh: list[str] = []
    for n in names:
        if _norm(n) in exclude:
            continue
        if _drop_reason(n):
            dropped_noise += 1
            continue
        fresh.append(n)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")

    print("\n=== Built In seed stats ===")
    print(f"  scraped_unique: {len(names)}")
    print(f"  excluded_existing: {len(names) - len(fresh) - dropped_noise}")
    print(f"  dropped_consult_noise: {dropped_noise}")
    print(f"  new_for_discovery: {len(fresh)}")
    print(f"Wrote {args.out}")
    print("Sample new:")
    for n in fresh[:15]:
        print(f"  {n}")
    return 0


def _label_for(base: str) -> str:
    path = urlparse(base).path.strip("/").lower()
    for metro in ("milwaukee", "indianapolis", "detroit", "chicago"):
        if metro in path:
            return metro
    return path or base


def _get(url: str, *, referer: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Mozilla/5.0 (compatible; jobFinderAgent-builtin-seed/0.1)",
            "Referer": referer,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} for {url}") from exc


def _norm(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(
        r"\b(inc|llc|corp|corporation|co|company|ltd|lp|the|group)\b",
        "",
        s,
    )
    return " ".join(s.split())


def _drop_reason(name: str) -> str | None:
    if LLP_RE.search(name):
        return "llp"
    if CONSULT_NAME_RE.search(name):
        return "consult_pattern"
    if LLC_RE.search(name):
        upper = name.upper()
        if any(tok in upper for tok in LLC_NOISE_TOKENS):
            return "llc_noise"
    return None


def _load_exclude_names(companies_path: Path, extra_paths: list[Path]) -> set[str]:
    out: set[str] = set()
    if companies_path.exists():
        data = json.loads(companies_path.read_text(encoding="utf-8"))
        for row in data:
            if isinstance(row, dict) and row.get("name"):
                out.add(_norm(str(row["name"])))
            elif isinstance(row, str):
                out.add(_norm(row))
    for path in extra_paths:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    out.add(_norm(item))
                elif isinstance(item, dict) and item.get("name"):
                    out.add(_norm(str(item["name"])))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
