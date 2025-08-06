# 📮 Postman Testing Scenarios for Enhanced Interactive Chat

## Overview
This document provides step-by-step scenarios you can test in Postman to verify the enhanced interactive chat system.

## Prerequisites
1. **Server Running**: Make sure your Flask app is running on `http://localhost:5000`
2. **Environment Variables**: Ensure `OPENAI_API_KEY` is set in your `.env` file
3. **Postman Collection**: Import these requests into Postman

---

## 🎯 Scenario 1: Complete Letter Editing Workflow

### Step 1: Create a Chat Session
**Method**: `POST`  
**URL**: `http://localhost:5000/chat/session/create`  
**Headers**:
```
Content-Type: application/json
```
**Body** (raw JSON):
```json
{
    "original_letter": "بسم الله الرحمن الرحيم\n\nإدارة المدرسة المحترمة\nالسلام عليكم ورحمة الله وبركاته\n\nنتقدم إليكم بطلب الموافقة على تنظيم رحلة مدرسية.\n\nوتفضلوا بقبول فائق الاحترام والتقدير،،،"
}
```
**Expected Response**:
```json
{
    "status": "success",
    "session_id": "uuid-here",
    "message": "Chat session created successfully"
}
```
**📝 Note**: Copy the `session_id` from the response for next steps.

---

### Step 2: Edit the Letter
**Method**: `POST`  
**URL**: `http://localhost:5000/chat/edit-letter`  
**Headers**:
```
Content-Type: application/json
```
**Body** (raw JSON):
```json
{
    "session_id": "paste-session-id-here",
    "letter": "بسم الله الرحمن الرحيم\n\nإدارة المدرسة المحترمة\nالسلام عليكم ورحمة الله وبركاته\n\nنتقدم إليكم بطلب الموافقة على تنظيم رحلة مدرسية.\n\nوتفضلوا بقبول فائق الاحترام والتقدير،،،",
    "feedback": "أضف تاريخ اليوم وغير كلمة 'المحترمة' إلى 'الموقرة'"
}
```
**Expected Response**:
```json
{
    "status": "success",
    "edited_letter": "edited letter content here...",
    "session_id": "same-session-id",
    "conversation_length": 2
}
```

---

### Step 3: Ask a Question About the Letter
**Method**: `POST`  
**URL**: `http://localhost:5000/chat/ask`  
**Headers**:
```
Content-Type: application/json
```
**Body** (raw JSON):
```json
{
    "session_id": "paste-session-id-here",
    "question": "كيف يمكنني جعل هذا الخطاب أكثر إقناعاً؟",
    "current_letter": "paste-edited-letter-from-step2-here"
}
```
**Expected Response**:
```json
{
    "status": "success",
    "answer": "AI advice about making the letter more persuasive...",
    "session_id": "same-session-id",
    "conversation_length": 4
}
```

---

### Step 4: Make Another Edit Based on Advice
**Method**: `POST`  
**URL**: `http://localhost:5000/chat/edit-letter`  
**Headers**:
```
Content-Type: application/json
```
**Body** (raw JSON):
```json
{
    "session_id": "paste-session-id-here",
    "letter": "paste-edited-letter-from-step2-here",
    "feedback": "أضف فقرة تشرح أهمية الرحلة التعليمية للطلاب"
}
```
**Expected Response**:
```json
{
    "status": "success",
    "edited_letter": "final edited letter with educational importance...",
    "session_id": "same-session-id", 
    "conversation_length": 6
}
```

---

### Step 5: Get Session Information
**Method**: `GET`  
**URL**: `http://localhost:5000/chat/session/info/paste-session-id-here`  
**Headers**: None needed

**Expected Response**:
```json
{
    "status": "success",
    "session_id": "session-id",
    "created_at": "2025-08-06T10:30:00.000000",
    "last_activity": "2025-08-06T10:35:00.000000",
    "conversation_length": 6,
    "has_original_letter": true
}
```

---

### Step 6: Check Active Sessions Count
**Method**: `GET`  
**URL**: `http://localhost:5000/chat/sessions/count`  
**Headers**: None needed

**Expected Response**:
```json
{
    "status": "success",
    "active_sessions": 1
}
```

---

### Step 7: Clear the Session
**Method**: `DELETE`  
**URL**: `http://localhost:5000/chat/session/clear/paste-session-id-here`  
**Headers**: None needed

**Expected Response**:
```json
{
    "status": "success",
    "message": "Session cleared"
}
```

---

## 🎯 Scenario 2: Test Legacy Endpoint (Backward Compatibility)

### Legacy Letter Edit
**Method**: `POST`  
**URL**: `http://localhost:5000/edit-letter`  
**Headers**:
```
Content-Type: application/json
```
**Body** (raw JSON):
```json
{
    "letter": "بسم الله الرحمن الرحيم\n\nهذا خطاب تجريبي للاختبار.",
    "feedback": "أضف التحية الرسمية في البداية"
}
```
**Expected Response**:
```json
{
    "status": "success",
    "edited_letter": "بسم الله الرحمن الرحيم\n\nالسلام عليكم ورحمة الله وبركاته\n\nهذا خطاب تجريبي للاختبار."
}
```

---

## 🎯 Scenario 3: Error Handling Tests

### Test with Invalid Session ID
**Method**: `POST`  
**URL**: `http://localhost:5000/chat/edit-letter`  
**Headers**:
```
Content-Type: application/json
```
**Body** (raw JSON):
```json
{
    "session_id": "invalid-session-id",
    "letter": "test letter",
    "feedback": "test feedback"
}
```
**Expected Response**:
```json
{
    "status": "error",
    "message": "Session not found or expired",
    "session_expired": true
}
```

### Test Missing Required Fields
**Method**: `POST`  
**URL**: `http://localhost:5000/chat/edit-letter`  
**Headers**:
```
Content-Type: application/json
```
**Body** (raw JSON):
```json
{
    "session_id": "test"
}
```
**Expected Response**:
```json
{
    "error": "session_id, letter, and feedback are required"
}
```

---