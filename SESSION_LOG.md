# Session Log

**Purpose:** This file exists to prevent context loss and hallucination drift across sessions. If you're starting a fresh Cursor/Claude session, read this file top to bottom before touching code. It answers: what actually exists, what was decided and why, and what's still open.

`PROJECT_BRIEF.md` is the stable spec and rarely changes. This file is the living record of what happened, in order. When in doubt about what's real, trust this file over memory of a past conversation.

---

## How to add an entry

Every session that changes something, code, scope, or a decision, adds one entry. Keep entries factual and short. Format:

```
## [Date] — [Short title]

**Changed:**
- what was added/modified/removed

**Why:**
- the reasoning, especially if it deviates from PROJECT_BRIEF.md

**Decisions made:**
- anything settled this session that wasn't settled before

**Open questions carried forward:**
- anything still unresolved, so the next session doesn't have to rediscover it
```

Do not delete old entries. If something changes direction, add a new entry explaining the change, don't edit history.

---

## [2026-08-05] — Project scoped, pre-code

**Changed:**
- No code yet. This is the planning session that produced `PROJECT_BRIEF.md`.

**Why:**
- Established as a smaller, faster warm-up build before committing to the larger OTC/FMCG portfolio project, to get real reps with the LLM API + agent design before a bigger investment.

**Decisions made:**
- Problem defined: fresh, relevant new-grad SWE job postings, Chicago area, without aggregator staleness.
- Handshake and Wellfound ruled out as data sources after checking ToS: Handshake explicitly prohibits scraping and restricts API access to university partners; Wellfound runs active anti-bot defenses. Full reasoning in `PROJECT_BRIEF.md` Section 4.
- Chosen data source instead: direct polling of company ATS APIs (Greenhouse, Lever, Ashby), publicly available, no auth, no ToS conflict, and inherently fresher than any aggregator.
- Architecture locked: deterministic pipeline (fetch, filter, dedupe) with exactly one agentic step (fit judgment).
- Model chosen: Claude Haiku 4.5 via Anthropic Console API key (personal, $500 credit), selected for the classification-style task fit and cost. Estimated cost: under $1/month at expected volume.
- Fireworks AI ($500 credit) deliberately not used in v1. Reserved as a future pre-filter layer if volume scales up.
- Scheduling and delivery mechanism chosen: GitHub Actions cron job, ending in an email summary. This single choice satisfies three separate requirements at once (unattended execution, scheduling, and living on GitHub).
- Clarified for the record: this project does not involve model fine-tuning or weight updates. Any future "learning" feature means feedback stored and replayed as prompt examples, not model training.

**Open questions carried forward:**
- Company list not yet built.
- Runtime/language for the scaffold not yet chosen.
- Email delivery mechanism (API vs SMTP) not yet chosen.

---

## [2026-08-05] — Company list expanded to 50, Google search sourcing evaluated and rejected

**Changed:**
- Company list expanded from 3 verified candidates to a target list of 50 Chicago-area companies.
- Evaluated using Google Boolean search as a job-sourcing method. Rejected.

**Why:**
- Google's Terms of Service explicitly prohibit automated queries against search results, same category of risk as Handshake. Google is actively litigating against a scraping company over this (Google v. SerpApi, DMCA claims), showing real enforcement teeth, not just a dormant clause.
- Google's official Custom Search API is ToS-compliant but capped at 100 free queries/day and returns general web results, not job-specific data. Would not solve the original noise complaint, just adds a rate limit on top of it.
- Reframed the underlying goal (coverage broader than a hand-picked company list) toward Adzuna, a legitimate free-tier job aggregator API (~1,000 calls/month, structured data). US coverage is present but thinner than UK/EU, so this is logged as a future supplementary source, not adopted now.
- The idea that the agent should judge posting legitimacy and profile fit is valid, but belongs on noisy aggregator data (e.g., Adzuna, if added later). Direct ATS data is already clean and structured at the source and does not need a legitimacy check, only the existing fit-matching step.

**Decisions made:**
- Google search scraping (raw or via Custom Search API): rejected for this project. Will not revisit without new information changing the ToS or rate-limit picture.
- V1 sourcing remains direct ATS polling only (Greenhouse/Lever/Ashby).
- Adzuna logged as a documented future option (see PROJECT_BRIEF.md Section 9 candidates), not built now.
- Company list locked at 50 for v1:

**Confirmed on Greenhouse:** Sprout Social, FourKites, Klaviyo (Chicago office presence unconfirmed)

**Fintech/Insurtech:** Discover Financial Services, Cboe Global Markets, Guaranteed Rate, Kin Insurance, Clearcover, CCC Intelligent Solutions, Origami Risk, tastytrade (IG North America), Capital One (Chicago tech hub), Enova International, Vouch, Coro

**Health Tech:** Tempus, VillageMD, HealthJoy, Artera, ALIS

**Supply Chain/Logistics:** project44, Echo Global Logistics, Coyote Logistics, ShipBob

**SaaS/Enterprise:** G2, ActiveCampaign, Uptake, Relativity, PowerReviews, Paylocity, OpenGov, Centro, Civis Analytics, Lessen

**Consumer/Marketplace:** Cameo, SpotHero, Tovala, Cars.com, Reverb, Groupon

**Other notable Chicago tech:** Motorola Solutions, Morningstar, Halo Investing, Upside, Metropolis, 37signals (Basecamp), Fooda, ParkWhiz, Cleo, Block (Square/Cash App Chicago hub)

**Open questions carried forward:**
- ATS platform (Greenhouse/Lever/Ashby/other) unconfirmed for all but the first 3 companies. First task for the ingestion script: attempt each known URL pattern per company, log misses for manual follow-up.
- Klaviyo's Chicago-specific office/hiring presence unconfirmed.
- Some companies on this list may use ATS platforms outside our supported set (Workday, iCIMS, etc.), those get flagged and excluded during ingestion, not manually pre-filtered.

---

## [2026-08-05] — GitHub repo created

**Changed:**
- Initialized local git repo on `main`.
- Added `.gitignore` (secrets, venvs, runtime data, OS junk).
- Created private GitHub repo `HardikLad10/jobFinderAgent` and pushed initial commit (`PROJECT_BRIEF.md`, `SESSION_LOG.md`, `.gitignore`).
- Installed and authenticated GitHub CLI (`gh`) as HardikLad10.

**Why:**
- Project brief requires the agent to live on GitHub (scheduling via Actions + version history). Repo needed before scaffolding code.

**Decisions made:**
- Repo visibility: private (will hold profile/resume paths and eventually rely on GitHub Secrets for API keys).

**Open questions carried forward:**
- Runtime/language for the scaffold still open.
- Email delivery mechanism still open.
- Company ATS discovery still pending.

---

## [2026-08-05] — v0 ingestion proven on Sprout Social (Greenhouse)

**Changed:**
- Chose Python 3 as runtime; scaffolded `config/`, `ingestion/`, `requirements.txt`, `run_ingestion.py`.
- Added company config for Sprout Social (`config/companies.json`).
- Implemented Greenhouse fetch + normalize (`title`, `company`, `location`, `posted_date`, `url`).
- Runner continues past per-company failures (HTTP/JSON/shape errors logged, other companies still run).
- Live smoke test: `python3 run_ingestion.py` → 8 normalized postings from Sprout Social.

**Why:**
- Session scoped to proving ingestion on one real source before scaling to 50 companies or adding filter/match/email.
- Stdlib only (`urllib` + `json`) for v0 — one GET does not justify a dependency yet. `requirements.txt` is a placeholder for later (Anthropic, etc.).

**Decisions made:**
- Runtime: Python 3.
- Board token: use `sproutsocial`, not `sproutsocialcollege`. The college board endpoint returns HTTP 200 with an empty `jobs` list, so it cannot prove fetch+normalize. Main board currently returns 8 jobs.
- `posted_date` mapped from Greenhouse `first_published`, falling back to `updated_at` (updated_at bumps on edits, so it is a weaker "posted" signal).
- Location missing/malformed → `"Unknown"` rather than dropping the job; missing title/url/date → skip that row only.

**Open questions carried forward:**
- Email delivery mechanism still open.
- ATS discovery for the remaining ~47 companies still pending.
- Lever and Ashby clients not built yet.
- Filtering, matching, email, scheduling still out of scope until ingestion is solid.

---

## [2026-08-05] — Expanded to 50 companies; Lever/Ashby clients; API key env

**Changed:**
- Wrote all 50 SESSION_LOG companies into `config/companies.json` with `status: resolved|unresolved`.
- Added ATS discovery helper `scripts/discover_ats.py` (slug probes against Greenhouse/Lever/Ashby).
- Implemented Lever + Ashby fetch/normalize clients; runner dispatches by `ats` and skips unresolved entries.
- Live run: **22 resolved boards → ~753 normalized postings**; 28 unresolved skipped without aborting.
- Added `.env` / `.env.example` for `ANTHROPIC_API_KEY` (not used yet — matching still unbuilt).
- `run_ingestion.py` now prints a per-company summary and writes full JSON to `data/latest_ingestion.json`.

**Why:**
- Session goal was scale company config + prep the Claude key location. Matching still deferred.
- Slug auto-discovery finds boards fast but produces false positives; each hit was spot-checked against company_name / career URL before marking resolved.

**Decisions made:**
- Resolved (22): Sprout Social, FourKites, Klaviyo, Kin (Ashby), tastytrade, Enova, HealthJoy, Artera (Lever), project44, G2 (Ashby), ActiveCampaign (Lever), OpenGov (Ashby), Centro→Basis (Lever), Civis Analytics, Lessen (Lever), Cameo, SpotHero, Tovala (Lever), Groupon, Upside (Ashby), Metropolis, Block.
- Rejected false-positive slug matches: `lever/capital` ≠ Capital One; `greenhouse/village` ≠ VillageMD; `greenhouse/relativity` = Relativity Space ≠ Relativity eDiscovery; `greenhouse/echo` = Echo Neurotechnologies ≠ Echo Global; `greenhouse/cleo` = meetcleo fintech ≠ Chicago Cleo.
- Vouch/Coro have Ashby HTML pages but public posting API 404 — left unresolved until a working API token is found.
- ParkWhiz left unresolved (folded into SpotHero careers post-acquisition).
- Claude key lives in local `.env` as `ANTHROPIC_API_KEY`; `.env` is gitignored. Matching code will read it later.

**Open questions carried forward:**
- Manual follow-up for 28 unresolved companies (many likely Workday/iCIMS/custom).
- Email delivery mechanism still open.
- Filtering + Claude fit-matching still next, not built.
- Whether to add `python-dotenv` when matching lands, or read `.env` manually.

---

## [2026-08-05] — Spec update: sponsorship filter + resume profile rules

**Changed:**
- Expanded `PROJECT_BRIEF.md` Architecture step 3 (Filtering) with sponsorship exclusion phrase list and red-flag semantics (`exclusion_found` / `none_found`).
- Documented resume input as stripped `config/resume_profile.md` under Tech Stack (Section 6).
- Verified description dependency against live data/APIs before building the filter (see Decisions).

**Why:**
- Sponsorship signal is almost never a positive claim; exclusionary language is the reliable deterministic check. Needs body text, so ingestion schema must grow before filter code lands.
- Resume PII must not rely on "private repo" alone because git history outlives visibility settings.

**Decisions made:**
- Current `data/latest_ingestion.json` has only `title/company/location/posted_date/url` — **no description**. Sponsorship filter blocked until ingestion captures body text.
- Greenhouse list needs `?content=true` (verified: adds HTML `content` field). Lever list already includes `descriptionPlain`; Ashby list already includes `descriptionPlain`. No per-job detail fetch required for Lever/Ashby if we start capturing those fields.
- Filter not implemented this entry — verify-then-build gate only.

**Open questions carried forward:**
- Build order: extend ingestion schema with `description` next, then deterministic filters (title/location/sponsorship/dedupe), then matching.
- Resume file `config/resume_profile.md` not created yet (needs user PDF → strip → manual review).
- Email delivery mechanism still open.

---

## [2026-08-05] — Stripped resume profile created

**Changed:**
- Added `config/resume_profile.md` from `Hardik_SWE_FullStack.pdf` with name/phone/email/profile links/project GitHub URLs removed.
- Gitignored `*.pdf` so the original resume is not committed.

**Why:**
- Matching needs a durable profile text; PII should not rely on private-repo privacy alone.

**Decisions made:**
- Kept education, experience, projects (sans URLs), and skills. Project GitHub URLs dropped because they embed a username.
- V1 remaining work after resume review: description ingestion → deterministic filters → matching → email → Actions cron (matching is not the final step).

**Open questions carried forward:**
- User should manually review `config/resume_profile.md` once before commit.
- Email delivery mechanism still open.

---

## [2026-08-05] — Description ingestion + filters + Claude matching

**Changed:**
- Extended normalized schema with `description`. Greenhouse now fetches `?content=true` and strips HTML; Lever/Ashby capture plain-text description fields already on the list endpoints.
- Added `config/filters.json` and `filtering/` module: title include/exclude → location → sponsorship red-flag → seen-URL dedupe.
- Added `matching/` module: Claude Haiku 4.5 (`claude-haiku-4-5`) via Anthropic Messages API over stdlib `urllib`; reads key from `.env`; scores `strong|maybe|no` + reasoning against `config/resume_profile.md`.
- Added `run_pipeline.py` (`--skip-match`, `--match-limit`, `--mark-seen`).
- Live run: 764 ingested (762 with description) → 3 after filters → 3 matched (2 strong, 1 maybe).

**Why:**
- Sponsorship filter needs body text; verified earlier that GH needs `content=true` while Lever/Ashby already return descriptions.
- Filters stay deterministic; Claude only runs on the survivors (cost control + philosophy).
- No Anthropic SDK yet — one HTTPS POST does not need a dependency.

**Decisions made:**
- Title keywords live in editable `config/filters.json` (same scalability idea as companies.json).
- Location include list covers Chicago/Illinois **and** `remote` — most target companies post Remote US; pure Chicago-only was dropping almost everything useful. Tunable in filters.json.
- Sponsorship drops `exclusion_found` from the match queue; survivors tagged `sponsorship_flag: none_found` (not a positive confirmation).
- Dedupe store: `data/seen_jobs.json`, updated only when `--mark-seen` is passed (avoid hiding jobs during iterative testing).
- Email + GitHub Actions still not built.

**Open questions carried forward:**
- Email delivery mechanism (API vs SMTP) still open.
- Whether title keywords / remote inclusion need tuning after a few real runs.
- Wire GitHub Actions cron once email path is chosen.

---

## [2026-08-05] — Resend email module + local dry-run

**Changed:**
- Added `delivery/` module: builds strong+maybe summary, sends via Resend API (stdlib urllib).
- Wired `--dry-run-email` / `--send-email` on `run_pipeline.py`.
- Updated `.env.example` with `RESEND_API_KEY`, `TO_EMAIL`, `FROM_EMAIL`.
- Local dry-run succeeded: To `hardiklad1@hotmail.com`, subject `Job matches: 2 strong, 1 maybe` — printed only, not sent.
- GitHub Actions workflow **not** added yet (local-first per request).

**Why:**
- Resend chosen over Hotmail SMTP for Actions reliability later.
- Dry-run first so email body can be reviewed before any real send or cloud cron.

**Decisions made:**
- Email includes strong + maybe only; zero matches → skip send.
- Default To: `hardiklad1@hotmail.com`. Default From: Resend onboarding sender until a domain is verified.
- Cloud Actions still the intended daily scheduler; not implemented this step.

**Open questions carried forward:**
- User needs a Resend API key in `.env` before `--send-email` works.
- Next: add GitHub Actions cron (`0 13 * * *` UTC / 8am CT) + persist `seen_jobs.json`.

---

## [2026-08-05] — First real Resend send (Gmail test recipient)

**Changed:**
- Confirmed `RESEND_API_KEY` in `.env` and sent a live email.
- Resend id `f29266a1-512f-406d-9178-b107025c70df`, subject `Job matches: 2 strong, 1 maybe`.

**Why / constraint:**
- Without a verified domain, Resend only allows sending to the account owner email (`hardik.lad773@gmail.com`). Sending to `hardiklad1@hotmail.com` returns HTTP 403.

**Decisions made:**
- For now, deliver to Gmail (Resend account email) until a domain is verified at resend.com/domains; then switch `TO_EMAIL` / `FROM_EMAIL` back to hotmail + custom from-address.

**Open questions carried forward:**
- Verify a domain (or keep Gmail as To) before Actions goes live to hotmail.
- GitHub Actions cron still not built.

---

## [2026-08-05] — GitHub Actions daily cron + Gmail as To

**Changed:**
- Default `TO_EMAIL` → `hardik.lad773@gmail.com` (Resend account email; hotmail deferred).
- Added `.github/workflows/daily_job_search.yml`: cron `0 13 * * *` (8am CDT) + `workflow_dispatch`.
- Pipeline on Actions: `python run_pipeline.py --send-email --mark-seen`, then commit-back of `data/seen_jobs.json`.
- Track `data/seen_jobs.json` in git (gitignore exception) so seen URLs persist across runs.

**Why:**
- Secrets are already in the repo; workflow was the missing piece for unattended cloud runs.
- Commit-back beats Actions cache for durable dedupe on a private personal agent.

**Decisions made:**
- Keep Gmail as destination (user confirmed). No Resend domain required for v1.
- Schedule only fires from the repo default branch (`main`); feature branch can still use Run workflow manually after push.

**Open questions carried forward:**
- Merge workflow to `main` so the daily cron actually arms.
- Optional: add `TO_EMAIL` secret (defaults to Gmail if omitted).

---

## [2026-08-05] — Include posted_date in match emails

**Changed:**
- Email text/HTML now shows `Posted: <posted_date>` for each strong/maybe job so the recipient can judge urgency without opening the ATS page.

**Why:**
- Pipeline already captures `posted_date` at ingest; it was omitted from the email body. Recency is a key action signal even without a hard recency filter.

**Decisions made:**
- Display raw ISO timestamp from ATS (no timezone reformatting yet). Missing date → `unknown`.

**Open questions carried forward:**
- Optional later: recency filter (e.g. only jobs posted in last N days).

---

## [2026-08-05] — Illinois CSOD within-1-day reminder (not full ingestion)

**Changed:**
- Added `alerts/illinois_csod.py`: fetch anonymous JWT from career page → POST CSOD search with `postingsWithinDays=1` → read `totalCount`.
- If count > 0 and `--send-email` / `--dry-run-email`, send a separate Reminder email: "X jobs found from this page" + board link + titles.
- Wired into `run_pipeline.py` (failures logged; do not abort main G/L/A pipeline). `--skip-illinois` to disable.

**Why:**
- UIUC grad use case: Illinois board often yields campus FT roles (H-1B exempt / lower tax angle), but has no native email alerts. User wants a daily nudge to check the board, not Claude fit-matching on CSOD.
- Verified live: count retrieval is easy today (`totalCount` available). Reminder-only keeps CSOD out of the matching schema.

**Decisions made:**
- CSOD is **reminder-only**, not a fourth matching ATS. Still not scraping Handshake-style; uses the same public career-page JWT the browser uses.
- Risk accepted for one board: token/HTML fragility may break the alert; main pipeline unaffected.
- Email only when X > 0; X = 0 → silent skip.

**Open questions carried forward:**
- Optional: include role links in the Illinois email (currently titles + board URL).
- Recency filter for G/L/A boards still optional.
