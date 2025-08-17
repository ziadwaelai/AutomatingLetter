# AutomatingLetter API - Postman Testing Guide

## Overview
This guide provides detailed instructions for testing the AutomatingLetter API using Postman. It includes step-by-step setup, request examples, and testing workflows.

**API Base URL:** `http://localhost:5000`

---

## Postman Collection Setup

### 1. Create Environment Variables

First, create a Postman environment with these variables:

```
BASE_URL: http://localhost:5000
SESSION_ID: (will be set dynamically)
LETTER_ID: (will be set dynamically)
```

### 2. Import Collection

Create a new Postman collection named "AutomatingLetter API" and organize requests by service.

---

## Test Scenarios

### Scenario 1: Complete Letter Generation Workflow

#### Step 1: Health Check
**GET** `{{BASE_URL}}/health`

**Expected Response:** 200 OK
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

**Post-Response Script:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Service is healthy", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.status).to.eql("healthy");
});
```

#### Step 2: Get Available Categories
**GET** `{{BASE_URL}}/api/v1/letter/categories`

**Expected Response:** 200 OK
```json
{
  "status": "success",
  "categories": [
    {
      "value": "academic",
      "display_name": "academic",
      "description": "فئة academic"
    }
  ]
}
```

**Post-Response Script:**
```javascript
pm.test("Categories retrieved successfully", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.status).to.eql("success");
    pm.expect(jsonData.categories).to.be.an('array');
});
```

#### Step 3: Generate Letter
**POST** `{{BASE_URL}}/api/v1/letter/generate`

**Headers:**
- `Content-Type: application/json`

**Body (raw JSON):**
```json
{
  "prompt": "اكتب خطاباً رسمياً للجامعة لطلب تأجيل دراسة",
  "recipient": "عميد الجامعة",
  "category": "academic",
  "member_name": "أحمد محمد علي",
  "is_first": true,
  "recipient_title": "الأستاذ الدكتور",
  "recipient_job_title": "عميد كلية الهندسة",
  "organization_name": "جامعة الملك سعود"
}
```

**Expected Response:** 200 OK
```json
{
  "ID": "LETTER_20250817_001",
  "Title": "خطاب طلب تأجيل دراسة",
  "Letter": "بسم الله الرحمن الرحيم\n\nالأستاذ الدكتور عميد كلية الهندسة...",
  "Date": "2025/08/17",
  "arabic_date": "1446/02/15"
}
```

**Post-Response Script:**
```javascript
pm.test("Letter generated successfully", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.ID).to.exist;
    pm.expect(jsonData.Letter).to.exist;
    
    // Save letter ID for next requests
    pm.environment.set("LETTER_ID", jsonData.ID);
});

pm.test("Letter contains Arabic content", function () {
    var jsonData = pm.response.json();
    var arabicRegex = /[\u0600-\u06FF]/;
    pm.expect(arabicRegex.test(jsonData.Letter)).to.be.true;
});
```

#### Step 4: Validate Generated Letter
**POST** `{{BASE_URL}}/api/v1/letter/validate`

**Headers:**
- `Content-Type: application/json`

**Body (raw JSON):**
```json
{
  "letter": "{{letter_content_from_previous_response}}"
}
```

**Pre-Request Script:**
```javascript
// Get letter content from previous response (you'll need to manually copy it)
const letterContent = pm.globals.get("generated_letter") || "بسم الله الرحمن الرحيم\nالسلام عليكم ورحمة الله وبركاته\nهذا خطاب تجريبي للاختبار";
pm.globals.set("letter_content", letterContent);
```

**Expected Response:** 200 OK
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

---

### Scenario 2: Chat-Based Letter Editing

#### Step 1: Create Chat Session
**POST** `{{BASE_URL}}/api/v1/chat/sessions`

**Headers:**
- `Content-Type: application/json`

**Body (raw JSON):**
```json
{
  "initial_letter": "بسم الله الرحمن الرحيم\nالأستاذ الدكتور عميد الجامعة\nالسلام عليكم ورحمة الله وبركاته\nأتقدم إليكم بطلب تأجيل دراستي...",
  "context": "تحرير خطاب أكاديمي لطلب تأجيل الدراسة"
}
```

**Expected Response:** 201 Created
```json
{
  "status": "success",
  "session_id": "session_20250817_001",
  "message": "Chat session created successfully",
  "expires_in": 1800
}
```

**Post-Response Script:**
```javascript
pm.test("Chat session created", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.status).to.eql("success");
    pm.expect(jsonData.session_id).to.exist;
    
    // Save session ID for subsequent requests
    pm.environment.set("SESSION_ID", jsonData.session_id);
});
```

#### Step 2: Edit Letter via Chat
**POST** `{{BASE_URL}}/api/v1/chat/sessions/{{SESSION_ID}}/edit`

**Headers:**
- `Content-Type: application/json`

**Body (raw JSON):**
```json
{
  "message": "اجعل الخطاب أكثر رسمية وأضف تحية أكثر تفصيلاً",
  "current_letter": "بسم الله الرحمن الرحيم\nالأستاذ الدكتور عميد الجامعة\nالسلام عليكم ورحمة الله وبركاته\nأتقدم إليكم بطلب تأجيل دراستي...",
  "editing_instructions": "استخدم لغة رسمية ومهذبة",
  "preserve_formatting": true
}
```

**Expected Response:** 200 OK
```json
{
  "updated_letter": "بسم الله الرحمن الرحيم\n\nالأستاذ الدكتور المحترم عميد الجامعة الموقر\nالسلام عليكم ورحمة الله وبركاته، وبعد:\n\nيشرفني أن أتقدم إلى سعادتكم بأسمى آيات الاحترام والتقدير...",
  "response_text": "تم تحديث الخطاب ليكون أكثر رسمية مع إضافة تحية مفصلة ولغة مهذبة",
  "session_id": "session_20250817_001",
  "changes_made": [
    "إضافة عبارات رسمية",
    "تحسين التحية",
    "تحسين البناء اللغوي"
  ]
}
```

**Post-Response Script:**
```javascript
pm.test("Letter edited successfully", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.updated_letter).to.exist;
    pm.expect(jsonData.response_text).to.exist;
    pm.expect(jsonData.session_id).to.eql(pm.environment.get("SESSION_ID"));
});
```

#### Step 3: Get Chat History
**GET** `{{BASE_URL}}/api/v1/chat/sessions/{{SESSION_ID}}/history?limit=10&offset=0`

**Expected Response:** 200 OK
```json
{
  "status": "success",
  "session_id": "session_20250817_001",
  "history": [
    {
      "timestamp": "2025-08-17T10:30:00Z",
      "user_message": "اجعل الخطاب أكثر رسمية",
      "ai_response": "تم تحديث الخطاب ليكون أكثر رسمية",
      "letter_version": "النسخة المحدثة..."
    }
  ],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 1
  }
}
```

#### Step 4: Get Session Status
**GET** `{{BASE_URL}}/api/v1/chat/sessions/{{SESSION_ID}}/status`

**Expected Response:** 200 OK
```json
{
  "status": "success",
  "session_info": {
    "session_id": "session_20250817_001",
    "created_at": "2025-08-17T10:00:00Z",
    "expires_at": "2025-08-17T10:30:00Z",
    "message_count": 1,
    "is_active": true
  }
}
```

---

### Scenario 3: Letter Archiving

#### Step 1: Archive Letter
**POST** `{{BASE_URL}}/api/v1/archive/letter`

**Headers:**
- `Content-Type: application/json`

**Body (raw JSON):**
```json
{
  "letter_content": "بسم الله الرحمن الرحيم\n\nالأستاذ الدكتور المحترم عميد الجامعة الموقر\nالسلام عليكم ورحمة الله وبركاته، وبعد:\n\nيشرفني أن أتقدم إلى سعادتكم بطلب تأجيل دراستي لهذا الفصل الدراسي نظراً للظروف الصحية التي أمر بها.\n\nأسأل الله أن يوفقكم لما فيه خير الجامعة والطلاب.\n\nوالسلام عليكم ورحمة الله وبركاته\n\nأحمد محمد علي\nرقم الطالب: 1234567",
  "ID": "{{LETTER_ID}}",
  "letter_type": "academic",
  "recipient": "عميد الجامعة",
  "title": "خطاب طلب تأجيل دراسة",
  "is_first": true,
  "template": "default_template",
  "username": "أحمد محمد علي"
}
```

**Expected Response:** 200 OK
```json
{
  "status": "success",
  "message": "Letter archiving started for ID: LETTER_20250817_001",
  "processing": "background",
  "letter_id": "LETTER_20250817_001"
}
```

**Post-Response Script:**
```javascript
pm.test("Letter archiving initiated", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.status).to.eql("success");
    pm.expect(jsonData.processing).to.eql("background");
});
```

#### Step 2: Check Archive Status
**GET** `{{BASE_URL}}/api/v1/archive/status/{{LETTER_ID}}`

**Expected Response:** 200 OK
```json
{
  "letter_id": "LETTER_20250817_001",
  "status": "processing",
  "message": "Archive status tracking not implemented yet"
}
```

---

### Scenario 4: Memory and Analytics

#### Step 1: Get Memory Statistics
**GET** `{{BASE_URL}}/api/v1/chat/memory/stats`

**Expected Response:** 200 OK
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

#### Step 2: Get Memory Instructions
**GET** `{{BASE_URL}}/api/v1/chat/memory/instructions?category=academic&session_id={{SESSION_ID}}`

**Expected Response:** 200 OK
```json
{
  "status": "success",
  "data": {
    "instructions": "تعليمات مُجمّعة للكتابة الأكاديمية...",
    "category": "academic",
    "session_id": "session_20250817_001"
  }
}
```

---

## Error Testing Scenarios

### Test 1: Invalid Letter Generation
**POST** `{{BASE_URL}}/api/v1/letter/generate`

**Body (invalid data):**
```json
{
  "prompt": "",
  "recipient": "",
  "category": "invalid_category"
}
```

**Expected Response:** 400 Bad Request
```json
{
  "error": "Invalid request data",
  "details": [
    {
      "type": "value_error",
      "loc": ["prompt"],
      "msg": "ensure this value has at least 1 characters"
    }
  ]
}
```

### Test 2: Session Not Found
**GET** `{{BASE_URL}}/api/v1/chat/sessions/invalid_session_id/status`

**Expected Response:** 404 Not Found
```json
{
  "status": "not_found",
  "session_id": "invalid_session_id",
  "message": "Session does not exist"
}
```

### Test 3: Missing Required Fields
**POST** `{{BASE_URL}}/api/v1/archive/letter`

**Body (missing fields):**
```json
{
  "letter_content": ""
}
```

**Expected Response:** 400 Bad Request
```json
{
  "error": "Missing required fields: ID"
}
```

---

## Performance Testing

### Load Test Configuration
For load testing, create these tests:

1. **Concurrent Letter Generation**
   - 10 concurrent requests to `/api/v1/letter/generate`
   - Monitor response times and success rates

2. **Session Management**
   - Create 50 concurrent chat sessions
   - Test session cleanup and memory management

3. **Archive Processing**
   - Queue multiple archive requests
   - Test background processing capacity

### Monitoring Endpoints
Use these endpoints to monitor system performance:

- `GET /health` - Overall system health
- `GET /api/v1/letter/health` - Letter service health  
- `GET /api/v1/chat/health` - Chat service health
- `GET /api/v1/archive/health` - Archive service health

---

## Postman Scripts

### Pre-Request Script for Authentication
```javascript
// Add any authentication headers if needed
pm.request.headers.add({
    key: 'User-Agent',
    value: 'PostmanTesting/1.0'
});
```

### Global Test Script
```javascript
// Common tests for all requests
pm.test("Response time is less than 5000ms", function () {
    pm.expect(pm.response.responseTime).to.be.below(5000);
});

pm.test("No errors in response", function () {
    pm.response.to.not.have.jsonBody("error");
});

// Log response for debugging
console.log("Response:", pm.response.text());
```

### Cleanup Script (for end of collection)
```javascript
// Clean up environment variables
pm.environment.unset("SESSION_ID");
pm.environment.unset("LETTER_ID");

console.log("Environment variables cleaned up");
```

---

## Testing Best Practices

### 1. Test Order
Run tests in this order:
1. Health checks
2. Letter generation
3. Letter validation  
4. Chat session creation
5. Chat editing
6. Letter archiving
7. Cleanup

### 2. Data Management
- Use unique IDs for each test run
- Clean up sessions after testing
- Test with both Arabic and English content
- Test edge cases (empty strings, very long content)

### 3. Environment Management
- Use separate environments for development/staging/production
- Store sensitive data (API keys) in environment variables
- Use dynamic variables for session IDs and letter IDs

### 4. Monitoring
- Track response times
- Monitor success/failure rates
- Check for memory leaks in long-running tests
- Verify Arabic text encoding

### 5. Automation
- Set up automated test runs
- Use collection runner for regression testing
- Export test results for analysis
- Integrate with CI/CD pipelines

---

## Troubleshooting Common Issues

### Issue 1: Arabic Text Display
**Problem:** Arabic text appears as question marks
**Solution:** Ensure UTF-8 encoding in Postman settings

### Issue 2: Session Timeouts
**Problem:** Chat sessions expire during testing
**Solution:** Use session extension endpoint or reduce test duration

### Issue 3: Rate Limiting
**Problem:** Too many requests error
**Solution:** Add delays between requests or reduce concurrency

### Issue 4: Memory Errors
**Problem:** Out of memory errors during load testing
**Solution:** Monitor memory usage and implement cleanup

### Issue 5: Google Services Authentication
**Problem:** Google Sheets/Drive access fails
**Solution:** Verify service account credentials and permissions

---

## Collection Export

To export your Postman collection:
1. Right-click on collection name
2. Select "Export"
3. Choose Collection v2.1 format
4. Save as `AutomatingLetter_API.postman_collection.json`

Include environment file:
1. Click gear icon (Manage Environments)
2. Select your environment
3. Click "Export"
4. Save as `AutomatingLetter_Environment.postman_environment.json`

---

## Support and Documentation

For additional support:
- Check API documentation: `docs/API_DOCUMENTATION.md`
- Review application logs in `logs/app.log`
- Use health check endpoints for system status
- Contact development team for complex issues

**Happy Testing! 🚀**
