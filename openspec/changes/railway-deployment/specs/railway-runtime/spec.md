## ADDED Requirements
### Requirement: One persistent Linux service
The app SHALL run one ASGI worker and one supervised independent scheduler, listen on 0.0.0.0:$PORT and persist data/reports on a separate mounted volume.
#### Scenario: Service restarts
- **WHEN** the Railway service restarts
- **THEN** observations, schedules and saved HTML reports remain available and a second scheduler does not duplicate a claimed slot
### Requirement: Secure portable providers
The app SHALL store personal Linux keys with authenticated encryption whose master key exists only in the service environment, while retaining Windows DPAPI behavior.
#### Scenario: Missing encryption key
- **WHEN** Linux personal storage is requested without a valid master key
- **THEN** the operation fails closed without writing plaintext
### Requirement: Safe deployment archive
The upload SHALL contain only application files and a bounded public-source seed, excluding .env, credentials, private chats, local databases, runtimes, caches and logs.
#### Scenario: Packaging scan
- **WHEN** the local-source upload is prepared
- **THEN** actual known credentials are absent from all selected file bytes
### Requirement: Honest live acceptance
The release SHALL distinguish build, startup, actual HTTPS/browser/model/monitor/report tests and measured storage/memory, and SHALL not upgrade plans without authorization.
#### Scenario: Free account limitation
- **WHEN** the real account or resource measurements prevent deployment
- **THEN** report the specific failure without claiming cloud success
