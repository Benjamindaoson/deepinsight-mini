## Why
Deploy the actual DeepInsight Mini app to one Railway Free service before the assessment deadline, preserving source/evidence and authentication gates.
## What Changes
- Add a Linux container, single-worker ASGI supervisor and one independent scheduler process.
- Persist SQLite, raw evidence, encrypted provider profiles and HTML reports on one volume.
- Add authenticated Linux secret storage using a Railway-managed encryption key, environment-backed workspace bootstrap, bounded job concurrency and resource measurements.
- Include only a curated public-source seed; exclude credentials, private conversations, local caches and unfiltered databases from upload.
- Deploy through the official authenticated CLI, create a domain and verify real HTTPS workflows, restart persistence and graceful failures.
## Capabilities
### New Capabilities
- `railway-runtime`: portable secrets, persistent bootstrap, supervised one-service runtime and actual cloud verification.
### Modified Capabilities
None.
## Impact
Deployment files, provider vault, resource/auth configuration, bootstrap, tests and deployment receipts. No Lite/Radar changes, plan upgrade or public notification sends.
