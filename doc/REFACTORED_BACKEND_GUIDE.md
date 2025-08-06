# AutomatingLetter Backend - Refactored Architecture

## 🎯 Overview

This document describes the completely refactored backend architecture for the AutomatingLetter application. The new structure provides a modern, scalable, and maintainable solution for Arabic letter generation with enhanced chat-based editing capabilities.

## 🏗️ Architecture Overview

### Project Structure
```
src/
├── config/
│   ├── __init__.py
│   └── settings.py          # Centralized configuration
├── models/
│   ├── __init__.py
│   └── schemas.py           # Pydantic data models
├── services/
│   ├── __init__.py
│   ├── letter_generator.py  # AI letter generation
│   ├── google_services.py   # Google Sheets/Drive integration
│   ├── pdf_service.py       # PDF generation
│   └── chat_service.py      # Session-based chat
├── utils/
│   ├── __init__.py
│   ├── helpers.py           # Utility functions
│   └── exceptions.py        # Error handling
└── api/
    ├── __init__.py
    ├── letter_routes.py      # Letter generation endpoints
    ├── chat_routes.py        # Chat editing endpoints
    └── pdf_routes.py         # PDF generation endpoints

new_app.py                   # Modern Flask application
app.py                       # Legacy application (preserved)
```

## 🚀 Key Features

### 1. Enhanced Chat System with Memory Management
- **Session-based conversations**: Each chat has a unique session ID with configurable timeout
- **Memory buffer management**: Automatic cleanup of old conversations
- **Letter version tracking**: Maintains history of letter edits within sessions
- **Background cleanup**: Automatic removal of expired sessions

### 2. Comprehensive Error Handling
- **Custom exception hierarchy**: Structured error types for different failure scenarios
- **Service-level error decorators**: Automatic error context and recovery
- **Detailed error responses**: Informative error messages with debugging context

### 3. Performance Monitoring
- **Request timing**: Automatic measurement of API response times
- **Service statistics**: Real-time metrics for all services
- **Connection pooling**: Efficient resource utilization for Google APIs

### 4. Configuration Management
- **Environment-based settings**: Different configs for development/production
- **Feature flags**: Enable/disable functionality without code changes
- **Security settings**: Centralized security configuration

## 📊 API Endpoints

### Letter Generation API (`/api/v1/letter/`)

#### Generate Letter
```http
POST /api/v1/letter/generate
Content-Type: application/json

{
  "category": "General",
  "recipient": "أحمد محمد",
  "prompt": "أود كتابة خطاب شكر وتقدير",
  "is_first": true,
  "member_name": "سعد العتيبي",
  "recipient_title": "الأستاذ الفاضل",
  "recipient_job_title": "مدير المبيعات",
  "organization_name": "شركة الأمل"
}
```

**Response:**
```json
{
  "ID": "LET_20241212_abc123",
  "Title": "خطاب شكر وتقدير",
  "Letter": "بسم الله الرحمن الرحيم...",
  "Date": "2024-12-12"
}
```

#### Other Letter Endpoints:
- `GET /api/v1/letter/categories` - Get available categories
- `POST /api/v1/letter/validate` - Validate letter content
- `GET /api/v1/letter/templates/{category}` - Get category template
- `GET /api/v1/letter/health` - Service health check

### Chat Editing API (`/api/v1/chat/`)

#### Create Chat Session
```http
POST /api/v1/chat/sessions
Content-Type: application/json

{
  "initial_letter": "بسم الله الرحمن الرحيم...",
  "context": "خطاب رسمي للشؤون الإدارية"
}
```

**Response:**
```json
{
  "status": "success",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Chat session created successfully",
  "expires_in": 30
}
```

#### Edit Letter via Chat
```http
POST /api/v1/chat/sessions/{session_id}/edit
Content-Type: application/json

{
  "message": "أضف فقرة شكر في النهاية",
  "current_letter": "النص الحالي للخطاب...",
  "editing_instructions": "حافظ على الطابع الرسمي",
  "preserve_formatting": true
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message_id": "msg_abc123",
  "response_text": "تم إضافة فقرة الشكر بنجاح",
  "updated_letter": "النص المحدث للخطاب...",
  "change_summary": "تم إضافة محتوى جديد (15 كلمة مضافة)",
  "letter_version_id": "ver_def456",
  "processing_time": 2.34,
  "status": "active"
}
```

#### Other Chat Endpoints:
- `GET /api/v1/chat/sessions/{session_id}/history` - Get chat history
- `GET /api/v1/chat/sessions/{session_id}/status` - Get session status
- `DELETE /api/v1/chat/sessions/{session_id}` - Delete session
- `GET /api/v1/chat/sessions` - List active sessions
- `POST /api/v1/chat/sessions/{session_id}/extend` - Extend session
- `POST /api/v1/chat/cleanup` - Manual cleanup

### PDF Generation API (`/api/v1/pdf/`)

#### Generate PDF
```http
POST /api/v1/pdf/generate
Content-Type: application/json

{
  "title": "خطاب رسمي",
  "content": "محتوى الخطاب...",
  "template_name": "default_template",
  "upload_to_drive": true,
  "options": {
    "page-size": "A4",
    "margin-top": "1in"
  }
}
```

**Response:**
```json
{
  "pdf_id": "PDF_20241212_xyz789",
  "filename": "خطاب_رسمي_PDF_20241212_xyz789.pdf",
  "file_size": 245760,
  "download_url": "/api/v1/pdf/download/PDF_20241212_xyz789",
  "drive_url": "https://drive.google.com/file/d/1abc...",
  "generated_at": "2024-12-12T10:30:00Z"
}
```

#### Other PDF Endpoints:
- `GET /api/v1/pdf/download/{pdf_id}` - Download PDF
- `GET /api/v1/pdf/templates` - Get available templates
- `POST /api/v1/pdf/preview` - Generate HTML preview
- `POST /api/v1/pdf/batch` - Batch PDF generation
- `GET /api/v1/pdf/list` - List generated PDFs
- `DELETE /api/v1/pdf/{pdf_id}` - Delete PDF

## 🔧 Configuration

### Environment Variables
```bash
# AI Configuration
OPENAI_API_KEY=your_openai_key
AI_MODEL=gpt-4-turbo-preview
AI_TEMPERATURE=0.3
AI_MAX_TOKENS=2000

# Chat Configuration
CHAT_SESSION_TIMEOUT_MINUTES=30
CHAT_MAX_MEMORY_SIZE=50
CHAT_CLEANUP_INTERVAL_MINUTES=5

# Server Configuration
FLASK_ENV=development
HOST=localhost
PORT=5000
DEBUG_MODE=true
CORS_ORIGINS=*

# Google Services
GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
GOOGLE_SHEET_ID=your_sheet_id

# Features
ENABLE_LEGACY_ENDPOINTS=true
LOG_REQUESTS=true
```

### Configuration Classes
```python
from src.config import get_config

config = get_config()
print(config.openai_api_key)
print(config.chat_session_timeout_minutes)
```

## 🛠️ Services Architecture

### 1. Letter Generation Service
```python
from src.services import get_letter_service

service = get_letter_service()
result = service.generate_letter(context)
```

**Features:**
- Same proven AI prompt as original system
- Enhanced error handling and validation
- Performance monitoring and statistics
- Automatic context preparation

### 2. Chat Service
```python
from src.services import get_chat_service

chat = get_chat_service()
session_id = chat.create_session()
response = chat.process_edit_request(session_id, message, letter)
```

**Features:**
- Session-based memory management
- Automatic session cleanup
- Letter version tracking
- Conversation context preservation

### 3. PDF Service
```python
from src.services import get_pdf_service

pdf = get_pdf_service()
result = pdf.generate_pdf(title, content, template)
```

**Features:**
- Jinja2 template system
- Configurable PDF options
- Arabic font support
- Batch processing capability

### 4. Google Services
```python
from src.services import get_sheets_service, get_drive_service

sheets = get_sheets_service()
config = sheets.get_letter_config_by_category("General")

drive = get_drive_service()
url = drive.upload_pdf(file_path, filename)
```

**Features:**
- Connection pooling and reuse
- Parallel execution for better performance
- Comprehensive error handling
- Automatic retry logic

## 🔒 Error Handling

### Exception Hierarchy
```python
AutomatingLetterException
├── ConfigurationError
├── ValidationError
├── ServiceError
│   ├── LetterGenerationError
│   ├── ChatServiceError
│   ├── PDFGenerationError
│   └── GoogleServicesError
└── ExternalServiceError
```

### Error Context Management
```python
from src.utils import ErrorContext

with ErrorContext("operation_name", {"param": "value"}):
    # Your operation
    pass
```

### Service Error Decorators
```python
from src.utils import service_error_handler

@service_error_handler
def my_service_method(self):
    # Automatic error handling and logging
    pass
```

## 📈 Performance Features

### Request Timing
```python
from src.utils import measure_performance

@measure_performance
def my_endpoint():
    # Automatic timing measurement
    pass
```

### Service Statistics
All services provide comprehensive statistics:
```python
service.get_service_stats()
# Returns: generation count, performance metrics, resource usage
```

### Connection Management
- Google Services use connection pooling
- Automatic connection lifecycle management
- Performance monitoring and optimization

## 🔄 Migration Guide

### From Legacy to New API

#### Legacy Letter Generation:
```python
# Old
POST /generate_letter
```

#### New Letter Generation:
```python
# New
POST /api/v1/letter/generate
```

#### Legacy Chat Editing:
```python
# Old
POST /edit_letter
{
  "letter": "content",
  "feedback": "changes"
}
```

#### New Chat Editing:
```python
# New - Step 1: Create session
POST /api/v1/chat/sessions

# New - Step 2: Edit via chat
POST /api/v1/chat/sessions/{session_id}/edit
{
  "message": "changes",
  "current_letter": "content",
  "editing_instructions": "specific instructions"
}
```

## 🧪 Testing

### Running the Application
```bash
# Development
python new_app.py

# Production
gunicorn -w 4 -b 0.0.0.0:5000 new_app:get_app
```

### Health Checks
```bash
# Overall health
curl http://localhost:5000/health

# Service-specific health
curl http://localhost:5000/api/v1/letter/health
curl http://localhost:5000/api/v1/chat/health
curl http://localhost:5000/api/v1/pdf/health
```

### Legacy Compatibility
The new application supports legacy endpoints through `ENABLE_LEGACY_ENDPOINTS=true` configuration option.

## 📝 Development Notes

### Code Quality
- Full type hints throughout the codebase
- Comprehensive docstrings
- Pydantic models for data validation
- Structured error handling

### Scalability
- Service-oriented architecture
- Configurable timeouts and limits
- Connection pooling
- Background cleanup processes

### Maintainability
- Clear separation of concerns
- Centralized configuration
- Comprehensive logging
- Modular design

## 🔮 Future Enhancements

### Planned Features
1. **Database Integration**: Replace in-memory storage with persistent database
2. **Authentication**: Add user authentication and authorization
3. **Rate Limiting**: Implement API rate limiting
4. **WebSocket Support**: Real-time chat capabilities
5. **Monitoring Dashboard**: Real-time service monitoring
6. **API Documentation**: Swagger/OpenAPI integration
7. **Testing Suite**: Comprehensive unit and integration tests

### Performance Optimizations
1. **Caching Layer**: Redis integration for better performance
2. **Load Balancing**: Support for horizontal scaling
3. **Async Processing**: Background job processing
4. **CDN Integration**: Static asset optimization

## 🤝 Contributing

The refactored architecture makes it easy to contribute new features:

1. **Adding new services**: Extend the services package
2. **New API endpoints**: Add routes to existing or new blueprints
3. **Enhanced error handling**: Extend the exception hierarchy
4. **Configuration options**: Add new settings to the config system

This refactored backend provides a solid foundation for scaling the AutomatingLetter application while maintaining backward compatibility and improving developer experience.
