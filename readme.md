## AutomatingLetter - AI-Powered Arabic Letter Generation API

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/your-repo/AutomatingLetter)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-2.x-red.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Modern, AI-powered Arabic letter generation system with interactive editing, PDF creation, and Google Workspace integration.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API Key
- Google Service Account (for Sheets/Drive integration)

### Installation
```bash
# Clone repository
git clone https://github.com/your-repo/AutomatingLetter.git
cd AutomatingLetter

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys and settings
```

### Configuration
Set these required environment variables:
```bash
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id
```

### Run Application
```bash
# Development server
python app.py

# Production server (with Gunicorn)
gunicorn --workers 4 --bind 0.0.0.0:5000 app:get_app
```

The API will be available at `http://localhost:5000`

## 🌟 Key Features

- 🤖 **AI-Powered Generation**: GPT-4 integration for high-quality Arabic letters
- 💬 **Interactive Editing**: Chat-based letter refinement with session management
- 📄 **PDF Generation**: Custom-templated PDF creation with Arabic support
- 📁 **Google Integration**: Seamless Sheets and Drive integration for storage
- 🔄 **RESTful API**: Clean, versioned API with comprehensive error handling
- 🏗️ **Modular Architecture**: Service-oriented design for scalability

## 📚 Documentation

- **[Complete Project Documentation](docs/COMPLETE_PROJECT_DOCUMENTATION.md)** - Comprehensive project overview
- **[API Documentation](docs/API_DOCUMENTATION.md)** - Detailed API reference
- **[Postman Testing Guide](docs/POSTMAN_TESTING_GUIDE.md)** - Complete testing guide

## 🔧 API Endpoints

### Letter Generation
```bash
POST /api/v1/letter/generate      # Generate new letter
POST /api/v1/letter/validate      # Validate letter content  
GET  /api/v1/letter/categories    # Get available categories
GET  /api/v1/letter/templates/{category} # Get category template
```

### Interactive Chat Editing
```bash
POST   /api/v1/chat/sessions                    # Create chat session
POST   /api/v1/chat/sessions/{id}/edit          # Edit letter via chat
GET    /api/v1/chat/sessions/{id}/history       # Get chat history
GET    /api/v1/chat/sessions/{id}/status        # Get session status
DELETE /api/v1/chat/sessions/{id}               # Delete session
```

### Letter Archiving
```bash
POST /api/v1/archive/letter           # Archive letter to PDF & Drive
GET  /api/v1/archive/status/{id}      # Get archive status
```

### System Health
```bash
GET /health                           # Overall system health
GET /api/v1/letter/health            # Letter service health
GET /api/v1/chat/health              # Chat service health
GET /api/v1/archive/health           # Archive service health
```

## 💡 Usage Examples

### Generate Letter
```bash
curl -X POST http://localhost:5000/api/v1/letter/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "اكتب خطاباً رسمياً للجامعة",
    "recipient": "عميد الجامعة", 
    "category": "academic",
    "is_first": true
  }'
```

### Edit Letter via Chat
```bash
# 1. Create session
curl -X POST http://localhost:5000/api/v1/chat/sessions

# 2. Edit letter
curl -X POST http://localhost:5000/api/v1/chat/sessions/{session_id}/edit \
  -H "Content-Type: application/json" \
  -d '{
    "message": "اجعل الخطاب أكثر رسمية",
    "current_letter": "محتوى الخطاب الحالي..."
  }'
```

### Archive Letter
```bash
curl -X POST http://localhost:5000/api/v1/archive/letter \
  -H "Content-Type: application/json" \
  -d '{
    "letter_content": "محتوى الخطاب الكامل...",
    "ID": "LETTER_20250817_001",
    "letter_type": "academic"
  }'
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Layer     │    │  Service Layer  │    │ External APIs   │
│                 │    │                 │    │                 │
│ ▪ Letter Routes │───▶│ ▪ Letter Gen    │───▶│ ▪ OpenAI GPT-4  │
│ ▪ Chat Routes   │───▶│ ▪ Chat Service  │───▶│ ▪ Google Sheets │
│ ▪ Archive Routes│───▶│ ▪ PDF Service   │───▶│ ▪ Google Drive  │
│ ▪ Health Routes │───▶│ ▪ Memory Service│    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Tech Stack

- **Backend**: Flask 2.x with service-oriented architecture
- **AI**: OpenAI GPT-4 via LangChain
- **Storage**: Google Sheets & Drive integration  
- **PDF**: Playwright-based PDF generation with Arabic support
- **Validation**: Pydantic for request/response validation
- **Logging**: Comprehensive logging with multiple outputs

## 🔒 Security & Configuration

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your_openai_api_key
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id

# Optional
DEBUG_MODE=false
LOG_LEVEL=INFO
CORS_ORIGINS=*
SECRET_KEY=your_secret_key
```

### Google Service Account
Place your Google service account JSON file as `automating-letter-creations.json` in the project root.

## 📊 Monitoring & Health

The API includes comprehensive health monitoring:
- Service-level health checks
- Performance metrics tracking
- Error rate monitoring
- Memory usage statistics

## 🧪 Testing

### Development Testing
```bash
# Run all tests
python -m pytest tests/

# Test specific service
python -m pytest tests/test_letter_service.py

# Integration tests
python -m pytest tests/integration/
```

### Postman Testing
Import the provided Postman collection:
1. Collection: `docs/postman/AutomatingLetter.postman_collection.json`
2. Environment: `docs/postman/AutomatingLetter.postman_environment.json`

## 🚢 Deployment

### Development
```bash
python app.py
```

### Production
```bash
# Using Gunicorn
gunicorn --workers 4 --bind 0.0.0.0:5000 --timeout 30 app:get_app

# Using Docker
docker build -t automating-letter .
docker run -p 5000:5000 automating-letter
```

## 📈 Performance

- **Response Time**: < 3 seconds for letter generation
- **Throughput**: 100+ concurrent requests supported
- **Scalability**: Horizontal scaling ready
- **Memory**: Optimized memory usage with session cleanup

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT-4 API
- **Google** for Workspace APIs
- **Flask** community for the excellent framework
- **Python** community for comprehensive libraries

## 📞 Support

- **Documentation**: See `docs/` folder for comprehensive guides
- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for feature requests
- **Email**: [your-email@domain.com] for direct support

---

**AutomatingLetter** - Making Arabic letter writing intelligent and effortless.

*Built with ❤️ for the Arabic-speaking community* 🔧 **Project Name**: Automating Letter with AI  
**Summary**: AI-powered tool to auto-generate and manage formal letters using pre-made templates + user input, with storage on Google Drive and enhanced interactive chat for editing.

---

## 🧩 **Main Features & Flow**

### **1. Letter Generation**
- **AI-powered letter generation** using OpenAI GPT models
- **Template-based approach** with category-specific instructions
- **Arabic language support** with formal letter formatting
- **Member-specific customization** with sender information

### **2. Enhanced Interactive Chat System** 🆕
- **Session-based conversations** with memory buffer
- **Contextual letter editing** with conversation history
- **Multi-turn dialogue** for refining letters
- **Automatic session management** with cleanup
- **Thread-safe operations** for concurrent users

### **3. Storage & Management**
- **Google Drive integration** for file storage
- **Google Sheets logging** for tracking and analytics
- **PDF generation** with customizable templates
- **Automated archiving** with metadata

---

## 🔥 **New: Enhanced Interactive Chat**

The project now includes a powerful interactive chat system that allows:

### **Session Management**
- Create chat sessions with unique IDs
- Maintain conversation context across multiple interactions
- Automatic session expiration and cleanup
- Thread-safe concurrent access

### **Contextual Editing**
```http
POST /chat/edit-letter
{
    "session_id": "uuid",
    "letter": "current letter text",
    "feedback": "user feedback"
}
```

### **Question & Answer**
```http
POST /chat/ask
{
    "session_id": "uuid", 
    "question": "How can I make this letter more formal?",
    "current_letter": "letter text"
}
```

### **API Endpoints**
- `POST /chat/session/create` - Create new session
- `POST /chat/edit-letter` - Edit with context
- `POST /chat/ask` - Ask questions
- `GET /chat/session/info/{id}` - Get session info
- `DELETE /chat/session/clear/{id}` - Clear session
- `GET /chat/sessions/count` - Active sessions count

---

## 🤖 **AI Generation Logic**

- Choose the right template based on dropdown
- Append user prompt and feed to AI model
- Generate personalized letter with consistent tone and format
- **Enhanced with memory**: Context-aware editing across conversations
- **Strict instruction following**: Same guidelines as main generator
- Return the letter as editable content in the UI

---

## 📂 **Storage Logic (Google Drive + Sheets)**

- One **Google Drive Folder** to store all letters
- Each letter saved as a file (PDF/Docx)
- One **Google Sheet ("logs")** for tracking:
  | Sheet Name | Date | Time | Link to Letter |
  |------------|------|------|----------------|