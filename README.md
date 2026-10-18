# Luna — offline Windows MVP scaffold
Small desktop chat with mock Zalo, reports, eOffice statistics and edit previews. No network connectors or model calls. No Firebase Rules/billing changes.

## Run on Windows (not yet validated)
Install Python 3.12+, then in PowerShell from this checkout:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m luna
```
Only PySide6 is declared; dependencies have not been installed or checked in this task. Playwright is a future optional dependency.

The file page generates and saves a clearly labeled mock PNG/PDF after confirmation. It does not download from Zalo. Reports are mock and can be explicitly saved locally. Select an existing local OneDrive folder in Settings or set LUNA_OUTPUT_DIR before saving; OneDrive desktop handles synchronization. On Linux set LUNA_OUTPUT_DIR to a disposable local directory before trying save operations; Windows paths are never used there. Offline records use LUNA_STATE_DIR or the OS user application-data directory, outside Git. .env.example is documentation; supply environment variables through your launcher.

RTDB is the future canonical DB. Current local JSON records are pending-sync cache only; no sync worker exists yet. No source tests/build were run by request. Review docs and source before installing/running. Do not assume production readiness.

## Settings
The Cấu hình tab has Zalo/eOffice/AI/Firebase/OneDrive cards. Live connection buttons are disabled; checks are mock/local only. Model keys can be explicitly encrypted with Windows DPAPI outside Git; this Windows-specific code has not been tested. No credential is loaded or sent. Folder selection changes the current output directory and can be saved to non-secret local settings. The folder must exist.

## Local configuration
No personal filesystem path or Firebase project identifier is committed. Choose your output folder in Settings (for example BAO CAO inside your OneDrive folder). Non-secret folder settings persist in local application data. Supply FIREBASE_PROJECT_ID and FIREBASE_DATABASE_URL through your launcher environment; .env.example lists names only and is not loaded automatically. The business group names and eOffice URL are intentional feature defaults, contain no credentials, and remain in source. All adapters remain offline.
