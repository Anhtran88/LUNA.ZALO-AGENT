# Product specification
Luna reads selected Zalo groups, summarizes selected periods, extracts operator-selected images/PDFs, creates reports, and previews eOffice edits. Current scaffold demonstrates these flows entirely with labeled fixtures; date-range filtering and real extraction remain unimplemented.

Exact allowed group names:
- ĐỐI CHIẾU KL- KẾ TOÁN IJC
- TDC-ĐỐI CHIẾU KL BÊ TÔN
- My Documents
Missing or duplicate matches stop the operation; never use fuzzy matching.

Company entry point: https://eoffice.becamexijc.com/workflow/sitepages/workflowdynamicrequest.aspx?rcid=8&rscid=0&wid=0
Read statistics and preview record/field/current/proposed values. No actual writes in validation MVP. Later every write/send/submit/delete/upload needs immediate operator confirmation; changed values invalidate previews.

Files: images/PDF only, selected by operator. Output: operator-selected local folder (for example a BAO CAO folder inside the local OneDrive directory). PO authorizes OneDrive synchronization via desktop client, not Firebase Storage upload. Retain indefinitely; warn and stop new writes when storage lacks capacity; never auto-delete. Long retention can incur quota/billing costs; no paid service without budget approval.

## Settings scaffold
Settings cards: Zalo, eOffice, AI Model, Firebase RTDB, File/OneDrive. Status labels distinguish missing config/login, local connection and errors. No live test is implemented. Mock checks do not establish authenticated connection. Zalo open/QR and Firebase live read-only tests remain disabled pending connector/auth implementation. Operator login checkboxes are declarations, not verified sessions.

eOffice URL is editable but stays within approved HTTPS domain and approved query; query changes need review to avoid storing credentials in URLs. UI previews still use fixtures. Model key input is masked; explicit save uses Windows user-scoped DPAPI, encrypted outside Git. No existing credential is read and no decryption/live consumption exists yet. No plaintext fallback. Live model test must later require valid configuration, billing/budget and explicit charge warning/confirmation; current test is mock only.

Folder picker checks existence and OS write-access flags without probe writes. Actual save errors remain authoritative. Files saved locally are not reported as cloud-synced. Settings persist non-secret values under local app data; no Firebase binary upload. Zalo allowlist checkboxes restrict mock report/file actions.

## Offline MVP implemented
Vietnamese desktop navigation: Chat, Zalo/Tệp, Báo cáo, eOffice, Hàng đợi offline, Cấu hình. Fixtures now include dated messages with source IDs, date filtering, persistent report history and TXT/JSON export. eOffice fixture table supports record/field selection and invalidates preview on edits. These are offline examples, never a claim to live extraction or AI inference.
