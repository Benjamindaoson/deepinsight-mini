# London Office Intelligence runbook

## Windows local operation

Use the project `.venv` for all application dependencies. Start the app with `deployment/windows/Start-Local.ps1`; on the audited tunnel workstation, add `-TunnelDns`. It binds loopback port 8766. `/health` confirms web availability, while `/monitor` separately shows scheduler heartbeat and source health.

The authorized recurring task **DeepInsightMini-LondonMarket** is installed. It runs `Scheduler-Tick.ps1` every minute, claims due Europe/London slots and exits. It is independent of the browser and web process. Python ZoneInfo handles GMT/BST. Defaults are 08:00/18:00. Changing preferences changes the Python due-slot calculation; reinstalling the OS task is unnecessary.

```powershell
.\deployment\windows\Install-Schedule.ps1 -TunnelDns
Get-ScheduledTaskInfo -TaskName DeepInsightMini-LondonMarket
Start-ScheduledTask -TaskName DeepInsightMini-LondonMarket
```

Task logs: `output/logs/scheduler.log`. Persistent slot/run records: `schedule_slots`, `monitor_runs`. The acceptance used a controlled current-minute morning setting, observed an actual scheduled run, then restored 08:00. This establishes one real schedule trigger; it does not establish multi-day uptime. A powered-off computer cannot monitor. The Windows installation uses the current user's normal task context; unattended operation after logout depends on that account/task configuration.

No-overlap mode and a process file lock protect writes. A slot is claimed before execution. A crashed claimed slot is not blindly rerun: inspect `monitor_runs` and `schedule_slots`, preserve the incident and explicitly run a manual monitor. Regular polling does not automatically backfill missed past slots.

## Official model connection

Private process variables: `MINI_API_KEY`, `MINI_BASE_URL=https://api.deepseek.com`, `MINI_MODEL`. The `LLM_*` names are supported fallbacks. Do not paste keys into a chat or commit `.env`. This application does not automatically source `.env`.

Run `python -m deepinsight model-check` after restoring quota or changing the authorized key. Current actual result is HTTP402. A cached provider block prevents repeat chat calls until an explicit check. Daily reservations limit requests and tokens transactionally; maximum tool rounds, request timeout and total model-loop duration also apply. Model IDs and credentials are server-managed. Only official DeepSeek is authorized; another host is rejected.

Live AI/tool calling, final answer semantics and six successful model answers remain unverified while this provider blocker exists. The deterministic stored-evidence search is clearly labeled and is not substituted for agent acceptance.

## Source monitoring and review

`config/sources.yaml` is the allowlist. Verify new hosts, public access and terms before enabling. The collector respects fetched robots rules, uses bounded HTTPS downloads and redirects, rejects private DNS addresses and limits PDFs to size/page/time budgets. Robots permission is an access signal, not a content republication license. Third-party full articles are retained for local audit and are not bundled into the source delivery.

```powershell
.\.venv\Scripts\python.exe -m deepinsight monitor --run once
.\.venv\Scripts\python.exe -m tools.backfill_metrics
```

Backfill re-extracts candidates from retained original documents idempotently; it never approves them. Review the exact original quote, period, geography, definition and unit before an explicit human approval:

```powershell
.\.venv\Scripts\python.exe -m deepinsight review --id OBSERVATION_ID --status APPROVED --reviewer "Reviewer name" --reason "Checked original period, unit and metric definition"
```

Use REJECTED or RETRACTED when required. Approving is an analyst action, not a model tool. Withdrawn/superseded/currently failed evidence invalidates dependent current signals. Reopen historical reports through the app to see current-evidence warnings on web, HTML and PDF. Previously downloaded files cannot be remotely revoked.

Dashboard cards may show source-reported candidates. Three explicitly labeled raw ONS history charts support the user's requested data inspection; they verify each value against retained JSON and never enter formal quantitative reports. Formal numeric conclusions and approved market trend charts require approved compatible observations. Q2 and H1 are different period frequencies. No approved historical pair means no approved market trend line. The 2026Q2 Savills page's article header is 6 August 2026; a related-story date was corrected with an audit log entry, preserving retained raw evidence.

## Notifications

External delivery defaults to off and remains off in the current installation. Settings can choose local EML capture (TEST ONLY), or explicitly opt in to external delivery. Credentials remain server-side. Each production channel is gated by a successful test receipt bound to its recipient and transport fingerprint. Changing a recipient, enabled channel or credentials invalidates the applicable authorization.

SMTP uses STARTTLS and environment credentials. Telegram uses its official Bot API. Apprise can use an explicitly configured destination. Acceptance by a transport does not mean a user received or read the message.

An isolated SMTP test is reproducible without external delivery:

```powershell
.\.venv\Scripts\python.exe -m tools.smtp_acceptance
```

It starts a loopback-only capture endpoint, sends actual HTML MIME, checks source/report/PDF links and verifies the repeat is deduplicated. It does not enable external delivery. Local EML captures are in `output/notification_capture/`; delivery attempts are in SQLite `notifications`.

Explicit connection-refused failures are retryable, with at most three attempts for the same report/channel/destination. Ambiguous transport failures are marked for operator review to avoid accepted-but-unacknowledged duplicate sends. Test and production identities are separate. No unattended external retry has been live-verified.

## PDF and browser setup

Browsers are isolated under `.browsers/`. Set `PLAYWRIGHT_BROWSERS_PATH` and `PLAYWRIGHT_SKIP_BROWSER_GC=1` before installation to preserve unrelated caches. The app uses that project browser; an installed Chromium Edge can be used as a fallback on Windows. Optional `MINI_BROWSER_CHANNEL=msedge` selects it explicitly.

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='D:\deepinsight-mini\.browsers'
$env:PLAYWRIGHT_SKIP_BROWSER_GC='1'
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m deepinsight report --pdf
```

Reports are A4 with clickable sources, page numbers and shared HTML/email data. Every acceptance PDF page was rendered and visually inspected. Archived PDF/HTML remains a time-bound snapshot, not proof of currently valid metrics.

## Linux VPS deployment

Create a dedicated non-root `deepinsight` account. Place this checkout at `/opt/deepinsight-mini`, create its `.venv`, install the locked dependencies and project-local Chromium, and create writable `data`/`output` directories owned by the service user. Store process variables in `/etc/deepinsight-mini.env` with restrictive permissions. Use `MINI_TUNNEL_DNS=0` on a normal VPS network.

```bash
cd /opt/deepinsight-mini
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
PLAYWRIGHT_BROWSERS_PATH=/opt/deepinsight-mini/.browsers PLAYWRIGHT_SKIP_BROWSER_GC=1 .venv/bin/python -m playwright install --with-deps chromium
.venv/bin/python -m deepinsight init
sudo cp deployment/linux/deepinsight-* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now deepinsight-web.service deepinsight-monitor.timer
journalctl -u deepinsight-monitor.service
```

The sample services bind localhost. A public deployment requires an HTTPS reverse proxy, `MINI_ADMIN_TOKEN`, exact `MINI_PUBLIC_HOST` and `MINI_PUBLIC_URL`. Never expose an unauthenticated listener. Authentication uses signed expiring sessions and same-origin CSRF checks. These files are deployment instructions; no VPS has been deployed or tested in this run.

## Backup and restore

Stop the web process and scheduler task before a simple filesystem backup, or use SQLite's online backup API for a consistent database snapshot. Back up `data/market.sqlite3`, `data/documents`, source configuration, `output/reports` and audit receipts. Protect `data/.session-secret`; it is a local authentication signing secret, not a model key. Rotate it on an intentional recovery if existing browser sessions should be invalidated.

Never copy only the SQLite main file while WAL writers are active. Restore into a stopped instance, verify document hashes and run a new source check before treating the restored state as current. Credentials come from the deployment environment and require a separate secure recovery path.

## Troubleshooting

| Symptom | Action |
|---|---|
| HTTP402 from official model | Restore provider quota or authorized official key, then run model-check |
| Private/special DNS error for public domains | Use the explicit tunnel mode only on the audited fake-IP workstation |
| FETCH_FAILED / PARTIAL | Inspect source health, robots and access receipts; do not call the market unchanged |
| No trend chart | Review compatible observations; do not insert synthetic history |
| Scheduler heartbeat absent | Check the OS task/service separately from the web listener |
| Claimed slot without completion | Inspect crash/run logs and use an explicit manual recovery |
| Notification blocked | Configure channel, run successful destination-bound test, then enable automatic delivery |
| Browser executable missing | Install project-local Chromium with GC disabled or select installed Edge |

## Business deck reproduction

The authored source is `tools/build_business_deck.mjs`. It uses the bundled Artifact Tool runtime, screenshots captured by `tools/capture_final.py`, five editable slides and a separate validated output. Create a private `output/slide-build/node_modules` junction to the bundled Node package directory, copy the authoring script there, then run it with the bundled Node executable. Select a new final output filename for a revision; the finalizer will not overwrite a delivered deck. Validation receipts are in `output/slide-build/` and slide previews in `output/slides/`. Structural checks and rendered review do not claim native Microsoft PowerPoint testing.
