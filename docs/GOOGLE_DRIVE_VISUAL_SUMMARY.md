# Google Drive Folder ID Integration - Visual Summary

## Problem → Solution

```
BEFORE (❌ Wrong):
┌─────────────────────────────────────────┐
│     All Clients' Letters                │
│   └─ Shared Google Drive Folder         │
│      ├─ Letter from Client A            │
│      ├─ Letter from Client B            │
│      ├─ Letter from Client C            │
│      └─ All mixed together ❌           │
└─────────────────────────────────────────┘
  Problem: No isolation, shared folder


AFTER (✅ Correct):
┌──────────────────────────────────────────────────────────┐
│           Client A Folder             │  Client B Folder │
│  ├─ Letter 1                          │  ├─ Letter 1     │
│  ├─ Letter 2                          │  ├─ Letter 2     │
│  └─ Letter 3                          │  └─ ...          │
└──────────────────────────────────────────────────────────┘
  Solution: Per-client isolation from JWT token
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Login Request                        │
│                  email + password                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           User Management Service                           │
│  ├─ Lookup user in client's sheet (by email)               │
│  └─ Validate password                                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           Master Sheet Lookup                               │
│  ├─ Find clientId for this user's domain                   │
│  ├─ Get ClientInfo:                                         │
│  │  ├─ sheet_id (user's Google Sheet)                      │
│  │  ├─ google_drive_id (user's Drive folder) ← KEY!        │
│  │  ├─ letter_template                                     │
│  │  └─ letter_type                                         │
│  └─ Return ClientInfo                                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           JWT Token Creation                                │
│  token = {                                                  │
│    "client_id": "...",                                      │
│    "admin_email": "...",                                    │
│    "sheet_id": "abc123...",                                 │
│    "google_drive_id": "xyz789...",  ← Per-client folder   │
│    "letter_template": "...",                                │
│    "letter_type": "...",                                    │
│    "user": {...},                                           │
│    "exp": timestamp                                         │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
                   Return JWT Token to Client
                   
                   ═══════════════════════════════════════════
                   
┌─────────────────────────────────────────────────────────────┐
│              Archive Letter Request                         │
│  POST /api/v1/archive/letter                               │
│  Authorization: Bearer <JWT_TOKEN>                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           Extract from JWT Token                            │
│  ├─ sheet_id → User's Google Sheet                          │
│  ├─ google_drive_id → User's Drive Folder ← KEY!           │
│  ├─ user.email → For logging                               │
│  └─ Validate both exist                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           Background Processing                             │
│  ├─ Generate PDF (from letter content)                      │
│  └─ Pass to drive_logger:                                   │
│     ├─ sheet_id (for logging)                              │
│     └─ google_drive_id (for upload) ← CRITICAL             │
└─────────────────────────────────────────────────────────────┘
                              ↓
                     Split into 2 Tasks
                    ↙                    ↘
      ┌──────────────────────┐    ┌──────────────────────┐
      │  Upload to Drive     │    │  Log to Sheet        │
      │  ├─ Folder ID:       │    │  ├─ Sheet ID:        │
      │  │  google_drive_id  │    │  │  sheet_id         │
      │  ├─ Filename:        │    │  ├─ Data:            │
      │  │  {Title}_{ID}.pdf │    │  │  ID, timestamp,    │
      │  └─ Result:          │    │  │  file_url, etc.    │
      │     file_url         │    │  └─ Result:          │
      │                      │    │     logged           │
      └──────────────────────┘    └──────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           Return to Client                                  │
│  {                                                          │
│    "status": "success",                                     │
│    "message": "Letter archiving started",                   │
│    "letter_id": "..."                                       │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘

RESULT:
├─ Letter PDF in: [Client's Google Drive Folder]
├─ Entry logged to: [Client's Google Sheet]
└─ Isolation verified: ✅
```

## Data Flow: JWT Token

```
Master Sheet
    ↓
┌─────────────────────────────────┐
│ clientId | ... | sheetId | GoogleDriveId  │
│ client_1 | ... | sheet_1 | folder_1       │
│ client_2 | ... | sheet_2 | folder_2       │
│ client_3 | ... | sheet_3 | folder_3       │
└─────────────────────────────────┘
    ↓ (lookup by email domain)
┌─────────────────────────────────┐
│ ClientInfo:                      │
│ ├─ client_id: "client_1"        │
│ ├─ sheet_id: "sheet_1"          │
│ └─ google_drive_id: "folder_1"  │
└─────────────────────────────────┘
    ↓ (encode into JWT)
┌─────────────────────────────────┐
│ JWT Token:                       │
│ {                               │
│   "sheet_id": "sheet_1",        │
│   "google_drive_id": "folder_1",│
│   ... other claims ...          │
│ }                               │
└─────────────────────────────────┘
    ↓ (sent with request)
┌─────────────────────────────────┐
│ Archive Request:                │
│ Authorization: Bearer JWT       │
│   sheet_id → User's Sheet       │
│   google_drive_id → User's Folder
└─────────────────────────────────┘
```

## File Locations After Changes

```
src/
├── services/
│   ├── user_management_service.py ← CHANGED (JWT token)
│   ├── drive_logger.py ← CHANGED (folder_id validation)
│   └── ...
├── api/
│   ├── archive_routes.py ← CHANGED (extract & pass google_drive_id)
│   └── ...
└── ...
```

## Key Changes Summary

```
File 1: user_management_service.py
╔════════════════════════════════════════════════════════════╗
║ _create_access_token()                                     ║
║ ─────────────────────────────────────────────────────────  ║
║ ADDED:                                                     ║
║   "google_drive_id": client_info.google_drive_id           ║
║                                                            ║
║ JWT Token now includes google_drive_id from master sheet   ║
╚════════════════════════════════════════════════════════════╝

File 2: archive_routes.py
╔════════════════════════════════════════════════════════════╗
║ archive_letter()                                           ║
║ ─────────────────────────────────────────────────────────  ║
║ ADDED:                                                     ║
║   ├─ Extract google_drive_id from JWT                     ║
║   ├─ Validate it's not None (return 400 if missing)       ║
║   └─ Pass to background function                          ║
║                                                            ║
║ process_letter_archive_in_background()                    ║
║ ─────────────────────────────────────────────────────────  ║
║ ADDED:                                                     ║
║   ├─ google_drive_id parameter                            ║
║   └─ Pass to save_letter_to_drive_and_log()               ║
║       folder_id=google_drive_id                           ║
╚════════════════════════════════════════════════════════════╝

File 3: drive_logger.py
╔════════════════════════════════════════════════════════════╗
║ save_letter_to_drive_and_log()                             ║
║ ─────────────────────────────────────────────────────────  ║
║ CHANGED:                                                   ║
║   ├─ folder_id now REQUIRED (not optional)                ║
║   ├─ NO fallback to GOOGLE_DRIVE_FOLDER_ID env var        ║
║   ├─ Return error if folder_id is None                    ║
║   └─ Better error handling for upload failures            ║
║                                                            ║
║ Behavior:                                                  ║
║   folder_id = None → Return {"status": "error", ...}      ║
║   folder_id = valid → Upload to that folder               ║
╚════════════════════════════════════════════════════════════╝
```

## Testing Workflow

```
Step 1: Setup
├─ Master sheet has GoogleDriveId column
├─ Each client has dedicated Drive folder
├─ Service account has Editor access to all folders
└─ Code deployed

Step 2: Login Test
├─ POST /api/v1/user/validate
├─ Get JWT token
├─ Decode JWT → check google_drive_id present ✅
└─ Verify folder ID matches master sheet ✅

Step 3: Archive Test
├─ POST /api/v1/archive/letter
├─ Background processing runs
├─ Check Google Drive:
│  └─ File in Client 1's folder ✅
│  └─ NOT in shared folder ✅
├─ Check Google Sheet:
│  └─ Entry logged with file_url ✅
└─ Check logs:
   └─ No warnings about env var ✅

Step 4: Isolation Test
├─ Archive letter from Client A
├─ Archive letter from Client B
├─ Client A's folder has only Client A's letter ✅
├─ Client B's folder has only Client B's letter ✅
└─ No cross-contamination ✅

SUCCESS ✅
```

## Error Scenarios

```
Scenario 1: Missing google_drive_id from JWT
├─ Cause: Master sheet missing GoogleDriveId column
├─ Error Response: HTTP 400
├─ Message: معرف مجلد Google Drive غير موجود في التوكن
└─ Fix: Add GoogleDriveId column to master sheet

Scenario 2: Invalid folder_id
├─ Cause: Service account lacks permission
├─ Error Response: HTTP 500
├─ Message: Drive upload failed: [API error]
└─ Fix: Share folder with service account (Editor)

Scenario 3: Empty google_drive_id in master sheet
├─ Cause: Cell is empty or null
├─ Error Response: HTTP 400 or 500 (depends on parsing)
├─ Message: folder_id is required for Drive upload
└─ Fix: Populate GoogleDriveId with valid folder ID

Scenario 4: Using old JWT token
├─ Cause: Token created before code change
├─ Error Response: HTTP 400
├─ Message: معرف مجلد Google Drive غير موجود في التوكن
└─ Fix: User must login again to get new token
```

## Before/After Comparison

```
BEFORE:
┌──────────────────────────────────────────┐
│ Archive Request                          │
│ Authorization: Bearer JWT                │
│   (JWT has sheet_id, but NO google_drive_id) │
└──────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────┐
│ Drive Logger                             │
│ folder_id = os.getenv("GOOGLE_DRIVE_...")│
│           = hardcoded folder             │
│           = shared for all clients ❌     │
└──────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────┐
│ Shared Google Drive Folder               │
│ ├─ Client A's letters                   │
│ ├─ Client B's letters                   │
│ └─ All mixed ❌                          │
└──────────────────────────────────────────┘

AFTER:
┌──────────────────────────────────────────┐
│ Archive Request                          │
│ Authorization: Bearer JWT                │
│   (JWT has sheet_id AND google_drive_id) │
└──────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────┐
│ Extract from JWT:                        │
│ ├─ sheet_id = "sheet_123"               │
│ └─ google_drive_id = "folder_456" ← KEY │
└──────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────┐
│ Drive Logger                             │
│ folder_id = google_drive_id              │
│           = client-specific folder ✅    │
│           = isolated per client          │
└──────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────┐
│ Client A Folder    │   Client B Folder   │
│ ├─ Letter 1        │   ├─ Letter 1      │
│ └─ Letter 2        │   └─ Letter 2      │
│ Isolated ✅        │   Isolated ✅       │
└──────────────────────────────────────────┘
```

---

**Status**: Implementation Complete ✅
**Files Modified**: 3
**Errors**: 0
**Ready for Deployment**: Yes ✅
