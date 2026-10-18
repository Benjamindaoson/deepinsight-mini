## Context
Greenfield Windows directory with Python 3.12, Node, OpenSpec and CodeGraph. User supplied the complete design and requested immediate implementation. Preserve it verbatim in docs/USER_REQUEST.txt. Target nontechnical asset managers, English product copy.

## Goals / Non-Goals
**Goals:** Persistent source monitoring, traceable evidence, bounded single-agent research, professional shared HTML/email/PDF, London-time independent scheduling, protected settings, actual browser evidence, five business slides.
**Non-Goals:** Enterprise tenancy, autonomous investment advice, proxying paywalls, fake positive experimental results, running any Lite component, vector infrastructure or agent frameworks.

## Decisions
- SQLite WAL, FTS5, unique document URL/hash identities, append-only evidence versions; a process file lock prevents overlapping monitors. Failed runs remain recorded. Source health accompanies all answers/reports.
- Public allowlisted source registry, HTTPS and public DNS checks, robots policy, bounded redirects and streamed size limits. Retain local raw bytes for audited public material only; no republication of full third-party articles.
- Numeric extraction is narrow and evidence-linked. All extracted market observations start PENDING_REVIEW. Explicit CLI human review with reviewer/reason is the only approval path; model tools cannot approve or alter past records.
- Comparison keys include publisher, metric, definition, geography, unit and period type. Revisions within the same period are not trends. No graph without two approved comparable periods.
- Model credentials come only from environment; existing official LLM_* configuration used first. Requests and maximum token reservations are transactional, bounded by daily budget. Only supplied evidence IDs/quotes can support validated claims; interpretation is labeled and never upgrades review status.
- Report generation is deterministic when no meaningful new evidence requires AI. AI failure does not lose monitor output. One report object feeds web/email/PDF.
- UI binds localhost, same-origin write protection and signed local sessions. Remote mode requires an admin token. Settings never return secret values. External delivery is opt-in after explicit test; isolated spool test does not establish external delivery.
- Windows task polls a shared London-time scheduler every minute (DST handled in Python). Linux timer uses the same entry point. Durable slot claims prevent repeat runs; scheduler state is distinct from web health.
- Palette #14263D / #16A6A0 / #F5F7FA / #263445 / white / #D97757. Segoe UI body and Georgia report headings. Left-aligned briefing with evidence status as the strongest visual cue, quiet navigation, mobile stacking.

## Risks / Trade-offs
- Missing credentials/quota -> BLOCKED actual AI acceptance, continue independent development.
- No approved numeric history -> honest unavailable cards and no trend graphs.
- Website terms/robots/blocking -> retain fetch errors, skip disallowed targets and use lawful alternatives.
- New live events may not occur during acceptance -> controlled fixtures TEST ONLY, do not claim live novel-event proof.
- Model grounded-output checks are structural, not a semantic certification -> retain explicit AI interpretation boundary and source links.

## Migration Plan
New isolated .venv and database. No existing dataset migration. Backup database plus documents/config/reports, restore into stopped instance. No public deployment without HTTPS/authentication.

## Open Questions
External recipients and transport credentials must be explicitly configured by the user. No external sends during development.
