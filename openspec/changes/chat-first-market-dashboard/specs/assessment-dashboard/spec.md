## ADDED Requirements
### Requirement: Chat-first navigation
The product SHALL show Ask AI first, Overview second, and render a GPT-like conversation at the default route.
#### Scenario: Open the product
- **WHEN** a user opens /
- **THEN** they see a central chat composer and saved conversations, and can navigate to /overview for market metrics.
### Requirement: Assessment coverage
The dashboard SHALL list every business concern in the supplied assessment with relevant metric IDs, questions, periods and source targets.
#### Scenario: Inspect current market figures
- **WHEN** source observations exist
- **THEN** their values, units, submarkets, periods, original links and review status are visible without representing pending values as approved trends.
### Requirement: Data-connected conversation
Ask AI SHALL use the same stored source and metric layer as the dashboard and provide topic-specific suggested questions.
#### Scenario: Provider unavailable
- **WHEN** the official API returns HTTP402
- **THEN** show an honest model blocker and allow inspection of deterministic evidence matches, without claiming successful model tool calling.
