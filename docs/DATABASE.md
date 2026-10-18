# Data and storage
Project: supplied locally through FIREBASE_PROJECT_ID
Database URL: supplied locally through FIREBASE_DATABASE_URL
These are identifiers, not proof of connectivity or permission. No live initialization performed. Web API key is not an Admin credential and is not stored in source.

Future canonical paths under /workspaces/{workspaceId}: tasks/{id}, reports/{id}, files/{id}, approvals/{id}, audit/{id}. Records include stable id, timestamps, revision, device reference and task/source references. Reports hold text/JSON. File metadata holds original/stored name, relative path, SHA-256, bytes, group and local/sync state. fileHashes/{hash}/{id} may index dedup; hash match alone must not delete originals.

Current JSON outbox stores task/report/file/approval/audit records locally as pending_sync. No RTDB sync is implemented. Future sync retries by stable ID, checks revisions and leaves conflicts visible. Offline permits drafts and local processing; never queues external writes for automatic execution on reconnect.

Binary stays in Windows/OneDrive. Never place large binary/base64 in RTDB. Firebase Storage is not configured and binary uploads are not authorized. Do not change Rules or billing. No automatic expiry/deletion. Warn on capacity; block new writes/sync at limits and ask operator. OneDrive upload completion is unknown to this scaffold.
