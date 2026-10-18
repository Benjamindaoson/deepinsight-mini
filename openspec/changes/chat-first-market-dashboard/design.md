## Context
User supplied ChatGPT layout reference and original assessment. Existing five-page app has a report-first overview and five pending market observations. Official API key is configured; a fresh model-check still returns HTTP402.
## Goals / Non-Goals
Goals: a chat-first interface, dashboard visibility for every assessment topic, real source-backed values and explicit periods, persistent questions and connected source lookup.
Non-Goals: fabricated quarterly history or approval of pending observations just to draw charts.
## Decisions
- / and /ask both render chat. /overview holds the dashboard. Sidebar order is Ask AI, Overview, Market Monitor, Reports, Settings.
- A topic catalog maps each assessment concern to metrics, questions, source targets and gaps. Includes City, West End, Canary Wharf, Midtown/Fringe, rents, vacancy/availability, leasing, pipeline, macro, occupier demand and news.
- The dashboard distinguishes source-reported candidates (visible for inspection with review badges) from approved decision metrics and trend charts. Source-reported values do not silently acquire approval.
- Re-extraction of retained raw evidence is idempotent and audited. Add lawful official macro connectors; unavailable endpoints remain visibly failed.
- Chat uses a centered empty state, suggestion prompts, left history and a persistent bottom composer. Do not include fake attachment/voice controls.
- Latest user steering explicitly requests dashboard plots of the connected metrics. Visualize retained ONS API history as source-reported raw data with pending review labels, one current official definition/unit/publisher per chart, explicit periods and inspectable data points. These charts never enter approved quantitative reports or imply a rent effect. This is separate from analyst-approved market trend publication.
## Risks / Trade-offs
Provider HTTP402 blocks live AI. Missing submarket observations must remain gaps. Some public APIs may be unavailable or disallow collection. Period/definition mismatch must continue to block comparisons.
