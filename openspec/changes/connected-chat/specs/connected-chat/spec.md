## ADDED Requirements
### Requirement: Readable GPT-style chat
The chat SHALL show a file plus button, a model/thinking menu and a bottom-left settings entry; chat text SHALL be at least 18px on desktop and 16px on mobile.
#### Scenario: User opens chat
- **WHEN** the user opens the homepage
- **THEN** Ask AI is default, the composer is centered and controls are keyboard accessible without overflow
### Requirement: Safe user credentials
The system SHALL permit personal ToAPIs and official DeepSeek profiles, storing keys encrypted outside SQLite/source/browser storage and never returning saved key values.
#### Scenario: User replaces an exhausted key
- **WHEN** a signed user saves a replacement key and explicitly runs a connection check
- **THEN** the selected provider is contacted, a safe receipt is returned and another user's personal credential is inaccessible
### Requirement: Actual model and thinking selection
The system SHALL fetch the provider model catalog and apply supported thinking parameters to the selected model in actual agent requests, preserving evidence and daily budget gates.
#### Scenario: Unsupported combination
- **WHEN** a model or thinking option is not supported
- **THEN** the request is rejected explicitly and no other model is substituted
### Requirement: Real bounded attachments
The system SHALL accept bounded PDF, DOCX, UTF-8 text/CSV/JSON and PNG/JPEG files with ownership checks; extracted text/images SHALL enter actual model input as untrusted data.
#### Scenario: Attachment is submitted
- **WHEN** a user sends a question with an owned attachment
- **THEN** its retained content is passed to the selected provider and remains in conversation provenance without entering approved market observations
### Requirement: Verified production change
The system SHALL retain a source/database backup and execute tests and real browser/provider checks, distinguishing transport/tool success from evidence approval.
#### Scenario: Provider fails
- **WHEN** the provider rejects a real request
- **THEN** the UI exposes a safe failure and saved sources remain available without claiming AI success
