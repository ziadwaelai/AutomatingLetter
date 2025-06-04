import os
import uuid
import json
import re
import random
from datetime import datetime
from typing import Optional, Dict, Any, Union

from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from google_services import log

# Constants
DEFAULT_MODEL = "gpt-4.1-2025-04-14"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_WRITING_INSTRUCTIONS = "Please ensure the letter is formal, clear, and adheres to the standard Arabic letter format."
DEFAULT_REFERENCE_CONTEXT = "Use a standard Arabic formal letter format if no style reference is provided."
DEFAULT_TONE = "رسمي"  # Default formal tone
DATE_FORMAT = "%d %B %Y"
LOG_SPREADSHEET = "AI Letter Generating"
LOG_WORKSHEET = "Logs"

# ID Generation
class IDGenerator:
    @staticmethod
    def generate_id() -> str:
        """Generate a random ID in the format AIZ-YYYYMMDD-XXXX."""
        today = datetime.now().strftime("%Y%m%d")
        random_num = random.randint(1, 9999)  # Generate random number between 1 and 9999
        counter = str(random_num).zfill(4)  # Pad with zeros to ensure 4 digits
        return f"AIZ-{today}-{counter}"

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY is missing. Please set it in your environment variables.")


class LetterOutput(BaseModel):
    """Pydantic model for letter generation output."""
    ID: str = Field(default_factory=IDGenerator.generate_id)
    Title: str
    Letter: str
    Date: str


class ArabicLetterGenerator:
    """Class to handle Arabic letter generation using LLM."""
    
    def __init__(self, model_name: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE):
        """Initialize the generator with model configuration."""
        self.llm = ChatOpenAI(
            model_name=model_name, 
            temperature=temperature, 
            openai_api_key=OPENAI_API_KEY
        )
        self.prompt_template = self._build_prompt_template()
        
    def _build_prompt_template(self) -> PromptTemplate:
        """Return a prompt template for generating formal Arabic letters."""
        json_parser = JsonOutputParser(pydantic_object=LetterOutput)
        format_instructions = json_parser.get_format_instructions()
        
        template = """
أنت كاتب خطابات محترف. مهمتك كتابة خطاب رسمي باللغة العربية الفصحى، مع الالتزام الكامل بالأسلوب الرسمي والهيكل الاحترافي.

# تفاصيل الخطاب:
- **الغرض/الموضوع:** {user_prompt}
- **النموذج المرجعي:** {reference_context}
- **العناصر السياقية:** {additional_context}
- **نبرة الخطاب:** {tone}

# تعليمات الكتابة:
{writing_instructions}

## الشروط:
- استخدم لغة عربية فصحى رسمية وواضحة.
- اتبع الهيكل والأسلوب الموجود في الخطاب المرجعي (إن وجد)، إلا إذا طلب المستخدم خلاف ذلك.
- التزم بجميع التعليمات المذكورة أعلاه بدقة.
- لا تخرج عن موضوع الخطاب أو تضف معلومات غير مطلوبة.

## ملاحظات:
- إذا لم يوجد نموذج مرجعي، استخدم أفضل الممارسات في كتابة الخطابات الرسمية العربية.
- إذا كان هذا أول تواصل مع الجهة، وضّح ذلك في الخطاب.

تأكد من أن المخرجات تتبع هذا التنسيق بدقة، وأن النص مكتوب بشكل صحيح باللغة العربية الفصحى.
# هام جداً: يجب أن يكون الرد بتنسيق JSON محدد كالتالي:
{format_instructions}
```json
"""
        return PromptTemplate(
            template=template,
            input_variables=[
                "user_prompt",
                "reference_context",
                "additional_context",
                "writing_instructions",
                "format_instructions",
                "tone"
            ]
        )
        
    def _build_additional_context(
        self, 
        title: Optional[str], 
        recipient: Optional[str], 
        is_first_contact: bool
    ) -> str:
        """Construct additional context for the letter."""
        context_parts = []
        if title:
            context_parts.append(f"Letter Title: {title}")
        if recipient:
            context_parts.append(f"Recipient: {recipient}")
        if is_first_contact:
            context_parts.append("هذا أول تواصل مع الجهة")
        context_parts.append(f"التاريخ: {datetime.now().strftime(DATE_FORMAT)}")
        return "\n".join(context_parts)
    
    def _parse_llm_response(self, content: str, letter_id: str, title: Optional[str] = None, user_prompt: str = "") -> Dict[str, Any]:
        """Parse the LLM response and handle JSON extraction."""
        try:
            # First try direct parsing
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON using regex
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # If all parsing fails, create fallback structure
            return {
                "Title": title or user_prompt[:50],
                "Letter": content,
                "Date": datetime.now().strftime(DATE_FORMAT),
                "ID": letter_id
            }
    
    def _log_letter_generation(self, user_prompt: str, letter_data: Dict[str, Any], 
                              title: Optional[str], recipient: Optional[str], 
                              tone: str, is_first_contact: bool, category: str, sub_category: str) -> None:
        """Log letter generation details to Google Sheets."""
        try:
            # Prepare data for logging
            request_data = {
                "prompt": user_prompt,
                "title": title,
                "recipient": recipient,
                "tone": tone,
                "is_first_contact": is_first_contact,
                "category": category,
                "sub_category": sub_category
            }
            
            response_data = {
                "title": letter_data.get("Title", ""),
                "id": letter_data.get("ID", ""),
                "date": letter_data.get("Date", ""),
                "letter_preview": letter_data.get("Letter", "") + "..." if letter_data.get("Letter") else ""
            }
            
            # Convert to JSON strings
            request_json = json.dumps(request_data, ensure_ascii=False)
            response_json = json.dumps(response_data, ensure_ascii=False)
            
            log(
                spreadsheet_name=LOG_SPREADSHEET,
                worksheet_name=LOG_WORKSHEET,
                entries=[{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Request": request_json,
                    "Response": response_json,
                    "ID": letter_data.get("ID", "")
                }]
            )
        except Exception as e:
            print(f"Error logging letter generation: {str(e)}")
        
    def generate_letter(
        self,
        user_prompt: str,
        reference_letter_context: Optional[str] = None,
        title: Optional[str] = None,
        recipient: Optional[str] = None,
        writing_instructions: Optional[str] = None,
        is_first_contact: bool = False,
        tone: Optional[str] = None,
        category: str = "",
        sub_category: str = ""
    ) -> LetterOutput:
        """
        Generate a consistent, professional Arabic letter.

        Args:
            user_prompt: Main instruction describing what the letter should say.
            reference_letter_context: A model letter to guide style and structure.
            title: Title of the letter (e.g., "طلب شهادة خبرة").
            recipient: Name of the recipient.
            writing_instructions: Explicit instructions for tone, structure, and style.
            is_first_contact: Whether this is the first communication with the recipient.
            tone: The tone of the letter (e.g., "رسمي", "ودي", "حازم").
            category: Category of the letter (e.g., "business", "personal").
            sub_category: Sub-category of the letter.

        Returns:
            LetterOutput: Pydantic model with ID, Title, Letter content, and Date.
            
        Raises:
            ValueError: If no prompt is provided.
            RuntimeError: If letter generation fails.
        """
        if not user_prompt:
            raise ValueError("A prompt is required to generate the letter.")

        # Apply defaults for optional parameters
        writing_instructions = writing_instructions or DEFAULT_WRITING_INSTRUCTIONS
        tone = tone or DEFAULT_TONE
        reference_context = reference_letter_context or DEFAULT_REFERENCE_CONTEXT
        
        try:
            # Generate a unique ID for this letter
            letter_id = IDGenerator.generate_id()
            
            # Prepare context and parameters
            additional_context = self._build_additional_context(
                title, recipient, is_first_contact
            )
            
            # Get format instructions for JSON output
            json_parser = JsonOutputParser(pydantic_object=LetterOutput)
            format_instructions = json_parser.get_format_instructions()
            
            # Create and execute the chain
            chain = self.prompt_template | self.llm
            result = chain.invoke({
                "user_prompt": user_prompt,
                "reference_context": reference_context,
                "additional_context": additional_context,
                "writing_instructions": writing_instructions,
                "format_instructions": format_instructions,
                "tone": tone
            })
            
            # Extract JSON from the response
            content = result.content
            letter_data = self._parse_llm_response(content, letter_id, title, user_prompt)
            
            # Ensure ID exists and is not empty
            if not letter_data.get("ID"):
                letter_data["ID"] = letter_id
            
            # Log the letter generation
            self._log_letter_generation(
                user_prompt=user_prompt,
                letter_data=letter_data,
                title=title,
                recipient=recipient,
                tone=tone,
                is_first_contact=is_first_contact,
                category=category,
                sub_category=sub_category
            )
            
            # Create and return the Pydantic model with guaranteed ID
            return LetterOutput(
                Title=letter_data.get("Title", title or user_prompt[:50]),
                Letter=letter_data.get("Letter", content),
                Date=letter_data.get("Date", datetime.now().strftime(DATE_FORMAT)),
                ID=letter_data.get("ID", letter_id)
            )

        except Exception as e:
            raise RuntimeError(f"Letter generation failed: {str(e)}")
