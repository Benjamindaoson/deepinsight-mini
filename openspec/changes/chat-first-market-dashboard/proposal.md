## Why
The user wants Ask AI as the primary, GPT-like chat experience and a separate dashboard that visibly covers the business assessment's metrics and questions.
## What Changes
- Make Ask AI first and default, Overview second at /overview.
- Redesign chat around conversation history, a central transcript and bottom composer.
- Add an assessment metric/question/source catalog, source-reported observations, approved-only numeric charts, coverage visualization and macro source connectors.
- Retest official DeepSeek, preserving HTTP402 as a real external blocker.
## Capabilities
### New Capabilities
- `assessment-dashboard`: business metric visibility, evidence states, topic questions and source coverage.
### Modified Capabilities
None.
## Impact
Routes, templates, styles, dashboard data contract, extractor, source registry, tests and browser acceptance. Existing evidence/review gates remain in effect.
