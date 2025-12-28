# Technical Documentation - Automating Letter backend
**Last Updated:** 14 December 2025

---

## 1. Project Overview

### What is This Project?

An AI-powered REST API for generating, editing, and managing formal Arabic letters. The system uses GPT-4 to create professional correspondence with proper formatting, context awareness, and learning capabilities.

### Tech Stack

- **Backend:** Python 3.x + Flask
- **AI:** OpenAI GPT-4.1, GPT-4o + LangChain
- **Database:** Google Sheets (as database)
- **Storage:** Google Drive
- **Document Generation:** Playwright (PDF), python-docx (DOCX)
- **External Integration:** WhatsApp (via n8n webhook)

---

## 2. System Architecture

```
┌─────────────────┐
│   Frontend      │ (Vercel)
│   Web Client    │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────────────────────────────┐
│   Flask API Server (Shobbak Server)     │
│  ┌──────────────────────────────────┐   │
│  │  API Routes                      │   │
│  │  - Letter Generation (/letter)   │   │
│  │  - Chat Editing (/chat)          │   │
│  │  - Archiving (/archive)          │   │
│  │  - WhatsApp (/whatsapp)          │   │
│  └──────────────┬───────────────────┘   │
│                 │                       │
│  ┌──────────────▼───────────────────┐   │
│  │  Services                        │   │
│  │  - Letter Generator              │   │
│  │  - Chat Service                  │   │
│  │  - PDF/DOCX Generator            │   │
│  │  - Memory Service                │   │
│  └──────────────┬───────────────────┘   │
└─────────────────┼───────────────────────┘
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
┌──────────┐ ┌─────────┐ ┌──────────┐
│  OpenAI  │ │ Google  │ │ WhatsApp │
│  GPT-4   │ │ Sheets  │ │  (n8n)   │
│          │ │ + Drive │ │          │
└──────────┘ └─────────┘ └──────────┘
```

---

## 3. Core Features

### 3.1 Letter Generation
- **AI-Powered:** Uses GPT-4.1 with category-specific templates
- **Context-Aware:** Considers previous letters, member info, recipient details
- **Memory System:** Learns user preferences over time
- **18 Strict Rules:** Ensures formal Arabic letter standards

### 3.2 Chat-Based Editing
- **Conversational Interface:** Edit letters through natural language
- **Session Management:** 60-minute sessions with extension support
- **Version History:** Track up to 10 versions per session
- **Async Learning:** Updates memory from user interactions

### 3.3 Document Archiving
- **Dual Format:** PDF (via Playwright) and DOCX (via python-docx)
- **Google Drive:** Automatic upload with public sharing
- **Google Sheets:** Logging to "Submissions" worksheet
- **Signature Support:** Job title + image + name layout

### 3.4 WhatsApp Integration
- **Assignment Tracking:** Manage letter assignments to signers
- **Status Updates:** Sync between WhatsApp sheet and Submissions
- **Webhook Integration:** Send letters via n8n automation
- **Rollback Support:** Clear assignments on failures

### 3.5 Memory & Learning
- **LangGraph Agent:** AI-powered instruction management
- **Smart Selection:** Usage-based effectiveness ranking
- **Category Support:** Organize by letter type
- **Automatic Updates:** Learn from every interaction

---

## 4. API Endpoints Reference

### Letter Generation

#### Generate Letter
```http
POST /api/v1/letter/generate
Content-Type: application/json

{
  "category": "خطاب جديد",
  "recipient": "وزارة التعليم",
  "prompt": "طلب موافقة على مشروع تعليمي",
  "is_first": true,
  "member_name": "أحمد محمد",
  "recipient_title": "معالي",
  "recipient_job_title": "وزير التعليم"
}

Response: {
  "ID": "251214-12345",
  "Title": "طلب موافقة على مشروع تعليمي",
  "Letter": "بسم الله الرحمن الرحيم...",
  "Date": "١٤ ديسمبر ٢٠٢٥"
}
```

#### Validate Letter
```http
POST /api/v1/letter/validate
Content-Type: application/json

{
  "letter": "بسم الله الرحمن الرحيم..."
}

Response: {
  "is_valid": true,
  "suggestions": ["اقتراحات تحسين..."]
}
```

### Chat Editing

#### Create Session
```http
POST /api/v1/chat/sessions
Content-Type: application/json

{
  "initial_letter": "خطاب موجود...",
  "context": "تحرير خطاب رسمي"
}

Response: {
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "expires_at": "2025-12-14T15:30:00Z"
}
```

#### Edit Letter
```http
POST /api/v1/chat/sessions/{session_id}/edit
Content-Type: application/json

{
  "message": "غير العنوان إلى طلب تأجيل",
  "current_letter": "الخطاب الحالي..."
}

Response: {
  "updated_letter": "الخطاب المحدث...",
  "change_summary": "تم تغيير العنوان",
  "letter_version_id": "v2"
}
```

### Archiving

#### Archive to PDF
```http
POST /api/v1/archive/letter
Content-Type: application/json

{
  "letter_content": "محتوى الخطاب...",
  "letter_type": "رسمي",
  "recipient": "وزارة التعليم",
  "title": "طلب موافقة",
  "ID": "251214-12345",
  "username": "أحمد"
}

Response: {
  "status": "completed",
  "file_url": "https://drive.google.com/file/d/..."
}
```

#### Update Letter
```http
PUT /api/v1/archive/update
Content-Type: application/json

{
  "letter_id": "251214-12345",
  "content": "المحتوى الجديد...",
  "include_signature": true,
  "signature_image_url": "https://drive.google.com/...",
  "signature_name": "د. محمد أحمد",
  "signature_job_title": "مدير عام"
}

Response: {
  "status": "completed",
  "file_url": "https://drive.google.com/file/d/..."
}
```

### WhatsApp Integration

#### Send Letter
```http
POST /api/v1/whatsapp/send
Content-Type: application/json

{
  "phone_number": "201123808495",
  "letter_id": "251214-12345"
}

Response: {
  "message": "Letter sent successfully",
  "webhook_status": 200
}
```

#### Get Assigned Letter
```http
GET /api/v1/whatsapp/assigned-letter/201123808495

Response: {
  "assigned_letter_id": "251214-12345",
  "name": "د. محمد أحمد",
  "title": "طلب موافقة",
  "sign": "https://drive.google.com/...",
  "is_assigned": true
}
```

---

## 5. Data Flow

### Letter Generation Flow
```
User Request
    ↓
API Validation
    ↓
Fetch Templates & Instructions (Google Sheets)
    ↓
Build Context (Member Info + Memory)
    ↓
GPT-4.1 Generation
    ↓
Validation & Response
```

### Archiving Flow
```
Archive Request
    ↓
Background Thread (15s timeout)
    ↓
Parse Content (GPT-4o)
    ↓
Generate Document (PDF/DOCX)
    ↓
Upload to Drive
    ↓
Log to Sheets
    ↓
Response with URL
```

### WhatsApp Flow
```
Send Request
    ↓
Check Assignment Status
    ↓
Assign Letter to Phone
    ↓
Fetch Letter Data
    ↓
Send to Webhook (n8n)
    ↓
Rollback on Failure
```

---

## 6. Google Sheets Database

### Spreadsheet: "AI Letter Generating"

#### Submissions Worksheet
| Column | Description |
|--------|-------------|
| Timestamp | Creation date/time |
| Type of Letter | Category |
| Recipient | Letter recipient |
| Title | Letter title |
| First Time? | Yes/No flag |
| Content | Full letter text |
| URL | Google Drive link |
| Revision | Status |
| ID | Unique ID (YYMMDD-XXXXX) |
| Username | Creator name |

#### WhatApp Worksheet
| Column | Description |
|--------|-------------|
| Name | Signer name |
| Number | Phone number |
| Letter_Id | Assigned letter |
| Title | Signer job title |
| Sign | Signature image URL |

#### Instructions Worksheet
| Column | Description |
|--------|-------------|
| Category | Letter type or "الجميع" |
| Instruction | Writing guideline |

#### Ideal Worksheet
| Column | Description |
|--------|-------------|
| Category | Letter type |
| Letter | Reference letter |

#### Poc Worksheet
| Column | Description |
|--------|-------------|
| Member Name | Member identifier |
| Member Info | Contact/role info |

---

## 7. Configuration

### Environment Variables (.env)
```bash
# Required
OPENAI_API_KEY=sk-proj-...
GOOGLE_DRIVE_FOLDER_ID=1sTgG5h1MXx_C3OY6hPgWMbzdyES89Z_k

# Optional
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=Ai Letter
DEBUG_MODE=false
HOST=0.0.0.0
PORT=5000
CORS_ORIGINS=*
LOG_LEVEL=INFO
```

### Service Account
- **File:** `automating-letter-creations.json`
- **Scopes:** Drive, Sheets
- **Never commit to git**

### Key Settings
```python
# AI
model_name = "gpt-4.1"
temperature = 0.2
timeout = 30s

# Chat
session_timeout = 60 minutes
memory_window = 10 messages
cleanup_interval = 5 minutes

# Files
max_content_length = 16MB
pdf_retention = 24 hours
```

---

## 8. Deployment

### 8.1 Backend Deployment (Shobbak Server)


#### Installation Steps
```bash
# 1. Clone repository
cd /var/www/
git clone <repository-url> AutomatingLetter
cd AutomatingLetter

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Create required directories
mkdir -p logs data LetterToPdf/templates

# 6. Configure environment
cp .env.example .env
nano .env  # Add your keys

# 7. Add service account credentials
# Upload automating-letter-creations.json to project root

# 8. Set permissions
chmod 600 automating-letter-creations.json
chmod 755 app.py
```

#### Running the Server

**Development:**
```bash
python app.py
```

**Production with Gunicorn:**
```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

**Production with systemd:**
```ini
# /etc/systemd/system/automating-letter.service
[Unit]
Description=Automating Letter API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/AutomatingLetter
Environment="PATH=/var/www/AutomatingLetter/venv/bin"
ExecStart=/var/www/AutomatingLetter/venv/bin/gunicorn \
    -w 4 \
    -b 0.0.0.0:5000 \
    --timeout 120 \
    --log-level info \
    app:app

Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable automating-letter
sudo systemctl start automating-letter
sudo systemctl status automating-letter
```

## 9. Monitoring & Maintenance

### Health Checks
```bash
# Global health
curl https://api.yourdomain.com/health

# Service-specific
curl https://api.yourdomain.com/api/v1/letter/health
curl https://api.yourdomain.com/api/v1/chat/health
curl https://api.yourdomain.com/api/v1/archive/health
```

### Logs
```bash
# Application logs
tail -f logs/app.log

# System service logs
sudo journalctl -u automating-letter -f

```

### Cleanup Tasks
```bash
# Clean old PDFs (automatic via service)
# Clean expired sessions (automatic every 5 min)

# Manual cleanup
curl -X POST https://api.yourdomain.com/api/v1/chat/cleanup
```


---

## 10. Troubleshooting

### Common Issues


#### 1. Google Sheets Connection Error
**Symptom:** "Failed to access Google Sheets"

**Solutions:**
```bash
# Verify service account file
ls -la automating-letter-creations.json

# Check permissions
chmod 600 automating-letter-creations.json

# Verify sheet sharing
# Share spreadsheet with service account email
```

#### 2. OpenAI API Errors
**Symptom:** "AI service unavailable"

**Solutions:**
```bash
# Verify API key
grep OPENAI_API_KEY .env

# Check quota
# Visit OpenAI dashboard

# Verify connectivity
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### 3. Session Not Found
**Symptom:** "Session expired or not found"

**Solutions:**
```bash
# Check session file
cat data/chat_sessions.json

# Verify cleanup interval
# Sessions expire after 60 minutes

# Extend session before expiry
curl -X POST https://api.yourdomain.com/api/v1/chat/sessions/{id}/extend
```

#### 4. WhatsApp Webhook Failure
**Symptom:** "Webhook delivery failed"

**Solutions:**
```bash
# Verify webhook URL
# Check n8n workflow status

# Test webhook manually
curl -X POST https://superpowerss.app.n8n.cloud/webhook/send \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Check rollback in logs
grep "Rollback" logs/app.log
```

---

## 11. Security Best Practices

### Credentials
- ✅ Never commit `.env` or `*.json` credentials
- ✅ Use environment variables for secrets
- ✅ Restrict service account permissions
- ✅ Rotate API keys regularly

### API Security
- ✅ Enable HTTPS only (SSL/TLS)
- ✅ Configure CORS properly
- ✅ Validate all inputs
- ✅ Sanitize user data
- ✅ Implement rate limiting (future)

### File Security
- ✅ Restrict file upload sizes (16MB)
- ✅ Validate file types
- ✅ Clean up temp files
- ✅ Use secure temp directories

### Server Security
- ✅ Run as non-root user (www-data)
- ✅ Keep dependencies updated
- ✅ Enable firewall (UFW/iptables)
- ✅ Monitor logs for anomalies

---

## 12. Performance Optimization

### Current Optimizations
- **Connection Pooling:** Google Sheets (1-hour lifetime)
- **Parallel Fetching:** Sheet data with ThreadPoolExecutor
- **Caching:** Memory service (5-minute TTL)
- **Background Processing:** Archiving, cleanup
- **Debounced Saves:** Session data (1-second delay)
- **File Cleanup:** 24-hour PDF retention

### Scaling Recommendations
- **Database:** Migrate to PostgreSQL/MongoDB for sessions
- **Caching:** Add Redis for sheets data
- **Queue:** Use Celery for background tasks
- **Load Balancer:** NGINX for multiple workers
- **CDN:** CloudFlare for static assets

---

## 13. API Response Examples

### Success Response
```json
{
  "ID": "251214-12345",
  "Title": "طلب موافقة على مشروع",
  "Letter": "بسم الله الرحمن الرحيم...",
  "Date": "١٤ ديسمبر ٢٠٢٥"
}
```

### Error Response
```json
{
  "error": "Validation error",
  "message": "Category is required",
  "details": [
    {
      "field": "category",
      "message": "Field required"
    }
  ]
}
```

### Processing Response
```json
{
  "status": "processing",
  "message": "Letter is being archived",
  "processing": "Letter archiving initiated for ID: 251214-12345"
}
```

---

## 14. Rate Limits & Quotas

### Current Limits
- **Request Size:** 16MB max
- **Session Timeout:** 60 minutes
- **Max Sessions:** 100 concurrent
- **PDF Retention:** 24 hours
- **Memory Window:** 10 messages

### OpenAI Quotas
- **RPM:** Depends on account tier
- **TPM:** Depends on account tier
- **Monitor:** OpenAI dashboard

### Google API Quotas
- **Sheets Read:** 300 requests/minute
- **Sheets Write:** 300 requests/minute
- **Drive Upload:** 1000 requests/day (default)

---

## 15. Quick Reference

### Important Files
```
app.py                              # Main entry point
.env                                # Environment config
automating-letter-creations.json    # Service account
requirements.txt                    # Dependencies
logs/app.log                        # Application logs
data/chat_sessions.json             # Session storage
```

### Important Directories
```
src/api/          # API routes
src/services/     # Business logic
src/config/       # Configuration
src/models/       # Data models
src/utils/        # Utilities
LetterToPdf/      # Templates
docs/             # Documentation
```

### Key Commands
```bash
# Start server
python app.py

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# View logs
tail -f logs/app.log

# Health check
curl http://localhost:5000/health

# Cleanup sessions
curl -X POST http://localhost:5000/api/v1/chat/cleanup
```

---

## 16. Support & Resources


### Getting Help
1. Check logs: `logs/app.log`
2. Review documentation: `docs/`
3. Test endpoints: Use Postman collection
4. Verify configuration: Check `.env` and service account

---
