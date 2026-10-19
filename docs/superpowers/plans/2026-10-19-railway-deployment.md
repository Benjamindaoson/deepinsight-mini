# Railway Emergency Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the actual Mini application through one Railway Free service and verify it on HTTPS.
**Architecture:** One small Docker image, one ASGI process and one independent supervised APScheduler process with existing durable locks/slots. A single `/persist` volume holds data and output. Linux credentials use Fernet authenticated encryption with an environment-only master key; Windows stays on DPAPI.
**Tech Stack:** Existing Python/FastAPI/SQLite/Skills/ECharts plus cryptography; official Railway CLI local-source upload. Chromium is not installed or launched for normal operation; PDF work remains paused.
**Spec:** openspec/changes/railway-deployment/specs/railway-runtime/spec.md

## Global Constraints
- Root is D:\deepinsight-mini; never deploy Lite or Radar. Existing uncommitted improvements are preserved in a working-source backup.
- No plan upgrades or domain purchases. External notifications remain off without recipients and authorization.
- Keep CSRF, trusted hosts, authenticated public operations, evidence approval and daily model budgets.
- Secrets use secure Railway variables; no plaintext secret in source, archive, logs or public receipts.
- Seed contains only retained public original evidence and a bounded saved briefing, with paths rewritten for the volume; no private chats/uploads/keys/session secret.

## Review Focus
- Lost environment encryption key must fail closed and never silently reinitialize an existing vault.
- Volume initialization must not overwrite established database/report state on restart.
- Scheduler child failure must be recorded/restarted with one worker and existing slot deduplication.
- Railway HTTPS/proxy host and Origin checks must stay usable and fail closed for hostile hosts.
- A seed's source hashes, report dependencies and private-data exclusions must survive migration.

### Task 1: Linux runtime
- [ ] Add failing Linux secret roundtrip/wrong-key, seed idempotence and resource tests.
- [ ] Implement portable secret backend, workspace bootstrap, bounded concurrency and supervisor; run targeted tests.
- [ ] Build/start Linux runtime locally if available; otherwise preserve explicit untested boundary and validate actual Railway runtime.

### Task 2: Actual deployment
- [ ] Authenticate CLI, inspect account plan and dedicated project selection.
- [ ] Generate bounded public seed, ignore rules, Dockerfile and railway config; scan actual upload for secrets.
- [ ] Create service and volume, set real secure env values without displaying, deploy and create Railway domain.

### Task 3: Cloud acceptance
- [ ] Exercise all requested HTTPS/browser/model/source/report/schedule/fault scenarios; record real versus controlled tests.
- [ ] Restart and check persistent identities, memory and disk; fix issues before final verdict.
- [ ] Independent review, tests and exact Git/source identity; deliver URL and factual verdict.

## Ledger
Backup: output/backups/railway-20261019-084121 contains working source and consistent database.
Ruling: User explicitly authorizes actual deployment and native execution; no extra deployment approval round. No spending beyond the existing Free account is authorized.
