## ADDED Requirements

### Requirement: Safe deterministic SQL analytics
The system SHALL compile structured QuerySpec requests into bounded read-only parameterized SQL. Temporal calculations SHALL use window functions and reject incompatible, pending, revised or missing consecutive periods. Percent-rate deltas SHALL be percentage points.

#### Scenario: Missing quarter
- **WHEN** approved observations exist at Q1 and Q3 with no Q2
- **THEN** a quarter-over-quarter request SHALL return NOT_COMPARABLE and no growth figure.

#### Scenario: Unsafe input
- **WHEN** an unknown metric, raw SQL operation, unbounded row count or extra input is submitted
- **THEN** schema validation SHALL reject it without executing arbitrary SQL.

### Requirement: Eight real domain skills
The system SHALL provide eight documented executable skills through one registry, with validated input/output, timeout, permissions, evidence IDs, warnings and safe errors. Same schemas SHALL support native function calling and the tested MCP adapter.

#### Scenario: Unpermitted mutation
- **WHEN** an agent requests approval or a monitor action without explicit mutation permission
- **THEN** no review or monitor write SHALL occur and a structured error SHALL be returned.

### Requirement: Evidence-driven BI dashboard
The system SHALL expose global geography, metric, grade, source, time and review filters that affect relevant API results, KPIs and charts. Approved data SHALL be the default. Empty, pending, incompatible, failed and stale evidence SHALL be explicit. Chart drill-down SHALL retain evidence IDs and scope when opening Ask AI.

#### Scenario: No eligible observations
- **WHEN** a selected regional metric has no approved compatible evidence
- **THEN** the dashboard SHALL show Not Verified and its coverage state without synthetic marks.

### Requirement: Independent scheduled delivery
The system SHALL run APScheduler 3 outside the web process at 08:00 and 18:00 Europe/London, invoke existing collection/analysis/report/outbox services and persist unique run slots. No data and no change SHALL remain distinct.

#### Scenario: Restart and repeated slot
- **WHEN** an already completed London date/type slot is encountered after restart
- **THEN** it SHALL not create a second run or send the report twice.

### Requirement: Real acceptance and honest claims
The system SHALL retain actual source, provider, SQL, scheduler, UI, export and isolated transport receipts. Synthetic regressions SHALL be separate from live market and model acceptance. Failed evidence SHALL not be silently approved.

#### Scenario: Provider failure
- **WHEN** a real model request fails or returns an incomplete final answer
- **THEN** the report SHALL preserve available evidence and explicitly state AI analysis unavailable; Real AI acceptance SHALL remain BLOCKED or FAIL.
