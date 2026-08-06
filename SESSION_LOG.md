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

---

## [2026-08-05] — Illinois reminder separated + minimal dual-recipient email

**Changed:**
- Removed Illinois from `run_pipeline.py` (main G/L/A agent intact again).
- Added standalone `run_illinois_reminder.py` + `.github/workflows/illinois_csod_reminder.yml`.
- Email body minimized: `X new jobs found today` + `a software jobs` / `b analyst jobs` (case-insensitive title substring) + board link.
- Recipients: `hardik.lad773@gmail.com` and `anvekshavinod24@gmail.com` via `ILLINOIS_TO_EMAILS`.

**Why:**
- User requested hard separation from main logic and a nudge email a classmate can also receive.
- Keyword flags are coarse on purpose — JDs still need manual review.

**Decisions made:**
- Separate workflow over shared job (isolation > tiny Actions-minute savings).
- Resend may 403 the second Gmail until a domain is verified; dry-run validates content regardless.

**Open questions carried forward:**
- Confirm real send to `anvekshavinod24@gmail.com` after Resend domain / allowlisting.
- Recency filter for main G/L/A boards still optional.

---

## [2026-08-05] — Illinois email: Hardik only (Gmail forward later)

**Changed:**
- `ILLINOIS_TO_EMAILS` default / workflow fallback → `hardik.lad773@gmail.com` only.
- Dropped dual Resend `to:` that caused HTTP 403 (blocked entire send including Hardik).

**Why:**
- Resend without a verified domain cannot email `anvekshavinod24@gmail.com`. User chose free option A: send to Hardik, Gmail auto-forward to classmate later (no domain spend).

**Decisions made:**
- Gmail SMTP / paid domain deferred. Forwarding is a Gmail UI step, not agent code.

**Open questions carried forward:**
- Set up Gmail filter/forward: subject contains `Illinois careers` → `anvekshavinod24@gmail.com`.
- Recency filter for main G/L/A boards still optional.

---

## [2026-08-05] — Locked Midwest/UIUC product geography + ATS tiers (pre-discovery)

**Changed:**
- Updated `PROJECT_BRIEF.md`: product outcome (daily curated SWE list for UIUC/Midwest grads), company geography (Greater Chicago + all Illinois + neighboring WI/IN/MI/MO/IA), location-filter intent, ATS tiers (G/L/A/Breezy primary → Workday next → defer Comeet/Paylocity/Oracle), filter-then-Claude cost posture.
- Discovery of 100–150+ companies **not started** — design/tradeoffs discussion next.

**Why:**
- Chicago-only under-serves a UIUC student in Urbana–Champaign. Location reward + school/alumni recognition in Midwest employers is the customer-obsessed framing.
- User OK exceeding 100–150 during discovery; triage effort later. Cost OK while filters run before Claude (~cents so far).

**Decisions made (locked):**
- Geography: all of metro+suburbs, statewide IL, neighboring-state tech footprint.
- ATS: expand on Greenhouse/Lever/Ashby/Breezy first; Workday second; skip Comeet/Paylocity/Oracle for now.
- Filters (title + location + sponsorship) remain the quality/cost control plane.
- End-product bar: daily list where most emailed roles are worth opening/applying.

**Open questions carried forward:**
- Design/tradeoffs for discovery execution (sources, false-positive checks, when to build Workday client, exact `filters.json` keyword expansion).
- Then run discovery with user go-ahead.

---

## [2026-08-05] — Workday canned for v1; prefer 10–999 emp companies

**Changed:**
- `PROJECT_BRIEF.md`: Workday moved from "v1 next" to **out of v1**. Discovery/resolution targets Greenhouse/Lever/Ashby/Breezy only.
- Company size bias locked: prefer small–mid (~10–999 employees), not megacorp Workday boards.

**Why:**
- v1 excludes Workday because boards are tenant-specific, fragile to scrape, and not a clean public JSON feed like G/L/A/Breezy; client cost (URL shape, POST, pagination, descriptions) is poor ROI.
- SMB-focused Midwest discovery (~10–999 employees for UIUC/callback fit / ATS mix) already targets G/L/A/Breezy — Workday would mainly surface megacorp boards outside that product criterion.
- May still note a Workday careers URL on unresolved rows for a future phase; no client build.

**Decisions made (confirm set for discovery plan):**
1. Seed style: curated Midwest/UIUC list (not aggregator scrape).
2. Workday: canned for v1.
3. Remote in location filter: keep while company list is Midwest-curated.
4. Phases: widen filters → discover G/L/A/Breezy → smoke ingest/filter (Claude capped); no Workday phase.
5. Strict false-positive spot-check before marking resolved.
6. Size: prefer ~10–999 emp.

**Open questions carried forward:**
- Execute via Cursor Plan when user approves the plan.

---

## [2026-08-05] — Phase 1: Midwest location filter widened

**Changed:**
- Expanded `config/filters.json` `location_include_any` with Chicago suburbs, Champaign/Urbana + other IL cities, and neighbor-state city/state tokens (WI/IN/MI/MN/MO/IA). Kept `remote`.
- Discovery seed ceiling noted for Phase 2: allow **>250** company names (user request).

**Why:**
- Locked product geography is Midwest/UIUC-local, not Chicago-only. Without wider location strings, good suburban/Champaign/neighbor roles would never reach Claude.

**Decisions made:**
- Short state tokens use comma/space forms where possible (`, wi`, `, in`) to reduce bare-word false positives; city names carry most of the signal.
- Phase 2 not started; waiting for user go. Seed size target raised above 250.

**Open questions carried forward:**
- Phase 2: curated seed >250 + probe G/L/A/Breezy.

---

## [2026-08-05] — Phase 2: Midwest seed discovery + merge

**Changed:**
- Wrote `config/midwest_seed.json` — **822** unique company names (existing 50 + Midwest/UIUC-relevant tech/fintech/health/logistics and adjacent SaaS).
- Upgraded `scripts/discover_ats.py` to load seed file, probe Greenhouse/Lever/Ashby/**Breezy**, prefer longer/specific slugs (short first-word tokens only via ALIASES), write `config/companies.discovered.json`.
- Ran full probe: raw hits **201/822** (G 143 / A 33 / L 24 / Breezy 1).
- Strict spot-check rejected **8** false positives; **0** Breezy boards kept after review.
- Merged into `config/companies.json`: **191 resolved** (was 22), **631 unresolved**, **822** total.

**Rejected false positives (this pass):**
- `greenhouse/fetch` ≠ Fetch Rewards (pet-insurance board)
- `greenhouse/indigo` ≠ Indigo Ag (underwriting board)
- `greenhouse/motive` ≠ Motive/KeepTruckin (`wearemotive.com` agency)
- `greenhouse/current` ≠ Current banking (Drupal/web agency)
- `ashby/shift` ≠ Shift used cars (Australia finance)
- `greenhouse/autotrader` ≠ Cox AutoTrader US (UK Auto Trader)
- `greenhouse/seesaw` ≠ Seesaw Learning (Amman/Qatar board)
- `breezy/katapult` ≠ Katapult Holdings (`Katapult Network`)

**Why:**
- Expand coverage beyond the original ~50 Chicago list without Workday; keep only boards that survive identity spot-check.

**Decisions made:**
- Prefer full-name/alias slugs over bare first-word guesses (blocks capital/village/echo/cleo class of FPs).
- Empty-but-valid boards (0 jobs at discovery) kept as resolved for future posts.
- Duplicate board names (`Block Inc`, `PathAI Inc`) left unresolved pointing at canonical entry.
- **No Phase 3 Breezy client** for now — only Breezy hit was a false company match.

**Open questions carried forward:**
- Phase 4: smoke ingest+filter (Claude capped) + push `main` when user says go.
- Triage unresolved megacorps / non-SMB entries later if ingest volume is noisy.

---

## [2026-08-05] — Discovery backlog: unresolved ≠ no careers board

**Clarified (product scoping, not Phase 4):**
- Phase 2 method: guess slug tokens → HTTP probe Greenhouse/Lever/Ashby/Breezy → spot-check board identity before marking resolved.
- **~631 of 822 unresolved does not mean "no careers board."** Usual causes: wrong ATS (Workday, custom/iCIMS/etc.), or a real G/L/A/Breezy slug that was unguessable from the company name.
- v1 intentionally does **not** deep-hunt careers pages for unresolved names (no HTML crawl of company sites to find the ATS).
- **Future scoping backlog:** when a real G/L/A/Breezy careers URL/slug is found in the wild, add the token to `config/companies.json`. Optional later: deeper ATS discovery — out of current v1 scope.
- **Phase 3 Breezy client skipped:** 0 verified Breezy boards after spot-check (only FP was Katapult Network ≠ Katapult Holdings).

**Decisions made:**
- Keep unresolved rows as a backlog of "public board not yet found," not "company has no jobs."
- Do not re-enable Workday or start Phase 4 from this note.

---

## [2026-08-05] — Phase 4: smoke ingest + filter (Claude capped)

**Command:** `python3 run_pipeline.py --match-limit 5` (~71s wall; full_network). Cap = **5** Claude Haiku calls (`--match-limit 5`). No `--mark-seen`, no email, no push, no commit.

**Funnel:**
| Stage | Count |
| --- | --- |
| Resolved boards attempted | **191** / 191 (G 135 / A 32 / L 24); 631 unresolved skipped |
| Hard ingest failures / rate limits | **0** |
| Empty boards (HTTP OK, 0 jobs) | **9** (KeepTruckin, OnDeck, Optiver, Carbon Health, Plaid, HubSpot, Boomi, Instructure, MyCase) |
| Jobs ingested | **15,092** (15,088 with description) |
| After title filter | **785** (title_drop=14,307) |
| After location filter | **248** (location_drop=537) |
| After sponsorship | **248** (sponsorship_drop=0) |
| After dedupe | **245** (dedupe_drop=3) |
| Claude matched (capped) | **5** → 1 strong / 1 maybe / 3 no |

**Claude spend:** ~5 Haiku calls only (~$0.01–0.02 at brief rates). Full filtered set was 245; matching stopped at the hard cap of 5.

**Issues worth knowing (not blockers):**
- Title include keywords `new grad` / `entry level` alone let non-SWE roles through (Flexport SDR ×2, Samsara tech sales, Grafana AE). Claude correctly marked sales as `no`; tighten title include (require SWE token) or add sales excludes later.
- Entrata `STRONG` hit is Pune, India — false location hit: filter token `, in` matches inside `, India`. Tighten Indiana token later.
- Empty boards above may be stale tokens or truly empty — leave as resolved for future posts (same Phase 2 policy).

**Artifacts:** `data/latest_ingestion.json`, `data/latest_filtered.json`, `data/latest_matches.json`, `data/phase4_smoke.log`. Working tree left dirty; **not pushed**.

**Decisions made:**
- Phase 4 smoke proven at 191-board scale; Claude remains optional/capped for cost.
- No Breezy client; no unresolved deep-hunt; push deferred until user says go.

---

## [2026-08-05] — Freshness filter (N=7) + compact match email

**Changed:**
- Added `max_age_days: 7` to `config/filters.json`.
- Extended `filtering/`: after sponsorship and before seen-URL dedupe, drop postings older than 7 days; missing/null/unparseable `posted_date` kept. Stage logged as `freshness_drop`.
- Reworked match email in `delivery/` to one compact line per strong/maybe: `Title — Company — Posted date — reasoning — link` (reasoning capped ~120 chars). Tiny count header only.
- Updated `PROJECT_BRIEF.md` Architecture/Delivery/V1 for freshness + email shape; removed "posted-within-N-days" from pure future list.

**Why:**
- Stale ATS listings were surviving title/location/sponsorship and reaching Claude/email; a deterministic date gate cuts noise before the agentic step without replacing URL-based seen dedupe.
- Multi-paragraph per-job emails were hard to scan; one line per match matches how the list is actually used (open link or skip).

**Decisions made:**
- Freshness N=7; null/missing/unparseable `posted_date` → keep.
- Chain order: title → location → sponsorship → **freshness** → URL seen-dedupe → Haiku.
- Email: one line per match; truncate long Claude reasons at display time only (matching prompt unchanged).
- Spec language stays third-person product rationale in `PROJECT_BRIEF.md`.

**Open questions carried forward:**
- No re-smoke ingest, no Claude matching, no push/commit in this session.
- Indiana location false-positive (`, in` vs India) and title-include sales bleed still open from Phase 4.

---

## [2026-08-05] — Actions verify + freshness filter re-smoke

**Actions (Step 4):** PASS — no edits.
- `.github/workflows/daily_job_search.yml` already runs `python run_pipeline.py --send-email --mark-seen`.
- Follow-up step commits/pushes `data/seen_jobs.json` when changed (`chore: update seen jobs after daily run`).
- Illinois reminder workflow untouched.

**Filter re-smoke (Step 5):** Reused `data/latest_ingestion.json` (15,092 postings); no re-ingest; `--skip-match` / no Claude; no `--mark-seen`.

Funnel (`max_age_days=7`, null posted_date kept):
- ingested **15092** → title_drop **14307** → location_drop **537** → sponsorship_drop **0** → freshness_drop **209** → dedupe_drop **0** → kept **39**

**Artifacts:** refreshed `data/latest_filtered.json` (39). **No push, no commit.**

---

## [2026-08-05] — Haiku match on 39 filtered (reuse, no re-ingest)

**Ran:** Loaded `data/latest_filtered.json` (39) → Haiku match all → `--send-email` + `--mark-seen` (no full ingest of ~15k).

**Funnel:** strong **14** · maybe **11** · no **14** (39/39). Elapsed ~109s. Rough cost ~**$0.12** (heuristic ~$0.003/job).

**Email:** Sent via Resend to hardik.lad773@gmail.com — subject `Job matches: 14 strong, 11 maybe` (compact one-line format). Resend id `6bfc2d28-f4fc-44fb-a7d1-342379baeccc`.

**Seen store:** `data/seen_jobs.json` 3 → 42 URLs so daily won't re-mail these.

**Commit/push:** Midwest discovery + freshness N=7 + compact email landed on `main` as `a0c42b4` (see prior entry / git log).

---

## [2026-08-05] — Email Strong/Maybe sections + remote geo gap scoped

**Changed:**
- `delivery/__init__.py`: match email body now has separate **Strong** and **Maybe** sections under the count header (text + HTML), not one flat list.
- `PROJECT_BRIEF.md`: location intent clarified to **US-remote** (not global remote); documented bare-`remote` substring as a known v1 gap that must be fixed in v1.
- This log entry: root-cause of EU remotes in the first Midwest-scale digest + Midwest visibility problem.

**Why / what went wrong:**
- Brief intent said remote/US-remote; early filter decision kept the token `remote` because many boards label "Remote US." Execution was **substring include of `remote` only** — not "Remote US." Grafana-style `Ireland | Remote` therefore passes location and reaches Haiku.
- After 191 boards + N=7, the kept set (39) was dominated by global remotes; Haiku correctly scored stack fit, so the email looked strong but **geo-wrong**. Midwest on-site roles were scarce in that survivor set (crowded out / fewer fresh title hits), not because Haiku hates Midwest.
- Scope was partially considered (Midwest keywords widened in Phase 1) but the remote rule was never tightened to match US-remote intent before scale-up — a brief vs filters.json mismatch.

**Decisions made:**
- Email section split ships now (v1 polish).
- Bare-`remote` over-admit is **in-scope for a v1 filter fix** (not deferred forever). Prefer deterministic filter engineering over asking Haiku to police geography. Expect some residual noise.
- Also track: `, in` matching India; title keywords leaking non-SWE "entry level" roles.

**Open questions carried forward:**
- Exact remote rule for the v1 fix (remote+US include list vs non-US exclude list vs both) — brief before implementing.
- Whether to clear/revisit `seen_jobs.json` for geo-false emails already marked seen (those URLs won't reappear until store prune/manual edit).

---

## [2026-08-05] — US-remote location gate (before Haiku) + seen reset

**Changed:**
- Removed bare `remote` from `location_include_any`; removed `, in` (India false positive).
- Added `remote_us_include_any` + `remote_non_us_exclude_any` and `_location_allowed()` in `filtering/`: Midwest geo OR (remote without non-US tokens; US signals preferred; bare remote kept as residual noise).
- Emptied `data/seen_jobs.json` so the prior EU-heavy digest does not block a clean re-score.
- `PROJECT_BRIEF.md` updated to match implemented rules.

**Why:**
- Geography is a deterministic cost/quality gate. Non-US remotes must not reach Haiku. Resetting seen avoids permanently suppressing jobs that were only "seen" under the bad rule.

**Decisions made:**
- Filter before Haiku (not prompt-based geo).
- Ambiguous "Remote" with no country still kept (recall > zero residual noise).
- Re-run filter+match on existing ingest (no need to re-poll 191 boards for this validation).
- `_lower_list` must **not** strip tokens: `" il "` → `"il"` was matching Oakv**il**le / Manv**il**le and admitting Canada/NJ noise. Fixed before re-score.

**Re-run (reuse ingest, empty seen):** 15092 → kept **16** (location_drop **640**) → Haiku 16 → **4 strong / 4 maybe / 8 no**. Email sent (Resend `f4684757-…`). EU remotes gone from digest. Residual title noise (Carvana “entry level” auto roles, Samsara recruiter via “software engineering” substring) correctly scored `no` by Haiku — title-keyword tighten still open.

**Open questions carried forward:**
- Title include: exclude `recruiter`; avoid bare `entry level` or require SWE co-token.
- Whether Atlanta-only “Remote Friendly” without US token should stay (currently kept as ambiguous remote).
