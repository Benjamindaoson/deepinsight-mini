# Connected chat and P0 market intelligence delivery

Verified against the running local project on 19 October 2026. Historical acceptance files remain historical. The live website is http://127.0.0.1:8766/ and the SQL/ECharts dashboard is /overview.

## Implemented and exercised

- Chat: supplied GPT-style centered composer;19px desktop and16px mobile input;18px desktop transcript; plus file picker; native model/thinking menu; bottom-left Settings & API keys.
- Personal credentials: actual save, encrypted DPAPI persistence, provider model discovery, replace/remove and live connection test. No saved key returned by GET APIs, SQLite, localStorage or rendered HTML. Signed HttpOnly owner identity and existing authentication/CSRF/host/CSP gates are preserved. Endpoint allowlist is ToAPIs and official DeepSeek, with verified TLS and redirects disabled.
- Actual supplied providers: GPT `gpt-5.6-terra` (low), Gemini `gemini-2.5-flash-official`, Claude `claude-haiku-4-5` via ToAPIs, and `deepseek-flash` via official DeepSeek returned successful text completions. Gateway-reported model identifiers are retained; this does not independently attest the gateway's upstream implementation.
- Attachments: PDF/DOCX/UTF-8 text/CSV/JSON/PNG/JPEG, max8MiB and five files, bounded extraction and owner checks. The browser uploaded a text note; the real model returned its exact unique phrase. Files never enter approved market observations. Unsupported OCR/format/vision combinations fail explicitly.
- Agent: eight implemented domain skill packages, typed input/output contracts,21 registered tools, FTS5 search, native tool calling, optional stdio MCP adapter. Live browser run `5eced452b37245b89d80f72b0d4357d2` succeeded with3 actual calls including `query_market_metrics`, and validated an attachment quote. Separate live source research also retained a source-validated qualitative claim.
- BI: real parameterized SQL filters for region, indicator, property grade, source, calendar period and review state. CTE/window calculations enforce compatible definitions, sources, units, approval and consecutive periods. Default reviewed mode retains missing values; View collected source figures explicitly reveals pending inspection data. The actual dataset has101 observations,21 series and zero approved numeric observations.
- ECharts:21 actual source-series charts/snapshots exercised, including rents, vacancy, availability, take-up, pipeline, demand and macro. Single-period bars are labeled snapshots; missing comparable history never becomes a fabricated trend. Original evidence is available through chart clicks and accessible data tables. Macro and office-market definitions remain separate. Events, coverage and health are visible.
- Monitoring: independent Windows Task Scheduler triggered controlled evening run `fbeff39c806f433a9d27f97d2bdf9aa6`, completed successfully, collected7/7 sources, ran actual AI tools and generated report `c312a96a715b40f4befe1b429f7433fa`. Task result0. Defaults restored to08:00/18:00 Europe/London. SQLite slots, monitor lock and notification identities suppress duplicates. APScheduler3 adapter uses the same durable slot identities; no second production scheduler was launched.
- HTML/email: the current scheduled briefing includes revalidated AI material labeled draft/review-required, original sources and evidence gaps. An actual HTML MIME email reached a loopback SMTP recipient once; repeat send was deduplicated. External delivery stays disabled. PDF development/export work was paused as requested.

## Verification

`python -m pytest -q`:82 passed, one upstream Starlette/HTTPX deprecation warning. `python -m ruff check app tests tools`, `python -m compileall -q app deepinsight tools`, `python -m pip check`: passed. OpenSpec connected-chat and mini-v2 changes validated.

Actual browser acceptance covers personal key save/catalog/live check, model/thinking selection, plus upload, exact model file reading, actual tools, SQL filters, source evidence drill-down, missing-data behavior and five mobile pages without horizontal overflow. Final receipt: `output/evidence/connected-chat/browser-acceptance.json`; zero page errors. The initial mobile harness used an invalid Playwright API; it was repaired and remaining UI checks resumed without repeating passed paid requests. A real mobile table overflow was fixed and rechecked.

Independent review reproduced a conversation-alias privacy bypass, a pending-input rolling-average leak, incorrect latest/rank selection within historical intervals and mixed monthly/quarterly filtering. Fixes and regression tests were applied. All four are covered by current code and tests.

## Backup, receipts and limits

Pre-change backup: `output/backups/chat-upgrade-20261019-080716` contains source.zip, consistent SQLite backup and SHA256 manifest. Keys are excluded from the source backup; personal vaults require the same Windows OS account or re-entry on migration. The project remains isolated from Lite.

Machine-readable current delivery: `output/evidence/connected-chat/P0_DELIVERY_RECEIPT.json`. Provider receipts contain no keys. Private uploaded data is not a public artifact. Current HTML: `output/reports/c312a96a715b40f4befe1b429f7433fa.html`.

The six original question runs were blocked by an old key; they have not been relabeled. New successful runs are separate. Full market coverage is not established: dedicated Canary Wharf/Midtown histories and direct hybrid-working measurements remain gaps. Pending observations require explicit review; no quantitative market conclusion or investment return is claimed. Personal key persistence was verified on Windows; Linux requires a native secret-store adapter or environment credentials. External recipient delivery, VPS deployment, multi-day uptime and Microsoft PowerPoint application rendering are not claimed.

## Operator choices

The user authorized direct native implementation and real ToAPIs/DeepSeek calls, superseding official-only restrictions. Provider hosts remain allowlisted rather than accepting arbitrary URLs; additional providers require operator review. Default dashboard analysis stays reviewed-only, with a separate explicit source-inspection action. The existing independent Windows task remains the active scheduler; the APScheduler alternative is available without launching a duplicate worker.

The refreshed five-slide local PowerPoint is `output/slides/London_Office_Intelligence_Business_Demo_v4.pptx`; structural/layout/font/import checks passed, no findings. It uses the actual new dashboard screenshot and current AI status. No new PDF was exported.
