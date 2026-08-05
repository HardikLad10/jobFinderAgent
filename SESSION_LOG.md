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
