import os
import json
import logging
from typing import Dict, Optional
from datetime import datetime
import pytz
from hijri_converter import Gregorian

# AI / LangChain Imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv

# Google Client Imports
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

# --- Configuration ---
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]
SERVICE_ACCOUNT_FILE = 'automating-letter-creations.json'

TEMPLATE_DOC_ID = "1qS8cAX8tFOm4d1Brb5Kpn8loTLrdJc3-XDB6I_7OmA0" 

class LetterContentParser:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API Key is required.")

    def parse(self, content: str) -> Dict[str, str]:
        try:
            llm = ChatOpenAI(model="gpt-4.1", temperature=0.3, openai_api_key=self.api_key)
            prompt = PromptTemplate.from_template("""
أنت مساعد متخصص في تحليل وتنسيق الخطابات الرسمية العربية.

قم بتحليل الخطاب التالي واستخرج المعلومات التالية:

**الخطاب المراد تحليله:**
{letter_content}

استخرج المعلومات التالية وأعد الاستجابة بتنسيق JSON صحيح:

1. **besmallah**: الفقرة الأولى أو بداية الخطاب (عادة "بسم الله الرحمن الرحيم" أو ما يشابهها). إذا لم توجد، استخدم سطر فارغ ""
2. **title**: عنوان الخطاب الرئيسي (REQUIRED - إلزامي). ابحث عن العنوان في:
   - السطور الأولى بعد البسملة
   - أي نص مكتوب بخط عريض أو مميز
   - الموضوع الرئيسي للخطاب
   - إذا لم تجد عنوان واضح، استنتج عنوانًا مناسبًا من محتوى الخطاب (مثل: "طلب...", "إفادة...", "خطاب رسمي...")
   - **يجب أن يكون العنوان موجودًا دائمًا ولا يمكن أن يكون فارغًا**
3. **date**: التاريخ إن وجد (قد يكون في البداية أو النهاية). إذا لم يوجد، استخدم سطر فارغ ""
4. **body**: محتوى الخطاب الرئيسي (REQUIRED - إلزامي). يشمل كل المحتوى بين العنوان والختام
5. **footer**: الختام والتوقيع (عادة في نهاية الخطاب مثل "وتفضلوا بقبول فائق الاحترام والتقدير"). إذا لم يوجد، استخدم سطر فارغ ""

⚠️ **مهم جداً:**
- الحقول **title** و **body** إلزامية ويجب أن تحتوي على قيمة
- إذا لم تجد عنوانًا صريحًا، استنتج عنوانًا من المحتوى
- الحفاظ على الترتيب الطبيعي للخطاب
- استخراج كل جزء بشكل كامل ودقيق
- عدم ترك أي محتوى مهم خارج body
- الحفاظ على التنسيق والأسطر الجديدة

أعد الاستجابة بصيغة JSON فقط (بدون أي نص إضافي):
{{
    "besmallah": "...",
    "title": "...",
    "date": "...",
    "body": "...",
    "footer": "..."
}}
""")
            chain = prompt | llm | JsonOutputParser()
            result = chain.invoke({"letter_content": content})
            if not result.get('title'): result['title'] = "خطاب رسمي"
            return result
        except Exception as e:
            logger.error(f"AI Parsing failed: {e}")
            raise
class GoogleDocsGenerator:
    def __init__(self, service_account_path: str = SERVICE_ACCOUNT_FILE):
        self.creds = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=SCOPES
        )
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.requests = []
        self.doc_id = None

    def create_doc_from_template(self, title: str, template_id: str) -> str:
        """Copies the template to a new file."""
        try:
            body = {'name': title}
            drive_response = self.drive_service.files().copy(
                fileId=template_id, body=body
            ).execute()
            self.doc_id = drive_response.get('id')
            self._set_public_permissions()
            return self.doc_id
        except Exception as e:
            logger.error(f"Failed to copy template: {e}")
            raise

    def _set_public_permissions(self):
        try:
            permission = {'type': 'anyone', 'role': 'writer'}
            self.drive_service.permissions().create(
                fileId=self.doc_id, body=permission, fields='id'
            ).execute()
        except Exception as e:
            logger.error(f"Failed to set permissions: {e}")

    def generate_full_doc(self, data: Dict, letter_id: Optional[str] = None):
        """Generates content matching your python-docx style exactly."""
        
        # 1. Find Start Index
        try:
            doc = self.docs_service.documents().get(documentId=self.doc_id).execute()
            content = doc.get('body').get('content')
            current_index = content[-1]['endIndex'] - 1 
        except:
            current_index = 1 

        self.requests = [] 

        # --- Helper Function with SPACING support ---
        def append_block(text, font_size=12, bold=False, underline=False, 
                         align='START', rtl=True, 
                         line_spacing_pct=100, space_below=0):
            nonlocal current_index
            if not text: return
            
            # Ensure text ends with newline
            content = text + "\n"
            
            # 1. Insert Text
            self.requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': content
                }
            })
            
            end_index = current_index + len(content)

            # 2. Text Style (Bold, Font, Underline)
            self.requests.append({
                'updateTextStyle': {
                    'range': {'startIndex': current_index, 'endIndex': end_index},
                    'textStyle': {
                        'fontSize': {'magnitude': font_size, 'unit': 'PT'},
                        'weightedFontFamily': {'fontFamily': 'Tajawal', 'weight': 700 if bold else 400},
                        'bold': bold,
                        'underline': underline
                    },
                    'fields': 'fontSize,weightedFontFamily,bold,underline'
                }
            })

            # 3. Paragraph Style (Alignment, Bidi, Spacing)
            self.requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': current_index, 'endIndex': end_index},
                    'paragraphStyle': {
                        'direction': 'RIGHT_TO_LEFT' if rtl else 'LEFT_TO_RIGHT',
                        'alignment': align,
                        # Line Spacing: 115 means 1.15
                        'lineSpacing': line_spacing_pct, 
                        # Spacing After Paragraph
                        'spaceBelow': {'magnitude': space_below, 'unit': 'PT'}
                    },
                    'fields': 'direction,alignment,lineSpacing,spaceBelow'
                }
            })
            
            current_index = end_index

        
        # A. Header Info (Single spacing 1.0, No extra space below)
        if letter_id:
            dates = self._get_formatted_dates()
            header_text = f"التاريخ: {dates['hijri']} ھ\nالموافق: {dates['gregorian']} م\nالرقم: {letter_id}"
            append_block(header_text, font_size=10, align='START', rtl=True, line_spacing_pct=100, space_below=0)

        # B. Besmallah (Center, Bold, 1.0 spacing)
        if data.get('besmallah'):
            append_block(data['besmallah'], font_size=16, bold=True, align='CENTER', space_below=12)

        # C. Title (Center, Bold, Underline, 1.0 spacing)
        append_block(data['title'], font_size=16, bold=True, underline=True, align='CENTER', space_below=18)

        # D. Body Content (Sections with 1.15 Spacing)
        body_text = data.get('body', '')
        if body_text:
            # 1. Split by Double Newline to identify sections/paragraphs
            if '\n\n' in body_text:
                paragraphs = body_text.split('\n\n')
            else:
                paragraphs = body_text.splitlines()

            for para in paragraphs:
                cleaned_para = para.strip()
                if not cleaned_para: continue
                
                append_block(
                    cleaned_para, 
                    font_size=14, 
                    align='START', 
                    rtl=True, 
                    line_spacing_pct=115,  # <--- 1.15 Spacing
                )

        # E. Footer
        if data.get('footer'):
            append_block("\n", font_size=12) 
            append_block(data['footer'], font_size=15, align='CENTER', rtl=True, line_spacing_pct=115)

        # F. Signature
        if data.get('include_signature'):
            sig_text = f"\n{data.get('signature_job_title')}\n\n\n{data.get('signature_name')}"
            append_block(sig_text, font_size=14, bold=True, align='END', line_spacing_pct=100)

        # Execute Batch
        if self.requests:
            self.docs_service.documents().batchUpdate(
                documentId=self.doc_id, body={'requests': self.requests}
            ).execute()
            logger.info("Batch update successful.")

        return f"https://docs.google.com/document/d/{self.doc_id}"

    def _get_formatted_dates(self) -> Dict[str, str]:
        try:
            ksa_tz = pytz.timezone('Asia/Riyadh')
            now = datetime.now(ksa_tz)
            g_date = f"{now.day}/{now.month}/{now.year}"
            h = Gregorian(now.year, now.month, now.day).to_hijri()
            h_date = f"{h.day}/{h.month}/{h.year}"
            return {"gregorian": g_date, "hijri": h_date}
        except:
            return {"gregorian": "", "hijri": ""}
class DocumentService:
    def __init__(self):
        self.parser = LetterContentParser()
        self.generator = GoogleDocsGenerator()

    def process_request(self, raw_text: str, letter_id: str, signature_data: Optional[Dict] = None):
        parsed_data = self.parser.parse(raw_text)
        if signature_data:
            parsed_data.update(signature_data)
            parsed_data['include_signature'] = True

        doc_title = f"{parsed_data.get('title', 'Letter')} - {letter_id}"
        
        # IMPORTANT: Use the Template ID here
        self.generator.create_doc_from_template(doc_title, TEMPLATE_DOC_ID)

        doc_url = self.generator.generate_full_doc(parsed_data, letter_id=letter_id)
        return doc_url

    def _parse_raw_letter_content(self, raw_text: str) -> Dict[str, str]:
        """
        Backward compatibility method for parsing raw letter content.
        Uses the LetterContentParser to parse the text.
        """
        self.parsed_data = self.parser.parse(raw_text)
        return self.parsed_data

    def create_from_json(self, parsed_data: Dict, letter_id: str, signature_data: Optional[Dict] = None):
        """
        Backward compatibility method for creating a Google Doc from parsed JSON data.
        """
        # Store parsed data
        self.parsed_data = parsed_data.copy()

        # Merge Signature Data if provided
        if signature_data:
            self.parsed_data.update(signature_data)
            self.parsed_data['include_signature'] = True

        # Create Doc from Template
        doc_title = f"{self.parsed_data.get('title', 'Letter')} - {letter_id}"
        self.generator.create_doc_from_template(doc_title, TEMPLATE_DOC_ID)

        # Generate Content
        self.doc_url = self.generator.generate_full_doc(self.parsed_data, letter_id=letter_id)

    def save(self, output_path: str) -> str:
        """
        Backward compatibility method for saving the document.
        Note: Google Docs API doesn't support direct local file saving.
        This method returns the Google Docs URL instead.
        """
        if not self.doc_url:
            raise ValueError("No document has been created yet. Call create_from_json first.")

        logger.info(f"Document created at Google Docs: {self.doc_url}")
        logger.warning(f"Note: Local file saving to {output_path} is not supported with Google Docs API. Use the Google Docs URL instead.")

        # Return the Google Docs URL
        return self.doc_url




# Factory functions for compatibility with old code
_document_service_instance = None

def get_enhanced_docx_service():
    """
    Factory function to get DocumentService instance.
    Returns the new DocumentService which creates Google Docs.
    """
    global _document_service_instance
    if _document_service_instance is None:
        _document_service_instance = DocumentService()
    return _document_service_instance

# Alias for backward compatibility
CreateDocument = DocumentService
EnhancedDOCXService = DocumentService