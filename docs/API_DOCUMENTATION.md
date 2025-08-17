# AutomatingLetter API Documentation

## Overview
The AutomatingLetter API is a modern, AI-powered letter generation system built with Flask. It provides comprehensive endpoints for letter generation, interactive editing, and archival to Google Drive.

**Version:** 2.0.0  
**Base URL:** `http://localhost:5000`

## Architecture
- **Backend:** Flask with modular service architecture
- **AI Integration:** OpenAI GPT-4 for Arabic letter generation
- **Storage:** Google Sheets & Google Drive integration
- **PDF Generation:** Enhanced PDF service with custom templates
- **Session Management:** Memory-based chat sessions for interactive editing

## Core Features
- 🤖 AI-powered Arabic letter generation
- 💬 Interactive chat-based letter editing
- 📄 PDF generation with custom templates
- 📁 Google Drive integration for archival
- 📊 Comprehensive logging and analytics
- 🔄 Session-based memory management

## Authentication
Currently, the API uses service account authentication for Google services. No user authentication is required for API endpoints.

## Error Handling
All endpoints return standardized error responses:
```json
{
  "error": "Error type",
  "message": "Detailed error message",
  "details": {...}, // Optional additional details
  "timestamp": "ISO timestamp"
}
```

## Rate Limiting
- Default request timeout: 30 seconds
- Max content length: 16MB
- Concurrent sessions: Up to 100 active chat sessions

## Health Monitoring
The API includes comprehensive health check endpoints at:
- `/health` - Overall service health
- `/api/v1/letter/health` - Letter generation service
- `/api/v1/chat/health` - Chat service
- `/api/v1/archive/health` - Archive service

---

# API Endpoints

## 1. Letter Generation Service (`/api/v1/letter`)

### Generate Letter
**POST** `/api/v1/letter/generate`

Generates a new Arabic letter based on user input and category templates.

**Request Body:**
```json
{
  "prompt": "اكتب خطاباً رسمياً للجامعة",
  "recipient": "عميد الجامعة",
  "category": "academic",
  "member_name": "أحمد محمد",
  "is_first": true,
  "recipient_title": "الأستاذ الدكتور",
  "recipient_job_title": "عميد كلية الهندسة",
  "organization_name": "جامعة الملك سعود",
  "previous_letter_content": "...",
  "previous_letter_id": "LETTER_12345"
}
```

**Response:**
```json
{
  "ID": "LETTER_20250817_001",
  "Title": "خطاب رسمي للجامعة",
  "Letter": "بسم الله الرحمن الرحيم...",
  "Date": "2025/08/17",
  "arabic_date": "1446/02/15",
  "metadata": {
    "word_count": 150,
    "character_count": 800,
    "category": "academic",
    "generation_time": 2.3
  }
}
```

### Validate Letter
**POST** `/api/v1/letter/validate`

Validates letter content for quality and Arabic writing standards.

**Request Body:**
```json
{
  "letter": "بسم الله الرحمن الرحيم\nالسلام عليكم..."
}
```

**Response:**
```json
{
  "status": "success",
  "validation": {
    "is_valid": true,
    "checks": {
      "has_arabic_content": true,
      "has_bismillah": true,
      "has_greeting": true,
      "sufficient_length": true
    },
    "metrics": {
      "word_count": 45,
      "character_count": 250,
      "line_count": 8
    },
    "suggestions": []
  }
}
```

### Get Letter Categories
**GET** `/api/v1/letter/categories`

Returns available letter categories.

**Response:**
```json
{
  "status": "success",
  "categories": [
    {
      "value": "academic",
      "display_name": "academic",
      "description": "فئة academic"
    },
    {
      "value": "business",
      "display_name": "business", 
      "description": "فئة business"
    }
  ]
}
```

### Get Letter Template
**GET** `/api/v1/letter/templates/{category}`

Retrieves template information for a specific category.

**Response:**
```json
{
  "status": "success",
  "template": {
    "category": "academic",
    "reference_letter": "نموذج الخطاب المرجعي...",
    "instructions": "تعليمات كتابة الخطاب...",
    "has_template": true
  }
}
```

---

## 2. Chat Service (`/api/v1/chat`)

### Create Chat Session
**POST** `/api/v1/chat/sessions`

Creates a new chat session for interactive letter editing.

**Request Body (Optional):**
```json
{
  "initial_letter": "محتوى الخطاب الأولي...",
  "context": "سياق إضافي للجلسة..."
}
```

**Response:**
```json
{
  "status": "success",
  "session_id": "session_20250817_001",
  "message": "Chat session created successfully",
  "expires_in": 1800
}
```

### Edit Letter via Chat
**POST** `/api/v1/chat/sessions/{session_id}/edit`

Edits letter content through conversational interface.

**Request Body:**
```json
{
  "message": "اجعل الخطاب أكثر رسمية",
  "current_letter": "محتوى الخطاب الحالي...",
  "editing_instructions": "تعليمات التحرير الإضافية",
  "preserve_formatting": true
}
```

**Response:**
```json
{
  "updated_letter": "النسخة المحدثة من الخطاب...",
  "response_text": "تم تحديث الخطاب ليكون أكثر رسمية...",
  "session_id": "session_20250817_001",
  "changes_made": [
    "إضافة عبارات رسمية",
    "تحسين البناء اللغوي"
  ]
}
```

### Get Chat History
**GET** `/api/v1/chat/sessions/{session_id}/history`

Retrieves chat history for a session.

**Query Parameters:**
- `limit` (optional): Number of messages (default: 50, max: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
  "status": "success",
  "session_id": "session_20250817_001",
  "history": [
    {
      "timestamp": "2025-08-17T10:30:00Z",
      "user_message": "اجعل الخطاب أكثر رسمية",
      "ai_response": "تم تحديث الخطاب...",
      "letter_version": "النسخة المحدثة..."
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 5
  }
}
```

### Get Session Status
**GET** `/api/v1/chat/sessions/{session_id}/status`

Gets current status of a chat session.

**Response:**
```json
{
  "status": "success",
  "session_info": {
    "session_id": "session_20250817_001",
    "created_at": "2025-08-17T10:00:00Z",
    "expires_at": "2025-08-17T10:30:00Z",
    "message_count": 5,
    "is_active": true
  }
}
```

### Delete Chat Session
**DELETE** `/api/v1/chat/sessions/{session_id}`

Deletes a chat session and clears its data.

**Response:**
```json
{
  "status": "success",
  "message": "Session deleted successfully",
  "session_id": "session_20250817_001"
}
```

### List Active Sessions
**GET** `/api/v1/chat/sessions`

Lists all active chat sessions.

**Query Parameters:**
- `include_expired` (optional): Include expired sessions (default: false)

**Response:**
```json
{
  "status": "success",
  "sessions": [
    {
      "session_id": "session_20250817_001",
      "created_at": "2025-08-17T10:00:00Z",
      "expires_at": "2025-08-17T10:30:00Z",
      "is_active": true
    }
  ],
  "total": 1,
  "include_expired": false
}
```

### Extend Session
**POST** `/api/v1/chat/sessions/{session_id}/extend`

Extends a chat session's expiration time.

**Request Body (Optional):**
```json
{
  "extend_minutes": 30
}
```

**Response:**
```json
{
  "status": "success",
  "session_id": "session_20250817_001",
  "new_expiration": "2025-08-17T11:00:00Z",
  "message": "Session extended successfully"
}
```

### Manual Cleanup
**POST** `/api/v1/chat/cleanup`

Manually triggers cleanup of expired sessions.

**Response:**
```json
{
  "status": "success",
  "cleanup_results": {
    "sessions_cleaned": 3,
    "memory_freed": "15MB"
  }
}
```

### Get Memory Stats
**GET** `/api/v1/chat/memory/stats`

Retrieves memory service statistics.

**Response:**
```json
{
  "status": "success",
  "data": {
    "total_instructions": 150,
    "categories": {
      "academic": 50,
      "business": 45,
      "general": 55
    },
    "memory_usage": "25MB",
    "last_updated": "2025-08-17T10:00:00Z"
  }
}
```

### Get Memory Instructions
**GET** `/api/v1/chat/memory/instructions`

Gets formatted memory instructions for a category/session.

**Query Parameters:**
- `category` (optional): Letter category
- `session_id` (optional): Session ID

**Response:**
```json
{
  "status": "success",
  "data": {
    "instructions": "تعليمات مُجمّعة للذاكرة...",
    "category": "academic",
    "session_id": "session_20250817_001"
  }
}
```

---

## 3. Archive Service (`/api/v1/archive`)

### Archive Letter
**POST** `/api/v1/archive/letter`

Archives letter to PDF, uploads to Google Drive, and logs to sheets. Process runs in background.

**Request Body:**
```json
{
  "letter_content": "محتوى الخطاب الكامل...",
  "ID": "LETTER_20250817_001",
  "letter_type": "academic",
  "recipient": "عميد الجامعة",
  "title": "خطاب رسمي للجامعة",
  "is_first": true,
  "template": "default_template",
  "username": "أحمد محمد"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Letter archiving started for ID: LETTER_20250817_001",
  "processing": "background",
  "letter_id": "LETTER_20250817_001"
}
```

### Get Archive Status
**GET** `/api/v1/archive/status/{letter_id}`

Gets archiving status for a letter.

**Response:**
```json
{
  "letter_id": "LETTER_20250817_001",
  "status": "processing",
  "message": "Archive status tracking not implemented yet"
}
```

---

## 4. System Endpoints

### Root Endpoint
**GET** `/`

Returns API information and available endpoints.

**Response:**
```json
{
  "service": "Automating Letter Creation API",
  "version": "2.0.0",
  "status": "running",
  "timestamp": "2025-08-17T10:00:00Z",
  "endpoints": {
    "health": "/health",
    "letter_generation": "/api/v1/letter",
    "chat_editing": "/api/v1/chat",
    "pdf_generation": "/api/v1/pdf",
    "archive": "/api/v1/archive"
  },
  "documentation": {
    "swagger": "/api/docs",
    "postman": "See README.md for Postman collection"
  }
}
```

### Health Check
**GET** `/health`

Comprehensive health check for all services.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-17T10:00:00Z",
  "services": {
    "letter_service": "healthy",
    "chat_service": "healthy",
    "pdf_service": "healthy",
    "sheets_service": "healthy"
  },
  "version": "2.0.0"
}
```

---

## Environment Configuration

### Required Environment Variables
```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Google Services
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id

# Server Configuration  
HOST=localhost
PORT=5000
DEBUG_MODE=true
CORS_ORIGINS=*

# Security
SECRET_KEY=your_secret_key

# Feature Flags
ENABLE_CHAT=true
ENABLE_PDF=true
ENABLE_DRIVE=true
ENABLE_LEGACY_ENDPOINTS=true

# Logging
LOG_LEVEL=INFO
LOG_REQUESTS=true
```

### Optional Environment Variables
```bash
# Performance
MAX_WORKERS=4
REQUEST_TIMEOUT=30

# Chat Settings
CHAT_SESSION_TIMEOUT=30
CHAT_MAX_MEMORY_SIZE=10
```

---

## Data Models

### Letter Generation Request
```json
{
  "prompt": "string (required)",
  "recipient": "string (required)",
  "category": "string (required)",
  "member_name": "string (optional)",
  "is_first": "boolean (optional, default: true)",
  "recipient_title": "string (optional)",
  "recipient_job_title": "string (optional)", 
  "organization_name": "string (optional)",
  "previous_letter_content": "string (optional)",
  "previous_letter_id": "string (optional)"
}
```

### Chat Edit Request
```json
{
  "message": "string (required)",
  "current_letter": "string (required)",
  "editing_instructions": "string (optional)",
  "preserve_formatting": "boolean (optional, default: true)"
}
```

### Archive Letter Request
```json
{
  "letter_content": "string (required)",
  "ID": "string (required)",
  "letter_type": "string (optional, default: 'General')",
  "recipient": "string (optional)",
  "title": "string (optional, default: 'undefined')",
  "is_first": "boolean (optional, default: false)",
  "template": "string (optional, default: 'default_template')",
  "username": "string (optional, default: 'unknown')"
}
```

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 201 | Created (e.g., new chat session) |
| 400 | Bad Request (validation errors) |
| 404 | Not Found (session/endpoint not found) |
| 405 | Method Not Allowed |
| 413 | Request Entity Too Large (file size limit) |
| 429 | Too Many Requests (rate limiting) |
| 500 | Internal Server Error |
| 503 | Service Unavailable (health check failed) |

---

## Logging and Monitoring

The API includes comprehensive logging:
- Request/response logging
- Performance metrics
- Error tracking with context
- Service health monitoring
- Memory usage statistics

Logs are written to:
- Console output (development)
- `logs/app.log` (file-based logging)
- Google Sheets (for letter submissions)

---

## Development Setup

1. **Clone the repository**
2. **Install dependencies:** `pip install -r requirements.txt`
3. **Set environment variables** (see configuration section)
4. **Run the application:** `python app.py`

The API will be available at `http://localhost:5000`

---

## Production Deployment

For production deployment:
1. Use WSGI server like Gunicorn
2. Set `FLASK_ENV=production`
3. Configure proper logging
4. Set up health monitoring
5. Enable rate limiting
6. Secure API keys and secrets

Example Gunicorn command:
```bash
gunicorn --workers 4 --bind 0.0.0.0:5000 app:get_app
```
