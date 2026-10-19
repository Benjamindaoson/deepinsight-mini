## Why
The production chat needs readable typography, real attachments, model/thinking controls and user-managed credentials when a workspace key runs out. The user explicitly authorizes ToAPIs and official DeepSeek live tests, superseding the earlier official-only restriction.
## What Changes
- Match the supplied GPT reference layout with 18px chat text, visible controls and bottom-left settings.
- Add encrypted server-side personal provider profiles; only approved HTTPS provider hosts, no arbitrary endpoints or credential echo.
- Discover actual models, check connectivity and select per-request thinking parameters without silently substituting models.
- Upload bounded documents/images, retain provenance and include them as untrusted context; never auto-approve market facts.
- Back up before changes, retain all evidence/budget/auth/notification gates and run offline plus real browser/provider acceptance.
## Capabilities
### New Capabilities
- `connected-chat`: provider profiles, attachments, readable chat and request controls.
### Modified Capabilities
None.
## Impact
FastAPI routes, agent request adapter, encrypted private storage, chat/settings templates and regression/browser acceptance.
