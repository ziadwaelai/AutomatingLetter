# Letter Generation Endpoint with JWT Authentication

## Overview
The letter generation endpoint now requires JWT authentication and loads instructions and templates from user-specific Google Sheets.

---

## Updated Endpoint: `POST /api/v1/letter/generate`

### Authentication
**Required Header:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### Request Body
```json
{
  "category": "Official",
  "recipient": "Recipient Name",
  "prompt": "Letter content request here...",
  "is_first": true,
  "letterType": "Official",
  "member_name": "Optional member name",
  "recipient_title": "Dr.",
  "recipient_job_title": "Manager",
  "organization_name": "Organization Name",
  "previous_letter_content": "Optional previous letter",
  "previous_letter_id": "Optional ID",
  "session_id": "Optional session ID"
}
```

### Response
```json
{
  "ID": "LET-20251022-12345",
  "content": "Generated letter content...",
  "category": "Official",
  "status": "success",
  ...
}
```

---

## How It Works

### 1. Authentication
- Token is extracted from `Authorization: Bearer <token>` header
- Token is decoded to extract:
  - `sheet_id` - User's Google Sheet ID
  - `user_email` - User's email
  - `client_id` - Client identifier

### 2. Load Instructions
- **Sheet Name:** `Instructions`
- **Columns:** `letterType`, `instructions`
- Searches for row where `letterType` matches the request's `letterType`
- Returns the `instructions` field

**Example Instructions Sheet:**
```
| letterType  | instructions                           |
|-------------|----------------------------------------|
| Official    | Write a formal letter in Arabic...     |
| Complaint   | Write a complaint letter...            |
| Request     | Write a professional request...        |
```

### 3. Load Template
- **Sheet Name:** `Templates`
- **Columns:** `templateType`, `templateBody`, `isActive`
- Searches for row where `templateType` matches and `isActive` is True
- Returns the `templateBody` field

**Example Templates Sheet:**
```
| templateType | templateBody              | isActive |
|--------------|---------------------------|----------|
| Official     | [Header]\n[Body]\n[Footer]| True     |
| Formal       | [Formal Letter Template]  | True     |
| Informal     | [Informal Template]       | False    |
```

### 4. Generate Letter
- Uses loaded instructions and template
- Combines with user's prompt and context
- Generates letter using AI service

---

## New Google Sheets Service Methods

### `get_instructions_by_type(sheet_id, letter_type)`
Fetches instructions from the Instructions sheet for a given letter type.

**Parameters:**
- `sheet_id` (str) - Google Sheet ID
- `letter_type` (str) - Type of letter

**Returns:**
- Instructions string if found
- None if not found or error

**Example:**
```python
instructions = sheets_service.get_instructions_by_type(
    sheet_id="1ABC...XYZ",
    letter_type="Official"
)
# Returns: "اكتب خطاباً رسمياً..."
```

### `get_template_by_type(sheet_id, template_type)`
Fetches active template from the Templates sheet for a given template type.

**Parameters:**
- `sheet_id` (str) - Google Sheet ID
- `template_type` (str) - Type of template

**Returns:**
- Template body string if found and active
- None if not found, inactive, or error

**Example:**
```python
template = sheets_service.get_template_by_type(
    sheet_id="1ABC...XYZ",
    template_type="Official"
)
# Returns: "[Header]\n[Body]\n[Footer]"
```

---

## Required Sheets Structure

### Instructions Sheet
**Columns:**
- `letterType` (str) - Type of letter
- `instructions` (str) - Writing instructions for this type

**Example:**
```
letterType | instructions
-----------|-------------------------------------------
Official   | اكتب خطاباً رسمياً باللغة العربية الفصحى
Complaint  | اكتب شكوى رسمية مفصلة وواضحة
Request    | اكتب طلب احترافي ومهذب
```

### Templates Sheet
**Columns:**
- `templateType` (str) - Type of template
- `templateBody` (str) - The template content
- `isActive` (boolean/string) - Whether this template is active

**Accepted values for `isActive`:**
- `True`, `true`, `TRUE`
- `Yes`, `yes`, `YES`, `نعم`
- `1`
- `صحيح`

**Example:**
```
templateType | templateBody           | isActive
-------------|------------------------|----------
Official     | [Header]               | True
Formal       | [Formal Template]      | True
Informal     | [Casual Template]      | False
```

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

### Missing sheet_id in Token
```json
HTTP 400
{
  "error": "معرف الجدول غير موجود في التوكن"
}
```

### Invalid Request Data
```json
HTTP 400
{
  "error": "بيانات الطلب غير صحيحة",
  "details": [...]
}
```

### Letter Generation Error
```json
HTTP 500
{
  "error": "خطأ في توليد الخطاب",
  "details": "..."
}
```

---

## Fallback Behavior

If instructions or template are not found in the sheets, the system uses defaults:

**Default Instructions:**
```
اكتب خطاباً رسمياً باللغة العربية
```

**Default Template:**
```
(Empty - letter generated without template)
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

### Step 2: Generate Letter
```bash
curl -X POST http://localhost:5000/api/v1/letter/generate \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "Official",
    "recipient": "John Doe",
    "prompt": "Please write a formal letter requesting a meeting",
    "is_first": true,
    "letterType": "Official"
  }'
```

---

## Logging

The system logs:
- User email and sheet ID at the start of request
- Letter type being processed
- Whether instructions/templates were found
- Any warnings or errors during the process

**Log Example:**
```
Letter generation request from user: user@domain.com, sheet: 1ABC...XYZ
Loaded instructions and template for letter type: Official
Letter generated successfully: LET-20251022-12345
```

---

## Benefits

✅ **User-Specific Configuration** - Each user's instructions and templates are loaded from their sheet
✅ **Secure** - Only authenticated users can generate letters
✅ **Flexible** - Instructions and templates can be updated without code changes
✅ **Active Management** - Only active templates are used
✅ **Fallback Support** - Defaults provided if sheets are missing data
✅ **Performance** - Parallel loading of data with caching
✅ **Audit Trail** - All requests logged with user info

---

## Integration Checklist

- ✅ Generate endpoint requires JWT authentication
- ✅ Sheet ID extracted from JWT token
- ✅ Instructions loaded from `Instructions` sheet
- ✅ Templates loaded from `Templates` sheet (only active)
- ✅ Fallback instructions provided
- ✅ Error handling for missing sheets
- ✅ Proper logging and audit trail

**The letter generation endpoint is now fully integrated with JWT authentication and user-specific configuration sheets!** 🎉
