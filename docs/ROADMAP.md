# Incremental roadmap
1. Current: docs, offline desktop mock, exact group resolution, selected fixture file saving with hashes, mock reports/stats/edit preview.
2. Validate Windows install/UI, storage failure/recovery, group ambiguity and offline outbox. Add meaningful tests when requested; none run in scaffold task.
3. Authorized headed browser read-only pilot: manual login, chosen groups/date ranges, eOffice selectors verified on target UI. No bypassing CAPTCHA/2FA.
4. Authorized RTDB authentication/rules review and idempotent sync. Model calls only after API budget/credentials approved.
5. Separately approved live edits with fresh preview, confirmation and verification. No autonomous writes, production rollouts or multi-agent platform in current scope.

Offline UI implementation and Linux offscreen smoke validation completed in the current workspace. Native Windows, DPAPI and OneDrive synchronization remain unverified. No live integration enabled.

Headed browser launch and conservative read-only DOM adapters added. Six browser fixture tests passed; real Zalo/eOffice DOM, Windows QR/profile lifecycle and native DPAPI still need operator validation. Unsupported DOM must stop, not be bypassed. No full-history/date-filter claim for browser reads.
