# Candidate Profile (stripped for matching)

PII removed: name, phone, email, LinkedIn/GitHub profile links, and personal location
lines. Project repo URLs omitted because they embed a GitHub username. Review
before committing — confirm nothing identifying remains.

Collated from three new-grad resume variants (general / SWE+AI+FDE / SWE new-grad).
Union of experience, projects, and skills — not a paste of any one PDF.

## Target roles

New-grad and intern Software Engineer, Forward Deployed Engineer (FDE), AI
Engineer, and AI FDE. Not targeting Solutions Engineer, sales engineering, or
senior/staff/principal IC.

## Summary

Software Engineer with 2 years building production systems, with depth in
distributed systems, full stack, and applied AI (RAG, ETL, agentic workflows).
Ships fast, owns problems end to end, and has worked with non-engineering
stakeholders (course staff, business users, accessibility programs).

## Experience

### Graduate Assistant – Digital Accessibility
**School of Information Sciences, UIUC** · August 2025 – May 2026

- Brought 200+ course files to WCAG compliance by auditing and remediating PDF,
  PowerPoint, and Word content for students using screen readers and assistive
  technologies
- Closed accessibility gaps across course materials with a 10-person team,
  recommending remediation strategies and applying inclusive design practices
  through Adobe Acrobat Pro and screen reader testing
- Tracked accessibility issues and remediation progress across 20+ courses,
  reporting findings and measurable usability improvements to program
  stakeholders

### Teaching Assistant – BADM 579 and BADM 550
**Gies College of Business, UIUC** · August 2025 – November 2025

- Improved project submission consistency across 3 cohorts by leading workshops
  on Git, GitHub, and CI/CD fundamentals using GitHub Actions, and on AI
  productivity tools including Cursor and Claude Code
- Reviewed technical project submissions for 100+ students with structured
  feedback on system design, data modeling, and implementation quality

### Software Engineer
**Business Intelligence Group, UIUC** · January 2025 – April 2025

- Cut query resolution time by 70% by building an ETL pipeline loading legal
  agreement PDFs into a ChromaDB vector database, powering an agentic,
  multi-turn RAG chatbot with Dialogflow CX
- Maintained stable response times under concurrent stakeholder testing and cut
  deployment setup time by 60% by containerizing with Docker, configuring
  Kubernetes horizontal pod autoscaling to scale replicas, and deploying on AWS
  (S3, EC2)

### Software Engineer (Senior Executive – IT)
**Piramal Consumer Healthcare** · July 2022 – July 2024

- Cut manual tracking effort by 40% by owning and developing internal web
  applications using React and REST APIs for E-Commerce and Modern Trade claims
  automation
- Reduced artwork and sample order approval time by 5+ days with event-driven
  backend pipelines using Python and Power Automate, integrating escalation
  matrices and webhook-based triggers
- Delivered 3x faster queries by migrating the Retail Outlet Portal from
  SharePoint Lists to cloud MS SQL, resolving dashboard load failures with
  indexing, triggers, and ACID-compliant transaction locking on 150K+ records
- Saved $50K annually and cut daily manual work by 4+ hours by building an
  AI-powered data pipeline automating 250K+ shelf audits using Power Platform
  and Python

## Projects

### RainStorm – Real-Time Distributed Stream Processing Engine

- Processed 100+ events/sec with 0% duplicate output by building a real-time
  distributed stream processing system in Python across a 10-node cluster using
  hash-based partitioning
- Achieved 100% output correctness and automatic crash recovery with exactly-once
  semantics, implemented using Write-Ahead Logging to a Hybrid DFS
- Automated task parallelism adjustment in <5 seconds under high-volume load by
  designing a dynamic autoscaling engine using watermark thresholds

### Research Paper Management System

- Shipped batch CRUD over 100+ papers per query on a full-stack platform using
  React, Node.js, and Express, backed by 25+ REST APIs and AI recommendations
  via Gemini 2.5
- Reduced app-layer bugs and accelerated queries by enforcing data integrity in
  stored procedures while pooling connections; deployed on GCP with OAuth2 and
  TLS

### Job Finder Agent – Agentic Job Matching Pipeline

- Cut LLM spend ~99% by narrowing tens of thousands of ATS postings with
  deterministic title, location, sponsorship, freshness, and URL-dedupe filters,
  reserving one Claude call for fit judgment
- Tightened match precision by benchmarking Claude Opus 5 against Haiku 4.5 on
  identical postings and shipping Opus for stricter level and stack judgment
- Hardened unattended daily GitHub Actions runs (fail-closed fit schema, seen
  state gated on successful email send)

## Education

**University of Illinois Urbana-Champaign** · Urbana-Champaign, IL  
Master of Science, Information Management · August 2024 – May 2026

**University of Mumbai**  
Bachelor of Engineering, Information Technology · August 2018 – May 2022

## Technical Skills

- **Languages:** Python, JavaScript (ES6+), TypeScript, SQL, Bash
- **Frameworks and Databases:** React, Node.js, Express, MySQL, MS SQL,
  ChromaDB (Vector/NoSQL)
- **Cloud and Tools:** AWS, GCP, Docker, Kubernetes, Git, Cursor, Claude Code,
  Linux CLI, Power Platform, Adobe Acrobat Pro
- **Domains:** Distributed Systems, Data Structures, Algorithms, Information
  Retrieval, Microservices, Event-Driven Architecture, ETL, RAG, CI/CD, REST
  APIs, Digital Accessibility (WCAG), Assistive Technology
