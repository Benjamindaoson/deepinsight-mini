# Mini V2 analytics and monitoring implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver eight unified skills, SQL-backed BI and independent scheduled reporting on the existing Mini PoC.

**Architecture:** Additive semantic views and QuerySpec compiler over the current SQLite store; one tool registry reused by the native single agent and optional MCP adapter; ECharts consumes the same analytical API. Independent APScheduler reuses persisted monitor slots and existing report/outbox services.

**Tech Stack:** Existing Python .venv, FastAPI, SQLite/FTS5/window SQL, Pydantic, Jinja2, local ECharts/HTMX, APScheduler 3, existing SMTP/Apprise and Chromium export.

**Spec:** openspec/changes/mini-v2-analytics-monitoring/specs/mini-v2-delivery/spec.md

## Global constraints
- All changes only D:\deepinsight-mini; Lite read-only.
- No new Agent framework, database or approval path. Existing connected-chat changes retained.
- Approved-only default; source-defined boundaries, time, units and review status remain explicit.
- Real model and external delivery require current configured authorization; no secret in browser or receipts.

## Review focus
- LAG over a missing period or a mixed publisher/definition must not produce a trend.
- Dashboard comparisons must not merge Canary Wharf with Docklands or weighted averages without denominators.
- Raw/source text, tool parameters and MCP calls are untrusted inputs.
- Source revocation or byte tampering must withdraw dependent displays and report conclusions.
- Scheduler restart/overlap and ambiguous delivery outcomes must not repeat sends.

## Tasks
- [ ] 1. Add analytics schema/views, QuerySpec, safe compiler and failing/green SQL regressions.
- [ ] 2. Add registry, eight domain packages and actual executable/schema/permission tests; wire native tools with compatibility retained.
- [ ] 3. Add local ECharts/HTMX BI UI, requested APIs, global filters, evidence drill-down and source-context Ask links; verify browser.
- [ ] 4. Add independent APScheduler worker with persistent slots and actual timed execution/restart evidence.
- [ ] 5. Recheck real sources/provider, obtain lawful eligible evidence, verify real agent/tool and report/PDF/loopback flows; preserve blockers.
- [ ] 6. Run full suite/lint/dependency checks, refresh runbook/acceptance matrix and five-slide business deck from real screenshots.
