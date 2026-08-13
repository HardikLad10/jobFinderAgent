#!/usr/bin/env python3
"""ATS board discovery for Midwest seed list.

Probes Greenhouse / Lever / Ashby / BreezyHR / SmartRecruiters / Workable /
Recruitee public endpoints with slug candidates. Prefers longer/specific
tokens; short first-word guesses are only used when listed in ALIASES
(avoids capital/village/echo false positives).

Not part of the scheduled pipeline — manual discovery helper.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = ROOT / "config" / "midwest_seed.json"
DEFAULT_OUT = ROOT / "config" / "companies.discovered.json"

# Extra slug aliases when the company name does not match the board token.
ALIASES: dict[str, list[str]] = {
    "Sprout Social": ["sproutsocial"],
    "Discover Financial Services": ["discover", "discoverfinancial", "discoverfinancialservices"],
    "Cboe Global Markets": ["cboe", "cboeglobalmarkets"],
    "Guaranteed Rate": ["guaranteedrate", "rate"],
    "Kin Insurance": ["kin", "kininsurance"],
    "CCC Intelligent Solutions": ["ccc", "cccis", "cccintelligentsolutions"],
    "Origami Risk": ["origami", "origamirisk"],
    "tastytrade": ["tastytrade", "tastyworks"],
    "Capital One": ["capitalone"],
    "Enova International": ["enova", "enovainternational"],
    "Tempus": ["tempus", "tempuslabs", "tempusai"],
    "Tempus Labs": ["tempus", "tempuslabs"],
    "Tempus AI": ["tempus", "tempusai", "tempuslabs"],
    "VillageMD": ["villagemd"],
    "Echo Global Logistics": ["echoglobal", "echogloballogistics"],
    "Coyote Logistics": ["coyote", "coyotelogistics"],
    "ActiveCampaign": ["activecampaign"],
    "Civis Analytics": ["civis", "civisanalytics"],
    "Cars.com": ["cars", "carsdotcom", "carscom"],
    "Cars Commerce": ["carscommerce", "cars"],
    "Motorola Solutions": ["motorolasolutions", "motorola"],
    "Halo Investing": ["haloinvesting", "halo"],
    "37signals": ["37signals", "basecamp"],
    "Block": ["block", "square", "cashapp", "joinblock"],
    "Block Inc": ["block", "joinblock"],
    "project44": ["project44", "p44"],
    "G2": ["g2", "g2crowd"],
    "G2.com": ["g2", "g2crowd"],
    "ALIS": ["alis", "alishealth"],
    "Artera": ["artera", "arteraai"],
    "Coro": ["coro"],
    "Vouch": ["vouch", "vouchinsurance"],
    "Lessen": ["lessen"],
    "Centro": ["centro", "basis", "basistechnologies"],
    "Basis Technologies": ["basis", "basistechnologies"],
    "Upside": ["upside"],
    "Upside Foods": ["upsidefoods", "upside"],
    "Metropolis": ["metropolis", "metropolistech"],
    "Cleo": ["cleo", "cleocommunications"],
    "Cleo Communications": ["cleo", "cleocommunications"],
    "Relativity": ["relativityone", "relativityoda"],
    "Relativity ODA": ["relativityone", "relativityoda"],
    "PowerReviews": ["powerreviews"],
    "OpenGov": ["opengov"],
    "Paylocity": ["paylocity"],
    "Uptake": ["uptake"],
    "HealthJoy": ["healthjoy"],
    "Clearcover": ["clearcover"],
    "FourKites": ["fourkites"],
    "Klaviyo": ["klaviyo"],
    "ShipBob": ["shipbob"],
    "Cameo": ["cameo"],
    "SpotHero": ["spothero"],
    "Tovala": ["tovala"],
    "Reverb": ["reverb"],
    "Groupon": ["groupon"],
    "Morningstar": ["morningstar"],
    "Fooda": ["fooda"],
    "ParkWhiz": ["parkwhiz"],
    "Fetch Rewards": ["fetch", "fetchrewards"],
    "LogicGate": ["logicgate"],
    "Built In": ["builtin", "builtinchicago"],
    "Packback": ["packback"],
    "Wolfram Research": ["wolfram", "wolframresearch"],
    "Epic Systems": ["epic", "epicsystems"],
    "GE HealthCare": ["gehealthcare", "gehealth"],
    "Oak Street Health": ["oakstreethealth", "oakstreet"],
    "Chicago Trading Company": ["ctc", "chicagotrading"],
    "Options Clearing Corporation": ["theocc", "occ"],
    "CME Group": ["cmegroup", "cme"],
    "Jump Trading": ["jumptrading", "jump"],
    "Citadel Securities": ["citadelsecurities", "citadel"],
    "Akuna Capital": ["akunacapital", "akuna"],
    "Belvedere Trading": ["belvederetrading", "belvedere"],
    "IMC Trading": ["imc", "imctrading"],
    "Hudson River Trading": ["hrt", "hudsonrivertrading"],
    "S&P Global": ["spglobal", "s&pglobal"],
    "HCSC": ["hcsc"],
    "Blue Cross Blue Shield of Illinois": ["bcbsil", "bcbs"],
    "John Deere": ["johndeere", "deere"],
    "CNH Industrial": ["cnh", "cnhindustrial"],
    "Kraft Heinz": ["kraftheinz"],
    "Mars Wrigley": ["marswrigley", "wrigley"],
    "DoorDash": ["doordash"],
    "Instacart": ["instacart"],
    "GoPuff": ["gopuff"],
    "1Password": ["1password"],
    "6sense": ["6sense"],
    "Apollo.io": ["apolloio", "apollo"],
    "dbt Labs": ["dbtlabs", "dbt"],
    "H2O.ai": ["h2oai", "h2o"],
    "Owner.com": ["owner", "ownercom"],
    "Bill.com": ["billcom", "bill"],
}


def slugify(name: str) -> list[str]:
    base = name.lower().strip()
    # Strip common legal suffixes before slugifying.
    base = re.sub(
        r"\b(inc|llc|ltd|corp|corporation|company|co|group|holdings|plc|nv|sa|ag|gmbh)\b\.?",
        "",
        base,
    )
    base = re.sub(r"\s+", " ", base).strip(" ,.-")
    variants: list[str] = []
    for raw in (
        re.sub(r"[^a-z0-9]", "", base),
        re.sub(r"[^a-z0-9]+", "-", base).strip("-"),
        re.sub(r"[^a-z0-9]+", "_", base).strip("_"),
    ):
        if raw and raw not in variants:
            variants.append(raw)
    return variants


def candidates_for(name: str) -> list[str]:
    """Prefer specific aliases + full-name slugs; skip bare short first words."""
    seen: list[str] = []
    for token in ALIASES.get(name, []) + slugify(name):
        if not token or token in seen:
            continue
        # Guard: very short tokens only if explicitly aliased.
        if len(token) < 5 and token not in ALIASES.get(name, []):
            continue
        seen.append(token)
    return seen


def http_get(url: str, timeout: float = 12.0) -> tuple[int, Any | None]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/html,*/*",
            "User-Agent": "Mozilla/5.0 (compatible; jobFinderAgent-discover/0.2)",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = getattr(resp, "status", None) or resp.getcode()
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except Exception:
        return -1, None

    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, None


def try_greenhouse(token: str) -> tuple[bool, int, str | None]:
    status, data = http_get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs")
    if status == 200 and isinstance(data, dict) and isinstance(data.get("jobs"), list):
        sample = None
        if data["jobs"]:
            sample = str(data["jobs"][0].get("title") or "")[:80]
        return True, len(data["jobs"]), sample
    return False, 0, None


def try_lever(token: str) -> tuple[bool, int, str | None]:
    status, data = http_get(f"https://api.lever.co/v0/postings/{token}?mode=json")
    if status == 200 and isinstance(data, list):
        sample = None
        if data:
            sample = str(data[0].get("text") or "")[:80]
        return True, len(data), sample
    return False, 0, None


def try_ashby(token: str) -> tuple[bool, int, str | None]:
    status, data = http_get(f"https://api.ashbyhq.com/posting-api/job-board/{token}")
    if status == 200 and isinstance(data, dict) and isinstance(data.get("jobs"), list):
        sample = None
        if data["jobs"]:
            sample = str(data["jobs"][0].get("title") or "")[:80]
        return True, len(data["jobs"]), sample
    return False, 0, None


def try_breezy(token: str) -> tuple[bool, int, str | None]:
    # Public feed; empty list can mean valid board with no jobs — treat as hit
    # only if JSON list and company metadata present, OR non-empty jobs.
    status, data = http_get(f"https://{token}.breezy.hr/json")
    if status != 200 or not isinstance(data, list):
        return False, 0, None
    if not data:
        # Ambiguous empty board — skip to avoid false positives on parking lots.
        return False, 0, None
    sample = str(data[0].get("name") or "")[:80]
    company = ""
    comp = data[0].get("company")
    if isinstance(comp, dict):
        company = str(comp.get("name") or "")
    hint = f"{sample} | {company}".strip(" |")
    return True, len(data), hint or None


def try_smartrecruiters(token: str) -> tuple[bool, int, str | None]:
    # Unknown identifiers return 200 + totalFound=0. Require real postings.
    status, data = http_get(
        f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=10&offset=0"
    )
    if status != 200 or not isinstance(data, dict):
        return False, 0, None
    content = data.get("content")
    if not isinstance(content, list) or not content:
        return False, 0, None
    total = data.get("totalFound")
    count = int(total) if isinstance(total, int) and total > 0 else len(content)
    sample = str(content[0].get("name") or "")[:80]
    return True, count, sample or None


def try_workable(token: str) -> tuple[bool, int, str | None]:
    status, data = http_get(
        f"https://apply.workable.com/api/v1/widget/accounts/{token}?details=false"
    )
    if status != 200 or not isinstance(data, dict):
        return False, 0, None
    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        return False, 0, None
    sample = str(jobs[0].get("title") or "")[:80]
    company = str(data.get("name") or "")
    hint = f"{sample} | {company}".strip(" |")
    return True, len(jobs), hint or None


def try_recruitee(token: str) -> tuple[bool, int, str | None]:
    status, data = http_get(f"https://{token}.recruitee.com/api/offers/")
    if status != 200 or not isinstance(data, dict):
        return False, 0, None
    offers = data.get("offers")
    if not isinstance(offers, list) or not offers:
        return False, 0, None
    sample = str(offers[0].get("title") or "")[:80]
    return True, len(offers), sample or None


PROBES: tuple[tuple[str, Callable[[str], tuple[bool, int, str | None]]], ...] = (
    ("greenhouse", try_greenhouse),
    ("lever", try_lever),
    ("ashby", try_ashby),
    ("breezy", try_breezy),
    ("smartrecruiters", try_smartrecruiters),
    ("workable", try_workable),
    ("recruitee", try_recruitee),
)

# Known false-positive (ats, token) pairs from prior discovery.
KNOWN_FALSE_POSITIVES: set[tuple[str, str]] = {
    ("lever", "capital"),
    ("greenhouse", "village"),
    ("greenhouse", "relativity"),
    ("greenhouse", "echo"),
    ("greenhouse", "cleo"),
    ("ashby", "upside"),  # Upside Foods vs Upside services — skip auto-resolve
    ("breezy", "katapult"),  # Katapult Network ≠ Katapult Holdings
    ("greenhouse", "fetch"),  # not Fetch Rewards
    ("greenhouse", "indigo"),  # not Indigo Ag
    ("recruitee", "allstate"),  # sample/demo board
    ("recruitee", "adecco"),
    ("ashby", "wilson"),  # WilsonAI ≠ Chicago Wilson
    ("ashby", "graphite"),  # Graphite code-review ≠ Chicago Graphite
    ("ashby", "pinecone"),  # Pinecone vector DB ≠ Chicago listing
    ("ashby", "gorilla"),  # Gorilla energy ≠ Gorilla Group
    ("ashby", "ampersand"),  # Ampersand SF ≠ Chicago Ampersand
    ("lever", "horizon"),  # Horizon Robotics ≠ Chicago Horizon
    ("lever", "mantra"),  # Tokyo Mantra ≠ Chicago Mantra, Inc.
    ("lever", "kepler"),  # Kepler Communications ≠ Kepler Group
    ("lever", "plexus"),  # legal-tech board ≠ Plexus Corp.
    ("lever", "factor"),  # Factor ALSP ≠ Chicago Factor
    ("greenhouse", "gemini"),  # Gemini crypto ≠ Chicago Gemini
}


def discover_one(name: str) -> dict[str, Any]:
    for token in candidates_for(name):
        for ats, probe in PROBES:
            if (ats, token) in KNOWN_FALSE_POSITIVES:
                continue
            ok, count, sample = probe(token)
            if ok:
                return {
                    "name": name,
                    "ats": ats,
                    "board_token": token,
                    "job_count_at_discovery": count,
                    "sample_title": sample,
                    "status": "resolved",
                    "needs_spot_check": True,
                }
            time.sleep(0.02)
    return {
        "name": name,
        "ats": None,
        "board_token": None,
        "status": "unresolved",
        "notes": "No Greenhouse/Lever/Ashby/Breezy/SmartRecruiters/Workable/Recruitee board matched slug candidates.",
    }


def load_seed(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"seed must be a JSON list: {path}")
    out: list[str] = []
    seen: set[str] = set()
    for item in data:
        name = str(item).strip()
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        out.append(name)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--limit", type=int, default=0, help="Optional cap for smoke tests")
    args = parser.parse_args()

    companies = load_seed(args.seed)
    if args.limit > 0:
        companies = companies[: args.limit]
    if len(companies) < 1:
        raise SystemExit("empty seed")

    print(f"Probing {len(companies)} companies with {args.workers} workers…", flush=True)
    results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(discover_one, name): name for name in companies}
        done = 0
        for fut in as_completed(futures):
            row = fut.result()
            results.append(row)
            done += 1
            if row["status"] == "resolved":
                print(
                    f"[{done}/{len(companies)}] {row['name']}: "
                    f"{row['ats']}/{row['board_token']} "
                    f"({row.get('job_count_at_discovery', 0)} jobs)",
                    flush=True,
                )
            elif done % 25 == 0 or done == len(companies):
                print(f"[{done}/{len(companies)}] progress…", flush=True)

    order = {name: i for i, name in enumerate(companies)}
    results.sort(key=lambda r: order[r["name"]])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    resolved = sum(1 for r in results if r["status"] == "resolved")
    by_ats: dict[str, int] = {}
    for r in results:
        if r["status"] == "resolved":
            by_ats[r["ats"]] = by_ats.get(r["ats"], 0) + 1
    print(f"\nDone: {resolved}/{len(results)} resolved → {args.out}")
    print("By ATS:", by_ats)


if __name__ == "__main__":
    main()
