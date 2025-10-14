# WhatsApp Integration API Documentation

## Overview
The WhatsApp integration provides two endpoints for sending letters via WhatsApp and managing their status updates. The system uses a Google Sheets database with two main worksheets:

1. **WhatApp** sheet - Contains phone numbers and their assigned letter IDs
   - Columns: `Number`, `Name`, `Letter_id`
2. **Submissions** sheet - Contains letter data and status information
   - Contains letter content and metadata with `ID` and `Status` columns

## Endpoints

### 1. Send WhatsApp Letter
**POST** `/api/v1/whatsapp/send`

Sends a letter to a phone number via WhatsApp webhook.

#### Request Body
```json
{
    "phone_number": "1234567890",
    "letter_id": "LTR_20241014_001"
}
```

#### Flow
1. Checks if the phone number exists in the WhatApp sheet
2. Verifies the phone number doesn't already have a letter assigned
3. Assigns the letter_id to the phone number in WhatApp sheet
4. Retrieves letter data from Submissions sheet using the letter_id
5. Sends letter data to the webhook: `https://superpowerss.app.n8n.cloud/webhook/send`

#### Success Response (200)
```json
{
    "message": "Letter sent successfully via WhatsApp",
    "letter_id": "LTR_20241014_001",
    "phone_number": "1234567890",
    "webhook_status": 200
}
```

#### Error Responses
- **404**: Phone number not found in WhatApp sheet
- **409**: Phone number already assigned to another letter
- **404**: Letter not found in Submissions sheet
- **500**: Webhook delivery failed or database error

### 2. Update WhatsApp Status
**POST** `/api/v1/whatsapp/update-status`

Updates letter status and clears the WhatsApp assignment.

#### Request Body
```json
{
    "phone_number": "1234567890",
    "letter_id": "LTR_20241014_001",
    "status": "delivered"
}
```

#### Flow
1. Updates the Status column in Submissions sheet for the given letter_id
2. Clears the Letter_id from WhatApp sheet for the given phone_number

#### Success Response (200)
```json
{
    "message": "Status updated and WhatsApp assignment cleared successfully",
    "letter_id": "LTR_20241014_001",
    "phone_number": "1234567890",
    "new_status": "delivered",
    "submissions_updated": true,
    "whatsapp_cleared": true
}
```

#### Partial Success Response (200)
If status update succeeds but clearing WhatsApp assignment fails:
```json
{
    "message": "Status updated but failed to clear WhatsApp assignment",
    "letter_id": "LTR_20241014_001",
    "phone_number": "1234567890",
    "new_status": "delivered",
    "submissions_updated": true,
    "whatsapp_cleared": false,
    "warning": "Error message"
}
```

## Error Handling

All endpoints return proper HTTP status codes and detailed error messages:

### Common Error Response Format
```json
{
    "error": "Error type",
    "message": "Detailed error description"
}
```

### Validation Errors (400)
```json
{
    "error": "Validation error",
    "details": [
        {
            "field": "phone_number",
            "message": "ensure this value has at least 10 characters"
        }
    ]
}
```

## Database Schema Requirements

### WhatApp Sheet
| Column | Type | Description |
|--------|------|-------------|
| Number | String | Phone number (10-20 characters) |
| Name | String | Contact name |
| Letter_id | String | Assigned letter ID (empty when available) |

### Submissions Sheet
| Column | Type | Description |
|--------|------|-------------|
| ID | String | Unique letter identifier |
| Status | String | Current letter status |
| ... | ... | Other letter data fields |

## Security Considerations

1. **Phone Number Validation**: Ensures phone numbers are within valid length ranges
2. **Letter ID Validation**: Prevents empty or invalid letter IDs
3. **Database Transactions**: Implements rollback on webhook failures
4. **Error Logging**: Comprehensive logging for debugging and monitoring

## Usage Examples

### Using curl

#### Send Letter
```bash
curl -X POST http://localhost:5000/api/v1/whatsapp/send \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "1234567890",
    "letter_id": "LTR_20241014_001"
  }'
```

#### Update Status
```bash
curl -X POST http://localhost:5000/api/v1/whatsapp/update-status \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "1234567890",
    "letter_id": "LTR_20241014_001",
    "status": "delivered"
  }'
```

### Using Python requests
```python
import requests

# Send letter
response = requests.post(
    "http://localhost:5000/api/v1/whatsapp/send",
    json={
        "phone_number": "1234567890",
        "letter_id": "LTR_20241014_001"
    }
)

# Update status
response = requests.post(
    "http://localhost:5000/api/v1/whatsapp/update-status",
    json={
        "phone_number": "1234567890",
        "letter_id": "LTR_20241014_001",
        "status": "delivered"
    }
)