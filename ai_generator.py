import os
import json
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from google_services import log 

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import Runnable
import random

# Assuming google_services.log exists. If not, this can be swapped with another logger.
# from google_services import log 

# --- Setup (Can be moved to a separate config.py) ---

# 1. Standardized Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 2. Centralized Configuration
@dataclass
class LetterGeneratorConfig:
    """Configuration settings for the letter generator."""
    model_name: str = "gpt-4.1" 
    temperature: float = 0.1
    date_format: str = "%d %B %Y"
    
    # Default texts
    writing_instructions: str = "Please ensure the letter is formal, clear, and adheres to the standard Arabic letter format."
    reference_context: str = "Use a standard Arabic formal letter format if no style reference is provided."
    default_tone: str = "رسمي"
    
    # Logging Configuration
    log_spreadsheet: str = "AI Letter Generating"
    log_worksheet: str = "Logs"

# --- Utility Functions ---

def generate_letter_id() -> str:
    """Generate a random ID in the format AIZ-YYYYMMDD-XXXXX."""
    # Using a more robust method for random part to ensure 5 digits
    random_part = str(random.randint(0, 99999)).zfill(5)
    date_part = datetime.now().strftime("%Y%m%d")
    return f"AIZ-{date_part}-{random_part}"

# --- Pydantic Output Model ---

class LetterOutput(BaseModel):
    """Pydantic model for the final letter output, including the generated ID."""
    ID: str = Field(description="The unique identifier for the letter.")
    Title: str = Field(description="The title of the letter in Arabic.")
    Letter: str = Field(description="The full content of the letter in formal Arabic.")
    Date: str = Field(description="The date the letter was generated.")

# --- Core Logic ---

class ArabicLetterGenerator:
    """
    An optimized class to generate professional Arabic letters using an LLM.
    
    This class builds a reusable LangChain Expression Language (LCEL) chain 
    for efficient and robust letter generation.
    """
    
    def __init__(self, config: LetterGeneratorConfig = LetterGeneratorConfig()):
        """
        Initializes the generator with a configuration and sets up the LLM chain.
        """
        self.config = config
        self.api_key = self._load_api_key()
        self.parser = JsonOutputParser(pydantic_object=LetterOutput)
        
        # Build the chain once during initialization for efficiency
        self.chain = self._build_chain()

    def _load_api_key(self) -> str:
        """Loads OpenAI API key from environment variables."""
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is missing. Please set it in your environment.")
        return api_key

    def _get_prompt_template(self) -> PromptTemplate:
        """
        Creates and returns a robust prompt template for letter generation.
        This version strictly separates content generation from style guidance.
        """
        template = """
أنت كاتب خطابات محترف ومساعد ذكي لشركة `نت زيرو`. مهمتك هي كتابة خطاب رسمي باللغة العربية بناءً على المعلومات التالية، مع الالتزام الصارم بجميع التعليمات المحددة أدناه.

# المصادر والمعلومات
1. **المحتوى الأساسي (المطلوب كتابته):** {user_prompt}
2. **نموذج للهيكل والأسلوب (للاسترشاد بالشكل فقط):** {reference_context}
3. **سياق إضافي للخطاب الجديد:** {additional_context}
4. **معلومات المُرسِل:** {member_info}
5. **تعليمات الكتابة:** {writing_instructions}
6. **بيانات الخطاب الجديد:**
   - معرف الخطاب: {letter_id}
   - تاريخ اليوم: {current_date}

# تعليمات صارمة يجب اتباعها
1. ✅ **يجب أن يستند الخطاب فقط إلى "المحتوى الأساسي".** لا تستخدم أي معلومة أو فكرة من خارج هذا القسم.
2. ✅ **النموذج المرجعي يستخدم فقط لتقليد الشكل والتنسيق (مقدمة/تنسيق الفقرات/الخاتمة)**، ويُمنع تمامًا الاقتباس أو إعادة صياغة أي جملة، أو أخذ أسماء أو أرقام أو تواريخ منه.
3. ⛔ **لا تضف أي عبارات تهنئة أو مناسبات أو ألقاب بروتوكولية (مثل: "سلمه الله"، "حفظه الله") أو دعاء أو شكر إلا إذا ذُكرت صراحة في "المحتوى الأساسي".** إذا لم يُذكر عيد أو مناسبة فلا تبدأ الخطاب بأي تهنئة.
4. 🧠 **ركّز على إنشاء خطاب جديد بالكامل حول "{user_prompt}" فقط، ولا تقم بتلخيص أو تعديل النموذج المرجعي أو استعارة أي من عناصره النصية.**
5. 📝 **الخطاب يجب أن يكون مفصلًا واحترافيًا، باللغة العربية الفصحى، مع التزام كامل بالمقدمة، عرض الغرض والمناسبة، شرح واضح لأي فعالية أو طلب، وإنهاء الخطاب بصيغة رسمية محترمة (حسب المعطيات).**
6. ⛔ **لا تدخل أي معلومات تواصل (أسماء، أرقام، بريد إلكتروني، توقيعات) إلا من "معلومات المُرسِل"، ولا تفترض أو تستنتج أو تنقل أي بيانات من النموذج المرجعي.**
7. ✅ **ابدأ الخطاب بهذا الترتيب إلزاميًا:** "بسم الله الرحمن الرحيم"، ثم اسم الجهة المخاطبة (حسب بيانات الخطاب أو السياق)، ثم التحية الرسمية ("السلام عليكم ورحمة الله وبركاته")، ثم محتوى الخطاب.
8. ✅ **في إخراج JSON، يجب أن يكون الحقل "Title" عنوانًا مختصرًا دقيقًا للخطاب مستمدًا فقط من "المحتوى الأساسي"، بدون أي عبارات ترحيب أو تهنئة.**
9. ✅ **الإخراج النهائي يجب أن يكون بتنسيق JSON صالح 100% ودون أي نص خارجي أو تعليق، ويطابق المخطط التالي بدقة.**
10. ⛔ **لا تكرر المعلومات داخل الخطاب بأكثر من صياغة.**
11. ✅ **في حال وجود أي تعارض بين التعليمات، الأولوية دائمًا للمحتوى الأساسي.**
12. ⛔ **لا تضف أو تستنتج أي فقرات أو جمل غير منصوص عليها بوضوح في التعليمات أو "المحتوى الأساسي".**

{format_instructions}
"""





        return PromptTemplate.from_template(
            template,
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
    def _build_chain(self) -> Runnable:
        """Constructs the full LCEL chain: prompt -> llm -> parser."""
        prompt = self._get_prompt_template()
        llm = ChatOpenAI(
            model_name=self.config.model_name,
            temperature=self.config.temperature,
            openai_api_key=self.api_key
        )
        # print the prompt template for debugging with data 
        return prompt | llm | self.parser

    def _log_generation(self, request_data: Dict[str, Any], response_data: Dict[str, Any]) -> None:
        """Logs request and response details."""
        try:
            log_entry = {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ID": response_data.get("ID", ""),
                "Request": json.dumps(request_data, ensure_ascii=False),
                "Response": json.dumps(response_data, ensure_ascii=False),
            }
            logger.info(f"Logging generation for ID: {log_entry['ID']}")
            log(
                spreadsheet_name=self.config.log_spreadsheet,
                worksheet_name=self.config.log_worksheet,
                entries=[log_entry]
            )
        except Exception as e:
            logger.error(f"Failed to log letter generation: {e}")

 # --- THIS IS THE UPDATED METHOD ---
    def generate_letter(
        self,
        user_prompt: str,
        recipient: Optional[str] = None,
        member_info: str = "غير محدد",
        is_first_contact: bool = False,
        reference_letter: Optional[str] = None,
        category: str = "General", # Added for better logging
        writing_instructions: Optional[str] = None,
        
    ) -> LetterOutput:
        """
        Generates a professional Arabic letter by invoking the pre-built chain.

        Args:
            user_prompt: Main instruction describing what the letter should say.
            title: Title of the letter (e.g., "طلب شهادة خبرة").
            recipient: Name of the recipient.
            member_info: Information about the sender.
            is_first_contact: Whether this is the first communication with the recipient.
            reference_letter: A model letter to guide style and structure.
            tone: The tone of the letter (e.g., "رسمي", "ودي", "حازم").
            category: Category of the letter for logging purposes.

        Returns:
            A LetterOutput object containing the generated letter details.
            
        Raises:
            ValueError: If the user_prompt is empty.
            RuntimeError: If the LLM fails to generate a valid response.
        """
        if not user_prompt:
            raise ValueError("A prompt is required to generate the letter.")

        letter_id = generate_letter_id()
        current_date = datetime.now().strftime(self.config.date_format)

        context_parts = []
        if recipient: context_parts.append(f"Recipient: {recipient}")
        if is_first_contact: context_parts.append("هذا هو الاتصال الأول مع المستلم.")
        
        input_data = {
            "user_prompt": user_prompt,
            "reference_context": reference_letter or self.config.reference_context,
            "additional_context": "\n".join(context_parts) or "لا توجد سياقات إضافية.",
            "writing_instructions": writing_instructions or self.config.writing_instructions,
            "member_info": member_info,
            "letter_id": letter_id,
            "current_date": current_date
        }

        
        try:
            # The chain returns a dictionary that conforms to the schema
            print("Invoking the chain with input data...")
            parsed_dict = self.chain.invoke(input_data)
            
            # **FIX:** Explicitly create the Pydantic object from the dictionary.
            # This validates the data and gives us the object we expect.
            letter_output = LetterOutput(**parsed_dict)

            # Now, call .model_dump() on the Pydantic object for logging
            self._log_generation(
                request_data={**input_data, "category": category},
                response_data=letter_output.model_dump()
            )
            
            # Return the validated Pydantic object
            return letter_output

        except Exception as e:
            logger.error(f"Letter generation failed for prompt '{user_prompt[:50]}...': {e}")
            raise RuntimeError(f"Failed to generate or parse the letter. Original error: {e}")