# Architecture
One Windows desktop process: PySide6 UI → application services → mock adapters and local pending-sync store. No API server, microservices, enterprise auth or multi-agent runtime.

ModelRouter keeps an OpenAI-compatible request/response contract; only mock exists. Zalo and eOffice adapters contain fixtures, not HTTP/browser operations. A future headed Playwright connector must be explicitly implemented and reviewed. QR/login are manual.

RTDB is canonical when configured and authorized. Local durable records are an offline outbox, never a competing canonical DB. Conflict handling will use stable IDs, revision checks and idempotency. No current cloud upload or sync. Native OneDrive client syncs output files independently.

## Settings scaffold
Settings cards: Zalo, eOffice, AI Model, Firebase RTDB, File/OneDrive. Status labels distinguish missing config/login, local connection and errors. No live test is implemented. Mock checks do not establish authenticated connection. Zalo open/QR and Firebase live read-only tests remain disabled pending connector/auth implementation. Operator login checkboxes are declarations, not verified sessions.

eOffice URL is editable but stays within approved HTTPS domain and approved query; query changes need review to avoid storing credentials in URLs. UI previews still use fixtures. Model key input is masked; explicit save uses Windows user-scoped DPAPI, encrypted outside Git. No existing credential is read and no decryption/live consumption exists yet. No plaintext fallback. Live model test must later require valid configuration, billing/budget and explicit charge warning/confirmation; current test is mock only.

Folder picker checks existence and OS write-access flags without probe writes. Actual save errors remain authoritative. Files saved locally are not reported as cloud-synced. Settings persist non-secret values under local app data; no Firebase binary upload. Zalo allowlist checkboxes restrict mock report/file actions.
