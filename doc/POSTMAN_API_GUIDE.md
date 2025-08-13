# 📮 AutomatingLetter - Postman API Testing Guide

## 🎯 Overview

This guide provides comprehensive instructions for testing the AutomatingLetter API using Postman. The API includes endpoints for chat sessions, letter generation, PDF conversion, archive management, and memory services.

---

## 🚀 Getting Started

### Base URL
```
http://localhost:5000
```

### Prerequisites
1. **Start the Application**: Run `python app.py`
2. **Postman Installed**: Download from [postman.com](https://www.postman.com/)
3. **Environment Setup**: Create Postman environment with base URL

### Postman Environment Variables
```
base_url: http://localhost:5000
session_id: {{session_id}} (will be set dynamically)
letter_id: {{letter_id}} (will be set dynamically)
pdf_id: {{pdf_id}} (will be set dynamically)
```

---

## 📝 API Endpoints Collection

### 1. **Chat Management APIs**

#### 1.1 Create New Chat Session
```http
POST {{base_url}}/api/v1/chat/session
Content-Type: application/json

{
    "user_id": "user123",
    "session_type": "letter_generation"
}
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "session_id": "session_20250813_141502",
        "user_id": "user123",
        "session_type": "letter_generation",
        "created_at": "2025-08-13T14:15:02.670002",
        "message_count": 0
    }
}
```

**Postman Test Script:**
```javascript
pm.test("Session created successfully", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.status).to.eql("success");
    pm.expect(response.data.session_id).to.exist;
    
    // Store session_id for subsequent requests
    pm.environment.set("session_id", response.data.session_id);
});
```

---

#### 1.2 Send Message to Session
```http
POST {{base_url}}/api/v1/chat/message
Content-Type: application/json

{
    "session_id": "{{session_id}}",
    "message": "أريد كتابة خطاب شكر للمدير العام بأسلوب رسمي ومختصر",
    "context": "formal_letter"
}
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "message_id": "msg_20250813_141503",
        "session_id": "session_20250813_141502",
        "response": "سأقوم بكتابة خطاب شكر رسمي ومختصر للمدير العام. هل تريد إضافة تفاصيل محددة في الخطاب؟",
        "timestamp": "2025-08-13T14:15:03.123456",
        "memory_learned": true
    }
}
```

**Postman Test Script:**
```javascript
pm.test("Message sent successfully", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.status).to.eql("success");
    pm.expect(response.data.response).to.exist;
    pm.expect(response.data.session_id).to.eql(pm.environment.get("session_id"));
});
```

---

#### 1.3 Get All Sessions
```http
GET {{base_url}}/api/v1/chat/sessions
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "sessions": [
            {
                "session_id": "session_20250813_141502",
                "user_id": "user123",
                "session_type": "letter_generation",
                "created_at": "2025-08-13T14:15:02.670002",
                "message_count": 1,
                "last_activity": "2025-08-13T14:15:03.123456"
            }
        ],
        "total_sessions": 1
    }
}
```

---

### 2. **Memory Service APIs**

#### 2.1 Get Memory Statistics
```http
GET {{base_url}}/api/v1/chat/memory/stats
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "total_instructions": 10,
        "active_instructions": 10,
        "instruction_types": {
            "style": 5,
            "format": 2,
            "content": 3
        },
        "memory_loading_time": 1.1,
        "last_updated": "2025-08-13T14:45:47.123456"
    }
}
```

**Postman Test Script:**
```javascript
pm.test("Memory stats retrieved", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.status).to.eql("success");
    pm.expect(response.data.total_instructions).to.be.a("number");
    pm.expect(response.data.instruction_types).to.be.an("object");
});
```

---

#### 2.2 Get Formatted Instructions
```http
GET {{base_url}}/api/v1/chat/memory/instructions
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "instructions": "# تعليمات المستخدم المحفوظة\n\n**تفضيلات الأسلوب:**\n• اكتب خطابات مختصرة\n• اكتب بأسلوب رسمي ومهذب\n\n**تفضيلات التنسيق:**\n• استخدم فقرات قصيرة في كل الخطابات\n\n**تفضيلات المحتوى:**\n• أضف دعوة للتواصل في نهاية كل خطاب",
        "category": null,
        "session_id": null,
        "instruction_count": 10
    }
}
```

---

### 3. **Letter Generation APIs**

#### 3.1 Generate New Letter
```http
POST {{base_url}}/api/v1/letters/generate
Content-Type: application/json

{
    "session_id": "{{session_id}}",
    "letter_type": "شكر",
    "recipient": "المدير العام",
    "sender": "أحمد محمد",
    "content_requirements": "خطاب شكر رسمي للمدير العام على الدعم المستمر",
    "style_preferences": "رسمي ومختصر",
    "additional_notes": "يرجى إضافة دعوة للتواصل في النهاية"
}
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "letter_id": "letter_20250813_141504",
        "session_id": "session_20250813_141502",
        "letter_content": "بسم الله الرحمن الرحيم\n\nسعادة المدير العام المحترم\n\nالسلام عليكم ورحمة الله وبركاته\n\nأتقدم إليكم بجزيل الشكر والامتنان على الدعم المستمر والتوجيه السديد...\n\nوتفضلوا بقبول فائق الاحترام والتقدير\n\nأحمد محمد",
        "metadata": {
            "letter_type": "شكر",
            "recipient": "المدير العام",
            "sender": "أحمد محمد",
            "word_count": 85,
            "generated_at": "2025-08-13T14:15:04.789012"
        }
    }
}
```

**Postman Test Script:**
```javascript
pm.test("Letter generated successfully", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.status).to.eql("success");
    pm.expect(response.data.letter_id).to.exist;
    pm.expect(response.data.letter_content).to.exist;
    
    // Store letter_id for subsequent requests
    pm.environment.set("letter_id", response.data.letter_id);
});
```

---

#### 3.2 Get Letter Content
```http
GET {{base_url}}/api/v1/letters/{{letter_id}}
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "letter_id": "letter_20250813_141504",
        "letter_content": "بسم الله الرحمن الرحيم\n\nسعادة المدير العام المحترم...",
        "metadata": {
            "letter_type": "شكر",
            "recipient": "المدير العام",
            "sender": "أحمد محمد",
            "word_count": 85,
            "generated_at": "2025-08-13T14:15:04.789012"
        }
    }
}
```

---

#### 3.3 Update Letter Content
```http
PUT {{base_url}}/api/v1/letters/{{letter_id}}
Content-Type: application/json

{
    "letter_content": "بسم الله الرحمن الرحيم\n\nسعادة المدير العام المحترم\n\nالسلام عليكم ورحمة الله وبركاته\n\nأتقدم إليكم بجزيل الشكر والامتنان على الدعم المتواصل...\n\nوتفضلوا بقبول فائق الاحترام والتقدير\n\nأحمد محمد",
    "update_reason": "تحسين المحتوى"
}
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "letter_id": "letter_20250813_141504",
        "updated": true,
        "word_count": 92,
        "updated_at": "2025-08-13T14:15:05.345678"
    }
}
```

---

### 4. **PDF Conversion APIs**

#### 4.1 Convert Letter to PDF
```http
POST {{base_url}}/api/v1/pdf/convert
Content-Type: application/json

{
    "letter_id": "{{letter_id}}",
    "pdf_options": {
        "page_size": "A4",
        "margin": "normal",
        "font_size": "12pt",
        "include_header": true,
        "include_footer": false
    }
}
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "pdf_id": "pdf_20250813_141506",
        "letter_id": "letter_20250813_141504",
        "pdf_url": "/api/v1/pdf/pdf_20250813_141506",
        "file_size": 245760,
        "pages": 1,
        "created_at": "2025-08-13T14:15:06.789012",
        "drive_file_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    }
}
```

**Postman Test Script:**
```javascript
pm.test("PDF converted successfully", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.status).to.eql("success");
    pm.expect(response.data.pdf_id).to.exist;
    pm.expect(response.data.pdf_url).to.exist;
    
    // Store pdf_id for subsequent requests
    pm.environment.set("pdf_id", response.data.pdf_id);
});
```

---

#### 4.2 Download PDF File
```http
GET {{base_url}}/api/v1/pdf/{{pdf_id}}
```

**Expected Response:**
- Content-Type: `application/pdf`
- Binary PDF file content

**Postman Test Script:**
```javascript
pm.test("PDF downloaded successfully", function () {
    pm.response.to.have.status(200);
    pm.expect(pm.response.headers.get("Content-Type")).to.include("application/pdf");
    pm.expect(pm.response.responseSize).to.be.above(1000); // PDF should be substantial
});
```

---

### 5. **Archive Management APIs**

#### 5.1 List Archived Letters
```http
GET {{base_url}}/api/v1/archive/letters?limit=10&offset=0
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "letters": [
            {
                "letter_id": "letter_20250813_141504",
                "letter_type": "شكر",
                "recipient": "المدير العام",
                "sender": "أحمد محمد",
                "created_at": "2025-08-13T14:15:04.789012",
                "word_count": 92,
                "has_pdf": true,
                "drive_file_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
            }
        ],
        "total_letters": 1,
        "limit": 10,
        "offset": 0
    }
}
```

---

#### 5.2 Get Specific Archived Letter
```http
GET {{base_url}}/api/v1/archive/letters/{{letter_id}}
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "letter_id": "letter_20250813_141504",
        "letter_content": "بسم الله الرحمن الرحيم...",
        "metadata": {
            "letter_type": "شكر",
            "recipient": "المدير العام",
            "sender": "أحمد محمد",
            "word_count": 92,
            "generated_at": "2025-08-13T14:15:04.789012",
            "updated_at": "2025-08-13T14:15:05.345678"
        },
        "pdf_info": {
            "pdf_id": "pdf_20250813_141506",
            "pdf_url": "/api/v1/pdf/pdf_20250813_141506",
            "drive_file_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        }
    }
}
```

---

#### 5.3 Delete Archived Letter
```http
DELETE {{base_url}}/api/v1/archive/letters/{{letter_id}}
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "letter_id": "letter_20250813_141504",
        "deleted": true,
        "deleted_at": "2025-08-13T14:15:07.123456"
    }
}
```

---

## 🧪 Complete Workflow Test

### Test Sequence for Full Workflow:

1. **Create Session** → Store `session_id`
2. **Send Message** → Memory learns preferences
3. **Generate Letter** → Store `letter_id`
4. **Convert to PDF** → Store `pdf_id`
5. **Download PDF** → Verify file
6. **Check Archive** → Verify storage
7. **Get Memory Stats** → Verify learning

### Postman Collection Runner:

Create a collection with all endpoints in sequence and run with:
- **Iterations**: 1
- **Delay**: 1000ms between requests
- **Data File**: Optional CSV with test data

---

## 🚫 Error Handling Test Cases

### 1. Invalid Session ID
```http
POST {{base_url}}/api/v1/chat/message
{
    "session_id": "invalid_session",
    "message": "Test message"
}
```

**Expected Response (400):**
```json
{
    "status": "error",
    "error": {
        "type": "ValidationError",
        "message": "Invalid session_id format",
        "code": "INVALID_SESSION"
    }
}
```

### 2. Missing Required Fields
```http
POST {{base_url}}/api/v1/letters/generate
{
    "session_id": "{{session_id}}"
    // Missing required fields
}
```

**Expected Response (400):**
```json
{
    "status": "error",
    "error": {
        "type": "ValidationError",
        "message": "Missing required fields: letter_type, recipient, sender",
        "code": "MISSING_FIELDS"
    }
}
```

### 3. Letter Not Found
```http
GET {{base_url}}/api/v1/letters/nonexistent_letter
```

**Expected Response (404):**
```json
{
    "status": "error",
    "error": {
        "type": "NotFoundError",
        "message": "Letter not found",
        "code": "LETTER_NOT_FOUND"
    }
}
```

---

## 📊 Performance Testing

### Load Testing Endpoints:

1. **High-Frequency Endpoints**:
   - `POST /api/v1/chat/message` (10 requests/second)
   - `GET /api/v1/chat/memory/stats` (5 requests/second)

2. **Resource-Intensive Endpoints**:
   - `POST /api/v1/letters/generate` (2 requests/second)
   - `POST /api/v1/pdf/convert` (1 request/second)

### Performance Assertions:
```javascript
pm.test("Response time is acceptable", function () {
    pm.expect(pm.response.responseTime).to.be.below(2000); // 2 seconds
});

pm.test("Memory usage is reasonable", function () {
    const response = pm.response.json();
    if (response.data.memory_loading_time) {
        pm.expect(response.data.memory_loading_time).to.be.below(5); // 5 seconds
    }
});
```

---

## 🔧 Environment Setup

### Postman Environment Variables:
```json
{
    "base_url": "http://localhost:5000",
    "session_id": "",
    "letter_id": "",
    "pdf_id": "",
    "user_id": "test_user_123",
    "api_timeout": "30000"
}
```

### Global Postman Scripts:

**Pre-request Script:**
```javascript
// Set timestamp for unique IDs
pm.globals.set("timestamp", Date.now());

// Set request timeout
pm.request.headers.add({
    key: "X-Request-Timeout",
    value: pm.environment.get("api_timeout")
});
```

**Test Script:**
```javascript
// Global response validation
pm.test("Response has correct structure", function () {
    const response = pm.response.json();
    pm.expect(response).to.have.property("status");
    pm.expect(response.status).to.be.oneOf(["success", "error"]);
});

// Global performance check
pm.test("Response time is reasonable", function () {
    pm.expect(pm.response.responseTime).to.be.below(5000);
});
```

---

## 📋 Checklist for Complete API Testing

### ✅ Basic Functionality:
- [ ] All endpoints return correct status codes
- [ ] Response formats match documentation
- [ ] Required fields validation works
- [ ] Optional parameters handled correctly

### ✅ Memory Service Testing:
- [ ] Instructions are learned from chat messages
- [ ] Memory stats reflect current state
- [ ] Formatted instructions are properly structured
- [ ] Duplicate detection works correctly

### ✅ Letter Generation Testing:
- [ ] Letters generated with correct Arabic formatting
- [ ] Memory preferences applied to generation
- [ ] Letter content meets requirements
- [ ] Metadata is properly stored

### ✅ PDF Conversion Testing:
- [ ] PDFs generated successfully from letters
- [ ] Arabic text renders correctly in PDF
- [ ] File sizes are reasonable
- [ ] Google Drive upload works

### ✅ Archive Management Testing:
- [ ] Letters stored in archive after generation
- [ ] Archive listing shows correct information
- [ ] Letter retrieval works correctly
- [ ] Deletion removes letters properly

### ✅ Error Handling Testing:
- [ ] Invalid inputs return appropriate errors
- [ ] Missing parameters handled gracefully
- [ ] Non-existent resources return 404
- [ ] Server errors return 500 with details

### ✅ Performance Testing:
- [ ] Response times within acceptable limits
- [ ] Memory service loads efficiently
- [ ] PDF generation completes in reasonable time
- [ ] Concurrent requests handled properly

---

**🎊 This comprehensive Postman guide covers all AutomatingLetter API endpoints with complete testing scenarios, error handling validation, and performance monitoring! 🎊**
