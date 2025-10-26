# JWT Authentication for Archiving System

## Overview
All archive endpoints now require JWT authentication. The token contains the user's `sheet_id` which is used to log letters to the correct Google Sheet.

---

## How It Works

### 1. User Login/Validation
```
POST /api/v1/user/validate
{
  "email": "user@domain.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "تم التحقق من المستخدم بنجاح"
}
```

### 2. JWT Token Contents
The JWT token contains:
```json
{
  "client_id": "client123",
  "admin_email": "admin@domain.com",
  "sheet_id": "1ABC...XYZ",  // ← Used for archiving
  "letter_template": "default_template",
  "letter_type": "General",
  "has_access": true,
  "exp": 1698057600,
  "user": {
    "email": "user@domain.com",
    "full_name": "User Name",
    "role": "user",
    "status": "active",
    "created_at": "2025-10-22T..."
  }
}
```

### 3. Using the Token for Archiving
```
POST /api/v1/archive/letter
Headers:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  Content-Type: application/json

Body:
{
  "letter_content": "Letter text here...",
  "ID": "LET-20251022-12345",
  "letter_type": "Official",
  "recipient": "Recipient Name",
  "title": "Letter Title",
  "is_first": false
}
```

**What Happens:**
1. ✅ Token is extracted from `Authorization` header
2. ✅ Token is decoded to get `sheet_id`
3. ✅ Letter is archived to Google Drive
4. ✅ Letter is logged to the user's Google Sheet (using `sheet_id` from token)
5. ✅ Response returned immediately (processing in background)

---

## JWT Utility Functions

### 1. `extract_token_from_request()`
Extracts JWT token from Authorization header.

```python
from src.utils import extract_token_from_request

token = extract_token_from_request()
# Returns: "eyJhbGc..." or None
```

### 2. `decode_jwt_token(token, secret, algorithm)`
Decodes JWT token and returns payload.

```python
from src.utils import decode_jwt_token
from src.config import get_config

config = get_config()
payload = decode_jwt_token(token, config.auth.jwt_secret, config.auth.jwt_algorithm)
# Returns: {"client_id": "...", "sheet_id": "...", ...} or None
```

### 3. `get_user_from_token()`
Convenience function that extracts and decodes token in one step.

```python
from src.utils import get_user_from_token

user_info = get_user_from_token()
# Returns: {"client_id": "...", "sheet_id": "...", ...} or None
```

### 4. `@require_auth` Decorator
Decorator to protect endpoints with JWT authentication.

```python
from src.utils import require_auth

@app.route('/protected')
@require_auth
def protected_endpoint(user_info):
    sheet_id = user_info['sheet_id']
    user_email = user_info['user']['email']
    # ... your logic here
    return {"message": "Success"}
```

**If no valid token:**
```json
HTTP 401
{
  "status": "error",
  "message": "غير مصرح",
  "error": "يجب تسجيل الدخول للوصول إلى هذه الصفحة"
}
```

---

## Updated Archive Endpoint

### Endpoint: `POST /api/v1/archive/letter`

**Headers Required:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "letter_content": "محتوى الخطاب هنا...",
  "ID": "LET-20251022-12345",
  "letter_type": "رسمي",
  "recipient": "اسم المستلم",
  "title": "عنوان الخطاب",
  "is_first": false,
  "template": "default_template"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Letter archiving started for ID: LET-20251022-12345",
  "processing": "background",
  "letter_id": "LET-20251022-12345"
}
```

**Background Process:**
1. Generate PDF from letter content
2. Upload PDF to Google Drive (using folder_id from env or config)
3. Log entry to Google Sheets (using `sheet_id` from JWT token)
4. Clean up temporary files

---

## Service Updates

### `drive_logger.py` - Updated Methods

#### `save_letter_to_drive_and_log()`
Now accepts `sheet_id` parameter:

```python
result = drive_logger.save_letter_to_drive_and_log(
    letter_file_path=pdf_path,
    letter_content=content,
    letter_type=letter_type,
    recipient=recipient,
    title=title,
    is_first=is_first,
    sheet_id=sheet_id,  # ← From JWT token
    letter_id=letter_id,
    username=username,
    folder_id=None  # Optional, uses env var if not provided
)
```

#### `log_to_sheet_by_id()`
New method to log to sheet by ID:

```python
result = drive_logger.log_to_sheet_by_id(
    sheet_id="1ABC...XYZ",
    log_entry={
        "Timestamp": "2025-10-22 10:30:00",
        "Type of Letter": "Official",
        "Recipient": "John Doe",
        # ... other fields
    },
    worksheet_name="Submissions"
)
```

### `google_services.py` - New Method

#### `log_entries_by_id()`
Logs entries to a specific Google Sheet by ID:

```python
result = sheets_service.log_entries_by_id(
    sheet_id="1ABC...XYZ",
    worksheet_name="Submissions",
    entries=[log_entry1, log_entry2]
)
```

**Returns:**
```json
{
  "status": "success",
  "entries_logged": 2,
  "sheet_id": "1ABC...XYZ",
  "worksheet": "Submissions"
}
```

---

## Testing the Flow

### Step 1: Get JWT Token
```bash
curl -X POST http://localhost:5000/api/v1/user/validate \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@domain.com",
    "password": "password123"
  }'
```

**Save the token from response.**

### Step 2: Archive a Letter
```bash
curl -X POST http://localhost:5000/api/v1/archive/letter \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "letter_content": "This is a test letter",
    "ID": "LET-20251022-99999",
    "letter_type": "Test",
    "recipient": "Test Recipient",
    "title": "Test Title",
    "is_first": false
  }'
```

### Step 3: Verify
- ✅ Check console logs for archiving progress
- ✅ Check Google Drive for uploaded PDF
- ✅ Check Google Sheet (with `sheet_id` from token) for logged entry

---

## Error Handling

### No Token Provided
```json
HTTP 401
{
  "status": "error",
  "message": "غير مصرح",
  "error": "يجب تسجيل الدخول للوصول إلى هذه الصفحة"
}
```

### Expired Token
```json
HTTP 401
{
  "status": "error",
  "message": "غير مصرح",
  "error": "يجب تسجيل الدخول للوصول إلى هذه الصفحة"
}
```

### Invalid Token
```json
HTTP 401
{
  "status": "error",
  "message": "غير مصرح",
  "error": "يجب تسجيل الدخول للوصول إلى هذه الصفحة"
}
```

### Missing sheet_id in Token
```json
HTTP 400
{
  "error": "معرف الجدول غير موجود في التوكن"
}
```

---

## Configuration

### JWT Settings (`src/config/settings.py`)
```python
@dataclass
class AuthConfig:
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"
    token_expiry_hours: int = 24
```

### Environment Variables
```env
JWT_SECRET=your-secure-secret-key-here
GOOGLE_DRIVE_FOLDER_ID=optional-default-folder-id
```

---

## Benefits

✅ **User-Specific Archiving** - Each user's letters are logged to their own sheet
✅ **Secure** - Only authenticated users can archive letters
✅ **Multi-Tenant** - Different clients have different sheets
✅ **Automatic** - sheet_id is automatically extracted from token
✅ **Traceable** - User email and client info logged with each letter

---

## Summary

1. ✅ User validates credentials → receives JWT token
2. ✅ Token contains `sheet_id` and user info
3. ✅ Archive endpoint requires token in `Authorization` header
4. ✅ `sheet_id` is extracted and used for logging to correct Google Sheet
5. ✅ Letters are archived to Drive and logged to user's specific sheet

**The archiving system is now fully integrated with JWT authentication!** 🎉
