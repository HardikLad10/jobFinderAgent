#!/usr/bin/env python3
"""One-shot ATS board discovery for the 50-company list.

Tries Greenhouse / Lever / Ashby public endpoints with slug candidates.
Prints JSON suitable for pasting into config/companies.json.
Not part of the scheduled pipeline — manual discovery helper.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

# Exact list from SESSION_LOG.md (2026-08-05 company expansion).
COMPANIES: list[str] = [
    # Confirmed Greenhouse candidates
    "Sprout Social",
    "FourKites",
    "Klaviyo",
    # Fintech/Insurtech
    "Discover Financial Services",
    "Cboe Global Markets",
    "Guaranteed Rate",
    "Kin Insurance",
    "Clearcover",
    "CCC Intelligent Solutions",
    "Origami Risk",
    "tastytrade",
    "Capital One",
    "Enova International",
    "Vouch",
    "Coro",
    # Health Tech
    "Tempus",
    "VillageMD",
    "HealthJoy",
    "Artera",
    "ALIS",
    # Supply Chain/Logistics
    "project44",
    "Echo Global Logistics",
    "Coyote Logistics",
    "ShipBob",
    # SaaS/Enterprise
    "G2",
    "ActiveCampaign",
    "Uptake",
    "Relativity",
    "PowerReviews",
    "Paylocity",
    "OpenGov",
    "Centro",
    "Civis Analytics",
    "Lessen",
    # Consumer/Marketplace
    "Cameo",
    "SpotHero",
    "Tovala",
    "Cars.com",
    "Reverb",
    "Groupon",
    # Other notable Chicago tech
    "Motorola Solutions",
    "Morningstar",
    "Halo Investing",
    "Upside",
    "Metropolis",
    "37signals",
    "Fooda",
    "ParkWhiz",
    "Cleo",
    "Block",
]

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
    "Tempus": ["tempus", "tempuslabs"],
    "VillageMD": ["villagemd", "village"],
    "Echo Global Logistics": ["echo", "echoglobal", "echogloballogistics"],
    "Coyote Logistics": ["coyote", "coyotelogistics"],
    "ActiveCampaign": ["activecampaign"],
    "Civis Analytics": ["civis", "civisanalytics"],
    "Cars.com": ["cars", "carsdotcom", "carscom"],
    "Motorola Solutions": ["motorolasolutions", "motorola"],
    "Halo Investing": ["haloinvesting", "halo"],
    "37signals": ["37signals", "basecamp"],
    "Block": ["block", "square", "cashapp", "joinblock"],
    "project44": ["project44", "p44"],
    "G2": ["g2", "g2crowd"],
    "ALIS": ["alis", "alishealth"],
    "Artera": ["artera", "arteraai"],
    "Coro": ["coro", "coro.net"],
    "Vouch": ["vouch", "vouchinsurance"],
    "Lessen": ["lessen"],
    "Centro": ["centro", "basis", "basistechnologies"],
    "Upside": ["upside", "upside.com", "upsidefoods"],
    "Metropolis": ["metropolis", "metropolistech"],
    "Cleo": ["cleo", "meetcleo"],
    "Relativity": ["relativity", "relativityone", "relativityspace"],
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
}


def slugify(name: str) -> list[str]:
    base = name.lower().strip()
    variants = {
        re.sub(r"[^a-z0-9]", "", base),
        re.sub(r"[^a-z0-9]+", "", base),
        re.sub(r"[^a-z0-9]+", "-", base).strip("-"),
        re.sub(r"[^a-z0-9]+", "_", base).strip("_"),
    }
    # Drop trailing Inc/LLC/etc noise already absent; keep first word as weak guess.
    first = re.sub(r"[^a-z0-9]", "", base.split()[0]) if base.split() else ""
    if first:
        variants.add(first)
    return [v for v in variants if v]


def candidates_for(name: str) -> list[str]:
    seen: list[str] = []
    for token in ALIASES.get(name, []) + slugify(name):
        if token and token not in seen:
            seen.append(token)
    return seen


def http_get(url: str, timeout: float = 12.0) -> tuple[int, Any | None]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "jobFinderAgent-discover/0.1"},
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


def try_greenhouse(token: str) -> tuple[bool, int]:
    status, data = http_get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs")
    if status == 200 and isinstance(data, dict) and isinstance(data.get("jobs"), list):
        return True, len(data["jobs"])
    return False, 0


def try_lever(token: str) -> tuple[bool, int]:
    status, data = http_get(f"https://api.lever.co/v0/postings/{token}?mode=json")
    if status == 200 and isinstance(data, list):
        return True, len(data)
    return False, 0


def try_ashby(token: str) -> tuple[bool, int]:
    status, data = http_get(f"https://api.ashbyhq.com/posting-api/job-board/{token}")
    if status == 200 and isinstance(data, dict) and isinstance(data.get("jobs"), list):
        return True, len(data["jobs"])
    return False, 0


PROBES = (
    ("greenhouse", try_greenhouse),
    ("lever", try_lever),
    ("ashby", try_ashby),
)


def discover_one(name: str) -> dict[str, Any]:
    for token in candidates_for(name):
        for ats, probe in PROBES:
            ok, count = probe(token)
            if ok:
                return {
                    "name": name,
                    "ats": ats,
                    "board_token": token,
                    "job_count_at_discovery": count,
                    "status": "resolved",
                }
            time.sleep(0.05)  # light politeness between probes
    return {
        "name": name,
        "ats": None,
        "board_token": None,
        "status": "unresolved",
        "notes": "No Greenhouse/Lever/Ashby board matched common slug candidates. Likely Workday/iCIMS/other — exclude until a public board is found.",
    }


def main() -> None:
    assert len(COMPANIES) == 50, f"expected 50 companies, got {len(COMPANIES)}"
    results: list[dict[str, Any]] = []

    # Parallelize across companies; each company probes serially to keep rate sane.
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(discover_one, name): name for name in COMPANIES}
        for fut in as_completed(futures):
            row = fut.result()
            results.append(row)
            print(
                f"{row['name']}: {row['status']}"
                + (
                    f" via {row['ats']}/{row['board_token']} ({row.get('job_count_at_discovery', 0)} jobs)"
                    if row["status"] == "resolved"
                    else ""
                ),
                flush=True,
            )

    # Preserve SESSION_LOG order.
    order = {name: i for i, name in enumerate(COMPANIES)}
    results.sort(key=lambda r: order[r["name"]])

    out_path = "config/companies.discovered.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        f.write("\n")

    resolved = sum(1 for r in results if r["status"] == "resolved")
    print(f"\nDone: {resolved}/{len(results)} resolved → {out_path}")


if __name__ == "__main__":
    main()
