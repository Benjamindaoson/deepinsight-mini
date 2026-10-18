# Original assessment → product coverage

The supplied screenshot asks for an interactive Python AI Agent PoC and 3–6 business slides. It lists the following business interests. It does not contain a numbered Q1–Q6 question list: the six acceptance questions came from the user's full development brief. Both are implemented as separate checklists below.

| Original business interest | Dashboard / question behavior | Connected primary evidence | Current boundary |
|---|---|---|---|
| Prime and Grade A rents | Separate City and West End source-reported cards, periods and definitions; rent-comparison prompt | Savills Q2 2026 research | One source/report, pending review; no invented rent history |
| Vacancy / availability rates | Percent vacancy separate from available floor area | Savills supply/vacancy | Central London, City and City Fringe observations; dedicated other submarkets incomplete |
| Leasing take-up / activity | Q2 and H1 totals and quarterly transaction count | Savills leasing summary | Half-year and quarterly totals are not like-for-like comparisons |
| Supply pipelines | Completion, construction and pre-let observations; planning event source | Savills; City of London announcement | Forecast/scheduled supply is not delivered supply; approval is not completion |
| City, West End, Canary Wharf, Midtown/Fringe | Four visible submarket areas and an explicit coverage matrix | Savills City/West End/City Fringe; official planning | Canary Wharf and dedicated Midtown series remain gaps |
| Interest rates, economic indicators, employment | BoE rate card; ONS CPI, employment and GDP cards plus original API history charts | BoE and three ONS JSON endpoints | UK context only; no causal office-rent effect claimed; source-reported plots remain review pending |
| Flight-to-quality, ESG/sustainability, hybrid working | Grade A/BREEAM share and active demand; dedicated question | Savills take-up / demand sections | Proxy evidence is not causality; direct hybrid-working measure missing |
| Emerging news, risks and opportunities | RSS/announcement candidates, source links, original date vs discovery date; event question | City of London newsroom and planning announcement | No live new-event arrival or investment return claimed |

Actual source endpoints are configurable in `config/sources.yaml`; the dashboard lists each endpoint's health and last successful fetch. Question definitions are in `app/dashboard.py` and render as eight chat suggestions and eight expandable dashboard topic rows.

## Six actual browser acceptance questions

1. Summarise the latest verifiable developments in the London office market. Focus on City, West End and Canary Wharf. Please distinguish verified data from information that is not yet available.
2. How have prime and Grade A office rents changed in the City and West End? Only compare figures with compatible periods, definitions and units.
3. What new London office leasing or planning events have been discovered since the previous monitoring run?
4. Which changes represent meaningful business risks or opportunities, and what evidence supports them?
5. Generate an executive briefing suitable for a non-technical asset management team, with sources, charts where justified, and clear limitations.
6. Monitor the London office market now, compare the result with the previous successful snapshot, and show me exactly what changed.

The browser run also submitted a follow-up asking which sources covered Canary Wharf and what remained missing. Actual inputs, outputs, source-search matches, zero live tool calls, durations, conversation/run IDs and screenshots are in `output/evidence/browser/acceptance.json`. Every question is currently **BLOCKED for real AI** because the official API returned HTTP402. Deterministic evidence matches remain available and are clearly labeled.

## Period notation

`2026Q2` means the second quarter; `2026H1` means the first half-year; `2026M08` is an official monthly series label. Bank Rate uses effective-change dates such as `2025-12-18`. ONS employment monthly labels can represent rolling estimates; read the original definition. Retrieval time and publication time never replace these observation periods.
