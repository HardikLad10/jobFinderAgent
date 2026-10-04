# Candidate profile

Sent to Claude on every fit call. Phone, email, LinkedIn, and the GitHub profile URL are omitted. Built from the AI/FDE resume (18 September 2026), the New Grad resume (18 September 2026), and the Full Stack resume (8 August 2026). The Business Intelligence Group role is taken only from the AI/FDE resume.

## Target roles

New-grad and early-career Software Engineer, Full Stack Software Engineer, AI Engineer, and Forward Deployed Engineer (FDE). Not targeting Solutions Engineer, sales engineering, or senior, staff, or principal IC roles. Not targeting internships that start after May 2026.

## Education

**University of Illinois Urbana-Champaign** — Master of Science, Information Management. Graduated May 2026. GPA 3.84/4.00. Coursework: Distributed Systems (CS 425), Database Systems (CS 411).

**University of Mumbai** — Bachelor of Engineering, Information Technology. May 2022. GPA 3.86/4.00. Coursework: Data Structures and Algorithms, Object-Oriented Design, Operating Systems, Computer Networks.

## Experience

### Software Engineer (Senior Executive, IT)

**Piramal Consumer Healthcare, Mumbai** · July 2022 – July 2024

- Cut manual tracking effort by 40% by owning internal web applications in React and REST APIs for e-commerce and modern-trade claims.
- Reduced artwork and sample-order approval time by 5+ days with event-driven backend pipelines in Python and Power Automate, including escalation and webhooks.
- Made queries 3x faster by moving the Retail Outlet Portal from SharePoint Lists to cloud MS SQL, fixing dashboard load failures with indexing, triggers, and transaction locking on 150K+ records.
- Saved $50K a year and cut daily manual work by 4+ hours by building a Python and Power Platform pipeline that automated 250K+ shelf audits.

### Teaching Assistant – BADM 579 and BADM 550

**Gies College of Business, UIUC** · August 2025 – November 2025

- Led workshops for 3 cohorts on Git, GitHub, GitHub Actions CI/CD, Cursor, and Claude Code.
- Reviewed technical project submissions for 100+ students, with feedback on system design, data modeling, and implementation.

### Software Engineer (Technical Consultant)

**Business Intelligence Group, UIUC** · January 2025 – April 2025

This role is taken from the AI/FDE resume.

- Cut aviation staff compliance lookup from about 5 minutes to under 30 seconds by building a full-stack RAG chatbot with Next.js, Drizzle ORM, Vercel Postgres, AWS S3, and Docker.
- Held time to first byte under 300 ms with server-sent events, UI updates throttled to 10 per second, and deferred title generation and message persistence.
- Cached chat history for low-connectivity use with a service worker, IndexedDB, and React/SWR.

## Projects

### RainStorm

Real-time distributed stream processing engine in Python.

- Processed 100+ events/sec with 0% duplicate output on a 10-node cluster using hash partitioning.
- Exactly-once delivery and crash recovery with a write-ahead log to a hybrid distributed file system.
- Autoscaling adjusted task parallelism in under 5 seconds using watermark thresholds.

### Research Paper Management System (PaperScope)

- Full-stack app with React, Node.js, and Express, 25+ REST APIs, and batch CRUD over 100+ papers per query.
- AI recommendations via Gemini 2.5. Data integrity through stored procedures. Connection pooling. Deployed on GCP with OAuth2 and TLS.

### Job Finder Agent

Daily pipeline that polls public Greenhouse, Lever, and Ashby boards, filters by title, location, sponsorship, and freshness, then makes one model call per surviving posting.

- On an early measured run, about 15K postings were narrowed to under 40 before the model call.
- Compared Claude Opus 5 with Haiku 4.5 on 16 identical postings: 12 agreed, 4 flipped more conservative, about $0.025 per job.
- Runs on a GitHub Actions cron. Invalid model scores are not treated as matches.

## Skills

Languages: Python, JavaScript, TypeScript, HTML, CSS, Java, SQL, Bash.

Frameworks and data stores: React, Node.js, Next.js, Express, MySQL, MS SQL, PostgreSQL, Drizzle ORM.

Cloud and tools: AWS, GCP, Docker, Git, GitHub Actions, Cursor, Claude Code, Linux, Power Platform.

Foundations and domains: data structures, algorithms, object-oriented design, operating systems, distributed systems, REST APIs, event-driven systems, ETL, RAG, information retrieval, CI/CD.

Java is a listed language from the AI/FDE resume. There is no Java project bullet.
