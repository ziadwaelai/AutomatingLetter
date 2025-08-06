# 🧪 Complete Postman Testing Guide for AutomatingLetter API

## 📋 Overview
This guide provides comprehensive testing instructions for the AutomatingLetter refactored backend API using Postman. All endpoints are fully documented with request examples, expected responses, and error scenarios.

## 🚀 Quick Setup

### 1. Import Environment Variables
Create a new Postman environment with these variables:
```json
{
  "baseUrl": "http://localhost:5000",
  "session_id": "",
  "letter_id": "",
  "archive_id": ""
}
```

### 2. Start the Server
```bash
cd d:\shobbak\AutomatingLetter
python new_app.py
```

The server will start on `http://localhost:5000`

## 📊 API Endpoints Testing

### 🏠 **Basic Health & Info**

#### 1. Root Endpoint
- **Method**: `GET`
- **URL**: `{{baseUrl}}/`
- **Description**: Get API information and available endpoints

**Expected Response:**
```json
{
  "service": "Automating Letter Creation API",
  "version": "2.0.0",
  "status": "running",
  "timestamp": "2024-12-12T10:30:00Z",
  "endpoints": {
    "health": "/health",
    "letter_generation": "/api/v1/letter",
    "chat_editing": "/api/v1/chat",
    "archive": "/api/v1/archive"
  }
}
```

#### 2. Health Check
- **Method**: `GET`
- **URL**: `{{baseUrl}}/health`
- **Description**: Check overall system health

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-12T10:30:00Z",
  "services": {
    "letter_service": "healthy",
    "chat_service": "healthy",
    "archive_service": "healthy",
    "sheets_service": "healthy"
  },
  "version": "2.0.0"
}
```

---

### 📝 **Letter Generation API** (`/api/v1/letter/`)

#### 3. Generate Letter
- **Method**: `POST`
- **URL**: `{{baseUrl}}/api/v1/letter/generate`
- **Headers**: `Content-Type: application/json`

**Request Body:**
```json
{
  "category": "General",
  "recipient": "أحمد محمد علي",
  "prompt": "أود كتابة خطاب شكر وتقدير للمساعدة المقدمة في المشروع الأخير",
  "is_first": true,
  "member_name": "سعد بن عبدالله العتيبي",
  "recipient_title": "الأستاذ الفاضل",
  "recipient_job_title": "مدير المشاريع",
  "organization_name": "شركة الرؤية المستقبلية"
}
```

**Expected Response:**
```json
{
  "ID": "LET-20241212-abc123",
  "Title": "خطاب شكر وتقدير",
  "Letter": "بسم الله الرحمن الرحيم\n\nالأستاذ الفاضل أحمد محمد علي\nمدير المشاريع\nشركة الرؤية المستقبلية\n\nالسلام عليكم ورحمة الله وبركاته\n\nيسرني أن أتقدم إليكم بأسمى آيات الشكر والتقدير...",
  "Date": "2024-12-12"
}
```

**Test Script (Add to Tests tab):**
```javascript
pm.test("Letter generation successful", function () {
    pm.response.to.have.status(200);
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("ID");
    pm.expect(jsonData).to.have.property("Letter");
    pm.expect(jsonData.ID).to.include("LET-");
    
    // Store letter ID for later use
    pm.environment.set("letter_id", jsonData.ID);
});
```

#### 4. Validate Letter Content
- **Method**: `POST`
- **URL**: `{{baseUrl}}/api/v1/letter/validate`
- **Headers**: `Content-Type: application/json`

**Request Body:**
```json
{
  "letter": "بسم الله الرحمن الرحيم\n\nالسلام عليكم ورحمة الله وبركاته\n\nأتقدم إليكم بهذا الخطاب للتعبير عن شكري وتقديري"
}
```

**Expected Response:**
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
      "word_count": 15,
      "character_count": 120,
      "line_count": 4
    },
    "suggestions": []
  }
}
```

#### 5. Get Letter Categories
- **Method**: `GET`
- **URL**: `{{baseUrl}}/api/v1/letter/categories`

**Expected Response:**
```json
{
  "status": "success",
  "categories": [
    {
      "value": "General",
      "display_name": "General",
      "description": "فئة General"
    },
    {
      "value": "President",
      "display_name": "President", 
      "description": "فئة President"
    }
  ]
}
```

#### 6. Get Letter Template
- **Method**: `GET`
- **URL**: `{{baseUrl}}/api/v1/letter/templates/General`

**Expected Response:**
```json
{
  "status": "success",
  "template": {
    "category": "General",
    "reference_letter": "نموذج الخطاب...",
    "instructions": "اكتب خطاباً رسمياً باللغة العربية",
    "has_template": true
  }
}
```

#### 7. Letter Service Health
- **Method**: `GET`
- **URL**: `{{baseUrl}}/api/v1/letter/health`

---

### 💬 **Chat Editing API** (`/api/v1/chat/`)

#### 8. Create Chat Session
- **Method**: `POST`
- **URL**: `{{baseUrl}}/api/v1/chat/sessions`
- **Headers**: `Content-Type: application/json`

**Request Body:**
```json
{
  "initial_letter": "بسم الله الرحمن الرحيم\n\nالسلام عليكم ورحمة الله وبركاته\n\nأتقدم إليكم بهذا الخطاب",
  "context": "خطاب رسمي للشؤون الإدارية"
}
```

**Expected Response:**
```json
{
  "status": "success",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Chat session created successfully",
  "expires_in": 30
}
```

**Test Script:**
```javascript
pm.test("Chat session created", function () {
    pm.response.to.have.status(201);
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("session_id");
    
    // Store session ID for later use
    pm.environment.set("session_id", jsonData.session_id);
});
```

#### 9. Edit Letter via Chat
- **Method**: `POST`
- **URL**: `{{baseUrl}}/api/v1/chat/sessions/{{session_id}}/edit`
- **Headers**: `Content-Type: application/json`

**Request Body:**
```json
{
  "message": "أضف فقرة شكر وتقدير في نهاية الخطاب مع إضافة التوقيع",
  "current_letter": "بسم الله الرحمن الرحيم\n\nالسلام عليكم ورحمة الله وبركاته\n\nأتقدم إليكم بهذا الخطاب للتعبير عن موضوع مهم",
  "editing_instructions": "حافظ على الطابع الرسمي والمهني للخطاب",
  "preserve_formatting": true
}
```

**Expected Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message_id": "msg_abc123",
  "response_text": "تم إضافة فقرة الشكر والتوقيع بنجاح",
  "updated_letter": "بسم الله الرحمن الرحيم\n\nالسلام عليكم ورحمة الله وبركاته\n\nأتقدم إليكم بهذا الخطاب للتعبير عن موضوع مهم\n\nوفي الختام، أتقدم بجزيل الشكر والتقدير لكم\n\nوالله الموفق\n\nسعد بن عبدالله العتيبي",
  "change_summary": "تم إضافة محتوى جديد (8 كلمات مضافة)",
  "letter_version_id": "ver_def456",
  "processing_time": 2.34,
  "status": "active"
}
```

#### 10. Get Chat History
- **Method**: `GET`
- **URL**: `{{baseUrl}}/api/v1/chat/sessions/{{session_id}}/history?limit=10&offset=0`

**Expected Response:**
```json
{
  "status": "success",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "history": [
    {
      "id": "msg_001",
      "role": "user",
      "content": "أضف فقرة شكر وتقدير",
      "timestamp": "2024-12-12T10:30:00Z",
      "metadata": {}
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": "تم إضافة فقرة الشكر بنجاح",
      "timestamp": "2024-12-12T10:30:05Z",
      "metadata": {
        "letter_version_id": "ver_def456",
        "processing_time": 2.34
      }
    }
  ],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 2
  }
}
```

#### 11. Get Session Status
- **Method**: `GET`
- **URL**: `{{baseUrl}}/api/v1/chat/sessions/{{session_id}}/status`

**Expected Response:**
```json
{
  "status": "success",
  "session_info": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2024-12-12T10:00:00Z",
    "last_activity": "2024-12-12T10:30:00Z",
    "expires_at": "2024-12-12T10:30:00Z",
    "is_active": true,
    "is_expired": false,
    "message_count": 4,
    "letter_versions": 2,
    "context": "خطاب رسمي للشؤون الإدارية"
  }
}
```

#### 12. List Active Sessions
- **Method**: `GET`
- **URL**: `{{baseUrl}}/api/v1/chat/sessions?include_expired=false`

#### 13. Extend Session
- **Method**: `POST`
- **URL**: `{{baseUrl}}/api/v1/chat/sessions/{{session_id}}/extend`
- **Headers**: `Content-Type: application/json`

**Request Body:**
```json
{
  "extend_minutes": 45
}
```

#### 14. Delete Session
- **Method**: `DELETE`
- **URL**: `{{baseUrl}}/api/v1/chat/sessions/{{session_id}}`

**Expected Response:**
```json
{
  "status": "success",
  "message": "Session deleted successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 📄 **Letter Archiving API** (`/api/v1/archive/`)

#### 15. Archive Letter (Complete Workflow)
- **Method**: `POST`
- **URL**: `{{baseUrl}}/api/v1/archive/letter`
- **Headers**: `Content-Type: application/json`
- **Description**: Complete archiving workflow (PDF generation + Google Drive upload + Sheets logging)

**Request Body:**
```json
{
  "letter_content": "بسم الله الرحمن الرحيم\n\nالسلام عليكم ورحمة الله وبركاته\n\nأتقدم إليكم بجزيل الشكر والتقدير على جهودكم المبذولة في المشروع الأخير...",
  "letter_type": "General",
  "recipient": "أحمد محمد علي السعدي",
  "title": "خطاب شكر وتقدير",
  "is_first": true,
  "ID": "LET-20241212-xyz789",
  "template": "default_template.html",
  "username": "test_user"
}
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Archive request initiated successfully",
  "letter_id": "LET-20241212-xyz789",
  "background_processing": true,
  "estimated_completion": "20-30 seconds"
}
```

**Test Script:**
```javascript
pm.test("Archive request initiated", function () {
    pm.response.to.have.status(200);
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("letter_id");
    pm.expect(jsonData.status).to.eql("success");
    
    // Store archive ID for later use
    pm.environment.set("archive_id", jsonData.letter_id);
});
```

---

## 🧪 **Complete Testing Scenarios**

### Scenario 1: Complete Letter Workflow (End-to-End)
**📋 Full Production Workflow Testing**

This scenario tests the complete letter creation, editing, and archiving workflow:

#### Step 1: Generate Initial Letter
```
POST {{baseUrl}}/api/v1/letter/generate
```
**Request:**
```json
{
  "category": "General",
  "recipient": "أحمد محمد علي السعدي",
  "prompt": "أود كتابة خطاب رسمي للتقدم بطلب إجازة سنوية للعام القادم مع توضيح الأسباب والمدة المطلوبة",
  "is_first": true,
  "member_name": "سعد بن عبدالله العتيبي",
  "recipient_title": "الأستاذ الفاضل",
  "recipient_job_title": "مدير الموارد البشرية",
  "organization_name": "شركة التقنية المتقدمة"
}
```

**Tests:**
```javascript
pm.test("Letter generated successfully", function () {
    pm.response.to.have.status(200);
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("ID");
    pm.expect(jsonData).to.have.property("Letter");
    pm.environment.set("letter_id", jsonData.ID);
    pm.environment.set("letter_content", jsonData.Letter);
});
```

#### Step 2: Create Chat Session for Editing
```
POST {{baseUrl}}/api/v1/chat/sessions
```
**Request:**
```json
{
  "initial_letter": "{{letter_content}}",
  "context": "خطاب رسمي للإجازة السنوية - تحرير وتحسين"
}
```

**Tests:**
```javascript
pm.test("Chat session created", function () {
    pm.response.to.have.status(201);
    var jsonData = pm.response.json();
    pm.environment.set("session_id", jsonData.session_id);
});
```

#### Step 3: Edit Letter via Chat (Multiple Iterations)
```
POST {{baseUrl}}/api/v1/chat/sessions/{{session_id}}/edit
```

**Edit #1 - Add Justification:**
```json
{
  "message": "أضف فقرة تبرير مفصلة للإجازة مع ذكر الأسباب الشخصية والمهنية",
  "current_letter": "{{letter_content}}",
  "editing_instructions": "حافظ على الطابع الرسمي وأضف تفاصيل مقنعة",
  "preserve_formatting": true
}
```

**Edit #2 - Add Conclusion:**
```json
{
  "message": "أضف جملة شكر وتقدير في نهاية الخطاب مع التوقيع الرسمي",
  "current_letter": "{{updated_letter}}",
  "editing_instructions": "استخدم عبارات مهذبة ورسمية",
  "preserve_formatting": true
}
```

**Tests:**
```javascript
pm.test("Letter edited successfully", function () {
    pm.response.to.have.status(200);
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("updated_letter");
    pm.expect(jsonData).to.have.property("change_summary");
    pm.environment.set("letter_content", jsonData.updated_letter);
});
```

#### Step 4: Check Session Status
```
GET {{baseUrl}}/api/v1/chat/sessions/{{session_id}}/status
```

#### Step 5: Archive Final Letter
```
POST {{baseUrl}}/api/v1/archive/letter
```
**Request:**
```json
{
  "letter_content": "{{letter_content}}",
  "letter_type": "General",
  "recipient": "أحمد محمد علي السعدي",
  "title": "طلب إجازة سنوية",
  "is_first": true,
  "ID": "{{letter_id}}",
  "template": "default_template.html",
  "username": "test_user"
}
```

#### Step 6: Cleanup Session
```
DELETE {{baseUrl}}/api/v1/chat/sessions/{{session_id}}
```

### Scenario 2: Error Handling & Edge Cases
1. **Invalid Request Data** → Test validation errors
2. **Non-existent Session** → Test 404 responses
3. **Expired Session** → Test session timeout
4. **Malformed JSON** → Test parsing errors
5. **Missing Required Fields** → Test field validation

### Scenario 3: Performance & Load Testing
1. **Multiple Concurrent Sessions** → Test concurrent chat sessions
2. **Large Letter Content** → Test with lengthy documents
3. **Rapid API Calls** → Test rate limiting
4. **Memory Usage** → Monitor session cleanup
5. **Archive Processing** → Test background job handling

## 📊 **Postman Collection Structure**

```
AutomatingLetter API v2.0
├── 🏠 System Health
│   ├── Root Info
│   └── Health Check
├── 📝 Letter Generation
│   ├── Generate Letter
│   ├── Validate Letter
│   ├── Get Categories
│   ├── Get Template
│   └── Service Health
├── 💬 Chat Editing
│   ├── Create Session
│   ├── Edit Letter (Chat)
│   ├── Get History
│   ├── Get Status
│   ├── List Sessions
│   ├── Extend Session
│   └── Delete Session
└── �️ Letter Archiving
    └── Archive Letter (Complete Workflow)
```

## 🔧 **Advanced Testing Tips**

### Environment Variables Setup
```json
{
  "baseUrl": "http://localhost:5000",
  "session_id": "{{session_id}}",
  "letter_id": "{{letter_id}}",
  "archive_id": "{{archive_id}}",
  "letter_content": "{{letter_content}}"
}
```

### Pre-request Script (Collection Level)
```javascript
// Set timestamp for requests
pm.environment.set("timestamp", new Date().toISOString());

// Generate random Arabic names for testing
const arabicNames = [
    "أحمد محمد السعدي", "فاطمة علي الخالدي", "محمد عبدالله العتيبي",
    "نورا سعد القحطاني", "خالد يوسف الشمري", "رنا أحمد الهذلي"
];
pm.environment.set("random_recipient", arabicNames[Math.floor(Math.random() * arabicNames.length)]);

// Generate test letter ID
pm.environment.set("test_letter_id", "LET-" + new Date().toISOString().slice(0,10).replace(/-/g, '') + "-" + Math.floor(Math.random() * 10000));
```

### Common Test Scripts
```javascript
// Standard response validation
pm.test("Response time is acceptable", function () {
    pm.expect(pm.response.responseTime).to.be.below(10000); // 10 seconds for AI operations
});

pm.test("Response has correct content type", function () {
    pm.expect(pm.response.headers.get("Content-Type")).to.include("application/json");
});

// Arabic content validation
pm.test("Response contains Arabic content", function () {
    var jsonData = pm.response.json();
    var arabicPattern = /[\u0600-\u06FF]/;
    
    if (jsonData.Letter) {
        pm.expect(arabicPattern.test(jsonData.Letter)).to.be.true;
    }
    if (jsonData.updated_letter) {
        pm.expect(arabicPattern.test(jsonData.updated_letter)).to.be.true;
    }
});

// Error response validation
pm.test("Error response structure", function () {
    if (pm.response.code >= 400) {
        var jsonData = pm.response.json();
        pm.expect(jsonData).to.have.property("error");
        pm.expect(jsonData).to.have.property("message");
    }
});
```

## 🚨 **Error Response Examples**

### 400 - Bad Request
```json
{
  "error": "Validation failed",
  "details": [
    {
      "field": "prompt",
      "message": "Prompt cannot be empty"
    }
  ]
}
```

### 404 - Session Not Found
```json
{
  "error": "Session not found",
  "message": "Chat session does not exist or has expired"
}
```

### 500 - Internal Server Error
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred",
  "timestamp": "2024-12-12T10:30:00Z"
}
```

## 📈 **Performance Testing Guidelines**

### Response Time Expectations
- **Letter Generation**: < 15 seconds (AI processing)
- **Chat Editing**: < 10 seconds (AI processing)
- **Session Management**: < 2 seconds
- **Archive Processing**: 20-30 seconds (background)
- **Other endpoints**: < 3 seconds

### Load Testing Scenarios
- [ ] 10 concurrent letter generations
- [ ] 5 active chat sessions with multiple edits
- [ ] Archive processing under load
- [ ] Session cleanup efficiency
- [ ] Memory usage monitoring

### Reliability Targets
- 99%+ success rate for valid requests
- Proper error handling for invalid requests
- Session persistence during server restart
- Archive completion guarantee
- No data loss during background processing

## 🎯 **Success Criteria Checklist**

### Core Functionality ✅
- [ ] Letter generation working (all categories)
- [ ] Chat-based editing operational
- [ ] Session management robust
- [ ] Complete archiving workflow (PDF + Drive + Sheets)
- [ ] Arabic text handling correct
- [ ] Error responses informative

### Performance ✅
- [ ] Response times within limits
- [ ] Background processing stable
- [ ] Memory usage controlled
- [ ] Session cleanup automatic
- [ ] Concurrent request handling

### Integration ✅
- [ ] OpenAI API integration working
- [ ] Google Drive upload successful
- [ ] Google Sheets logging accurate
- [ ] PDF generation reliable
- [ ] Frontend compatibility maintained

---

## 📝 **Quick Reference**

### Base URL
```
http://localhost:5000
```

### Core Endpoints
- **Generate Letter**: `POST /api/v1/letter/generate`
- **Create Chat Session**: `POST /api/v1/chat/sessions`  
- **Edit via Chat**: `POST /api/v1/chat/sessions/{id}/edit`
- **Archive Letter**: `POST /api/v1/archive/letter`

### Authentication
Currently no authentication required for testing.

### Rate Limiting
No rate limiting implemented in current version.

### Content Types
- Request: `application/json`
- Response: `application/json`

**Happy Testing! 🚀**

---

## 🔄 **Automated Testing Script**

For comprehensive testing, use the provided Python script:

```bash
# Run complete workflow test
python test_complete_workflow.py

# Run quick chat test
python test_chat.py
```

Both scripts provide detailed logging and verify all core functionality including the complete archiving workflow.
