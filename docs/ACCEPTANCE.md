# DeepInsight Mini acceptance record

Client date: **19 October 2026**. Timestamps in stored receipts and SQLite are observed UTC; London schedules use Europe/London. This record distinguishes working local software from blocked live AI and unverified business claims.

## Final assessment

| Area | Result | Evidence boundary |
|---|---|---|
| Engineering Readiness | PASS for the tested local PoC | 43 tests; Ruff, compileall and dependency checks; actual browser run |
| Real AI Readiness | BLOCKED | Official DeepSeek actually returned HTTP402, including a fresh retry requested by user |
| Data Reliability | PARTIAL | Seven real endpoints, retained primary evidence, 101 pending observations; no autonomous approval |
| Monitoring Readiness | PASS for controlled execution | Actual Windows scheduled run and persistent slot; repeated live collection with no duplicate new content |
| Report Quality | PASS for rendered outputs | Shared saved object, actual HTML/email/PDF, all PDF pages rendered and inspected |
| Notification Delivery | PASS isolated / external BLOCKED | One real loopback SMTP receipt; repeat deduplicated; no external recipient configured/enabled |
| Business PoC Readiness | PARTIAL | Chat/dashboard/report/monitor work locally, but successful live AI/tool calling and complete submarket coverage remain missing |

The latest machine-readable state, run IDs, provider failure, source URLs, artifact sizes and SHA-256 hashes are in `output/evidence/FINAL_RECEIPT.json`.

## G0 · Environment and model connectivity

**Implemented:** Independent Windows project and `.venv`; FastAPI/SQLite and bounded native SDK tool loop; environment-only model key. Project remains isolated from Lite.

**Source Files:** `requirements.txt`, `requirements.lock`, `pyproject.toml`, `app/config.py`, `app/agent.py`.

**Commands Executed:** `python -m venv .venv`; project-local dependency install; `python tools/model_preflight.py`; `python -m deepinsight model-check`.

**Test Results:** Python 3.12 environment works. Actual official API HTTP402; no model output/tool call is declared successful.

**Evidence:** `output/evidence/G0-model-smoke.json`; SQLite `model_calls`, cached `model_block`.

**Known Limitations:** Provider quota/usable official credential is externally blocked. No authorized fallback provider was used.

**Next Priority:** Restore official quota, run model-check, then repeat actual agent/browser questions.

## G1 · Real sources

**Implemented:** HTML/RSS collectors and official JSON series; robots check, bounded HTTPS, raw hashes, article publication dates and document versions. Savills, City of London, BoE and ONS are four independent publishers across seven endpoints.

**Source Files:** `config/sources.yaml`, `app/skills/source_reader.py`, `app/skills/market_data.py`.

**Commands Executed:** Multiple actual `python -m deepinsight monitor --run once` runs; `tools.backfill_metrics`, metadata/scope validation.

**Test Results:** Seven endpoints healthy in latest collection; repeated live check found zero new versions/events. Original evidence yields 101 pending observations and 21 dashboard series.

**Evidence:** SQLite `sources`, `documents`, `document_states`, `document_revisions`, `observations`, `audit_log`; `data/documents/`; `output/expanded-sources.log`.

**Known Limitations:** Small source registry; missing dedicated Canary Wharf/Midtown series and direct hybrid-working evidence. Source-reported values are not approved conclusions. One article-date parser error was corrected using its explicit original `<time>` element; out-of-scope RSS items were quarantined without deleting history.

**Next Priority:** Add verified submarket sources and review period/unit definitions.

## G2 · Monitoring and evidence gates

**Implemented:** Process lock, persistent checks, canonical/body/event identities, version restorations, deterministic compatible comparisons, pending/approved/retracted states and dependency invalidation.

**Source Files:** `app/database.py`, `app/skills/monitor.py`, `app/skills/compare.py` and regression tests.

**Commands Executed:** Full pytest suite, actual repeated collection and controlled scheduled collection.

**Test Results:** Baseline/repeat/update, percentage-point vs relative percent, mismatched periods/definitions/units, signal retraction, prior-period supersession and A→B→A restoration tested. Synthetic cases are TEST ONLY. A genuinely newly published market event arriving between two acceptance checks was not observed and is not claimed.

**Evidence:** `tests/test_core.py`, `test_monitor.py`, `test_review_regressions.py`, `test_security_and_monitoring.py`; SQLite monitor and signal history.

**Known Limitations:** Rule-based event/entity deduplication is conservative and is not a semantic event-resolution benchmark. There are zero approved market signals in the current dataset.

**Next Priority:** Human review of candidate metrics and live observation of future new events.

## G3 · Agent

**Implemented:** Single SDK agent with six allowlisted tools, persisted conversations, bounded rounds/time/request/token budgets, exact source checks, numeric observation binding, and safe blocked state. Free model summaries/limitations cannot bypass display gates.

**Source Files:** `app/agent.py`; six modules under `app/skills/`.

**Commands Executed:** Unit tests, actual model-check and browser questions.

**Test Results:** Engineering gates pass. Actual provider returned HTTP402. Six browser questions each have status BLOCKED and zero actual model skill calls.

**Evidence:** `output/evidence/browser/acceptance.json`, `agent_runs`, `conversations`, `model_calls`.

**Known Limitations:** Live tool calling, multi-step model quality and semantic answer correctness remain unverified.

**Next Priority:** Repeat live acceptance after quota is restored.

## G4 · Reports and visualization

**Implemented:** One report object for web/email/PDF, source links, observation-period separation, fact/interpretation labels, print layout, historical validity warnings and approved-only quantitative report charts. Dashboard shows three source-reported ONS history charts separately, as requested by the user; each plotted value must match retained JSON evidence.

**Source Files:** `app/skills/report.py`, `app/templates/briefing.html`, `email.html`, `app/dashboard.py`, static assets.

**Commands Executed:** `python -m deepinsight report --pdf`; real browser PDF download; PyMuPDF rendering and visual inspection of every page.

**Test Results:** Actual professional briefing and PDF generated. No fabricated market history, source-reported raw API plots are labeled pending review, and no market numeric chart enters the formal briefing without approval.

**Evidence:** `output/reports/`, `output/evidence/browser/pdf-page-*.png`, `output/screenshots/official-api-charts.png`.

**Known Limitations:** No approved quantitative market trend exists yet. Native desktop PowerPoint is not a PDF-report test.

**Next Priority:** Review comparable market observations before formal trend publication.

## G5 · Scheduling and notifications

**Implemented:** Installed Windows task, persistent London slots with DST, Linux systemd examples; SMTP/Telegram/Apprise adapters, local capture, destination/transport-bound per-channel test gates, deduplication and bounded safe retry states.

**Source Files:** `app/services/`, `deepinsight/__main__.py`, `deployment/`, `tools/smtp_acceptance.py`.

**Commands Executed:** `Install-Schedule.ps1 -TunnelDns`, `Start-ScheduledTask`, `Get-ScheduledTaskInfo`; actual independent scheduled monitor; loopback SMTP acceptance.

**Test Results:** Controlled morning run `838a1f352ab947e4a788094b1967a4fc` succeeded and generated report `f5802561f63e4375bef7cdb908538b49`. London defaults restored to 08:00/18:00. Loopback SMTP received exactly one actual MIME email; repeat was deduplicated. External delivery mode is disabled.

**Evidence:** `schedule_slots`, `monitor_runs`, `notifications`; `output/logs/scheduler.log`; `output/evidence/smtp/receipt.json`.

**Known Limitations:** No real external mailbox/Telegram recipient delivery; no multi-day unattended uptime or VPS execution claim. A missed/crashed slot requires explicit operator recovery.

**Next Priority:** Authorized destination setup and per-channel external tests, then observe routine scheduled delivery.

## G6 · User-facing product

**Implemented:** User steering applied: Ask AI is first/default and GPT-like; Overview second, with actual reported metrics, 21 summary series, 3 raw ONS charts, source links, periods and all 8 assessment topic questions. Sources, monitor, reports and settings persist.

**Source Files:** `app/main.py`, `app/dashboard.py`, templates, `app/static/app.js`, `chat-dashboard.css`.

**Commands Executed:** Actual local Uvicorn start and Playwright browser acceptance.

**Test Results:** Twelve browser workflow checks passed; zero page errors. Six required questions and a follow-up were actually submitted and saved; their live AI result remains BLOCKED. Desktop and mobile containment passed.

**Evidence:** `output/evidence/browser/acceptance.json`, `output/screenshots/ask-ai-gpt.png`, `overview-viewport.png`, `official-api-charts.png`.

**Known Limitations:** Server-managed model credentials/ID; dedicated submarket data gaps; live AI blocked. Source-reported dashboard values do not equal approved quantitative conclusions.

**Next Priority:** Successful real model research once the official provider permits it.

## G7 · Delivery

**Implemented:** Runnable Python, protected UI, report outputs, scheduling, isolated notification proof, README/RUNBOOK, OpenSpec changes and five-slide business PPTX with actual screenshots and explicit limits.

**Source Files:** `tools/build_business_deck.mjs`, docs and all application/deployment modules.

**Commands Executed:** Full tests/lint/compile/dependency checks, two OpenSpec validations, browser acceptance, Artifact Tool export/finalizer/import and per-slide visual review.

**Test Results:** 43 tests passed with one upstream deprecation warning; Ruff, compileall, pip check and specs passed. Five-slide PPTX package/layout/import checks passed. No fabricated ROI or successful AI claim.

**Evidence:** `output/slides/London_Office_Intelligence_Business_Demo_v2.pptx`, slide PNGs, finalizer validation JSON, final receipt and browser evidence.

**Known Limitations:** Overall business PoC remains PARTIAL because live AI is blocked and data/external delivery coverage is incomplete. Initial independent code review found five issues that were reproduced, fixed and regression-tested; a second independent review attempt hit a reviewer usage limit, so no second-review pass is claimed.

**Next Priority:** Official-model completion and a narrowly scoped final business demonstration.
