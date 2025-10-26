# Google Drive Integration - Data Flow Diagrams

## Complete Request/Response Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                      CLIENT APPLICATION                            │
│                                                                    │
│  Step 1: User clicks "Generate Letter"                            │
│          Enters: letter content, recipient, type                  │
└────────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│                      STEP 2: LOGIN PHASE                           │
│                                                                    │
│  POST /api/v1/user/validate                                       │
│  Body: { email: "user@acme.com", password: "***" }               │
└────────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│                 USER MANAGEMENT SERVICE                            │
│                                                                    │
│  1. Lookup "user@acme.com" in client's Users sheet                │
│  2. Validate password                                             │
│  3. Find client by email domain                                   │
│  4. Lookup master sheet by domain                                 │
└────────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│                   MASTER SHEET LOOKUP                              │
│                                                                    │
│  Query: WHERE primaryDomain = "acme.com"                          │
│  Result ClientInfo:                                               │
│  ├─ clientId: "acme_001"                                          │
│  ├─ sheet_id: "11eCtNuW4cl03TX0G20...GKlI"                       │
│  ├─ google_drive_id: "1A2B3C4D5E6F7G8H9..."  ← CRITICAL         │
│  ├─ admin_email: "admin@acme.com"                                 │
│  └─ letter_template: "default_template"                           │
│                                                                    │
│  Master Sheet Row:                                                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ clientId│displayName│primaryDomain│sheetId│GoogleDriveId│  │
│  │ acme_001│ ACME Corp │  acme.com   │sheet1 │folder_xyz789│  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│              CREATE JWT TOKEN (via _create_access_token)           │
│                                                                    │
│  token = jwt.encode({                                             │
│    "client_id": "acme_001",                                       │
│    "admin_email": "admin@acme.com",                               │
│    "sheet_id": "11eCtNuW4cl03TX0G20...GKlI",                     │
│    "google_drive_id": "1A2B3C4D5E6F7G8H9...",  ← ADDED           │
│    "letter_template": "default_template",                         │
│    "user": {                                                      │
│      "email": "user@acme.com",                                    │
│      "full_name": "John Doe",                                     │
│      ...                                                          │
│    },                                                             │
│    "exp": 1729606000  (24 hours from now)                        │
│  }, secret, algorithm="HS256")                                    │
│                                                                    │
│  TOKEN = eyJ0eXAiOiJKV1QiLCJhbGc...[very long string]           │
└────────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│              RETURN JWT TO CLIENT                                  │
│                                                                    │
│  Response:                                                        │
│  {                                                                │
│    "status": "success",                                           │
│    "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",                        │
│    "message": "تم التحقق من المستخدم بنجاح"                    │
│  }                                                                │
│                                                                    │
│  Client stores: localStorage.token = JWT                          │
└────────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│                    STEP 3: ARCHIVE PHASE                           │
│                                                                    │
│  POST /api/v1/archive/letter                                      │
│  Headers: Authorization: Bearer eyJ0eXAi...                       │
│  Body: {                                                          │
│    "letter_content": "محتوى الخطاب...",                         │
│    "letter_type": "عام",                                         │
│    "recipient": "أحمد محمد",                                     │
│    "title": "طلب معلومات",                                       │
│    "is_first": true,                                              │
│    "ID": "LET-20251022-12345"                                     │
│  }                                                                │
└────────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│            EXTRACT FROM JWT (in archive_letter)                    │
│                                                                    │
│  Decode JWT token:                                                │
│  {                                                                │
│    "sheet_id": "11eCtNuW4cl03TX0G20...GKlI",                     │
│    "google_drive_id": "1A2B3C4D5E6F7G8H9...",  ← CRITICAL       │
│    "user": { "email": "user@acme.com", ... }                     │
│  }                                                                │
│                                                                    │
│  Validate:                                                        │
│  if not sheet_id → return 400                                     │
│  if not google_drive_id → return 400  ← NEW VALIDATION           │
└────────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│          START BACKGROUND PROCESSING THREAD                        │
│                                                                    │
│  threading.Thread(                                                │
│    target=process_letter_archive_in_background,                  │
│    args=(                                                         │
│      template,                                                    │
│      letter_content,                                              │
│      letter_id,                                                   │
│      letter_type,                                                 │
│      recipient,                                                   │
│      title,                                                       │
│      is_first,                                                    │
│      sheet_id,                                                    │
│      user_email,                                                  │
│      google_drive_id  ← PASSED HERE                              │
│    )                                                              │
│  ).start()                                                        │
│                                                                    │
│  Return immediate success:                                        │
│  {                                                                │
│    "status": "success",                                           │
│    "message": "Letter archiving started",                         │
│    "letter_id": "LET-20251022-12345"                             │
│  }                                                                │
└────────────────────────────────────────────────────────────────────┘
         ↓                                           ↓
    BACKGROUND THREAD CONTINUES...
    
    ┌──────────────────────────────────────────────────────────┐
    │  Step 1: Generate PDF                                    │
    │  ├─ Input: letter_content                               │
    │  ├─ Template: default_template                          │
    │  └─ Output: /tmp/letter_LET-20251022-12345.pdf         │
    └──────────────────────────────────────────────────────────┘
                        ↓
            ┌───────────────────────┐
            │   SPLIT INTO 2 TASKS  │
            └───────────────────────┘
           ↙                         ↖
                                     
    ┌──────────────────────────┐ ┌──────────────────────────┐
    │    TASK 1: DRIVE UPLOAD  │ │   TASK 2: SHEET LOGGING │
    │                          │ │                          │
    │ upload_file_to_drive(    │ │ log_to_sheet_by_id(      │
    │   file_path,             │ │   sheet_id,              │
    │   folder_id,             │ │   log_entry              │
    │   filename               │ │ )                        │
    │ )                        │ │                          │
    │                          │ │ Entry: {                 │
    │ folder_id =              │ │   ID: letter_id,         │
    │ "1A2B3C4D5E6F7G8..."     │ │   Timestamp: now,        │
    │ (from JWT token) ✅      │ │   Created_by: email,     │
    │                          │ │   Final_letter_url: url  │
    │ ├─ Connect to Drive      │ │   ...                    │
    │ ├─ Create file metadata  │ │ }                        │
    │ ├─ Set parent: folder_id │ │                          │
    │ ├─ Upload PDF            │ │ Target Sheet:            │
    │ └─ Return: file_id, url  │ │ client's Google Sheet    │
    │                          │ │ (from sheet_id)          │
    │ Result:                  │ │                          │
    │ file_id: "abc123..."     │ │ Result:                  │
    │ url: "drive.google.com.."│ │ Logged: Success          │
    └──────────────────────────┘ └──────────────────────────┘
           ↓                              ↓
    ┌──────────────────────────┐ ┌──────────────────────────┐
    │  ACME's Drive Folder     │ │  ACME's Google Sheet     │
    │                          │ │                          │
    │ 1A2B3C4D5E6F7G8H9...     │ │ 11eCtNuW4cl03TX0G20...  │
    │ ├─ Letter 1              │ │ Submissions Sheet:       │
    │ ├─ Letter 2              │ │ ID│Timestamp│Created_by  │
    │ ├─ طلب معلومات_LET...pdf│ │ ..│..........│..........  │
    │ │  ✅ File in correct     │ │ ..|..........│ACME User   │
    │ │     folder!             │ │ ..|..........│........... │
    │ └─ ...                   │ │ ..|..........│....      │
    │                          │ │ ..✅ Entry logged        │
    └──────────────────────────┘ └──────────────────────────┘

RESULT: ✅
├─ PDF uploaded to: ACME's Google Drive folder
├─ Entry logged to: ACME's Google Sheet
└─ Isolation verified: Per-client folders maintained
```

## Folder Isolation Diagram

```
Before Implementation (❌ WRONG):
┌───────────────────────────────────────────────────────────┐
│                                                             │
│            Shared Google Drive Folder                       │
│       (GOOGLE_DRIVE_FOLDER_ID env variable)               │
│                                                             │
│   ├─ Letter from User A (Client 1)                        │
│   ├─ Letter from User B (Client 2)                        │
│   ├─ Letter from User C (Client 1)                        │
│   ├─ Letter from User D (Client 3)                        │
│   ├─ Letter from User E (Client 2)                        │
│   └─ All mixed together - no isolation! ❌                │
│                                                             │
└───────────────────────────────────────────────────────────┘


After Implementation (✅ CORRECT):
┌──────────────────┬──────────────────┬──────────────────┐
│  Client 1 Folder │  Client 2 Folder │  Client 3 Folder │
│                  │                  │                  │
│  (From master    │  (From master    │  (From master    │
│   sheet)         │   sheet)         │   sheet)         │
│                  │                  │                  │
│  ├─ Letter A     │  ├─ Letter B     │  ├─ Letter D     │
│  ├─ Letter C     │  └─ Letter E     │  └─ ...          │
│  └─ ...          │                  │                  │
│                  │                  │                  │
│  ✅ Isolated     │  ✅ Isolated     │  ✅ Isolated     │
└──────────────────┴──────────────────┴──────────────────┘
     (Per-client, from JWT token)
```

## Master Sheet Lookup Flow

```
User Email: user@acme.com
    ↓
Extract Domain: acme.com
    ↓
Query Master Sheet:
WHERE primaryDomain = "acme.com" OR extraDomains CONTAINS "acme.com"
    ↓
Find Row:
┌────────────────────────────────────────────────────────────┐
│ clientId│displayName│primaryDomain│extraDomains│sheetId│GoogleDriveId
│ acme_1  │ ACME Corp │ acme.com    │ subsidiary │sheet1 │folder_xyz789
└────────────────────────────────────────────────────────────┘
    ↓
Extract ClientInfo:
├─ client_id: acme_1
├─ sheet_id: sheet1 (user's data sheet)
└─ google_drive_id: folder_xyz789 (user's drive folder) ← KEY
    ↓
Create JWT with:
├─ sheet_id
├─ google_drive_id ← Embedded in token
└─ user info
    ↓
Token can now be used for:
├─ sheet_id → Access user's sheets
└─ google_drive_id → Upload to user's folder
```

## Error Handling Flow

```
Archive Request with JWT
    ↓
┌─────────────────────────────┐
│ Decode JWT Token            │
│ Extract: sheet_id, etc.     │
└─────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Check 1: sheet_id present?              │
│  NO → Return 400                        │
│  YES → Continue                         │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Check 2: google_drive_id present?       │
│  NO → Return 400 ← NEW CHECK            │
│  YES → Continue                         │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Generate PDF & Start Upload             │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Check 3: Drive Upload                   │
│  folder_id is None?                     │
│  YES → Return error {"status": "error"} │
│  NO → Upload to folder_id               │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Check 4: Upload Successful?             │
│  NO → Return error with details         │
│  YES → Continue to logging              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Log to Sheet                            │
│  All data logged with file_url          │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Return Success                          │
│  {                                      │
│    "status": "success",                 │
│    "file_id": "...",                    │
│    "file_url": "drive.google.com/..."   │
│  }                                      │
└─────────────────────────────────────────┘
```

---

**All diagrams show the complete flow with google_drive_id integration** ✅
