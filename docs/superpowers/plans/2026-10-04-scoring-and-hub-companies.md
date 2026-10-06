# Scoring, Apply Email, and Hub Companies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Score each job once against one master profile, name which resume to send in a short email, and add hub-city companies on the seven existing job boards.

**Architecture:** `config/resume_profile.md` stays the only profile sent to Claude. The match JSON gains `role`. The email prints that role and the full reasoning. Company discovery stays a manual script, then a merge into `config/companies.json`. The morning cron does not discover boards.

**Tech Stack:** Python 3, stdlib `unittest`, existing `matching/`, `delivery/`, `filtering/`, `scripts/seed_from_builtin.py`, `scripts/discover_ats.py`.

## Global Constraints

- One Claude call per surviving job. Model `claude-opus-5-5`, effort `xhigh`.
- The profile sent on that call is `config/resume_profile.md`, loaded by `load_resume()` in `matching/__init__.py`.
- Read the posting. Separate required skills from preferred skills. An “or” list is one requirement: any listed skill the profile has is enough.
- A missing required skill, or a level that does not fit, is `no`. A missing preferred skill can make `maybe` and cannot make `no`.
- Reject a job when it does not fit this profile and the target roles. Do not reject it because one alternative in an or-list is absent.
- `role` is `new_grad`, `full_stack`, or `ai_fde`. Unknown `fit` or `role` is `invalid`.
- Email strong and maybe only. Reasoning is not trimmed to 120 characters.
- New boards only: Greenhouse, Lever, Ashby, Breezy, SmartRecruiters, Workable, Recruitee. No LinkedIn, Indeed, Handshake, or Workday.
- Do not discover boards inside the daily cron.
- Freshness stays 3 days. Hub location tokens stay.

**Spec:** `docs/superpowers/specs/2026-10-04-scoring-and-hub-companies-design.md`

## File structure

- Modify `config/resume_profile.md` — one master profile. This is step 0 and is the file `load_resume()` sends on every API call.
- Modify `config/filters.json` — four title excludes.
- Modify `matching/__init__.py` — prompt, JSON parse, `role` on `MatchResult`.
- Modify `delivery/__init__.py` — resume line and full reasoning.
- Modify `tests/test_filters.py` — Sr. and fellowship drops.
- Modify or add `tests/test_matching_guardrails.py` — `role` fail-closed.
- Add an email test next to the delivery module’s existing tests, or in `tests/test_delivery.py` if none exist.
- Modify `scripts/seed_from_builtin.py` — four hub directory URLs.
- Modify `config/companies.json` only after a reviewed discovery run.
- Modify `PROJECT_BRIEF.md` and `SESSION_LOG.md`.

---

### Task 0: Master profile

Do this before Tasks 1–5. `match_jobs` calls `load_resume()`, which reads `config/resume_profile.md`, and that string is the `## Candidate profile` block in the one API call.

**Files:**
- Modify: `config/resume_profile.md`

**Interfaces:**
- Consumes: the three PDFs named in the spec. The Business Intelligence Group bullets come only from the AI/FDE resume.
- Produces: the only profile text sent to Claude.

The file is already rewritten from those PDFs. Before the later tasks, confirm it still matches these checks:

```bash
python3 - << 'PY'
from pathlib import Path
text = Path("config/resume_profile.md").read_text()
for banned in ("217-693", "hotmail", "linkedin.com", "C++"):
    assert banned not in text, banned
assert "Graduated May 2026" in text
assert "Next.js" in text and "Drizzle" in text
assert "ChromaDB" not in text.split("Business Intelligence")[1].split("## Projects")[0]
assert "Kubernetes" not in text
print("profile ok")
PY
```

Expected: `profile ok`

Commit with the scoring work, not by itself, unless this file is the only change ready.

---

### Task 1: Title excludes

**Files:**
- Modify: `config/filters.json` (`title_exclude_any`)
- Test: `tests/test_filters.py`

**Interfaces:**
- Consumes: `filter_postings` and `FilterHistoricalBugsTest._kept_urls`.
- Produces: titles containing `sr.`, `sr `, `high school`, or `fellowship` are dropped. `Software Engineer II` is kept.

- [ ] **Step 1: Write the failing test**

Add to `FilterHistoricalBugsTest`:

```python
def test_sr_and_fellowship_titles_dropped_engineer_ii_kept(self) -> None:
    jobs = [
        _job(url="u-sr-dot", title="Sr. Software Engineer"),
        _job(url="u-sr-space", title="Sr Software Engineer"),
        _job(url="u-hs", title="High School Fellowship, Software Engineering"),
        _job(url="u-ii", title="Software Engineer II"),
        _job(url="u-swe", title="Software Engineer"),
    ]
    kept = self._kept_urls(jobs)
    self.assertEqual(kept, {"u-ii", "u-swe"})
```

- [ ] **Step 2: Run it and confirm it fails**

```bash
python3 -m unittest tests.test_filters.FilterHistoricalBugsTest.test_sr_and_fellowship_titles_dropped_engineer_ii_kept -v
```

Expected: FAIL because `Sr. Software Engineer` is still kept.

- [ ] **Step 3: Add the excludes**

Append to `title_exclude_any` in `config/filters.json`:

```json
"sr.",
"sr ",
"high school",
"fellowship"
```

- [ ] **Step 4: Re-run filter tests**

```bash
python3 -m unittest tests.test_filters -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config/filters.json tests/test_filters.py
git commit -m "$(cat <<'EOF'
Drop Sr. and fellowship titles before they reach Claude.

EOF
)"
```

---

### Task 2: Score once and name the resume

**Files:**
- Modify: `matching/__init__.py`
- Test: `tests/test_matching_guardrails.py`

**Interfaces:**
- Consumes: `load_resume()` and `_parse_fit_json`.
- Produces: `MatchResult.role` as `new_grad`, `full_stack`, or `ai_fde`. Parse failure returns fit `invalid`.

- [ ] **Step 1: Write the failing parser test**

Cover three cases: valid `strong` plus `full_stack`; missing `role` is invalid; `role` `intern` is invalid.

- [ ] **Step 2: Run that test and confirm it fails**

```bash
python3 -m unittest tests.test_matching_guardrails -v
```

- [ ] **Step 3: Change the prompt and parser**

Prompt rules are spec section 3, verbatim in intent. JSON shape:

```json
{"fit":"strong"|"maybe"|"no","role":"new_grad"|"full_stack"|"ai_fde","reasoning":"<two or three short sentences>"}
```

Store `role` on `MatchResult`. If `role` is missing or not one of the three values, return `invalid`.

- [ ] **Step 4: Re-run the matching tests**

```bash
python3 -m unittest tests.test_matching_guardrails -v
```

Expected: PASS. Do not call the live API.

- [ ] **Step 5: Commit**

```bash
git add matching/__init__.py tests/test_matching_guardrails.py
git commit -m "$(cat <<'EOF'
Name the resume to send and fail closed on a bad role.

EOF
)"
```

---

### Task 3: Email the resume and the proof

**Files:**
- Modify: `delivery/__init__.py`
- Test: `tests/test_delivery.py`

**Interfaces:**
- Consumes: `MatchResult.role` and `MatchResult.reasoning`.
- Produces: email text with `Send the New Grad resume`, `Send the Full Stack resume`, or `Send the AI/FDE resume`, plus the full reasoning.

- [ ] **Step 1: Write a failing test**

Build a fake strong match with a reasoning longer than 120 characters and `role="full_stack"`. Assert the email contains `Send the Full Stack resume` and the full reasoning.

- [ ] **Step 2: Run it and confirm it fails**

```bash
python3 -m unittest tests.test_delivery -v
```

- [ ] **Step 3: Change `build_email`**

Stop using `_short_reason` for this email. Map `new_grad` → `Send the New Grad resume`, `full_stack` → `Send the Full Stack resume`, `ai_fde` → `Send the AI/FDE resume`.

- [ ] **Step 4: Re-run the test**

```bash
python3 -m unittest tests.test_delivery tests.test_filters tests.test_matching_guardrails -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add delivery/__init__.py tests/test_delivery.py
git commit -m "$(cat <<'EOF'
Tell the email which resume to send and why.

EOF
)"
```

---

### Task 4: Hub company boards

**Files:**
- Modify: `scripts/seed_from_builtin.py`
- Create: a seed JSON under `config/` from the script run
- Modify: `config/companies.json` only with boards that pass the spec

**Interfaces:**
- Consumes: Built In directory pages and `scripts/discover_ats.py`.
- Produces: new `resolved` companies in `config/companies.json`. Unresolved names stay out of the daily fetch.

- [ ] **Step 1: Add the four directory URLs**

Add San Francisco, Seattle, New York, and Boston software-company Built In URLs next to the existing metro list. If a URL returns no company names, skip that city and write the URL into the session log.

- [ ] **Step 2: Run the seed and the ATS probe**

Keep the existing consulting and staffing name filter. Probe only the seven supported boards. Keep a board only when it returns at least one job and the slug is that company.

- [ ] **Step 3: Merge**

Add the kept boards to `config/companies.json`. Do not add the merge to the GitHub Actions workflow.

- [ ] **Step 4: Smoke the filter, not a full model run**

```bash
python3 run_pipeline.py --skip-match
```

Expected: the process finishes, `ingested` is greater than 0, and the log shows filter stats. Do not send email. Do not mark seen.

- [ ] **Step 5: Commit**

```bash
git add scripts/seed_from_builtin.py config/companies.json PROJECT_BRIEF.md SESSION_LOG.md
git commit -m "$(cat <<'EOF'
Add hub-city companies on the existing public job boards.

EOF
)"
```

Update `PROJECT_BRIEF.md` and `SESSION_LOG.md` in this commit. Do not edit older session-log entries.

Do not push unless asked.

## Decided 2026-10-05 — US-wide boards, then a week, then Workday

Approved next step: one US-wide Built In pass on Greenhouse, Lever, Ashby, Breezy, SmartRecruiters, Workable, and Recruitee. Add every resolved board that is not already in `config/companies.json`. Built In’s US directory is about 50,000 company names. Public Greenhouse, Lever, and Ashby boards are about 10,000, not 48,000. This pass should add several thousand boards, not 20,000.

After that list is on the daily cron, watch seven scheduled mornings. Record `kept`, strong, and maybe. Do not start Workday during that week.

Workday is a later project, after that week. It is not part of this plan’s implementation.

The 964 hub-city boards and the scoring changes stay. They are the version under test until the US-wide list replaces the “only four hubs” discovery limit.

## Decided 2026-10-06 — all US locations are the immediate next filter change

After `config/companies.discovered.builtin_us.json` is written, and before that board list is pushed, change the location filter from the four hubs to the United States.

Keep full state names and clear US place names. Do not add two-letter state abbreviations. Keep US-remote, title, sponsorship, 3-day freshness, and seen-URL dedupe. Do not build the city list by scraping city names out of the probe. The probe has companies and board slugs, not job cities.

This sends more fresh US jobs to Claude, including more `no` scores. The email stays strong and maybe only.
