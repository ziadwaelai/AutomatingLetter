# Validation and Create User Endpoints - Summary

## Overview
This document explains how the `/validate` and `/create-user` endpoints work with the correct return logic.

---

## 1. VALIDATE ENDPOINT (`/api/v1/user/validate`)

### Purpose
Validates user credentials (email + password) and returns a JWT token if successful.

### Request
```json
POST /api/v1/user/validate
{
  "email": "user@domain.com",
  "password": "userpassword"
}
```

### Service Method
`validate_user_credentials(email, password)` returns `(success, client_info, user_info)`

### Response Logic

| Scenario | Return Values | HTTP Status | Response |
|----------|--------------|-------------|----------|
| ✅ Valid credentials | `(True, client_info, user_info)` | 200 | Success + JWT token |
| ❌ Wrong password | `(False, client_info, user_info)` | 401 | "كلمة المرور غير صحيحة" |
| ❌ User not found | `(False, client_info, None)` | 404 | "المستخدم غير موجود" |
| ❌ No matching client | `(False, None, None)` | 400 | "لا يوجد عميل مطابق" |
| ❌ User inactive | `(False, client_info, user_info)` | 401 | User status not active |

### Validation Steps
1. ✓ Check if email domain matches a client (primary or extra domains)
2. ✓ Check if user exists in client's "Users" sheet
3. ✓ Check if user status is "active"
4. ✓ Verify password (supports both hashed and plain text)
5. ✓ Auto-rehash plain text passwords for security
6. ✓ Generate JWT token on success

### Success Response
```json
{
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "تم التحقق من المستخدم بنجاح"
}
```

### Error Responses

**No matching client (domain not found):**
```json
HTTP 400
{
  "status": "error",
  "message": "لا يمكن التحقق من المستخدم",
  "error": "لا يوجد عميل مطابق لهذا البريد الإلكتروني"
}
```

**User not found in Users sheet:**
```json
HTTP 404
{
  "status": "error",
  "message": "المستخدم غير موجود",
  "error": "البريد الإلكتروني غير مسجل"
}
```

**Wrong password:**
```json
HTTP 401
{
  "status": "error",
  "message": "كلمة المرور غير صحيحة",
  "error": "كلمة المرور غير صحيحة"
}
```

---

## 2. CREATE USER ENDPOINT (`/api/v1/user/create-user`)

### Purpose
Creates a new user account in the appropriate client's "Users" sheet.

### Request
```json
POST /api/v1/user/create-user
{
  "email": "newuser@domain.com",
  "password": "newpassword",
  "full_name": "John Doe"
}
```

### Service Method
`create_user(email, password, full_name)` returns `(success, client_info, user_info)`

### Response Logic

| Scenario | Return Values | HTTP Status | Response |
|----------|--------------|-------------|----------|
| ✅ User created | `(True, client_info, user_info)` | 201 | Success + user info |
| ❌ User already exists | `(False, client_info, user_info)` | 409 | "المستخدم موجود بالفعل" |
| ❌ No matching client | `(False, None, None)` | 400 | "لا يوجد عميل مطابق" |

### Creation Steps
1. ✓ Find client by email domain
2. ✓ Check if user already exists
3. ✓ Create "Users" worksheet if it doesn't exist
4. ✓ Hash the password using werkzeug
5. ✓ Add user with default role "user" and status "active"
6. ✓ Return user info

### New User Default Values
- **Role:** `user`
- **Status:** `active` (user can login immediately)
- **Password:** Hashed using `pbkdf2:sha256`
- **Created At:** ISO 8601 timestamp

### Success Response
```json
HTTP 201
{
  "status": "success",
  "message": "تم إنشاء المستخدم بنجاح",
  "user": {
    "email": "newuser@domain.com",
    "full_name": "John Doe",
    "role": "user",
    "status": "active",
    "created_at": "2025-10-22T10:30:00.000000"
  },
  "client": {
    "client_id": "client123",
    "display_name": "Example Company"
  }
}
```

### Error Responses

**User already exists:**
```json
HTTP 409
{
  "status": "error",
  "message": "المستخدم موجود بالفعل",
  "error": "البريد الإلكتروني مسجل مسبقاً"
}
```

**No matching client:**
```json
HTTP 400
{
  "status": "error",
  "message": "لا يمكن إنشاء المستخدم",
  "error": "لا يوجد عميل مطابق لهذا البريد الإلكتروني"
}
```

---

## Key Implementation Details

### Password Security
- ✅ New passwords are hashed using `werkzeug.security.generate_password_hash()`
- ✅ Password verification uses `check_password_hash()` for hashed passwords
- ✅ Backward compatibility: Plain text passwords are auto-detected and re-hashed
- ✅ Hash format: `pbkdf2:sha256:...`

### Client Lookup
- ✅ Matches email domain against `primaryDomain` field
- ✅ Also checks `extraDomains` field (comma or semicolon separated)
- ✅ Case-insensitive domain matching
- ✅ Results cached for 5 minutes (TTL: 300 seconds)

### User Sheet Structure
Required columns in "Users" worksheet:
- `email` - User email address
- `full_name` - User's full name
- `role` - User role (default: "user")
- `status` - Account status (default: "active")
- `created_at` - ISO timestamp
- `password` - Hashed password

---

## Testing the Endpoints

### Test Validate Endpoint
```bash
curl -X POST http://localhost:5000/api/v1/user/validate \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword"
  }'
```

### Test Create User Endpoint
```bash
curl -X POST http://localhost:5000/api/v1/user/create-user \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "newpassword123",
    "full_name": "Test User"
  }'
```

---

## Error Handling

Both endpoints use comprehensive error handling:
- ✓ Request validation (JSON format, required fields)
- ✓ Email format validation
- ✓ Service-level error catching
- ✓ Detailed logging for debugging
- ✓ User-friendly Arabic error messages
- ✓ Appropriate HTTP status codes

---

## Summary

✅ **VALIDATE endpoint** - Checks credentials and returns JWT token
✅ **CREATE USER endpoint** - Creates new users with hashed passwords
✅ Both endpoints use proper return value logic
✅ Clear differentiation between different error scenarios
✅ Secure password handling
✅ Ready for production use
