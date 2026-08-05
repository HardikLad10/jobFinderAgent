# Job Search Agent — Project Brief

**Status:** Core pipeline working (ingest → filter → match). Email delivery and GitHub Actions cron still open. Day-to-day progress in `SESSION_LOG.md`.
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
- **Future scope is designed for, not built.** Code should be structured so features listed in Section 6 could be added without a rewrite. That does not mean building them now.

---

## 2. Problem Statement

Finding job postings isn't hard. Finding postings that are actually new and actually relevant is. Aggregators like Jobright surface postings that are already a day or more old, presented as fresh. There's no reliable way to see new-grad SWE postings the moment they go live, filtered to fit, without manually checking multiple sites daily.

## 3. Why This Is an Agent, Not Just Prompting Claude Directly

Manually pasting a job posting into Claude and asking "does this fit me" works, but it requires a human to find the posting, copy it, and ask, every single time. That's not automation, that's a human doing 90% of the work and Claude doing the last 10%.

An agent means the fetching, filtering, and deduping are automated and unattended. Claude is invoked only for the one step that needs real judgment: does this specific posting fit this specific profile. The value isn't "smarter AI," it's removing the manual checking.

**Note on "learning":** this project does not involve the model updating its own weights (that's fine-tuning/RL, a different and heavier thing, out of scope). "Learning" here, if built later, means storing feedback on past matches and feeding examples back into future prompts. Real, but it's adaptation through context, not model training. Don't conflate the two.

## 4. Platform Constraints — Decided, Don't Revisit Without New Information

- **Handshake: do not scrape.** Handshake's Terms of Service explicitly prohibit bulk collection via automated scripts, and API access is restricted to official university Career Services partners, not individual students. An autonomous agent hitting Handshake risks the account, which is tied to university identity. Decision: excluded from this project entirely.
- **Wellfound: do not scrape.** Public listings are viewable without login, but the platform runs active anti-bot defenses (rate limiting, JS challenges, CAPTCHAs on repeated automated requests). Building against that is a maintenance burden, not a clean data source. Decision: excluded from v1.
- **Chosen approach: pull directly from company ATS platforms.** Greenhouse, Lever, and Ashby all expose public, structured, unauthenticated JSON job APIs. This is also a better technical answer to the original problem: pulling from the source of truth is inherently fresher than any aggregator, and there's no ToS conflict.

## 5. Architecture

Deterministic pipeline with exactly one agentic step.

1. **Company list (manual, deterministic).** Curated list of companies, Chicago-area or Chicago-office startups, posting on Greenhouse/Lever/Ashby. Lives in a config file, grows over time.
2. **Ingestion (deterministic).** Poll each company's public ATS API on a schedule. Normalize into one schema: title, company, location, posted date, URL, description (full body text required by the sponsorship filter below).
3. **Filtering (deterministic, no LLM).** Keyword match on title, location filter for Chicago/Illinois, sponsorship exclusion (below), dedupe against a "seen jobs" store.

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

   Dependency: requires full job description body text, not just title/location. Check `data/latest_ingestion.json` first — if description content isn't already captured, the ingestion step needs a `content=true` param (Greenhouse) or a per-job detail fetch before this filter can run. Verify before building.

4. **Matching (the one agentic step).** For each new, filtered posting, one Claude call compares it against the resume/profile and returns a fit verdict plus short reasoning.
5. **Delivery (deterministic).** Summary of matches sent to personal email at end of run.
6. **Scheduling (deterministic, infrastructure).** GitHub Actions cron job triggers the full pipeline. No human intervention required. Code and run history live in the GitHub repo, satisfying the "should be on GitHub" requirement in the same step as scheduling.

## 6. Tech Stack — Locked Decisions

- **Matching model:** Claude Haiku 4.5, via Anthropic Console API key (personal account, $500 credit). Chosen because this is a classification/judgment task, not creative generation, and Haiku is the cost/speed-appropriate tier for that. Current pricing: $1 input / $5 output per million tokens.
- **Fireworks AI ($500 credit):** not used in v1. Reserved for later, specifically as a cheap pre-filter layer if posting volume grows large enough that filtering everything through Claude becomes wasteful. Documented reasoning, not dead credits.
- **Scheduling:** GitHub Actions (cron trigger, free tier).
- **Email delivery:** simple email API or SMTP from within the scheduled script.
- **Language/runtime:** Python 3. Chosen during v0 scaffolding; keep it simple, no heavy framework.
- **Resume input:** `config/resume_profile.md`, stripped version, not the original PDF.

  Strip: name, email, phone, home address, LinkedIn/GitHub URLs (if not meant to be public).
  Keep: education, skills, work experience, project descriptions, everything relevant to judging fit.

  Reasoning: private repo today doesn't guarantee private history forever — git retains old commits even after a file is deleted or the repo's visibility changes later. Strip by default rather than relying on repo privacy alone.

  Process: paste resume PDF into Cursor, ask it to strip the above fields and output as `config/resume_profile.md`. Manually review the output once before committing — stripping tasks are exactly where a model might miss one line.

### Cost Reference (so this isn't re-derived later)

Roughly 1,500 input tokens + 150 output tokens per job evaluated. At Haiku 4.5 rates, that's about **$0.0025 per job checked**. Even at 300 postings/month, that's under $1/month. Cost is a non-issue at this project's scale, don't spend time optimizing it in v1.

## 7. V1 Scope

- Company config list (Chicago-area, Greenhouse/Lever/Ashby only)
- Ingestion from each company's ATS API
- Deterministic filtering + dedupe
- One Claude Haiku call per new posting for fit + reasoning
- Email summary of results
- GitHub Actions cron trigger, fully unattended
- Backend only, no UI

## 8. Explicitly Out of Scope for V1

- No frontend/dashboard
- No feedback-based learning loop
- No Fireworks integration
- No Handshake or Wellfound as data sources

## 9. Future Scaling Ideas — Documented, Not Built

Recorded here so they're not lost, and so the code doesn't accidentally make them harder to add later. None of this is being built now.

- **Feedback-based matching improvement.** Track liked/skipped decisions, feed as examples into future matching prompts.
- **Fireworks pre-filter layer.** If daily posting volume grows large, use a cheap Fireworks model to do a first-pass filter before the more expensive Claude judgment call.
- **More ATS platforms.** Workday, SmartRecruiters, etc., if target companies use them.
- **Resume-per-role-type matching.** Different resume versions for backend vs. full-stack vs. product roles; agent picks the best-fit version per posting.
- **Notification tiering.** Immediate email for strong matches, weekly digest for maybes.
- **Draft (never auto-send) a tailored outreach note per strong match.** Stays human-approved by design, this should never become an auto-send feature.
- **Lightweight application tracking.** Did I apply, did I hear back, layered on top of existing match data.

## 10. Open Decisions

- Exact email delivery method (API vs SMTP) not yet chosen.
- ATS board tokens still unresolved for 28 of 50 companies (notes in `config/companies.json`).
- Title/location keyword tuning in `config/filters.json` after more real runs.
