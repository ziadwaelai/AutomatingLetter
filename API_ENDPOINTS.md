# API Endpoints Documentation

## Authentication
**JWT Token from:** `POST /api/v1/user/validate`
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
**Response:**
```json
{
  "token": "eyJhbGc...",
  "sheet_id": "user_google_sheet_id",
  "google_drive_id": "user_drive_folder_id"
}
```

---

## Letter Generation

### 1. Generate Letter
```
POST /api/v1/letter/generate
Authorization: Bearer <JWT>
```
**Payload:**
```json
{
  "letterType": "Inquiry",
  "prompt": "Write letter about partnership",
  "recipient": "Ahmed Ali",
  "isFirst": true,
  "recipientJobTitle": "Manager"
}
```
**Response:** `200`
```json
{
  "ID": "LET-20250423-12345",
  "Title": "Partnership Request",
  "Letter": "بسم الله...",
  "Date": "23 أبريل 2025",
  "token_usage": 2500,
  "cost_usd": 0.05
}
```

### 2. Validate Letter
```
POST /api/v1/letter/validate
```
**Payload:**
```json
{"letter": "letter content..."}
```
**Response:** `200` (valid/invalid with suggestions)

### 3. Get Categories
```
GET /api/v1/letter/categories
```
**Response:** `200` (list of letter types)

### 4. Get Templates
```
GET /api/v1/letter/templates/<category>
```
**Response:** `200` (template & instructions)

---

## Chat & Sessions

### 1. Create Session
```
POST /api/v1/chat/sessions
```
**Payload:**
```json
{
  "initial_letter": "letter content...",
  "context": "additional context",
  "idempotency_key": "unique-key"
}
```
**Response:** `201`
```json
{
  "session_id": "session-uuid",
  "expires_in": 3600
}
```

### 2. Edit Letter (Chat)
```
POST /api/v1/chat/sessions/<session_id>/edit
```
**Payload:**
```json
{
  "user_message": "make it shorter",
  "context": "edit context"
}
```
**Response:** `200`
```json
{
  "edited_letter": "updated letter...",
  "session_id": "session-uuid"
}
```

### 3. Get Chat History
```
GET /api/v1/chat/sessions/<session_id>/history?limit=10&offset=0
```
**Response:** `200` (history with pagination)

### 4. Get Session Status
```
GET /api/v1/chat/sessions/<session_id>/status
```
**Response:** `200` (session metadata)

### 5. Extend Session
```
POST /api/v1/chat/sessions/<session_id>/extend
```
**Payload:**
```json
{"extend_minutes": 30}
```
**Response:** `200` (new expiration time)

### 6. Delete Session
```
DELETE /api/v1/chat/sessions/<session_id>
```
**Response:** `200` (deletion confirmation)

### 7. List Sessions
```
GET /api/v1/chat/sessions?include_expired=false
```
**Response:** `200` (list of sessions)

---

## User Management

### 1. Validate User (Login)
```
POST /api/v1/user/validate
```
**Payload:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
**Response:** `200`
```json
{
  "token": "jwt_token",
  "sheet_id": "xxx",
  "google_drive_id": "xxx"
}
```

### 2. Create User
```
POST /api/v1/user/create-user
```
**Payload:**
```json
{
  "email": "new@example.com",
  "password": "password123",
  "full_name": "User Name",
  "phone_number": "5551234567"
}
```
**Response:** `201` (user created)

### 3. Get Client Info
```
POST /api/v1/user/client
```
**Payload:**
```json
{"email": "user@example.com"}
```
**Response:** `200` (client details)

### 4. Get All Clients
```
GET /api/v1/user/clients
```
**Response:** `200` (list of clients)

---

## Archive & PDF

### 1. Archive Letter (Generate PDF)
```
POST /api/v1/archive/letter
Authorization: Bearer <JWT>
```
**Payload:**
```json
{
  "letter_content": "letter text...",
  "ID": "LET-20250423-12345",
  "letter_type": "Inquiry",
  "recipient": "Ahmed Ali",
  "title": "Partnership Request",
  "is_first": true
}
```
**Response:** `200` (async processing)
```json
{
  "status": "processing",
  "message": "PDF generation started",
  "processing": true
}
```

### 2. Get Archive Status
```
GET /api/v1/archive/status/<letter_id>
```
**Response:** `200` (status info)

### 3. Update Archived Letter
```
PUT /api/v1/archive/update
```
**Payload:**
```json
{
  "letter_id": "LET-20250423-12345",
  "content": "updated content..."
}
```
**Response:** `200` (async update)

---

## WhatsApp Integration

### 1. Send Letter via WhatsApp
```
POST /api/v1/whatsapp/send
```
**Payload:**
```json
{
  "phone_number": "966501234567",
  "letter_id": "LET-20250423-12345"
}
```
**Response:** `200` (sent confirmation)
```json
{
  "status": "sent",
  "message": "Letter sent successfully"
}
```

### 2. Update Status
```
POST /api/v1/whatsapp/update-status
```
**Payload:**
```json
{
  "phone_number": "966501234567",
  "status": "read"
}
```
**Response:** `200` (status updated)

### 3. Get Letter
```
GET /api/v1/whatsapp/letter/<letter_id>
```
**Response:** `200` (letter data)

### 4. Get Assigned Letter
```
GET /api/v1/whatsapp/assigned-letter/<phone_number>
```
**Response:** `200` (assigned letter ID)

---

## Submissions Data

### 1. Get All Submissions (Paginated)
```
GET /api/v1/submissions?page=1&page_size=10&sort_by=ID&sort_order=desc
Authorization: Bearer <JWT>
```
**Response:** `200`
```json
{
  "status": "success",
  "data": [
    {
      "ID": "LET-20250423-12345",
      "Timestamp": "2025-04-23 14:30:00",
      "Created_by": "user@example.com",
      "Letter_type": "Inquiry",
      "Recipient_name": "Ahmed Ali",
      "Subject": "Partnership Request",
      "Review_status": "Pending"
    }
  ],
  "pagination": {
    "current_page": 1,
    "page_size": 10,
    "total_pages": 15,
    "total_items": 150,
    "has_next": true,
    "has_prev": false
  }
}
```

### 2. Get Single Submission
```
GET /api/v1/submissions/<submission_id>
Authorization: Bearer <JWT>
```
**Response:** `200` (single submission)

### 3. Get Submissions Stats
```
GET /api/v1/submissions/stats
Authorization: Bearer <JWT>
```
**Response:** `200`
```json
{
  "status": "success",
  "data": {
    "total_submissions": 150,
    "by_review_status": {
      "Pending": 45,
      "Approved": 80,
      "Rejected": 20
    },
    "by_letter_type": {
      "Inquiry": 60,
      "Proposal": 40,
      "Other": 50
    }
  }
}
```

---

## Health Checks

All routes have `/health` endpoint:
- `GET /api/v1/letter/health`
- `GET /api/v1/chat/health`
- `GET /api/v1/archive/health`
- `GET /api/v1/user/health`

---

## Error Codes
| Code | Meaning |
|------|---------|
| `400` | Invalid request |
| `401` | Unauthorized |
| `403` | Forbidden |
| `404` | Not found |
| `409` | Conflict |
| `429` | Quota exceeded |
| `500` | Server error |

---

## Common Headers
```
Authorization: Bearer <jwt_token>  (required for protected endpoints)
Content-Type: application/json
X-Idempotency-Key: unique-key     (optional, for session creation)
```
