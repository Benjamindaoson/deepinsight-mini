# London Office Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Deliver a running, evidence-constrained London office monitoring PoC with interactive AI and five business slides.
**Architecture:** One Python application, shared six skills, SQLite and filesystem evidence. Independent CLI scheduling uses the same monitor entry point as the UI. Facts require approval before quantitative publication.
**Tech Stack:** Python 3.12, FastAPI, Jinja2, SQLite FTS5, httpx, Trafilatura, feedparser, PyMuPDF, OpenAI compatible SDK, Playwright, Matplotlib.
**Spec:** openspec/changes/london-office-intelligence/ plus docs/USER_REQUEST.txt (verbatim supplied request).

## Global Constraints
No writes to Lite. No invented market data. No mock AI represented as real. Europe/London 08:00/18:00. External sends disabled until configured, tested and explicitly enabled. Secrets remain in environment. Independent .venv.

## Review Focus
- Failed collectors must yield partial coverage, never a claim of no market changes.
- Same-period revisions and mismatched periods/units/definitions must not become trend signals.
- Retracted or stale evidence must invalidate active signals and current report claims.
- Untrusted document instructions and arbitrary URLs cannot gain execution or network authority.
- Model budgets, concurrency locks and notification retries must remain effective across processes.

### Task 1: G0 environment and configuration
**Files:** requirements.txt, pyproject.toml, app/config.py, app/database.py, tests/test_core.py.
**Interfaces:** Settings.from_env(), Store(path), smoke(store).
- [ ] Write behavioral tests for fresh SQLite persistence, comparison, canonical URLs and review gates; observe failures.
- [ ] Implement isolated setup, schema and environment-only credentials; run real model smoke and save redacted receipt.

### Task 2: G1–G2 collectors and monitor
**Files:** config/sources.yaml, app/skills/{source_reader,market_data,compare,monitor,research}.py, tests/test_monitor.py.
**Interfaces:** read_source(source), run_monitor(store, trigger), compare(old,new), research(store,query).
- [ ] Test idempotent baseline, changed documents, failure coverage, incompatible observations and signal retraction.
- [ ] Implement bounded public-source fetch, robots checks, raw hashes, versioned documents, FTS5, pending metric extraction, deterministic comparison and transactional run lock.
- [ ] Execute two live collections and preserve source receipts. Real new-event timing remains observational.

### Task 3: G3 bounded AI
**Files:** app/agent.py, tests/test_agent.py.
**Interfaces:** ask(store, question, conversation_id), six allowlisted tools.
- [ ] Test budget exhaustion, unknown tool rejection, citation verification and evidence-poor answers.
- [ ] Implement native tool calling, persisted conversations, token/request reservations, tool/output validation and real model execution.

### Task 4: G4–G5 report and delivery
**Files:** app/skills/report.py, app/services/{notifications,scheduler}.py, deepinsight/__main__.py, deployment/.
**Interfaces:** make_report(store,run_id), export_pdf(report_id), dispatch(report_id), tick(now).
- [ ] Test shared report serialization, approval-only charts, notification idempotency, retries, DST and persisted schedule slots.
- [ ] Implement HTML/email/PDF, independent scheduler CLI and isolated local notification capture.
- [ ] Observe a controlled scheduled run and render/inspect every PDF page.

### Task 5: G6–G7 web and business delivery
**Files:** app/main.py, app/templates/, app/static/, tools/browser_acceptance.py, README.md, RUNBOOK.md, output/slides/.
**Interfaces:** five UI pages; authenticated same-origin writes; persistent job progress; report/source downloads.
- [ ] Test access control, settings validation and rendered main flows.
- [ ] Implement business UI; run real browser six questions, follow-up, monitoring, PDF, settings and reopen persistence.
- [ ] Review branch, repair failures, create five PPTX slides with actual screenshot and honest limits; record stage matrix and hashes.

## Execution rulings
- User explicitly requested immediate execution with a complete written design; proceed inline without an additional design approval gate.
- No global gstack command discovered; use direct pytest, Ruff, browser QA and independent review.
- Credential routing uses existing LLM_* official DeepSeek endpoint first; do not infer provider identity from variable names alone.
