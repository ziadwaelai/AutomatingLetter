# User Management API - Testing Guide

This document provides complete API endpoint documentation and Postman test examples for the User Management Service.

## Base URL
```
http://localhost:5000/api/v1/user
```

## Endpoints Overview

1. **POST** `/validate` - Validate user access by email
2. **POST** `/client` - Get client information by email
3. **GET** `/clients` - Get all clients (admin endpoint)
4. **POST** `/cache/clear` - Clear cache (admin endpoint)
5. **GET** `/health` - Health check endpoint

---

## 1. Validate User Access

**Endpoint:** `POST /api/v1/user/validate`

**Description:** Validates if a user email has access and returns associated client information.

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "has_access": true,
  "message": "تم التحقق من المستخدم بنجاح",
  "client": {
    "client_id": "client_001",
    "display_name": "Example Company",
    "primary_domain": "example.com",
    "extra_domains": ["example.org", "example.net"],
    "sheet_id": "1ABC123...",
    "google_drive_id": "1XYZ789...",
    "sheet_url": "https://docs.google.com/spreadsheets/d/...",
    "admin_email": "admin@example.com",
    "created_at": "2024-01-15",
    "letter_template": "template_1",
    "letter_type": "official"
  }
}
```

**Error Response (403 - Access Denied):**
```json
{
  "status": "error",
  "has_access": false,
  "message": "المستخدم غير مصرح له بالوصول",
  "error": "لا يوجد عميل مطابق لهذا البريد الإلكتروني"
}
```

**Error Response (400 - Bad Request):**
```json
{
  "error": "البريد الإلكتروني مطلوب"
}
```

**Error Response (400 - Invalid Format):**
```json
{
  "error": "صيغة البريد الإلكتروني غير صحيحة"
}
```

### Postman Test Examples:

**Test 1: Valid Email**
```json
POST http://localhost:5000/api/v1/user/validate
Content-Type: application/json

{
  "email": "john@company.com"
}
```

**Test 2: Invalid Email Format**
```json
POST http://localhost:5000/api/v1/user/validate
Content-Type: application/json

{
  "email": "invalid-email-format"
}
```

**Test 3: Email Not in Master Sheet**
```json
POST http://localhost:5000/api/v1/user/validate
Content-Type: application/json

{
  "email": "user@unknown-domain.com"
}
```

---

## 2. Get Client Information

**Endpoint:** `POST /api/v1/user/client`

**Description:** Retrieves client information (Sheet ID, Drive ID, etc.) for a given user email.

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "client": {
    "client_id": "client_001",
    "display_name": "Example Company",
    "primary_domain": "example.com",
    "extra_domains": ["example.org"],
    "sheet_id": "1ABC123...",
    "google_drive_id": "1XYZ789...",
    "sheet_url": "https://docs.google.com/spreadsheets/d/...",
    "admin_email": "admin@example.com",
    "created_at": "2024-01-15",
    "letter_template": "template_1",
    "letter_type": "official"
  }
}
```

**Error Response (404 - Not Found):**
```json
{
  "status": "error",
  "message": "لا يوجد عميل مطابق لهذا البريد الإلكتروني"
}
```

**Error Response (400 - Missing Email):**
```json
{
  "error": "البريد الإلكتروني مطلوب"
}
```

### Postman Test Examples:

**Test 1: Get Client Info**
```json
POST http://localhost:5000/api/v1/user/client
Content-Type: application/json

{
  "email": "admin@mycompany.com"
}
```

**Test 2: Client Not Found**
```json
POST http://localhost:5000/api/v1/user/client
Content-Type: application/json

{
  "email": "user@nonexistent-domain.com"
}
```

---

## 3. Get All Clients

**Endpoint:** `GET /api/v1/user/clients`

**Description:** Returns a list of all clients from the master sheet (Admin endpoint).

**Headers:**
```
Content-Type: application/json
```

**Request Body:** None (GET request)

**Success Response (200):**
```json
{
  "status": "success",
  "count": 3,
  "clients": [
    {
      "client_id": "client_001",
      "display_name": "Company A",
      "primary_domain": "companya.com",
      "extra_domains": ["companya.org"],
      "sheet_id": "1ABC123...",
      "google_drive_id": "1XYZ789...",
      "sheet_url": "https://docs.google.com/spreadsheets/d/...",
      "admin_email": "admin@companya.com",
      "created_at": "2024-01-15",
      "letter_template": "template_1",
      "letter_type": "official"
    },
    {
      "client_id": "client_002",
      "display_name": "Company B",
      "primary_domain": "companyb.com",
      "extra_domains": [],
      "sheet_id": "1DEF456...",
      "google_drive_id": "1UVW012...",
      "sheet_url": "https://docs.google.com/spreadsheets/d/...",
      "admin_email": "admin@companyb.com",
      "created_at": "2024-02-20",
      "letter_template": "template_2",
      "letter_type": "formal"
    }
  ]
}
```

### Postman Test Example:

```
GET http://localhost:5000/api/v1/user/clients
```

---

## 4. Clear Cache

**Endpoint:** `POST /api/v1/user/cache/clear`

**Description:** Clears the user management cache to force fresh data retrieval (Admin endpoint).

**Headers:**
```
Content-Type: application/json
```

**Request Body:** None

**Success Response (200):**
```json
{
  "status": "success",
  "message": "تم مسح ذاكرة التخزين المؤقت بنجاح"
}
```

### Postman Test Example:

```json
POST http://localhost:5000/api/v1/user/cache/clear
Content-Type: application/json
```

---

## 5. Health Check

**Endpoint:** `GET /api/v1/user/health`

**Description:** Check the health status of the user management service.

**Headers:**
```
Content-Type: application/json
```

**Request Body:** None (GET request)

**Success Response (200):**
```json
{
  "status": "healthy",
  "service": "user_management",
  "stats": {
    "service": "UserManagementService",
    "master_sheet_id": "11eCtNuW4cl03TX0G20alx3_6B5DI7IbpQPnPDeRGKlI",
    "cache_size": 5,
    "cache_ttl_seconds": 300,
    "last_connection": 1704123456.789,
    "connection_lifetime": 3600
  }
}
```

**Error Response (503 - Service Unhealthy):**
```json
{
  "status": "unhealthy",
  "error": "Error message here"
}
```

### Postman Test Example:

```
GET http://localhost:5000/api/v1/user/health
```

---

## Complete Postman Collection

Here's a complete Postman collection JSON you can import:

```json
{
  "info": {
    "name": "User Management API",
    "description": "API endpoints for user management and client lookup",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Validate User Access",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"email\": \"user@example.com\"\n}"
        },
        "url": {
          "raw": "http://localhost:5000/api/v1/user/validate",
          "protocol": "http",
          "host": ["localhost"],
          "port": "5000",
          "path": ["api", "v1", "user", "validate"]
        }
      }
    },
    {
      "name": "Get Client Info",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"email\": \"user@example.com\"\n}"
        },
        "url": {
          "raw": "http://localhost:5000/api/v1/user/client",
          "protocol": "http",
          "host": ["localhost"],
          "port": "5000",
          "path": ["api", "v1", "user", "client"]
        }
      }
    },
    {
      "name": "Get All Clients",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "http://localhost:5000/api/v1/user/clients",
          "protocol": "http",
          "host": ["localhost"],
          "port": "5000",
          "path": ["api", "v1", "user", "clients"]
        }
      }
    },
    {
      "name": "Clear Cache",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "url": {
          "raw": "http://localhost:5000/api/v1/user/cache/clear",
          "protocol": "http",
          "host": ["localhost"],
          "port": "5000",
          "path": ["api", "v1", "user", "cache", "clear"]
        }
      }
    },
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "http://localhost:5000/api/v1/user/health",
          "protocol": "http",
          "host": ["localhost"],
          "port": "5000",
          "path": ["api", "v1", "user", "health"]
        }
      }
    }
  ]
}
```

---

## Master Sheet Structure

The master sheet should have the following columns:

| Column Name | Description | Example |
|------------|-------------|---------|
| clientId | Unique client identifier | client_001 |
| displayName | Client display name | Example Company |
| primaryDomain | Primary email domain | example.com |
| extraDomains | Additional domains (comma/semicolon separated) | example.org,example.net |
| sheetId | Google Sheets ID for client | 1ABC123... |
| GoogleDriveId | Google Drive folder ID | 1XYZ789... |
| sheeturl | Direct link to sheet | https://docs.google.com/... |
| admin email | Admin contact email | admin@example.com |
| createdAt | Creation date | 2024-01-15 |
| letter template | Template identifier | template_1 |
| letter type | Type of letters | official |

**Master Sheet ID:** `11eCtNuW4cl03TX0G20alx3_6B5DI7IbpQPnPDeRGKlI`

---

## How It Works

1. **Email Validation:**
   - User provides email address
   - System extracts domain from email (e.g., `user@example.com` → `example.com`)
   - System searches master sheet for matching `primaryDomain` or `extraDomains`
   - If match found, returns client information
   - If no match, returns access denied

2. **Caching:**
   - Results are cached for 5 minutes (300 seconds)
   - Reduces Google Sheets API calls
   - Cache can be cleared manually via `/cache/clear` endpoint

3. **Multiple Domains:**
   - Each client can have one primary domain
   - Each client can have multiple extra domains (comma or semicolon separated)
   - Any matching domain grants access to that client's resources

---

## Testing Workflow

1. **Start the server:**
   ```bash
   python app.py
   ```

2. **Test health endpoint first:**
   ```
   GET http://localhost:5000/api/v1/user/health
   ```

3. **Get all clients to see available domains:**
   ```
   GET http://localhost:5000/api/v1/user/clients
   ```

4. **Test validation with a real email from the list:**
   ```json
   POST http://localhost:5000/api/v1/user/validate
   {
     "email": "user@[domain-from-step-3]"
   }
   ```

5. **Get client info:**
   ```json
   POST http://localhost:5000/api/v1/user/client
   {
     "email": "user@[domain-from-step-3]"
   }
   ```

6. **Test with invalid email:**
   ```json
   POST http://localhost:5000/api/v1/user/validate
   {
     "email": "user@invalid-domain.com"
   }
   ```

---

## Error Codes

| Status Code | Description |
|------------|-------------|
| 200 | Success |
| 400 | Bad Request (missing or invalid data) |
| 403 | Forbidden (user not authorized) |
| 404 | Not Found (client not found) |
| 500 | Internal Server Error |
| 503 | Service Unhealthy |

---

## Notes

- All endpoints return JSON responses
- Email addresses are case-insensitive
- Domains are matched case-insensitively
- Cache TTL is 5 minutes (300 seconds)
- Master sheet is accessed in real-time when cache expires
- Connection to Google Sheets is reused for 1 hour
