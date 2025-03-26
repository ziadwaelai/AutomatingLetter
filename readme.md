## 🔧 **Project Name**: Automating Letter with AI  
**Summary**: AI-powered tool to auto-generate and manage formal letters using pre-made templates + user input, with storage on Google Drive.

---

## 🧩 **Main Features & Flow**

### **1. UI (User Interface)**

#### Components:
- **Dropdown Menu**: Choose letter type/category (e.g., President, HR, Finance, etc.)
- **Prompt Input Box**: User writes the purpose/details of the letter  
  _Example: "اكتب خطاب لي رئيس مجلس الإدارة لتهنئة عيد الفطر"_

- **Generate Button**: Sends template + user prompt to AI for generating the letter

- **Letter Preview Section**:  
  Display the generated letter and allow manual edits  
  (e.g., WYSIWYG editor or simple text area with formatting options)

- **Save Button**:  
  Once finalized, clicking "Save" will:
  - Save the letter (PDF/Docx format) into a specific Google Drive folder
  - Log metadata (Sheet name, Date, Time, Link) into a **Google Sheet** called `logs`

---

## 🤖 **AI Generation Logic**

- Choose the right template based on dropdown
- Append user prompt and feed to AI model
- Generate personalized letter with consistent tone and format
- Return the letter as editable content in the UI

---

## 📂 **Storage Logic (Google Drive + Sheets)**

- One **Google Drive Folder** to store all letters
- Each letter saved as a file (PDF/Docx)
- One **Google Sheet ("logs")** for tracking:
  | Sheet Name | Date | Time | Link to Letter |
  |------------|------|------|----------------|