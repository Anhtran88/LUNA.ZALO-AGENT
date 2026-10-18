# Windows computer agent
Desktop app and agent are one process initially. Headed Playwright is planned but not installed or called. Future browser profile remains local, outside OneDrive; operator scans QR and handles login challenges.

Zalo workflow: resolve exactly one allowed group → select period → read available messages → summarize with source references → operator selects image/PDF → save with collision-resistant name/hash → report. Missing/truncated history must be reported. Current sample files are generated fixtures, not Zalo downloads.

eOffice: allow only eoffice.becamexijc.com, start at configured workflow page. External login redirects require explicit review. Read stats, preview record/field/old/new. No submit in scaffold. Future execution re-reads values, requests immediate confirmation, acts once and verifies result.

Local saves require user confirmation. Windows output uses an operator-selected local directory; tests/Linux must supply a native path via LUNA_OUTPUT_DIR. Save exclusively, calculate SHA-256, persist metadata locally. OneDrive desktop handles upload, and sync success is not inferred from file existence. Cancellation, quota and offline handling must be validated on Windows before use with user data.

## Settings scaffold
Settings cards: Zalo, eOffice, AI Model, Firebase RTDB, File/OneDrive. Status labels distinguish missing config/login, local connection and errors. No live test is implemented. Mock checks do not establish authenticated connection. Zalo open/QR and Firebase live read-only tests remain disabled pending connector/auth implementation. Operator login checkboxes are declarations, not verified sessions.

eOffice URL is editable but stays within approved HTTPS domain and approved query; query changes need review to avoid storing credentials in URLs. UI previews still use fixtures. Model key input is masked; explicit save uses Windows user-scoped DPAPI, encrypted outside Git. No existing credential is read and no decryption/live consumption exists yet. No plaintext fallback. Live model test must later require valid configuration, billing/budget and explicit charge warning/confirmation; current test is mock only.

Folder picker checks existence and OS write-access flags without probe writes. Actual save errors remain authoritative. Files saved locally are not reported as cloud-synced. Settings persist non-secret values under local app data; no Firebase binary upload. Zalo allowlist checkboxes restrict mock report/file actions.
