# Simple safety model
Single operator; exact group allowlist and eOffice hostname allowlist. No enterprise identity platform. RTDB still needs authenticated least-privilege access; never public read/write. Admin credentials are not distributed inside desktop source.

Secrets and browser sessions never enter Git, RTDB, model prompts or reports. Future browser profile stays under local application data, outside OneDrive and checkout. Manual QR/login/2FA/CAPTCHA; never export or share session cookies. Only necessary message/report/image/PDF content may be sent to an approved model.

No real connector, execution endpoint or billing activation exists in scaffold. eOffice preview is not approval to write. Future approvals bind record, field, old/new values and action hash, expire, are single-use, and must be reconfirmed after target changes. Redact sensitive log content. Local audit is useful history, not tamper-proof evidence.

## Settings scaffold
Settings cards: Zalo, eOffice, AI Model, Firebase RTDB, File/OneDrive. Status labels distinguish missing config/login, local connection and errors. No live test is implemented. Mock checks do not establish authenticated connection. Zalo open/QR and Firebase live read-only tests remain disabled pending connector/auth implementation. Operator login checkboxes are declarations, not verified sessions.

eOffice URL is editable but stays within approved HTTPS domain and approved query; query changes need review to avoid storing credentials in URLs. UI previews still use fixtures. Model key input is masked; explicit save uses Windows user-scoped DPAPI, encrypted outside Git. No existing credential is read and no decryption/live consumption exists yet. No plaintext fallback. Live model test must later require valid configuration, billing/budget and explicit charge warning/confirmation; current test is mock only.

Folder picker checks existence and OS write-access flags without probe writes. Actual save errors remain authoritative. Files saved locally are not reported as cloud-synced. Settings persist non-secret values under local app data; no Firebase binary upload. Zalo allowlist checkboxes restrict mock report/file actions.

## Read-only browser increment (supersedes disabled browser statements above)
Windows-only headed browser launch and scoped reads are now explicitly user-triggered. Session/login declarations alone never authorize extraction: DOM group identity or approved eOffice table checks must pass. Adapter selectors remain unverified against live services and may reject current UI. No autofill, challenge bypass, send/submit/upload automation or model calls. Playwright exceptions are not printed to avoid leaking signed URLs. Profiles and DPAPI ciphertext are fixed outside Git/OneDrive in AppData; no existing secret is read. User-entered key buffer is cleared after encryption; Python/Qt cannot guarantee erasure of every in-memory string copy.
