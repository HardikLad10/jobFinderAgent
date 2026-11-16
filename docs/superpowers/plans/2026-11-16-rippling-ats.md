# Rippling ATS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch Rippling boards through the existing daily pipeline, then add only the new resolved boards that survive the same merge rules as the other public ATS.

**Architecture:** `ingestion/rippling.py` lists a board with the public v2 JSON API and fetches a description only for software-looking titles. `scripts/discover_ats.py` probes unresolved US company names for a Rippling slug. A later merge appends the kept rows to `config/companies.json`. The morning cron does not change until that merge and a skip-match timing run are both committed and the user asks for a push.

**Tech Stack:** Python 3, stdlib `urllib` via `ingestion/http.py`, `unittest`.

## Global Constraints

- UltiPro is out of this plan.
- One list call per board. A detail call only when the title matches the SmartRecruiters hint list.
- HTTP 404 is a miss. An empty item list is a miss.
- Probe unresolved names from `config/companies.discovered.builtin_us.json` only. Do not re-run the seven existing ATS probes.
- 12 workers, one process. Write `config/companies.discovered.rippling.json` only when the probe process exits.
- Merge a board only when it is new, has at least one job, is under 1000 jobs, and is not a sample, test, consulting, or staffing name.
- Do not call Claude on the timing run. Do not pass `--send-email` or `--mark-seen`.
- Do not push. Do not open a pull request.

**Spec:** `docs/superpowers/specs/2026-11-16-rippling-ats-design.md`

## File structure

- Create `ingestion/rippling.py` — list, detail, and normalize one Rippling board.
- Create `tests/test_rippling.py` — stubbed HTTP tests for that client.
- Modify `ingestion/runner.py` — register `rippling`.
- Modify `scripts/discover_ats.py` — add `try_rippling` for a later probe. The probe command is a separate task and is not run inside Task 1.

---

### Task 1: Rippling client

**Files:**
- Create: `ingestion/rippling.py`
- Create: `tests/test_rippling.py`
- Modify: `ingestion/runner.py`

**Interfaces:**
- Consumes: `ingestion.http.get_json`, `ingestion.schema.JobPosting`, `ingestion.textutil.html_to_text`
- Produces: `fetch_rippling_jobs(company_name: str, board_token: str) -> list[JobPosting]` registered as `FETCHERS["rippling"]`

- [x] **Step 1: Write the failing test**

```python
"""Rippling client tests. HTTP is stubbed."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ingestion.errors import IngestionError
from ingestion.rippling import fetch_rippling_jobs


LIST_PAGE_0 = {
    "items": [
        {
            "id": "job-swe",
            "name": "Software Engineer",
            "url": "https://ats.rippling.com/acme/jobs/job-swe",
            "locations": [
                {
                    "name": "Austin, TX",
                    "workplaceType": "ON_SITE",
                }
            ],
        },
        {
            "id": "job-sales",
            "name": "Account Executive",
            "url": "https://ats.rippling.com/acme/jobs/job-sales",
            "locations": [{"name": "Chicago, IL", "workplaceType": "ON_SITE"}],
        },
    ],
    "page": 0,
    "pageSize": 100,
    "totalItems": 2,
    "totalPages": 2,
}
LIST_PAGE_1 = {
    "items": [
        {
            "id": "job-remote",
            "name": "Backend Engineer",
            "url": "https://ats.rippling.com/acme/jobs/job-remote",
            "locations": [
                {"name": "United States", "workplaceType": "REMOTE"},
            ],
        }
    ],
    "page": 1,
    "pageSize": 100,
    "totalItems": 3,
    "totalPages": 2,
}
DETAIL = {
    "createdOn": "2026-11-02T11:50:55.300000-08:00",
    "description": {
        "company": "<p>Acme builds tools.</p>",
        "role": "<p>Python required. Visa sponsorship available.</p>",
    },
}


class RipplingClientTest(unittest.TestCase):
    def test_pages_and_skips_non_software_titles(self) -> None:
        calls: list[str] = []

        def fake_get(url: str, *, company_name: str) -> dict:
            calls.append(url)
            if "page=0" in url:
                return LIST_PAGE_0
            if "page=1" in url:
                return LIST_PAGE_1
            if url.endswith("/jobs/job-swe"):
                return DETAIL
            if url.endswith("/jobs/job-remote"):
                return DETAIL
            raise AssertionError(url)

        with patch("ingestion.rippling.get_json", side_effect=fake_get):
            jobs = fetch_rippling_jobs("Acme", "acme")

        titles = [job.title for job in jobs]
        self.assertEqual(titles, ["Software Engineer", "Backend Engineer"])
        self.assertNotIn("job-sales", " ".join(calls))
        remote = jobs[1]
        self.assertEqual(remote.location, "Remote - United States")
        self.assertIn("Python required", jobs[0].description)
        self.assertIn("Acme builds tools", jobs[0].description)
        self.assertEqual(jobs[0].posted_date, "2026-11-02T11:50:55.300000-08:00")
        self.assertEqual(jobs[0].url, "https://ats.rippling.com/acme/jobs/job-swe")

    def test_detail_failure_keeps_the_posting(self) -> None:
        def fake_get(url: str, *, company_name: str) -> dict:
            if "page=0" in url:
                return {
                    "items": [
                        {
                            "id": "job-swe",
                            "name": "Software Engineer",
                            "url": "https://ats.rippling.com/acme/jobs/job-swe",
                            "locations": [{"name": "Austin, TX"}],
                        }
                    ],
                    "totalItems": 1,
                    "totalPages": 1,
                }
            raise IngestionError("detail down")

        with patch("ingestion.rippling.get_json", side_effect=fake_get):
            jobs = fetch_rippling_jobs("Acme", "acme")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].description, "")
        self.assertEqual(jobs[0].posted_date, "")


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run the test and confirm it fails**

Run: `python3 -m unittest tests.test_rippling -v`

Expected: FAIL because `ingestion.rippling` does not exist.

- [x] **Step 3: Write the client and register it**

`ingestion/rippling.py` implements `fetch_rippling_jobs` as specified above. `ingestion/runner.py` imports `fetch_rippling_jobs` and sets `FETCHERS["rippling"]`.

- [x] **Step 4: Run the test and confirm it passes**

Run: `python3 -m unittest tests.test_rippling -v`

Expected: PASS, 2 tests.

- [x] **Step 5: Commit**

```bash
git add ingestion/rippling.py ingestion/runner.py tests/test_rippling.py \
  docs/superpowers/specs/2026-11-16-rippling-ats-design.md \
  docs/superpowers/plans/2026-11-16-rippling-ats.md
git commit -m "$(cat <<'EOF'
Add a Rippling job-board client that matches the other public ATS fetchers.

EOF
)"
```

Do not push.

---

### Task 2: Rippling-only discovery probe

**Files:**
- Modify: `scripts/discover_ats.py`

**Interfaces:**
- Consumes: the list URL from Task 1
- Produces: `try_rippling(token: str) -> tuple[bool, int, str | None]`

- [ ] **Step 1: Add the probe**

Add this function next to `try_recruitee` and append `("rippling", try_rippling)` to `PROBES`.

```python
def try_rippling(token: str) -> tuple[bool, int, str | None]:
    # Unknown slugs return HTTP 404. Empty boards are misses.
    status, data = http_get(
        "https://api.rippling.com/platform/api/ats/v2/board/"
        f"{token}/jobs?page=0&pageSize=10"
    )
    if status != 200 or not isinstance(data, dict):
        return False, 0, None
    items = data.get("items")
    total = data.get("totalItems")
    if not isinstance(items, list) or not items:
        return False, 0, None
    count = int(total) if isinstance(total, int) and total > 0 else len(items)
    sample = str(items[0].get("name") or "")[:80]
    return True, count, sample or None
```

Update the unresolved `notes` string so it names Rippling.

- [ ] **Step 2: Build the unresolved seed and start the probe**

One process, 12 workers. Do not start a second probe. The output file is written only when the process exits.

```bash
python3 - << 'PY'
import json
from pathlib import Path
rows = json.loads(Path("config/companies.discovered.builtin_us.json").read_text())
names = [row["name"] for row in rows if row.get("status") == "unresolved" and row.get("name")]
Path("config/builtin_us_unresolved_seed.json").write_text(json.dumps(names, indent=2) + "\n")
print(len(names))
PY
python3 -u scripts/discover_ats.py \
  --seed config/builtin_us_unresolved_seed.json \
  --out config/companies.discovered.rippling.json \
  --workers 12
```

Expected: the process prints `Probing N companies` and ends with `Done:` and a `By ATS:` line that includes `rippling`. Do not merge the file in this task.

- [ ] **Step 3: Commit the probe code and the finished JSON**

```bash
git add scripts/discover_ats.py config/builtin_us_unresolved_seed.json config/companies.discovered.rippling.json
git commit -m "$(cat <<'EOF'
Probe unresolved US company names for Rippling boards.

EOF
)"
```

Do not push. Do not commit a partial JSON if the process is still running.

---

### Task 3: Merge and time

**Files:**
- Modify: `config/companies.json`
- Append: `SESSION_LOG.md`

- [ ] **Step 1: Merge kept boards**

Load `config/companies.discovered.rippling.json` and `config/companies.json`. Keep a discovered row when `status` is `resolved`, `ats` is `rippling`, `job_count_at_discovery` is from 1 through 999, `sample_title` does not match `(?i)\b(sample|test)\b`, and `scripts.seed_from_builtin._drop_reason(name)` is `None`. Skip a `(rippling, board_token)` pair already present. Append:

```python
{
    "name": name,
    "ats": "rippling",
    "board_token": token,
    "status": "resolved",
    "notes": "Rippling board from the unresolved US name probe.",
}
```

- [ ] **Step 2: Time the fetch**

```bash
python3 run_pipeline.py --skip-match
```

Record the wall-clock minutes and the `filter stats` line. No email. No seen-job update.

- [ ] **Step 3: Commit and stop**

Append a `SESSION_LOG.md` entry with the board count added, the probe hit count, and the skip-match minutes. Commit `config/companies.json` and `SESSION_LOG.md`. Do not push. Report the counts and that GitHub `main` is unchanged.
