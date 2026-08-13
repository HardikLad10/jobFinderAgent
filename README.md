# Job Finder Agent

A **daily, unattended job search agent** for a UIUC / Midwest new-grad software engineer.

It polls public company job boards, throws away everything that is not a fresh Midwest or US-remote SWE role, asks Claude whether the leftover jobs fit the resume, and **emails the strong/maybe matches**. There is no website and no “apply for me” button.

## Why it exists

Job aggregators are often a day late and full of noise. Checking dozens of career pages by hand is the real work. This agent does the checking; Claude only judges **fit** on the few postings that already passed hard filters.

## What it does each morning

GitHub Actions runs around **6:00 AM Central** (`Daily job search` workflow):

1. **Fetch** jobs from public ATS JSON feeds (Greenhouse, Lever, Ashby, Breezy, SmartRecruiters, Workable, Recruitee) — hundreds of Midwest-relevant boards, tens of thousands of postings.
2. **Filter** (no AI): software-engineering titles → Illinois / neighboring Midwest / US-remote → drop “we don’t sponsor” language → posted in the last **3 days** → skip URLs already judged.
3. **Match** (the only LLM step): Claude Opus 5 scores each survivor `strong` / `maybe` / `no` against `config/resume_profile.md`.
4. **Email** strong and maybe matches via Resend. Quiet days send **nothing** — that is normal.

It does **not** scrape LinkedIn, Handshake, or Wellfound. It does **not** talk to Workday (those boards are not a simple public JSON feed).

## What you will *not* find in this repo

The **email is the day’s product**. GitHub does not store the digest.

| In git | Not in git |
|--------|------------|
| Company list, filters, code, this README | Full job dump (`data/latest_*.json`) |
| `data/seen_jobs.json` — URLs already scored | Email body / Claude reasoning |
| `data/quarantine.json` — posts that broke matching | A dashboard |

**To see a given day:** the inbox, [Resend’s sent mail](https://resend.com/emails), or the **Actions log** for `Daily job search` (search for `filter stats` and `[STRONG]` / `[MAYBE]`).

## Repo map

| Path | Role |
|------|------|
| [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md) | Design spec (how it works, what’s in/out of scope) |
| [`SESSION_LOG.md`](SESSION_LOG.md) | Build diary (dates, experiments, counts) |
| [`config/companies.json`](config/companies.json) | Boards to poll (`resolved`) vs names with no public slug yet (`unresolved`) |
| [`config/filters.json`](config/filters.json) | Title / location / sponsorship / freshness rules |
| [`run_pipeline.py`](run_pipeline.py) | Ingest → filter → match → email |
| [`.github/workflows/daily_job_search.yml`](.github/workflows/daily_job_search.yml) | Morning cron |

Two other workflows send **reminders** (not fit-matching): Illinois CSOD and Research Park.

## Run locally

```bash
cp .env.example .env   # add ANTHROPIC_API_KEY and RESEND_API_KEY
python3 run_pipeline.py --send-email --mark-seen
```

`--dry-run-email` prints the digest without sending. `--skip-match` stops after filters (no Claude).

## Docs

Start with **[PROJECT_BRIEF.md](PROJECT_BRIEF.md)** — especially section 5 (pipeline + how a day’s artifacts work). Use **[SESSION_LOG.md](SESSION_LOG.md)** only if you need the history of a decision.
