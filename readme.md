## 🔧 **Project Name**: Automating Letter with AI  
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