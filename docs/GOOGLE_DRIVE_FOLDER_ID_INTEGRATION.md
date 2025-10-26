# Google Drive Folder ID Integration via JWT Token

## Overview

The Google Drive folder ID (where letters are uploaded) is now extracted from the JWT token instead of using a hardcoded environment variable. This allows each client to have their own dedicated Google Drive folder.

**Before**: All letters uploaded to a single shared folder (from `GOOGLE_DRIVE_FOLDER_ID` environment variable)
**After**: Each client's letters uploaded to their specific folder (from `google_drive_id` in JWT token)

## Master Sheet Structure

The master sheet contains the required columns:

```
clientId | displayName | primaryDomain | extraDomains | sheetId | GoogleDriveId
```

- `clientId`: Unique client identifier
- `displayName`: Client name for display
- `primaryDomain`: Primary email domain
- `extraDomains`: Additional email domains (comma-separated)
- `sheetId`: Google Sheet ID for client's data
- `GoogleDriveId`: Google Drive folder ID where letters are uploaded

## Implementation Details

### 1. JWT Token Enhancement

**File**: `src/services/user_management_service.py`

**Method**: `_create_access_token()`

**Changes**:
- Added `google_drive_id` field to JWT payload
- Extracted from `ClientInfo.google_drive_id` (read from master sheet)

```python
token = jwt.encode(
    {
        "client_id": client_info.client_id,
        "admin_email": client_info.admin_email,
        "exp": time.time() + (self.config.auth.token_expiry_hours * 3600),
        "sheet_id": client_info.sheet_id,
        "google_drive_id": client_info.google_drive_id,  # NEW
        "letter_template": client_info.letter_template,
        "has_access": has_access,
        "letter_type": client_info.letter_type,
        "user": user_info.to_dict()
    },
    self.config.auth.jwt_secret,
    algorithm=self.config.auth.jwt_algorithm
)
```

### 2. Archive Route Update

**File**: `src/api/archive_routes.py`

**Endpoint**: `POST /api/v1/archive/letter`

**Changes**:
- Extract `google_drive_id` from JWT token
- Validate that it's present
- Pass to background processing function

```python
@archive_bp.route('/letter', methods=['POST'])
@measure_performance
@require_auth
def archive_letter(user_info):
    try:
        # Extract sheet_id and google_drive_id from JWT token
        sheet_id = user_info.get('sheet_id')
        google_drive_id = user_info.get('google_drive_id')
        
        if not sheet_id:
            return build_error_response("معرف الجدول غير موجود في التوكن", 400)
        
        if not google_drive_id:
            return build_error_response("معرف مجلد Google Drive غير موجود في التوكن", 400)
        
        # ... rest of code ...
```

### 3. Background Processing Function Update

**File**: `src/api/archive_routes.py`

**Function**: `process_letter_archive_in_background()`

**Changes**:
- Added `google_drive_id` parameter
- Pass it to `save_letter_to_drive_and_log()`

```python
def process_letter_archive_in_background(
    template: str,
    letter_content: str,
    letter_id: str,
    letter_type: str,
    recipient: str,
    title: str,
    is_first: bool,
    sheet_id: str,
    user_email: str,
    google_drive_id: str  # NEW
) -> None:
    """
    Process letter archiving in background thread.
    
    Args:
        google_drive_id: Google Drive folder ID for upload (from JWT token)
    """
    try:
        # ... PDF generation ...
        
        archive_result = drive_logger.save_letter_to_drive_and_log(
            letter_file_path=pdf_result.file_path,
            letter_content=letter_content,
            letter_type=letter_type,
            recipient=recipient,
            title=title,
            is_first=is_first,
            sheet_id=sheet_id,
            letter_id=letter_id,
            user_email=user_email,
            folder_id=google_drive_id  # User's Google Drive folder ID from token
        )
```

### 4. Drive Logger Update

**File**: `src/services/drive_logger.py`

**Method**: `save_letter_to_drive_and_log()`

**Changes**:
- Made `folder_id` parameter **required** (no fallback to environment variable)
- Return error if `folder_id` is None
- Clear error message when Drive upload fails

```python
def save_letter_to_drive_and_log(self, 
                                 letter_file_path: str,
                                 letter_content: str,
                                 letter_type: str,
                                 recipient: str,
                                 title: str,
                                 is_first: bool,
                                 sheet_id: str,
                                 letter_id: str,
                                 user_email: str,
                                 folder_id: str = None) -> Dict[str, Any]:
    """
    Complete workflow: Upload PDF to Drive and log to sheets.
    
    Args:
        folder_id: REQUIRED - Google Drive folder ID (from google_drive_id in JWT token)
    """
    try:
        # Validate folder_id is provided (required for Drive upload)
        if folder_id is None:
            error_msg = "folder_id (google_drive_id from JWT token) is required for Drive upload"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "file_id": None,
                "file_url": None,
                "letter_id": letter_id
            }
```

## Flow Diagram

```
User Login Request
        ↓
User Management validates credentials
        ↓
Lookup ClientInfo from master sheet
        ↓
ClientInfo includes:
  - sheet_id (user's Google Sheet)
  - google_drive_id (user's Drive folder) ← KEY ADDITION
        ↓
_create_access_token creates JWT with google_drive_id
        ↓
JWT Token returned to client
        ↓
Archive Letter Request with JWT
        ↓
Extract sheet_id and google_drive_id from JWT
        ↓
Validate both are present
        ↓
Generate PDF in background
        ↓
Upload to Drive using google_drive_id
        ↓
Log to user's Google Sheet using sheet_id
```

## Setup Instructions

### 1. Master Sheet Configuration

Ensure your master sheet has the `GoogleDriveId` column:

```
Column Headers:
clientId | displayName | primaryDomain | extraDomains | sheetId | GoogleDriveId

Example Row:
client_001 | ACME Corp | acme.com | subsidiary.com | [Sheet ID] | [Drive Folder ID]
```

### 2. Create Google Drive Folders

For each client:
1. Create a folder in Google Drive
2. Copy the folder ID (from URL: `https://drive.google.com/drive/folders/[FOLDER_ID]`)
3. Add folder ID to master sheet's `GoogleDriveId` column
4. Share folder with service account email

### 3. Share Folder with Service Account

1. Get service account email from `automating-letter-creations.json`
2. Open the Google Drive folder
3. Share with service account email with **Editor** access

### 4. Update Master Sheet

Update the master sheet with folder IDs for all clients:

```
SET GoogleDriveId = "1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P" WHERE clientId = "client_001"
```

## Error Handling

### Missing google_drive_id in JWT

**Error Response**:
```json
{
  "status": "error",
  "message": "معرف مجلد Google Drive غير موجود في التوكن",
  "error_code": 400
}
```

**Cause**: Master sheet doesn't have GoogleDriveId for this client

**Solution**: Add GoogleDriveId to master sheet

### Invalid Folder ID

**Error Response**:
```json
{
  "status": "error",
  "message": "folder_id (google_drive_id from JWT token) is required for Drive upload",
  "file_id": null,
  "file_url": null,
  "letter_id": "LET-20251022-12345"
}
```

**Cause**: Folder ID doesn't exist or service account doesn't have access

**Solution**: 
- Verify folder ID is correct
- Verify service account has Editor access
- Check Google Drive API is enabled

### Upload Failed

**Error Response**:
```json
{
  "status": "error",
  "message": "Drive upload failed: [Specific error details]",
  "file_id": null,
  "file_url": null,
  "letter_id": "LET-20251022-12345"
}
```

**Cause**: Various Drive API issues

**Solution**:
- Check Google Drive API credentials
- Verify service account permissions
- Check folder still exists
- Review Google Drive API quotas

## Testing

### Test 1: Verify JWT Token Contains google_drive_id

```bash
# Login
curl -X POST http://localhost:5000/api/v1/user/validate \
  -H "Content-Type: application/json" \
  -d '{"email": "user@client.com", "password": "password"}'

# Response:
# {
#   "status": "success",
#   "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
# }

# Decode JWT (use jwt.io or Python):
import jwt
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
decoded = jwt.decode(token, options={"verify_signature": False})
print(decoded["google_drive_id"])  # Should show folder ID
```

### Test 2: Archive Letter to Correct Folder

```bash
curl -X POST http://localhost:5000/api/v1/archive/letter \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt_token>" \
  -d '{
    "letter_content": "Test letter content",
    "letter_type": "General",
    "recipient": "John Doe",
    "title": "Test Letter",
    "is_first": true,
    "ID": "LET-20251022-12345"
  }'

# Response:
# {
#   "status": "success",
#   "message": "Letter archiving started for ID: LET-20251022-12345",
#   "processing": "background",
#   "letter_id": "LET-20251022-12345"
# }

# Check Google Drive - file should appear in the correct folder
```

### Test 3: Verify Sheet Logging

The letter should also be logged to the user's sheet (specified by `sheet_id` in JWT):

```bash
# Query the user's sheet
# The Submissions sheet should contain a new row with:
# - ID: LET-20251022-12345
# - Created_by: user@client.com
# - Final_letter_url: [Google Drive link]
# - Status: Pending
```

## Monitoring & Logging

### Log Examples

**Successful Archive**:
```
INFO: Archive request from user: user@client.com, client: client_001, sheet: sheet_id_123, drive: folder_id_456
INFO: Starting background archiving for letter ID: LET-20251022-12345 (sheet: sheet_id_123, drive: folder_id_456)
INFO: Uploading to Drive and logging for letter ID: LET-20251022-12345 to sheet: sheet_id_123, drive: folder_id_456
INFO: File uploaded to Drive: Test Letter_LET-20251022-12345.pdf (ID: file_id_789)
INFO: Successfully archived letter LET-20251022-12345 to Drive and logged to sheet sheet_id_123
```

**Missing google_drive_id**:
```
ERROR: Archive request rejected - google_drive_id missing from JWT token
ERROR: folder_id (google_drive_id from JWT token) is required for Drive upload
```

## Security Considerations

✅ **Per-client isolation**: Each client has their own Drive folder
✅ **JWT-based access**: Folder ID tied to authenticated user
✅ **No hardcoded credentials**: Folder ID in master sheet, not in code/env vars
✅ **Service account permissions**: Only required permissions granted
✅ **Audit trail**: All uploads logged with user email and timestamp

## Backward Compatibility

⚠️ **Breaking Change**: Previously, letters were uploaded to a single shared folder

**Migration Path**:
1. Create individual Drive folders for each client
2. Update master sheet with folder IDs
3. Deploy updated code
4. Future letters will upload to correct folders
5. Existing letters remain in old shared folder

## Related Documentation

- [Archive Routes Documentation](./API_DOCUMENTATION.md#archive-routes)
- [User Management Service](./USER_MANAGEMENT_API.md)
- [JWT Authentication](./API_DOCUMENTATION.md#authentication)

---

**Status**: ✅ Production Ready

Google Drive folder IDs are now properly isolated per client via JWT tokens, ensuring each client's letters are stored in their dedicated folders.
