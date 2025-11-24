# Admin User Management Endpoints

All endpoints require **JWT Token** with **admin role**.

## 🆕 EmailMappings Auto-Management

**NEW**: Admin endpoints now automatically manage EmailMappings for public email domains (gmail.com, yahoo.com, outlook.com, etc.)

- ✅ **Create User**: Automatically adds EmailMapping if user has public email domain
- ✅ **Delete User**: Automatically removes EmailMapping if user has public email domain
- ✅ **Transparent**: No extra steps required by admin

**Supported Public Domains**: gmail.com, yahoo.com, outlook.com, hotmail.com, aol.com, icloud.com, live.com, msn.com, mail.com, protonmail.com, zoho.com

---

## 1. List All Users

```
GET /api/v1/user/admin/users
Authorization: Bearer <JWT_TOKEN>
```

**Response (200):**
```json
{
  "status": "success",
  "count": 3,
  "client_id": "CLI-002",
  "users": [
    {
      "email": "user@moe.gov.sa",
      "full_name": "User Name",
      "phone_number": "966551234567",
      "role": "user",
      "status": "active",
      "created_at": "2025-10-28T08:38:11"
    }
  ]
}
```

---

## 2. Create User

```
POST /api/v1/user/admin/users/create
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Payload:**
```json
{
  "email": "newuser@moe.gov.sa",
  "username": "New User",
  "phone_number": "966551234567",
  "password": "password123",
  "role": "user",
  "status": "inactive"
}
```

**Required Fields:** email, username, password
**Optional Fields:** phone_number
**Default Values:** role=user, status=inactive

**Response (201):**
```json
{
  "status": "success",
  "message": "تم إنشاء المستخدم بنجاح",
  "email": "newuser@moe.gov.sa",
  "username": "New User",
  "phone_number": "966551234567",
  "role": "user",
  "status": "inactive",
  "admin": "ziad2@moe.gov.sa"
}
```

### 🆕 Public Email Domain Support

When creating a user with a public email domain (gmail.com, yahoo.com, etc.), the system will:

1. Create the user in the admin's client sheet (Users worksheet)
2. **Automatically add EmailMapping** entry in Master Sheet
3. User can immediately login with their gmail/yahoo email

**Example**:
```json
{
  "email": "alice@gmail.com",
  "username": "Alice Smith",
  "password": "SecurePass123",
  "role": "admin",
  "status": "active"
}
```

**Behind the scenes**:
- User added to admin's client sheet → Users worksheet
- EmailMapping added → Master Sheet → EmailMappings worksheet
  - `alice@gmail.com` → `admin's sheet_id` → `admin's drive_id`
- Alice can now login with `alice@gmail.com`

---

## 3. Update User

```
POST /api/v1/user/admin/users/update
Authorization: Bearer <JWT_TOKEN>
X-User-Email: user@moe.gov.sa
Content-Type: application/json
```

**Payload (all fields optional):**
```json
{
  "username": "Updated Name",
  "phone_number": "966559999999",
  "password": "newpassword123",
  "role": "admin",
  "status": "active"
}
```

**Response (200):**
```json
{
  "status": "success",
  "message": "تم تحديث المستخدم بنجاح",
  "email": "user@moe.gov.sa",
  "updates": {
    "username": "Updated Name",
    "phone_number": "966559999999",
    "role": "admin",
    "status": "active"
  },
  "admin": "ziad2@moe.gov.sa"
}
```

---

## 4. Delete User

```
DELETE /api/v1/user/admin/users/delete
Authorization: Bearer <JWT_TOKEN>
X-User-Email: user@moe.gov.sa
```

**Response (200):**
```json
{
  "status": "success",
  "message": "تم حذف المستخدم بنجاح",
  "email": "user@moe.gov.sa",
  "admin": "ziad2@moe.gov.sa"
}
```

### 🆕 Public Email Domain Cleanup

When deleting a user with a public email domain (gmail.com, yahoo.com, etc.), the system will:

1. Delete the user from the admin's client sheet (Users worksheet)
2. **Automatically remove EmailMapping** entry from Master Sheet
3. User can no longer login

**Example**:
```
DELETE /api/v1/user/admin/users/delete
X-User-Email: alice@gmail.com
```

**Behind the scenes**:
- User deleted from admin's client sheet → Users worksheet
- EmailMapping removed → Master Sheet → EmailMappings worksheet
- `alice@gmail.com` entry is removed
- Alice can no longer login

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Invalid request (bad email, short password, missing fields) |
| 401 | No JWT token or expired token |
| 403 | JWT valid but user NOT admin |
| 404 | User or client not found |
| 409 | User already exists (create only) |
| 500 | Server error |

---

## Quick cURL Examples

**List Users:**
```bash
curl -X GET "http://localhost:5000/api/v1/user/admin/users" \
  -H "Authorization: Bearer <TOKEN>"
```

**Create User:**
```bash
curl -X POST "http://localhost:5000/api/v1/user/admin/users/create" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@moe.gov.sa","username":"User","password":"123456"}'
```

**Update User:**
```bash
curl -X POST "http://localhost:5000/api/v1/user/admin/users/update" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "X-User-Email: user@moe.gov.sa" \
  -H "Content-Type: application/json" \
  -d '{"role":"admin","status":"active"}'
```

**Delete User:**
```bash
curl -X DELETE "http://localhost:5000/api/v1/user/admin/users/delete" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "X-User-Email: user@moe.gov.sa"
```
