# Scoring, apply email, and hub companies

Date: 4 October 2026

This spec replaces the one-line fit email with a short apply note, scores from one master profile, and adds company boards in the four hub cities. It does not add a second model call, and it does not add LinkedIn, Indeed, Handshake, or Workday.

## 1. Purpose

The hub city filter raised the email from about one strong or maybe job a day to about 2.2. Two of nine mornings reached 5. That is not enough, and the notes are too short to apply from. Claude must read the posting, separate required skills from preferred skills, and grade them against this profile. An or-list is one requirement. A job is rejected only when the level or the required skills do not fit. A missing preferred skill can lower strong to maybe. It cannot make a no.

Success:

- Claude still runs once per surviving job, on one master profile.
- The email names New Grad, Full Stack, or AI/FDE, and cites the profile lines that matched. You can apply without opening the job description.
- An or-list counts when the profile has any one of the listed skills. “Java, Python, or C++” is an example of that rule, not a special case.
- A required skill you do not have is a no. Missing preferred skills never produce a no.
- New boards are only companies in the San Francisco Bay Area, Seattle, New York City, or Boston whose public board is Greenhouse, Lever, Ashby, Breezy, SmartRecruiters, Workable, or Recruitee.

Out of scope:

- Three model calls, or pasting three full resumes into the prompt.
- Attaching the PDF to the email. The email names which resume to send.
- LinkedIn, Indeed, Handshake, Wellfound, or Workday.
- Changing freshness from 3 days, or removing the hub location tokens.

## 2. Master profile

`config/resume_profile.md` is the only profile text. `match_jobs` calls `load_resume()`, which reads that file, and the string is placed under `## Candidate profile` in the one API call.

Build it only from these files:

- AI/FDE: `/Users/hardiklad10/Documents/Resume - Resources/AI_FDE_Resumes/AI_FDE_v2/Hardik_Lad_Resume.pdf` (18 September 2026)
- New Grad: `/Users/hardiklad10/Documents/Resume - Resources/New_Grad/New_Grad_Fullstack/Hardik_Lad_Resume.pdf` (18 September 2026)
- Full Stack: `/Users/hardiklad10/Documents/Resume - Resources/Full_Stack/TBD | Kubernetes Docker Project missing/Hardik_SWE_FullStack.pdf` (8 August 2026)

Strip phone, email, LinkedIn, the GitHub profile URL, and street address. Keep project names.

When the 18 September resumes disagree with the 8 August resume on a number, use the 18 September number.

The Business Intelligence Group role comes only from the AI/FDE resume:

- Full-stack RAG chatbot with Next.js, Drizzle ORM, Vercel Postgres, AWS S3, and Docker. Compliance lookup from about 5 minutes to under 30 seconds.
- Time to first byte under 300 ms, with server-sent events and deferred title generation.
- Offline chat history with a service worker, IndexedDB, and React/SWR.

Do not describe that role with the ChromaDB, Dialogflow, or Kubernetes wording from the other two PDFs. Do not add a standalone Kubernetes project.

Java stays as a listed language because the AI/FDE resume lists it. Do not add a Java project bullet. Do not add C++. It is not on these resumes.

Include RainStorm, PaperScope, the Job Finder Agent project, Piramal, the teaching assistant role, and both degrees. Write the Illinois degree as graduated May 2026.

Do not copy the accessibility graduate-assistant role into this profile. It is not on these three PDFs.

Target roles: New Grad software engineer, Full Stack software engineer, AI Engineer, and FDE. Not senior, staff, principal, or solutions engineer. Not an internship that starts after May 2026.

## 3. Scoring

One call. Input is `config/resume_profile.md` and the full job text. Model stays `claude-opus-5-5` at `xhigh`.

The model reads the posting and the profile. It separates required skills from preferred skills. It does not treat an example stack as a special case. “Java, Python, or C++” is only an example of an or-list: if the profile has one of the listed skills, that requirement is met. The same rule applies to any or-list in a posting.

Return only JSON:

```json
{"fit":"strong"|"maybe"|"no","role":"new_grad"|"full_stack"|"ai_fde","reasoning":"<two or three short sentences>"}
```

Rules:

- Read required skills and preferred skills from the posting’s own wording.
- An or-list is one requirement. Any one listed skill that the profile has is enough.
- If a required skill is missing after that rule, fit is no.
- If the level does not fit the target roles, fit is no. That includes senior, staff, principal, lead, and an internship whose term is after May 2026.
- If level and required skills fit, and one or more preferred skills are missing, fit is maybe, not no.
- If level and required skills fit, and no preferred skill is missing, fit is strong. A posting with no preferred list can be strong.
- Reject a job only when it does not fit the profile and the target roles.
- Do not invent experience.

`role` is which resume to send:

- `new_grad` when the title says new grad, new college grad, university grad, early career, associate, or graduate developer.
- `ai_fde` when the title says FDE, forward deployed, or AI engineer, and it is not a new-grad title.
- `full_stack` for other software engineer, backend, frontend, and full-stack titles.

A new-grad AI title stays `new_grad`.

`reasoning` names the profile proof and the skill result in plain sentences. It says which required skill was met and, for a maybe, which preferred skill is missing. It does not use the words leverage, robust, seamless, cutting-edge, delve, or landscape.

Bad JSON, an unknown `fit`, or an unknown `role` is `invalid`. It is never coerced to maybe. The existing quarantine rule stays.

## 4. Email

Strong and maybe only. No email when both counts are zero.

Replace the 120-character one-line reason. Each job is a short block:

- Title, company, location, and the apply link.
- One line: `Send the New Grad resume`, `Send the Full Stack resume`, or `Send the AI/FDE resume`.
- The reasoning from the model, two or three sentences, not trimmed to 120 characters.

Example:

```text
Software Engineer — Asana — San Francisco
Send the Full Stack resume.
The Piramal claims tool was React and REST, and RainStorm is a Python distributed system. The posting’s required Python is covered. Preferred Go is missing, so this is a maybe.
https://example.com/job
```

Subject stays `Job matches: N strong, M maybe`.

## 5. Title leaks that must not reach Claude

Add these title excludes, matched as case-insensitive substrings, same as the current exclude list:

- `sr.`
- `sr `
- `high school`
- `fellowship`

Do not add a blanket `ii` exclude. Software Engineer II was sometimes a maybe.

Tests must drop “Sr. Software Engineer”, “Sr Software Engineer”, and “High School Fellowship, Software Engineering”, and must still keep “Software Engineer II” and “Software Engineer”.

## 6. Hub companies

Add companies. Do not add a new applicant-tracking system.

Discovery uses the existing Built In seed script and the existing ATS probe. City directories to try:

- San Francisco software companies on Built In
- Seattle software companies on Built In
- New York software companies on Built In
- Boston software companies on Built In

If a directory URL does not return company names, skip that city and record the URL. Do not invent a slug.

Then probe Greenhouse, Lever, Ashby, Breezy, SmartRecruiters, Workable, and Recruitee. A company is added only when the probe returns a real board with at least one job. Drop names already in `config/companies.json`. Drop consulting and staffing names with the existing name filter. Drop a slug that belongs to a different company.

Merge the kept boards into `config/companies.json` before the next daily run. Do not auto-merge inside the morning cron.

After the merge is on `main`, the next five scheduled runs are the measure. Record `kept`, strong, and maybe. This spec does not promise 5–8 emails a day.

## 7. Tests

- Parser: valid JSON with `fit` and `role` passes. Missing `role`, unknown `role`, and unknown `fit` are invalid.
- Title excludes in section 5, on the real `config/filters.json`.
- Email text contains the resume line and does not cut the reasoning at 120 characters.
- No live model call in unit tests.

## 8. Docs

Update `PROJECT_BRIEF.md` so the match step names the role and the email cites profile proof. Update `SESSION_LOG.md` with the profile rules, the skill rules, and the hub-company merge. Do not edit older log entries.
