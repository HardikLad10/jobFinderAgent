#!/usr/bin/env python3
"""Build Midwest SWE employer seed from DOL H-1B LCA disclosure Excel files.

v2 locked rules (PROJECT_BRIEF):
- Filter WORKSITE_STATE ∈ Midwest first (efficiency).
- Certified-ish cases only; SWE-ish SOC/title.
- Drop H_1B_DEPENDENT = Y (staffing-mill signal).
- LLC soft-drop: drop only when name has LLC/L.L.C. AND noise tokens
  (STAFFING, CONSULTING, SOLUTIONS, SERVICES, …).
- Hard-drop LLP and known consultancy / body-shop name patterns.

Not part of the daily pipeline — discovery helper only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LCA_DIR = ROOT / "discovery"
DEFAULT_OUT = ROOT / "config" / "lca_midwest_swe_seed.json"

MIDWEST_STATES = frozenset({"IL", "WI", "IN", "MI", "MO", "IA", "MN"})

TITLE_KEYWORDS = (
    "software",
    "full stack",
    "fullstack",
    "full-stack",
    "backend",
    "back-end",
    "front end",
    "frontend",
    "front-end",
    "devops",
    "sre",
    "data engineer",
    "machine learning engineer",
    "ml engineer",
)

# LLC soft-drop: only when paired with these noise tokens.
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

CONSULT_NAME_RE = re.compile(
    r"\b("
    r"INFOSYS|TATA|WIPRO|COGNIZANT|HCL\b|TECH MAHINDRA|LTIMINDTREE|MINDTREE|"
    r"ACCENTURE|CAPGEMINI|DELOITTE|ERNST\s*&\s*YOUNG|\bEY\b|KPMG|PRICEWATER|PWC\b|"
    r"IBM\b|HTC GLOBAL|GLOBALLOGIC|HEXAWARE|YASH TECHNOLOGIES|COMPUNNEL|"
    r"PERSISTENT|MPHASIS|LARSEN|LTI\b|"
    r"CONSULTING|STAFFING|GLOBAL SERVICES"
    r")\b",
    re.I,
)

LLC_RE = re.compile(r"\bL\.?L\.?C\.?\b", re.I)
LLP_RE = re.compile(r"\bL\.?L\.?P\.?\b", re.I)

# Q1 uses H-1B_DEPENDENT; Q2–Q4 use H_1B_DEPENDENT.
H1B_ALIASES = ("H_1B_DEPENDENT", "H-1B_DEPENDENT")


def _load_quarter(path: Path, pd):  # type: ignore[no-untyped-def]
    """Read one LCA workbook; normalize H-1B dependent column name across quarters."""
    header = pd.read_excel(path, nrows=0, engine="openpyxl")
    cols = list(header.columns)
    h1b = next((c for c in H1B_ALIASES if c in cols), None)
    if h1b is None:
        raise SystemExit(f"{path.name}: missing H-1B dependent column (tried {H1B_ALIASES})")
    usecols = [
        "CASE_STATUS",
        "JOB_TITLE",
        "SOC_CODE",
        "EMPLOYER_NAME",
        "WORKSITE_STATE",
        h1b,
    ]
    missing = [c for c in usecols if c not in cols]
    if missing:
        raise SystemExit(f"{path.name}: missing columns {missing}")
    df = pd.read_excel(path, usecols=usecols, engine="openpyxl")
    if h1b != "H_1B_DEPENDENT":
        df = df.rename(columns={h1b: "H_1B_DEPENDENT"})
    return df


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lca-dir", type=Path, default=DEFAULT_LCA_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--quarters",
        nargs="*",
        default=["Q1", "Q2", "Q3", "Q4"],
        help="Which FY2025 quarter files to read (default: all four)",
    )
    args = parser.parse_args()

    try:
        import pandas as pd
    except ImportError:
        print("Installing pandas + openpyxl…", file=sys.stderr)
        import subprocess

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pandas", "openpyxl", "-q"]
        )
        import pandas as pd

    paths = []
    for q in args.quarters:
        q = q.upper()
        matches = sorted(args.lca_dir.glob(f"LCA_Disclosure_Data_FY2025_{q}.xlsx"))
        if not matches:
            raise SystemExit(f"missing LCA file for {q} under {args.lca_dir}")
        paths.append(matches[0])

    kept_names: Counter[str] = Counter()
    stats = Counter()

    for path in paths:
        print(f"Loading {path.name}…", flush=True)
        df = _load_quarter(path, pd)
        stats["rows_raw"] += len(df)

        df["WORKSITE_STATE"] = (
            df["WORKSITE_STATE"].astype(str).str.upper().str.strip()
        )
        df = df[df["WORKSITE_STATE"].isin(MIDWEST_STATES)]
        stats["rows_midwest_worksite"] += len(df)

        status = df["CASE_STATUS"].astype(str).str.lower()
        df = df[status.str.contains("cert", na=False)]
        stats["rows_certified"] += len(df)

        soc = df["SOC_CODE"].astype(str).str.startswith("15-12")
        titles = df["JOB_TITLE"].astype(str).str.lower()
        title_hit = titles.apply(lambda t: any(k in t for k in TITLE_KEYWORDS))
        df = df[soc | title_hit]
        stats["rows_swe"] += len(df)

        dep = df["H_1B_DEPENDENT"].astype(str).str.upper().str.strip()
        df = df[~dep.isin(["Y", "YES"])]
        stats["rows_after_h1b_dep_drop"] += len(df)

        for raw_name in df["EMPLOYER_NAME"].astype(str):
            name = " ".join(raw_name.split()).strip()
            if not name or name.lower() == "nan":
                continue
            reason = _drop_reason(name)
            if reason:
                stats[f"drop_{reason}"] += 1
                continue
            kept_names[name] += 1
            stats["rows_kept"] += 1

    # Stable sort: most LCA hits first, then name.
    ordered = [n for n, _ in kept_names.most_common()]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")

    print("\n=== LCA seed stats ===")
    for key in sorted(stats):
        print(f"  {key}: {stats[key]}")
    print(f"  unique_employers: {len(ordered)}")
    print(f"Wrote {args.out}")
    print("Top 15:")
    for name, n in kept_names.most_common(15):
        print(f"  {n:4d}  {name}")
    return 0


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


if __name__ == "__main__":
    raise SystemExit(main())
