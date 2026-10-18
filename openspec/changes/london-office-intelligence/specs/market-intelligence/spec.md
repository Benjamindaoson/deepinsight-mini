## ADDED Requirements

### Requirement: Traceable public collection
The system SHALL collect at least two independent allowed public sources, persist raw hashes and document versions, and expose source health and citations.
#### Scenario: Repeated collection
- **WHEN** the same source body is collected twice
- **THEN** only one version exists and the second run has no duplicate updates.
#### Scenario: Source failure
- **WHEN** a source fails or access is disallowed
- **THEN** coverage is PARTIAL or FAILED and the source is marked FETCH_FAILED without implying market stability.

### Requirement: Deterministic evidence gates
The system MUST withhold pending or retracted numeric observations from quantitative publication, compare compatible approved observations only, and preserve revisions.
#### Scenario: Percentage comparison
- **WHEN** approved same-definition vacancy changes from 7.2 to 7.0 percent across compatible quarterly periods
- **THEN** delta is -0.2 percentage points with a separate relative percentage.
#### Scenario: Revision or mismatch
- **WHEN** periods match or definition, publisher, geography, period type or unit differs
- **THEN** comparison returns NOT_COMPARABLE with a reason.
#### Scenario: Retraction
- **WHEN** an underlying observation or source is invalidated
- **THEN** dependent current signals are invalidated and historical reports show a current-evidence warning.

### Requirement: Bounded actual agent
The system SHALL use actual SDK tool calling with six shared skill interfaces, persisted follow-ups, source verification and hard request/time/token budgets.
#### Scenario: Real research
- **WHEN** a user asks a market question
- **THEN** a successful live acceptance includes actual model tool calls and verifiable source IDs; insufficient evidence is disclosed.
#### Scenario: Untrusted instructions
- **WHEN** a retrieved page includes instructions or tool names
- **THEN** it remains untrusted evidence and cannot alter system authority or approved facts.

### Requirement: Shared professional reports
The system SHALL save one structured report object and render HTML, email and A4 PDF, with source links, fact/interpretation distinctions, limitations and approval-only charts.
#### Scenario: Missing comparable history
- **WHEN** fewer than two compatible approved observations exist
- **THEN** no invented chart is rendered and the report says Insufficient comparable observations.

### Requirement: Independent scheduled delivery
The system SHALL execute one shared monitor outside the web process at 08:00 and 18:00 Europe/London, persist slot and run records, prevent overlap and deduplicate notifications.
#### Scenario: DST
- **WHEN** London changes between GMT and BST
- **THEN** morning remains 08:00 local London time.
#### Scenario: Delivery disabled
- **WHEN** external recipients have not been configured, tested and explicitly enabled
- **THEN** no external message is sent and isolated capture is labeled TEST ONLY.

### Requirement: Interactive business product
The system SHALL provide Overview, Ask AI, Monitor, Reports and Settings with protected writes, persistent settings, progress states, historical reports and PDF downloads.
#### Scenario: Browser acceptance
- **WHEN** a business user monitors, asks and follows up, opens sources, downloads PDF, saves settings and reopens the page
- **THEN** records persist and failures are clearly explained without secret values or tracebacks.

### Requirement: Honest delivery evidence
The system MUST ship runnable Python, run instructions, evidence matrix and five business PPTX slides with actual screenshots and no fabricated ROI.
#### Scenario: External blocker
- **WHEN** quota, source permission or recipient configuration prevents live proof
- **THEN** the corresponding acceptance remains BLOCKED or PARTIAL independently of unit test success.
