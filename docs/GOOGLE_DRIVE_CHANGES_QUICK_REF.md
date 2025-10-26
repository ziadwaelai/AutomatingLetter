# Quick Reference: Google Drive Folder ID Changes

## What Changed?

**Before**: Letters saved to hardcoded environment variable folder
```python
folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")  # Single shared folder for all
```

**After**: Letters saved to client-specific folder from JWT token
```python
folder_id = user_info.get('google_drive_id')  # Per-client folder from master sheet
```

## Modified Files

### 1. `src/services/user_management_service.py`

**Location**: Line 660-677 (method `_create_access_token`)

**Before**:
```python
token = jwt.encode({
    "client_id": client_info.client_id,
    "admin_email": client_info.admin_email,
    "exp": time.time() + ...,
    "sheet_id": client_info.sheet_id,
    "letter_template": client_info.letter_template,
    "has_access": has_access,
    "letter_type": client_info.letter_type,
    "user": user_info.to_dict()
}, ...)
```

**After**:
```python
token = jwt.encode({
    "client_id": client_info.client_id,
    "admin_email": client_info.admin_email,
    "exp": time.time() + ...,
    "sheet_id": client_info.sheet_id,
    "google_drive_id": client_info.google_drive_id,  # ← ADDED
    "letter_template": client_info.letter_template,
    "has_access": has_access,
    "letter_type": client_info.letter_type,
    "user": user_info.to_dict()
}, ...)
```

### 2. `src/api/archive_routes.py`

**Location 1**: Line 30-48 (method `archive_letter`)

**Before**:
```python
def archive_letter(user_info):
    # Extract sheet_id from JWT token
    sheet_id = user_info.get('sheet_id')
    if not sheet_id:
        return build_error_response("معرف الجدول غير موجود في التوكن", 400)
    
    # Get user email for logging
    user_email = user_info.get('user', {}).get('email', 'unknown')
    client_id = user_info.get('client_id', 'unknown')
    
    logger.info(f"Archive request from user: {user_email}, client: {client_id}, sheet: {sheet_id}")
```

**After**:
```python
def archive_letter(user_info):
    # Extract sheet_id and google_drive_id from JWT token
    sheet_id = user_info.get('sheet_id')
    if not sheet_id:
        return build_error_response("معرف الجدول غير موجود في التوكن", 400)
    
    google_drive_id = user_info.get('google_drive_id')  # ← ADDED
    if not google_drive_id:  # ← ADDED
        return build_error_response("معرف مجلد Google Drive غير موجود في التوكن", 400)  # ← ADDED
    
    # Get user email for logging
    user_email = user_info.get('user', {}).get('email', 'unknown')
    client_id = user_info.get('client_id', 'unknown')
    
    logger.info(f"Archive request from user: {user_email}, client: {client_id}, sheet: {sheet_id}, drive: {google_drive_id}")
```

**Location 2**: Line 84-89 (background thread call)

**Before**:
```python
background_thread = threading.Thread(
    target=process_letter_archive_in_background,
    args=(template, letter_content, letter_id, letter_type, recipient, title, is_first, sheet_id, user_email)
)
```

**After**:
```python
background_thread = threading.Thread(
    target=process_letter_archive_in_background,
    args=(template, letter_content, letter_id, letter_type, recipient, title, is_first, sheet_id, user_email, google_drive_id)  # ← ADDED
)
```

**Location 3**: Line 111-120 (function signature)

**Before**:
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
    user_email: str
) -> None:
```

**After**:
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
    google_drive_id: str  # ← ADDED
) -> None:
```

**Location 4**: Line 155-162 (drive_logger call)

**Before**:
```python
archive_result = drive_logger.save_letter_to_drive_and_log(
    letter_file_path=pdf_result.file_path,
    letter_content=letter_content,
    letter_type=letter_type,
    recipient=recipient,
    title=title,
    is_first=is_first,
    sheet_id=sheet_id,
    letter_id=letter_id,
    user_email=user_email
)
```

**After**:
```python
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
    folder_id=google_drive_id  # ← ADDED (was None before)
)
```

### 3. `src/services/drive_logger.py`

**Location**: Line 130-195 (method `save_letter_to_drive_and_log`)

**Before**:
```python
def save_letter_to_drive_and_log(self, ..., folder_id: str = None) -> Dict[str, Any]:
    try:
        # Get folder_id from environment if not provided
        if folder_id is None:
            import os
            folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
            if not folder_id:
                logger.warning("No folder_id provided and GOOGLE_DRIVE_FOLDER_ID not set, using sheet's Drive folder")
        
        filename = f"{title}_{letter_id}.pdf" if title != 'undefined' else f"letter_{letter_id}.pdf"
        
        if folder_id:
            file_id, file_url = self.upload_file_to_drive(letter_file_path, folder_id, filename)
        else:
            logger.warning(f"No folder_id for Drive upload, letter {letter_id} will only be logged to sheet")
            file_id = "N/A"
            file_url = "No Drive folder configured"
```

**After**:
```python
def save_letter_to_drive_and_log(self, ..., folder_id: str = None) -> Dict[str, Any]:
    try:
        # Validate folder_id is provided (required for Drive upload)
        if folder_id is None:  # ← CHANGED: Now required, not optional
            error_msg = "folder_id (google_drive_id from JWT token) is required for Drive upload"
            logger.error(error_msg)  # ← CHANGED: Error instead of warning
            return {
                "status": "error",
                "message": error_msg,
                "file_id": None,
                "file_url": None,
                "letter_id": letter_id
            }
        
        filename = f"{title}_{letter_id}.pdf" if title != 'undefined' else f"letter_{letter_id}.pdf"
        
        try:  # ← CHANGED: Added try/except
            file_id, file_url = self.upload_file_to_drive(letter_file_path, folder_id, filename)
        except Exception as upload_error:  # ← CHANGED: Better error handling
            logger.error(f"Failed to upload letter {letter_id} to Drive: {upload_error}")
            return {
                "status": "error",
                "message": f"Drive upload failed: {str(upload_error)}",
                "file_id": None,
                "file_url": None,
                "letter_id": letter_id
            }
```

## Summary of Changes

| File | Change Type | Impact |
|------|------------|--------|
| `user_management_service.py` | Enhancement | JWT token now includes `google_drive_id` |
| `archive_routes.py` (3 places) | Enhancement | Extract and pass `google_drive_id` through call chain |
| `drive_logger.py` | Enforcement | Folder ID is now required, no fallback to env var |

## Backward Compatibility

⚠️ **Breaking Change**: Code will fail if master sheet doesn't have `GoogleDriveId` column

**Action Required**:
1. Add `GoogleDriveId` column to master sheet
2. Populate with client-specific Google Drive folder IDs
3. Ensure service account has access to all folders
4. Deploy updated code

## Verification

All changes verified:
- ✅ `user_management_service.py` - No compilation errors
- ✅ `archive_routes.py` - No compilation errors
- ✅ `drive_logger.py` - No compilation errors

## Testing Command

```bash
# After deployment, test with:
curl -X POST http://localhost:5000/api/v1/archive/letter \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt_token_with_google_drive_id>" \
  -d '{
    "letter_content": "Test letter",
    "letter_type": "General",
    "recipient": "Test User",
    "title": "Test",
    "is_first": true,
    "ID": "TEST-001"
  }'

# Verify:
# 1. Response is HTTP 200 (success)
# 2. Letter appears in client's Google Drive folder (not shared folder)
# 3. Entry logged in user's Google Sheet
```

---

**Complete Details**: See `GOOGLE_DRIVE_FOLDER_ID_INTEGRATION.md`
