## Context

Baseline: 45 passing tests, SQLite relational observations and FTS5, native SDK agent with six function tools, source-backed Jinja pages, evidence-first HTML/PDF, SMTP outbox and durable London-time monitor slots. The parallel connected-chat change owns attachment/provider configuration and chat appearance. This phase adds analytics and BI through focused modules rather than replacing that work.

## Goals / Non-Goals

Goals: eight executable domain packages sharing a registry and ToolResult; server-compiled QuerySpec SQL; verified compatibility and missing-period behavior; global dashboard filters; evidence-linked ECharts; independent APScheduler; actual local execution evidence. Preserve source terms, pending states, current monitor/report implementations and Lite isolation.

Non-Goals: a second agent, unrestricted SQL, distributed infrastructure, automatic approval, fabricated history, automatic external delivery or a claim that a transport receipt proves human receipt.

## Decisions

- Additive SQL migration creates dimension tables, audit links and views over authoritative existing observations/documents. Source-bound series keys include publisher/definition/unit/geography/frequency. Window SQL computes changes; consecutive-period checks prevent LAG from bridging gaps. No aggregate vacancy without denominator evidence.
- QuerySpec and whitelisted metrics/operations compile parameter-bound SQL. A read-only SQLite URI, query-only pragma, execution deadline and row caps protect the tool interface.
- One registry exposes eight domain skills. Read operations reuse current services; explicit permission flags gate collect, monitor, report creation and notifications. Model tools cannot review/approve observations. MCP adapter uses the identical schema/dispatcher and is tested locally before being described as available.
- A new BI API and template use local Apache ECharts SVG rendering. Approved is the default. Candidate inspection is explicit and marked; comparison/ranking requires approved matched series. Native tables and evidence links remain available for keyboard users and printing.
- APScheduler runs only in a separate worker. It calls the existing durable slot claim and monitor pipeline; current OS timer compatibility remains supported, with one worker authority and a process lock.
- PDF/email continue to use the shared existing report. Additional analytical report fields are deterministic or cite retrieved approved observations. Existing final-answer evidence checks remain mandatory.

## Risks / Trade-offs

- Pending production observations → empty confirmed charts with a visible coverage matrix and optional clearly labelled inspection mode; no silent promotion.
- Concurrent chat changes → own analytics modules/assets; keep integration small and preserve other changes; rerun the combined suite.
- Model credential/402 → one bounded real connectivity check using the configured provider; no fallback destination without current authorization.
- Calendar/DST/restart → Europe/London CronTrigger plus persisted date/type slots and single instance, explicit recovery tests.
- Source revisions/hash failures → validate retained original bytes and current evidence before analytics; revoke dependent output at read time.

## Migration Plan

Online SQLite backup before schema changes; additive idempotent migrations, never delete originals or review history. New routes coexist with compatibility APIs. Disable V2 route registration to roll back UI exposure while retaining audit tables. Acceptance writes use separate output/evidence/v2 paths.

## Open Questions

Live provider usability and independent regional coverage remain empirical acceptance results. External recipients remain unconfigured and disabled.
