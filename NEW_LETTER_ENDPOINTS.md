# New Letter Endpoints

## 1. GET Letter by ID

**Endpoint:** `GET /api/v1/letter/{letter_id}`

**Header:**
```
Authorization: Bearer <jwt_token>
```

**URL Example:**
```
GET http://localhost:5000/api/v1/letter/LET-20251028-12345
```

**Response (200 - Success):**
```json
{
  "status": "success",
  "letter": {
    "ID": "LET-20251028-12345",
    "Timestamp": "2025-10-28 10:30:45",
    "Created_by": "user@moe.gov.sa",
    "Letter_type": "خطاب جديد",
    "Recipient_name": "Minister Name",
    "Subject": "Letter Title",
    "Letter_content": "Full letter text..."
  }
}
```

**Error Responses:**
- `404` - Letter not found
- `403` - Not authorized (letter created by another user)
- `400` - Invalid letter ID format or missing sheet_id

---

## 2. DELETE Letter by ID

**Endpoint:** `DELETE /api/v1/letter/{letter_id}`

**Header:**
```
Authorization: Bearer <jwt_token>
```

**URL Example:**
```
DELETE http://localhost:5000/api/v1/letter/LET-20251028-12345
```

**Response (200 - Success):**
```json
{
  "status": "success",
  "message": "تم حذف الخطاب بنجاح",
  "letter_id": "LET-20251028-12345"
}
```

**Error Responses:**
- `404` - Letter not found
- `403` - Not authorized (only creator can delete)
- `400` - Invalid letter ID format or missing sheet_id

---

## JWT Token

The token must contain:

```json
{
  "sheet_id": "user-google-sheet-id",
  "user": {
    "email": "user@moe.gov.sa"
  }
}
```

---

## Example Requests

### cURL

```bash
# GET letter
curl -X GET "http://localhost:5000/api/v1/letter/LET-20251028-12345" \
  -H "Authorization: Bearer <jwt_token>"

# DELETE letter
curl -X DELETE "http://localhost:5000/api/v1/letter/LET-20251028-12345" \
  -H "Authorization: Bearer <jwt_token>"
```
## Notes

- Both endpoints require valid JWT token
- Any authenticated user can access and delete any letter
- Letter ID format: `LET-YYYYMMDD-XXXXX`
- All errors return status: "error"
