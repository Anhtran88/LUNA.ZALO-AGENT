# Working on Luna
Use /workspace/LUNA.ZALO-AGENT, official origin Anhtran88/LUNA.ZALO-AGENT. Use the existing isolated checkout; do not create a worktree unless requested. GitHub is source of truth. Codex is the engineering agent.

Keep this a small Windows-first Python application. No multi-agent platform or large monorepo. Read docs before changing behavior. Never commit credentials, sessions, browser profiles, or user files. Configuration belongs outside Git. Default to mock/offline; do not enable live services without explicit authorization. Do not change Firebase Rules/billing automatically.

Zalo groups must match the exact allowlist, with exactly one result. eOffice writes remain preview only. Sending, submitting, deleting, uploading, or changing external data requires per-action confirmation. Do not bypass login/2FA/CAPTCHA. OneDrive synchronization is performed by the user's desktop client, not an API integration.

Development: Python 3.12+, python -m venv .venv; install with python -m pip install -e .; run python -m luna. PySide6 is required. Playwright is deliberately not installed until a real connector is authorized. No tests/build were executed during initial scaffolding, per PO instruction. Future validation should cover group ambiguity, file containment/hash/collisions, offline persistence, UI flows and preview-only behavior before live work.
