# Connected Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modify the real website to provide readable GPT-style chat, attachments, selectable models/thinking and safe personal API credentials.
**Architecture:** Preserve FastAPI/Jinja/SQLite and the six-skill bounded agent. Add a DPAPI encrypted provider vault and owner-bound attachment store outside SQLite; explicit runtime configuration is carried into background jobs. Use approved HTTPS hosts api.deepseek.com and toapis.cn, verified TLS, no redirects or automatic provider fallback.
**Tech Stack:** Existing Python .venv, OpenAI SDK/httpx, PyMuPDF, stdlib ZIP/XML and native browser controls.
**Spec:** openspec/changes/connected-chat/specs/connected-chat/spec.md

## Global Constraints
- User authorizes direct production edits, native execution and real requests using supplied keys. Earlier official-only restriction is superseded.
- Do not expose keys in logs, source, receipts, SQLite or localStorage; persisted personal secrets use Windows DPAPI and owner isolation.
- Keep daily global budgets, verified sources, exact quotes, approved-only quantitative conclusions, CSRF/auth/host and external-notification gates.
- Files max 8 MiB, five per question, extracted text max 24,000 chars, PDF max 30 pages; images max 12 million pixels. Unsupported uploads fail explicitly.
- Current app is a shared research workspace with personal credential/upload isolation, not a multi-tenant market-data platform.

## Review Focus
- Cross-browser profile/upload IDs cannot expose another person's credentials or attachments.
- Endpoint tampering, redirects and invalid key input must not leak credentials.
- Model switches and unsupported thinking must not silently fall back; job config must be immutable.
- PDF/DOCX bombs, binary text and oversized files must fail without entering the agent.
- Failed provider calls, invalid model JSON and uploaded prompt injection must not bypass existing evidence gates.

### Task 1: Provider profiles and request adapter
Files: app/providers.py, app/config.py, app/main.py, tests/test_connected_chat.py.
Interfaces: ProviderVault(root).save(owner, input), .public(owner), .resolve(owner,id); runtime_scope(config) carries the immutable selected configuration. Connection check and catalog use bounded httpx requests.
- [ ] Write failing owner isolation, encrypted-at-rest, HTTPS allowlist and parameter mapping tests; run pytest and observe missing behavior.
- [ ] Implement vault + sanitized profile/catalog/check APIs; test replacement retains no plaintext and budget failures are explicit.
- [ ] Run targeted tests, then commit implementation.

### Task 2: Attachments and agent integration
Files: app/attachments.py, app/agent.py, app/main.py; tests/test_connected_chat.py.
Interfaces: AttachmentStore(root).add(owner,name,bytes), .context(owner,ids) returns bounded untrusted text/image parts. ask(..., attachments=None) persists provenance and passes content through completion.
- [ ] Write failing type/size/ownership and actual outgoing request content tests.
- [ ] Implement bounded extraction and multimodal context; keep uploads separate from approved observations.
- [ ] Run suite; verify no evidence gate regressions.

### Task 3: Production UI and verification
Files: app/templates/{layout,ask,settings}.html, app/static/{app.js,connected-chat.js,connected-chat.css}, tools/connected_chat_acceptance.py, docs/CONNECTED_CHAT_ACCEPTANCE.md.
- [ ] Implement larger typography, black/white GPT-like composer, plus upload, native model/thinking controls and left-bottom settings.
- [ ] Validate saved profiles without exposing credentials, remove queued files and retain upload labels in history.
- [ ] Discover live catalogs and test one GPT/Gemini/Claude and official DeepSeek; run one full source-backed question with a successful provider.
- [ ] Run pytest/ruff/compile/pip checks, desktop/mobile browser acceptance and a fresh independent whole-change review; fix material findings with regression tests.
- [ ] Record backup, commands, provider outcomes, limitations and local URL; commit verified changes.

## Execution ledger
Task 0: complete. Backup output/backups/chat-upgrade-20261019-080716 contains source.zip, consistent market.sqlite3 and hashes.
Ruling: User explicitly requested direct implementation, so no additional design-approval round. Native execution with final independent review.
Pre-flight: provider runtime and attachments must be resolved before executor submission; subsequent user model switches cannot alter an in-flight job.

Task 1: complete — encrypted profiles, allowlist, actual catalogs and four successful provider probes; targeted tests green.
Task 2: complete — owner-bound attachments, exact uploaded-quote validation and actual live model file reading.
Task 3: complete — SQL/ECharts and GPT-style UI, real independent scheduled AI/HTML run, loopback SMTP, browser desktop/mobile, full suite and repaired independent review findings.
Ruling: The user prioritized P0 and paused PDF work; existing PDF artifacts were preserved, new work focused on HTML, dashboard and delivery. Cost if wrong: PDF layout improvements remain deferred.
