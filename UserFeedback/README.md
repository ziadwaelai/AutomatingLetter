# Enhanced Interactive Chat System

This document describes the enhanced interactive chat system with memory buffer and session management for the AutomatingLetter project.

## Overview

The enhanced chat system provides:
- **Session-based conversations** with memory buffer
- **Automatic session cleanup** to prevent memory leaks
- **Thread-safe session management**
- **Conversation context** for better letter editing
- **Backward compatibility** with existing code

## Features

### 1. Memory Buffer
- Maintains conversation history within sessions
- Configurable memory window (default: 10 messages)
- Context-aware responses based on previous interactions

### 2. Session Management
- Unique session IDs for each conversation
- Automatic session expiration (default: 30 minutes of inactivity)
- Background cleanup thread removes expired sessions

### 3. Letter Editing with Context
- Enhanced letter editing using conversation context
- Same strict instructions as the main AI generator
- Memory of previous edits and feedback

### 4. Thread Safety
- Thread-safe session storage with locks
- Safe for concurrent access in multi-user environments

## API Endpoints

### Create Session
```http
POST /chat/session/create
Content-Type: application/json

{
    "original_letter": "optional original letter text"
}
```

**Response:**
```json
{
    "status": "success",
    "session_id": "uuid-string",
    "message": "Chat session created successfully"
}
```

### Edit Letter with Session
```http
POST /chat/edit-letter
Content-Type: application/json

{
    "session_id": "uuid-string",
    "letter": "current letter text",
    "feedback": "user feedback for editing"
}
```

**Response:**
```json
{
    "status": "success",
    "edited_letter": "edited letter text",
    "session_id": "uuid-string",
    "conversation_length": 5
}
```

### Ask Questions
```http
POST /chat/ask
Content-Type: application/json

{
    "session_id": "uuid-string",
    "question": "user question about the letter",
    "current_letter": "optional current letter text"
}
```

**Response:**
```json
{
    "status": "success",
    "answer": "AI response to the question",
    "session_id": "uuid-string",
    "conversation_length": 6
}
```

### Get Session Info
```http
GET /chat/session/info/{session_id}
```

**Response:**
```json
{
    "status": "success",
    "session_id": "uuid-string",
    "created_at": "2025-08-06T10:30:00.000Z",
    "last_activity": "2025-08-06T10:35:00.000Z",
    "conversation_length": 6,
    "has_original_letter": true
}
```

### Clear Session
```http
DELETE /chat/session/clear/{session_id}
```

**Response:**
```json
{
    "status": "success",
    "message": "Session cleared"
}
```

### Get Active Sessions Count
```http
GET /chat/sessions/count
```

**Response:**
```json
{
    "status": "success",
    "active_sessions": 3
}
```

## Usage Examples

### Basic Letter Editing (Legacy)
```python
from UserFeedback.interactive_chat import edit_letter_based_on_feedback

# This still works as before
edited_letter = edit_letter_based_on_feedback(
    letter="original letter text",
    feedback="change the date to tomorrow"
)
```

### Enhanced Letter Editing with Session
```python
from UserFeedback.enhanced_chat import chat_manager

# Create session
session_id = chat_manager.create_session(original_letter="original letter")

# Edit letter multiple times with context
result1 = chat_manager.edit_letter(session_id, letter, "change the date")
result2 = chat_manager.edit_letter(session_id, result1["edited_letter"], "make it more formal")

# Ask questions
question_result = chat_manager.chat_about_letter(
    session_id, 
    "What's the best way to end this letter?"
)

# Clean up when done
chat_manager.clear_session(session_id)
```

### Using API Endpoints
```javascript
// Create session
const sessionResponse = await fetch('/chat/session/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ original_letter: letterText })
});
const { session_id } = await sessionResponse.json();

// Edit letter
const editResponse = await fetch('/chat/edit-letter', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        session_id: session_id,
        letter: currentLetter,
        feedback: userFeedback
    })
});
const { edited_letter } = await editResponse.json();

// Ask question
const questionResponse = await fetch('/chat/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        session_id: session_id,
        question: "How can I make this letter more professional?",
        current_letter: edited_letter
    })
});
const { answer } = await questionResponse.json();
```

## Configuration

The chat manager can be configured during initialization:

```python
from UserFeedback.enhanced_chat import InteractiveChatManager

chat_manager = InteractiveChatManager(
    model_name="gpt-4.1",              # OpenAI model
    temperature=0.2,                   # Model temperature
    memory_window=10,                  # Messages to keep in memory
    session_timeout_minutes=30,        # Session expiration time
    cleanup_interval_minutes=5         # Cleanup frequency
)
```

## Error Handling

All endpoints return consistent error responses:

```json
{
    "status": "error",
    "message": "Error description",
    "session_expired": true  // Only for session-related errors
}
```

## Session Expiration

Sessions automatically expire after 30 minutes of inactivity. When a session expires:
- It's automatically removed from memory
- API calls return `session_expired: true`
- Client should create a new session

## Backward Compatibility

The original `edit_letter_based_on_feedback` function continues to work exactly as before. It now uses the enhanced system internally but creates temporary sessions that are automatically cleaned up.

## Thread Safety

The system is designed to be thread-safe and can handle multiple concurrent users and requests safely.

## Monitoring

- Use `/chat/sessions/count` to monitor active sessions
- Check logs for session creation/cleanup information
- Session info includes creation time and activity timestamps

## Best Practices

1. **Create sessions** when starting a new conversation
2. **Reuse sessions** for related edits and questions
3. **Clear sessions** when done to free memory immediately
4. **Handle session expiration** gracefully in client code
5. **Monitor active sessions** in production environments
