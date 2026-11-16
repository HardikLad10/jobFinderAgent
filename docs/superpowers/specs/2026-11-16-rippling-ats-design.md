# Rippling ATS

## Purpose

Add Rippling as an eighth public job-board source. The daily pipeline keeps the same order: fetch, title, location, sponsorship, 3-day freshness, seen-URL dedupe, one Claude call per survivor, email strong and maybe only. UltiPro stays out.

## Approaches

1. **Recommended. Same client shape as SmartRecruiters, then a Rippling-only probe of unresolved names.** One list call per board. A second call only for software-looking titles, because that call is what carries the description and the posted date. Names that already resolved to another ATS stay on that ATS.
2. Import a third-party list of about 860 Rippling boards. Faster to collect, and it would add boards whose names were never in the US seed. It also adds boards this project did not choose, including tiny and non-software employers, and it lengthens a morning fetch that already takes about 3.5 hours.
3. Re-run all 42,223 US names through all eight ATS. `discover_one` stops at the first hit, so companies already on Greenhouse would never be checked for Rippling, and the probe repeats work that already finished.

## Client

`ingestion/rippling.py` exposes `fetch_rippling_jobs(company_name: str, board_token: str) -> list[JobPosting]`.

List: `GET https://api.rippling.com/platform/api/ats/v2/board/{board_token}/jobs?page={page}&pageSize=100`. Page is 0-based. Stop at `totalPages`. Cap the loop at 50 pages. An HTTP 404 raises `IngestionError` and the runner skips that company. A 200 with no items returns an empty list.

Keep a list row only when the title contains one of the same hints SmartRecruiters uses: software, developer, engineer, swe, full stack, fullstack, backend, frontend, front-end, devops, sre, programmer, data engineer, machine learning, ml engineer.

For each kept row, `GET https://api.rippling.com/platform/api/ats/v1/board/{board_token}/jobs/{id}`. `posted_date` is `createdOn`. `description` is the plain text of `description.role` and `description.company`. A failed detail call keeps the job with an empty description and an empty posted date, and logs a warning.

`url` is the list `url` when it is a non-empty string, otherwise `https://ats.rippling.com/{board_token}/jobs/{id}`. Location is the `name` of each entry in `locations`, joined with `"; "`. When `workplaceType` is `REMOTE` and that name does not already contain "remote", prefix `Remote - `.

`ingestion/runner.py` registers `"rippling"` in `FETCHERS`.

## Discovery

`scripts/discover_ats.py` gains `try_rippling`. A hit is HTTP 200 and `totalItems` greater than 0. HTTP 404 and an empty item list are misses. The probe does not call the detail endpoint.

The seed is the unresolved names from `config/companies.discovered.builtin_us.json`. The probe checks Rippling only. It uses 12 workers in one process and writes `config/companies.discovered.rippling.json` only when the process finishes.

## Merge

Add a row to `config/companies.json` only when the probe resolved it, `job_count_at_discovery` is at least 1, the `(ats, board_token)` pair is new, the sample title is not a sample or test job, and the name is not consulting or staffing under the existing seed filter. Drop a board whose `job_count_at_discovery` is 1000 or more. The row shape stays `name`, `ats`, `board_token`, `status`, `notes`.

## Timing and release

After the merge, run `python3 run_pipeline.py --skip-match` once. No Claude call, no email, and no `--mark-seen`. Record the minutes. Do not push. GitHub `main` stays unchanged until a later request, and that request has to include the client, the merged boards, and the timing result together.

## Tests

`tests/test_rippling.py` uses `unittest` and stubs `get_json`. It covers a two-page list, a remote location, a software title that requests the detail, a non-software title that does not, and a detail failure that still returns the posting.
