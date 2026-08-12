# Job Search Agent — Project Brief

**Status:** Core pipeline + daily Actions live. V2 coverage expansion shipped (LCA + Built In seeds → ~418 resolved boards; freshness N=3). Next: Breezy ingest. Day-to-day progress in `SESSION_LOG.md`.
**Type:** Warm-up build. Smaller and faster than the main portfolio project (OTC/FMCG agentic project, scoped separately). Purpose here is reps with the stack and real engineering judgment, not scale.

This file is the stable reference. It should rarely change. Day-to-day progress, decisions made while building, and things that changed from this plan belong in `SESSION_LOG.md`, not here.

---

## 1. Engineering Philosophy — Read This First

This is not a "get it working" project. The output that matters is the judgment behind the code, not just a working script. Every non-trivial decision should be explainable: why this approach, what else was considered, what the tradeoff was.

Non-negotiables for anyone (human or AI) working on this codebase:

- **Clarity over cleverness.** Code should be readable by someone who didn't write it. No unnecessary abstraction, no magic.
- **Understand before you use.** No framework or library gets added without understanding what it's doing underneath. If a library is used, be able to explain what it would take to build that piece by hand.
- **Deterministic by default, agentic only where judgment is genuinely needed.** Most of this pipeline is plumbing (fetch, filter, dedupe). Exactly one step needs an LLM: deciding if a job fits. Do not let "AI-powered" creep into steps that are really just logic.
- **State tradeoffs, don't hide them.** Every meaningful design choice in this project should have a one-line "why this, not that" attached, either in code comments or in `SESSION_LOG.md`.
- **Future scope is designed for, not built.** Code should be structured so features listed in Section 9 could be added without a rewrite. That does not mean building them now.

---

## 2. Problem Statement

Finding job postings isn't hard. Finding postings that are actually new and actually relevant is. Aggregators like Jobright surface postings that are already a day or more old, presented as fresh. There's no reliable way to see new-grad SWE postings the moment they go live, filtered to fit, without manually checking multiple sites daily.

### Product outcome (customer obsession)

For a UIUC student (or similar Midwest grad), the win is a **daily curated list of SWE-fit roles they can open and apply to**, where most survivors are already profile-matched (~80% target intuition, not a hard SLA).

Chicago-only is the wrong north star. What matters:

1. **Location reward** — roles in places where being local / regional raises callback odds (Illinois including Champaign–Urbana and Chicago suburbs; neighboring Midwest states with a tech footprint; Remote US tied to those employers).
2. **UIUC / Midwest name recognition** — employers that hire from UIUC or have Midwest alumni density; campus and regional signal beats "random coastal FAANG board."

Company-list geography and the location filter are **two knobs**. We poll a wide Midwest-relevant company set; deterministic filters decide what reaches Claude.

## 3. Why This Is an Agent, Not Just Prompting Claude Directly

Manually pasting a job posting into Claude and asking "does this fit me" works, but it requires a human to find the posting, copy it, and ask, every single time. That's not automation, that's a human doing 90% of the work and Claude doing the last 10%.

An agent means the fetching, filtering, and deduping are automated and unattended. Claude is invoked only for the one step that needs real judgment: does this specific posting fit this specific profile. The value isn't "smarter AI," it's removing the manual checking.

**Cost posture:** always **filter first, then Claude**. Opus 5 on survivors only (deterministic filters already cut the firehose). At current filtered volume cost stays modest; do not optimize Claude spend until filters are wrong or volume explodes. Fireworks remains a documented future pre-filter, not v1 work.

**Note on "learning":** this project does not involve the model updating its own weights (that's fine-tuning/RL, a different and heavier thing, out of scope). "Learning" here, if built later, means storing feedback on past matches and feeding examples back into future prompts. Real, but it's adaptation through context, not model training. Don't conflate the two.

## 4. Platform Constraints — Decided, Don't Revisit Without New Information

- **Handshake: do not scrape.** Handshake's Terms of Service explicitly prohibit bulk collection via automated scripts, and API access is restricted to official university Career Services partners, not individual students. An autonomous agent hitting Handshake risks the account, which is tied to university identity. Decision: excluded from this project entirely.
- **Wellfound: do not scrape.** Public listings are viewable without login, but the platform runs active anti-bot defenses (rate limiting, JS challenges, CAPTCHAs on repeated automated requests). Building against that is a maintenance burden, not a clean data source. Decision: excluded from v1.
- **Chosen approach: pull directly from company ATS platforms.** Prefer public, structured, unauthenticated JSON job APIs (source of truth, fresher than aggregators, no ToS fight when the board is public).

### ATS support tiers (locked 2026-08-05)

| Tier | ATS | Notes |
|---|---|---|
| **v1 only** | Greenhouse, Lever, Ashby, BreezyHR | Clean public JSON feeds; all company discovery/resolution targets these |
| **Out of v1** | Workday | Canned for v1 — boards are tenant-specific, fragile to scrape, and not a clean public JSON feed like G/L/A/Breezy (POST, tenant/site/dc, pagination, often detail fetch). May note `workday_url` on unresolved rows for a future phase; do not build the client now |
| **Defer** | Comeet, Paylocity, Oracle Cloud | No clean no-auth board feed for this agent |
| **Separate product** | Illinois CSOD (`illinois.csod.com`) | Reminder-only workflow; not part of fit-matching |

### Company size bias (locked)

Prefer **small–mid employers (~10–999 employees)** for the curated list. Why: better UIUC/callback fit than megacorp boards; SMB-focused Midwest discovery targets public G/L/A/Breezy feeds (cleaner than tenant-specific Workday). Large enterprises can appear as unresolved notes if useful later, but they are not the discovery priority.

## 5. Architecture

Deterministic pipeline with exactly one agentic step.

1. **Company list (manual, deterministic).** Curated list of Midwest-relevant employers (see geography below). Lives in `config/companies.json`, grows via discovery. Target 100–150+ resolved boards; seed lists may exceed **250** names during discovery — triage afterward. Prefer ~10–999 employees. **Unresolved** rows mean "public G/L/A/Breezy board not yet found" (wrong ATS, custom careers page, or unguessable slug) — not "company has no jobs." They are a discovery backlog for later scoping, not an employment-empty signal.
2. **Ingestion (deterministic).** Poll each company's public ATS API on a schedule. Normalize into one schema: title, company, location, posted date, URL, description (full body text required by the sponsorship filter below).
3. **Filtering (deterministic, no LLM).** Title keywords → location → sponsorship exclusion → **freshness (posted within last N days)** → dedupe against a "seen jobs" store (URL identity). Robust filters are the cost and quality control plane; Claude never sees the raw firehose.

   **Title filter intent:** Prefer software-engineering role tokens (`software engineer`, `software developer`, `swe`, fullstack/backend/frontend variants, etc.). Level-only phrases such as bare `entry level` / `new grad` / `junior` are **not** sufficient includes — they admitted non-SWE work (e.g. automotive lot roles). Real new-grad SWE titles still pass via the role token (e.g. “New Grad Software Engineer”). Explicit excludes cover recruiters, sales SDRs, and common non-SWE auto/warehouse titles so substring hits like “Software Engineering” inside a recruiter title do not reach Claude.

   **Location filter intent:** Illinois (Chicago metro + suburbs such as Naperville/Schaumburg/Bolingbrook + Champaign/Urbana and other IL tech locales) **and** neighboring Midwest signals (WI/IN/MI/MO/IA/MN) **and** **US-remote**.

   **Location rules (deterministic, before Claude):**
   1. Pass if location matches a Midwest/geo include token (`location_include_any` in `config/filters.json`). Bare `remote` is **not** a geo token.
   2. Else if location contains `remote`: **drop** when a non-US country/region token appears (`remote_non_us_exclude_any`); **keep** when a US signal appears (`remote_us_include_any`); ambiguous remote-only strings are **kept** (residual noise accepted).
   3. Else drop.

   Residual noise is expected; geography must not rely on the matching model. Indiana uses full tokens (`indiana`, `indianapolis`) — not `, in` — to avoid India false positives.

   **Freshness filter (deterministic):** Keep postings whose `posted_date` falls within the last **N = 3** days (`max_age_days` in `config/filters.json`; v2 lock — was 7). Missing, null, or unparseable `posted_date` values are **kept** (do not drop on uncertainty). Older than N days are dropped. Sits after sponsorship and before seen-URL dedupe so stale boards do not reach Claude; stage drop count is logged as `freshness_drop`. Seen-URL dedupe remains the identity gate for "already emailed / already judged" — freshness does not replace it.

   **Sponsorship exclusion filter (deterministic, keyword-based):**

   Purpose: companies rarely state they DO sponsor, but sometimes explicitly state they DON'T. Reverse-engineer the signal by flagging exclusionary language instead of searching for a positive signal that rarely exists.

   This is a RED-FLAG filter, not a green-flag one. Absence of these phrases means "no exclusion found," not "confirmed sponsorship available." Tag output accordingly (e.g. `sponsorship_flag: "exclusion_found"` / `"none_found"`), never as a positive confirmation.

   Match on phrases, not bare words — "citizen" alone false-positives on "global citizen," "corporate citizenship," etc.

   Phrase list:
   - "U.S. citizen" / "US citizen"
   - "citizens only"
   - "citizenship required"
   - "must be authorized to work" (without sponsorship)
   - "unable to sponsor"
   - "no visa sponsorship"
   - "does not sponsor" / "do not sponsor"
   - "security clearance" / "clearance required"
   - "ITAR" (strong signal in aerospace/defense postings specifically)

   Dependency: requires full job description body text, not just title/location. Greenhouse uses `?content=true`; Lever/Ashby include plain text on list endpoints.

4. **Matching (the one agentic step).** For each new, filtered posting, one Claude Opus 5 call compares the resume/profile to that posting’s **full normalized record**: title, company, location, posted date, URL, and **complete job description** (About / Requirements / responsibilities / preferred quals as the ATS provided them). **Do not truncate the description** for matching — filters already bound daily Claude volume to tens of survivors; email-only trimming of *reasoning* display is separate (step 5).
5. **Delivery (deterministic).** Strong/maybe matches emailed at end of run. Format: tiny header with counts, then separate **Strong** / **Maybe** sections, each with **one compact line per match** — `Title — Company — Posted date — one-line reasoning — link`. Reasoning is trimmed/capped (~120 chars) for email display; no multi-paragraph per-job summaries.
6. **Scheduling (deterministic, infrastructure).** GitHub Actions cron triggers the pipeline for an early-morning America/Chicago delivery window (cron at 6:00 AM Central; see Tech Stack). Separate workflow for Illinois CSOD reminder (same window).

### Company geography (locked)

Discovery targets all of:

- **Greater Chicago metro + suburbs** (Naperville, Schaumburg, Bolingbrook, etc.)
- **All Illinois**, including UIUC / Champaign–Urbana ecosystem
- **Neighboring states with a tech footprint** (WI, IN, MI, MO, IA)

Why: for a UIUC user, callback odds rise with local/regional roles and Midwest employers that recognize the school and host alumni — not with "Chicago startups only."

## 6. Tech Stack — Locked Decisions

- **Matching model:** Claude Opus 5 (`claude-opus-5`), via Anthropic Console API key. Deterministic filters already narrow the set; Opus 5 is the locked judgment model on survivors (stronger level/stack discrimination than Haiku 4.5). Pricing: **$5 input / $25 output** per million tokens. Matching uses medium effort (thinking on by default) with `max_tokens` 4096.

  **Haiku → Opus tradeoff (measured 2026-08-06, same 16 URLs):** Opus agreed with Haiku on 12/16 fits and flipped 4 toward more conservative labels (several `strong` → `maybe`, one `maybe` → `no`). Clear mismatches (recruiter, non-SWE auto roles, senior-specialist L4) stayed `no` on both. Product effect: fewer `strong` rows in email, more `maybe`. Cost for that 16-job pass was ~**$0.40** (~**$0.025/job** wall ~76s). Acceptable at tens of survivors per day; title filters should keep non-SWE junk from reaching Opus.
- **Fireworks AI ($500 credit):** not used in v1. Reserved for later, specifically as a cheap pre-filter layer if posting volume grows large enough that filtering everything through Claude becomes wasteful. Documented reasoning, not dead credits.
- **Email delivery:** Resend API. To: `hardik.lad773@gmail.com`. From: Resend onboarding sender until a custom domain is verified.
- **Scheduling:** GitHub Actions — `Daily job search` + `Illinois CSOD reminder`. Single cron **`0 11 * * *` UTC** (= **6:00 AM CDT** / **5:00 AM CST**). Early morning delivery is acceptable; late morning is worse. GitHub schedule lag can still delay starts. Do **not** use dual CDT/CST crons with a season allowlist — after a cron string changes, GitHub may keep firing the old expression for a while, and an allowlist will skip the only run that fires. `workflow_dispatch` remains for manual runs.
- **Language/runtime:** Python 3. Chosen during v0 scaffolding; keep it simple, no heavy framework.
- **Resume input:** `config/resume_profile.md`, stripped version, not the original PDF.

  Strip: name, email, phone, home address, LinkedIn/GitHub URLs (if not meant to be public).
  Keep: education, skills, work experience, project descriptions, everything relevant to judging fit.

  Reasoning: private repo today doesn't guarantee private history forever — git retains old commits even after a file is deleted or the repo's visibility changes later. Strip by default rather than relying on repo privacy alone.

  Process: paste resume PDF into Cursor, ask it to strip the above fields and output as `config/resume_profile.md`. Manually review the output once before committing — stripping tasks are exactly where a model might miss one line.

### Cost Reference (so this isn't re-derived later)

Roughly 1,500 input tokens plus thinking/output tokens per job at medium effort. Measured Opus 5 spend on a 16-job head-to-head was about **$0.40** (~**$0.025 per job**). Filters keep daily Claude volume in the tens; expanding the company list mainly increases ATS fetch work, not a 1:1 Claude bill.

## 7. V1 Scope

- Company config list (Midwest geography above; Greenhouse/Lever/Ashby/Breezy only; prefer ~10–999 emp)
- Ingestion from each resolved company's ATS API
- Deterministic filtering (title, location, sponsorship, freshness N=3) + URL-based seen dedupe
- One Claude Opus 5 call per new filtered posting for fit + reasoning (**full description**, no prompt truncation)
- Compact one-line-per-match email of strong/maybe results
- GitHub Actions cron aimed at early-morning Central delivery (`0 11 * * *` UTC), fully unattended
- Separate Illinois CSOD within-1-day reminder workflow
- Backend only, no UI
- **Guardrails + evals** per §7a (P0 then P1; locked 2026-08-10)

### 7a. V1 guardrails and evals (locked 2026-08-10 — implemented)

Plain intent: fail closed on bad model output; never permanently hide jobs the model did not reliably score; stop infinite Opus retries on poison URLs; lock filter regressions with tests; then add a freshness-sorted score ceiling, a snapshotted gold eval, and an ingest-empty alarm.

**P0 (ship before claiming production schema/seen guardrails; resume bullet 3 depends on this):**

1. **Fail-closed fit schema.** Malformed JSON or unknown `fit` → explicit `invalid`. API/scoring failures → `error`. `invalid` and `error` share identical handling: not in `NOTIFY_FITS`, not emailed.
2. **Split seen-state.** Stamp `seen` only for jobs that received a real score (`strong` / `maybe` / `no`). Mark `no` after successful score. Mark `strong` / `maybe` only after successful email send. Never mark `invalid` / `error` as ordinary seen on that attempt.
3. **Retry + quarantine.** One in-run Anthropic retry with backoff. Persist quarantine in `data/quarantine.json` (attempt count, last error, URL); gitignore exception + Actions commit-back like `seen_jobs.json`. After **3** failed attempts, quarantine with an explanatory note so the URL stops burning Opus. **P0 acceptance:** observe a real quarantine event (forced or natural), not merge-only.
4. **Filter unit tests.** Fixture-based; seed the four historical bugs: bare `remote` → non-US; `, in` → India false positive; `" il "` strip / substring geo bleed; level-only / recruiter–non-SWE title admits.

**P1 (after P0):**

5. **Survivor ceiling 100**, survivors sorted by `posted_date` descending before the cut. **Token/spend logging included in the same work** (required — not optional/best-effort).
6. **Gold eval set of 12** — store **snapshotted posting JSON** (not live URLs). Severity-weighted pass rule (e.g. ≥10/12 exact; **zero** `no↔strong` flips; include 3–4 boundary cases). Record `model` + `effort` on match output for diffs.
7. **Ingest-health alert:** `ingested == 0` only for this alert’s v1 (same-day). Trailing-average drop detection deferred unless a persisted stats file ships alongside quarantine-style persistence.

**Explicitly deferred:**

- Zero-kept streak alerts (`kept=0` is often a quiet day)
- Wiring `--match-limit` into the daily cron (unsafe until split seen-state lands; weakest guardrail)

## 8. Explicitly Out of Scope for V1

- No frontend/dashboard
- No feedback-based learning loop
- No Fireworks integration
- No Handshake or Wellfound as data sources
- No Comeet / Paylocity / Oracle Cloud / **Workday** clients in v1 (Workday explicitly canned)
- No CSOD full fit-matching (reminder only)
- No Firecrawl / auto-apply automation

## 9. Future Scaling Ideas — Documented, Not Built

Recorded here so they're not lost, and so the code doesn't accidentally make them harder to add later. None of this is being built now.

- **Feedback-based matching improvement.** Track liked/skipped decisions, feed as examples into future matching prompts.
- **Fireworks pre-filter layer.** If daily posting volume grows large, use a cheap Fireworks model to do a first-pass filter before the more expensive Claude judgment call.
- **More ATS platforms.** Workday (canned for v1), SmartRecruiters, etc., if revisited later.
- **Resume-per-role-type matching.** Different resume versions for backend vs. full-stack vs. product roles; agent picks the best-fit version per posting.
- **Notification tiering.** Immediate email for strong matches, weekly digest for maybes.
- **Draft (never auto-send) a tailored outreach note per strong match.** Stays human-approved by design, this should never become an auto-send feature.
- **Lightweight application tracking.** Did I apply, did I hear back, layered on top of existing match data.
- **Tunable freshness window** (v2 default is N=3; was N=7 in early v1).
- **Non-LCA Midwest company discovery** (Built In / other public directories) — LCA is one seed factory, not the full universe.
- **Ingest trailing-average / sharp-drop alert** (beyond `ingested == 0`) if a durable stats file is added later.
- **Zero-kept streak alert** (deferred; quiet days are normal).

## 10. Open Decisions / Next

- Discovery Phase 2 + v2 coverage expansion complete locally: ~**418 resolved** / ~631 unresolved / ~1,049 total. Unresolved = public G/L/A/Breezy board not yet found — opportunistic slug backlog.
- **Next build:** Breezy ingest client (resolved Breezy tokens are skipped today); optional more Built In industry types / unresolved slug fills.
- Email To locked to Gmail (`hardik.lad773@gmail.com`) for Resend; classmate Illinois copy is manual forward for now.

### 10a. V2 coverage expansion (locked 2026-08-11)

**Product goal:** Any Midwest-relevant SWE role on a public Greenhouse/Lever/Ashby/Breezy board should reach the pipeline without manual LinkedIn hunting. LinkedIn is a coverage benchmark only — never a daily ingest source.

**Freshness:** `max_age_days = 3` (72h).

**LCA seed factory (DOL H-1B disclosure Excel under `discovery/`):**
1. Filter **WORKSITE_STATE** ∈ {IL, WI, IN, MI, MO, IA, MN} first.
2. Keep certified-ish cases; SWE-ish SOC (`15-12*`) / title keywords.
3. **Drop `H_1B_DEPENDENT = Y`** (staffing-mill signal).
4. **LLC soft-drop:** drop only if name matches LLC/L.L.C. **and** noise tokens (STAFFING, CONSULTING, SOLUTIONS, SERVICES, TECHNOLOGIES, …).
5. Hard-drop LLP and consultancy / body-shop name patterns.
6. Output: `config/lca_midwest_swe_seed.json` via `scripts/seed_from_lca.py`.

**Explicit:** LCA is help for discovery, not the full Midwest universe. Built In Chicago + adjacent-metro software seeds shipped after the LCA pass.

**Built In Chicago seed (locked 2026-08-11):** Public **Software Companies** directory via `scripts/seed_from_builtin.py` → `config/builtin_chicago_software_seed.json`. Exclude names already in `companies.json` / LCA / midwest seeds, then `discover_ats`. Prefer this over SEC public-company lists for G/L/A/Breezy coverage.

**Built In adjacent metros:** `--adjacent-metros` scrapes Milwaukee / Indianapolis / Detroit software directories → `config/builtin_adjacent_metros_software_seed.json`. Chicago suburb path filters are not usable (no real slice).
