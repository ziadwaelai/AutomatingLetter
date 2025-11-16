"""
Refactored AI Letter Generation Service
Enhanced version of the original ai_generator.py with better error handling and structure.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import Runnable

from ..config import get_config
from ..models import LetterOutput, LetterCategory
from ..utils import (
    generate_letter_id, 
    get_current_arabic_date,
    handle_ai_service_errors,
    measure_performance,
    ErrorContext,
    AIServiceError,
    ValidationError
)

logger = logging.getLogger(__name__)

@dataclass
class LetterGenerationContext:
    """Context for letter generation with all necessary information."""
    user_prompt: str
    recipient: Optional[str] = None
    member_info: str = "غير محدد"
    is_first_contact: bool = False
    reference_letter: Optional[str] = None
    category: str = "General"
    writing_instructions: Optional[str] = None
    recipient_title: Optional[str] = None
    recipient_job_title: Optional[str] = None
    organization_name: Optional[str] = None
    previous_letter_content: Optional[str] = None
    previous_letter_id: Optional[str] = None
    letter_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate and process context data."""
        if not self.user_prompt or not self.user_prompt.strip():
            raise ValidationError("User prompt is required and cannot be empty")
        
        if self.letter_id is None:
            self.letter_id = generate_letter_id()
        
        # Sanitize inputs
        self.user_prompt = self.user_prompt.strip()
        if self.recipient:
            self.recipient = self.recipient.strip()

class ArabicLetterGenerationService:
    """
    Enhanced Arabic letter generation service with improved error handling and logging.
    """
    
    def __init__(self):
        """Initialize the letter generation service."""
        self.config = get_config()
        self._validate_configuration()
        
        self.parser = JsonOutputParser(pydantic_object=LetterOutput)
        self.chain = self._build_chain()
        
        logger.info("Arabic Letter Generation Service initialized")
    
    def _validate_configuration(self):
        """Validate service configuration."""
        if not self.config.openai_api_key:
            raise AIServiceError("OpenAI API key is not configured")
        
        logger.info(f"Using AI model: {self.config.ai.model_name}")
    
    def _get_memory_instructions(self, context: LetterGenerationContext) -> str:
        """Get formatted memory instructions for the prompt."""
        try:
            from .memory_service import get_memory_service
            memory_service = get_memory_service()
            instructions = memory_service.format_instructions_for_prompt(
                category=context.category,
                session_id=context.session_id
            )
            logger.info(f"Retrieved memory instructions for category='{context.category}', session_id='{context.session_id}': {len(instructions)} chars")
            logger.debug(f"Memory instructions content: {instructions}")
            return instructions
        except Exception as e:
            logger.warning(f"Failed to get memory instructions: {e}")
            return ""
    
    def _get_prompt_template(self) -> PromptTemplate:
        """
        Creates and returns the comprehensive prompt template for letter generation.
        This follows the same strict guidelines as the original ai_generator.py
        """
        template = """
أنت كاتب خطابات محترف ومساعد ذكي لشركة `نت زيرو`. مهمتك هي كتابة خطاب رسمي باللغة العربية بناءً على المعلومات التالية، مع الالتزام الصارم بجميع التعليمات المحددة أدناه.

# المصادر والمعلومات
1. **المحتوى الأساسي (المطلوب كتابته):** {user_prompt}
2. **نموذج للهيكل والأسلوب (للاسترشاد بالشكل فقط):** {reference_context}
3. **سياق إضافي للخطاب الجديد:** {additional_context}
4. **معلومات المُرسِل (يجب دمجها في الخطاب بصياغة رسمية مناسبة):** {member_info}

# تعليمات خاصة حول معلومات التواصل:
- عند الحاجة لإدراج معلومات التواصل، يجب أن تُدمج في سياق الخطاب بصياغة رسمية مناسبة، مثل:
  • "وللاستفسارات أو التنسيق، يُرجى التواصل مع الشخص المسؤول على الرقم: [رقم الجوال]، أو عبر البريد الإلكتروني: [البريد الإلكتروني]"
  • أو: "مدير العمليات في \"نت زيرو\"، هاتف: [رقم الجوال] ، بريد إلكتروني: [البريد الإلكتروني]"
- يُمنع سرد معلومات التواصل بشكل منفصل أو جاف (مثل: "الاسم: ...، البريد الإلكتروني: ...، الجوال: ...")، ويجب دائماً دمجها ضمن جملة رسمية أو فقرة ختامية مناسبة.

5. **تعليمات الكتابة:** {writing_instructions}
6. **بيانات الخطاب الجديد:**
   - معرف الخطاب: {letter_id}
   - تاريخ اليوم: {current_date}
7. {previous_letter_info}

{memory_instructions}

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
10. ⛔ **لا تكرر المعلومات داخل الخطاب بأكثر من صياغة أو تكرار الطلبات أو العبارات في أكثر من فقرة.**
11. ✅ **في حال وجود أي تعارض بين التعليمات، الأولوية دائمًا للمحتوى الأساسي.**
12. ⛔ **لا تضف أو تستنتج أي فقرات أو جمل غير منصوص عليها بوضوح في التعليمات أو "المحتوى الأساسي".**
13. ✅ **في الخاتمة: اكتب كلمات ختامية مهذبة فقط، ولا تدمج موضوعات جديدة أو تبدأ بطلبات إضافية.**
14. ⛔ **تجنب استخدام العبارات التالية أو ما يشابهها في جميع الخطابات: "نتشرف بمخاطبتكم"، "يطيب لنا"، أو أي تعبير مبالغ فيه في التبجيل أو التكلف. استخدم عبارات مباشرة مثل: "نتقدم إليكم بجزيل الشكر" أو "نثمن جهودكم" بحسب السياق.**
15. ✅ **إذا كان الخطاب تهنئة أو مناسبة، اجعل عبارة التهنئة الختامية (مثل "كل عام وأنتم بخير") في سطر مستقل، واحذف أي عبارات رسمية ختامية (مثل: "وتفضلوا بقبول فائق الاحترام والتقدير") من خطابات التهنئة.**
16. ✅ **في الخطابات الرسمية (غير التهنئة)، عند كتابة عبارة الخاتمة (مثل: "وتفضلوا بقبول فائق الاحترام والتقدير")، أضف ثلاث فواصل (،،،) بعد العبارة.**
17. ✅ **قسّم الطلبات والتوصيات إلى فقرات واضحة، وتجنب تكرار نفس الطلب أو التوصية في أكثر من فقرة. حسن الانتقال بين الفقرات بحيث يكون الخطاب متسقاً وسلساً.**
18. ⛔ **يُمنع منعًا باتًا على المساعد إضافة أو افتراض أو استنتاج أي تواريخ أو مواعيد أو أيام أحداث (مثل: "في اليوم الموافق ...") إلا إذا وردت صراحة في "المحتوى الأساسي" المُدخل من المستخدم.**

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
            model=self.config.ai.model_name,
            temperature=self.config.ai.temperature,
            openai_api_key=self.config.openai_api_key,
            timeout=self.config.ai.timeout,
            max_retries=self.config.ai.max_retries
        )
        return prompt | llm | self.parser
    
    def _build_context_string(self, context: LetterGenerationContext) -> str:
        """Build additional context string from generation context."""
        context_parts = []

        if context.recipient:
            context_parts.append(f"المرسل إليه: {context.recipient}")
        if context.recipient_title:
            context_parts.append(f"""تعليمات هامة حول اللقب والدعاء للمرسل إليه:
- اللقب المرسل إليه الخطاب يجب وضعه قبل الاسم: {context.recipient_title}
- يجب وضع الدعاء المناسب للقب المرسل إليه في أقصى اليسار على نفس السطر الذي يظهر فيه اسمه
- صيغة الدعاء المناسب حسب اللقب:
  • أصحاب السمو: يُستخدم معهم دعاء "حفظه الله"
  • السادة: يُستخدم معهم دعاء "سلمهم الله"
  • أصحاب المعالي، معالي، سعادة، وغيرهم من الألقاب المشابهة: يُستخدم معهم دعاء "سلمه الله"
- مثال: سعادة الأستاذ عبدالله محمد                سلمه الله""")
        if context.recipient_job_title:
            context_parts.append(f"""تعليمات هامة حول المخاطبة:
- يجب مراعاة التذكير والتأنيث في الألقاب والوظائف حسب جنس المرسل إليه
- للإناث: استخدم صيغة التأنيث (مثل: مهندسة، دكتورة، أستاذة، مديرة)
- للذكور: استخدم صيغة التذكير (مثل: مهندس، دكتور، أستاذ، مدير)
- أمثلة توضيحية: (مهندسة فاطمة وليس مهندس فاطمة) (الدكتورة نورة وليس الدكتور نورة)
- وظيفة المرسل إليه الخطاب: {context.recipient_job_title}""")
        # if context.organization_name:
        #     context_parts.append(f"اسم المؤسسة: {context.organization_name}")

        if context.is_first_contact:
            try:
                from .google_services import get_sheets_service
                sheets_service = get_sheets_service()
                intro_text = sheets_service.get_intro_text()

                if intro_text:
                    context_parts.append(intro_text)
                    logger.debug("Intro text loaded from Intro worksheet")
                else:
                    logger.warning("No intro text found in Intro worksheet, using fallback text")
                    context_parts.append("هذا هو الاتصال الأول مع المستلم.")
            except Exception as e:
                logger.error(f"Failed to fetch intro text from sheet: {e}, using fallback text")
                context_parts.append("هذا هو الاتصال الأول مع المستلم.")
        else:
            context_parts.append("توجد مراسلات سابقة مع الجهة المذكورة")
        
        return "\n".join(context_parts) if context_parts else "لا توجد سياقات إضافية."
    
    def _build_previous_letter_info(self, context: LetterGenerationContext) -> str:
        """Build previous letter information string."""
        if context.previous_letter_content and context.previous_letter_id:
            return f"""**معلومات الخطاب السابق:**
- معرف الخطاب السابق: {context.previous_letter_id}
- محتوى الخطاب السابق (للسياق فقط): {context.previous_letter_content[:500]}...
- تعليمة: استخدم هذه المعلومات للسياق وتجنب التكرار، ولكن لا تقتبس منها مباشرة."""
        return ""
    
    @handle_ai_service_errors
    @measure_performance
    def generate_letter(self, context: LetterGenerationContext) -> LetterOutput:
        """
        Generate a professional Arabic letter using the provided context.
        
        Args:
            context: Letter generation context with all necessary information
            
        Returns:
            LetterOutput containing the generated letter
            
        Raises:
            AIServiceError: If letter generation fails
            ValidationError: If context validation fails
        """
        with ErrorContext("letter_generation", {"letter_id": context.letter_id, "category": context.category}):
            # Prepare input data for the chain
            input_data = {
                "user_prompt": context.user_prompt,
                "reference_context": context.reference_letter or "استخدم تنسيق الخطاب الرسمي العربي القياسي",
                "additional_context": self._build_context_string(context),
                "writing_instructions": context.writing_instructions or "اكتب خطاباً رسمياً واضحاً ومهنياً",
                "member_info": context.member_info,
                "letter_id": context.letter_id,
                "current_date": get_current_arabic_date(),
                "previous_letter_info": self._build_previous_letter_info(context),
                "memory_instructions": self._get_memory_instructions(context)
            }
            
            logger.info(f"Generating letter with ID: {context.letter_id}")
            logger.debug(f"Input data prepared for letter generation: {list(input_data.keys())}")
            logger.debug(f"Memory instructions being used: '{input_data['memory_instructions']}'")
            
            try:
                # Invoke the chain
                result = self.chain.invoke(input_data)
                
                # Handle different result types from LangChain
                if isinstance(result, dict):
                    # JsonOutputParser returned a dictionary, convert to LetterOutput
                    try:
                        result = LetterOutput(**result)
                    except Exception as e:
                        logger.error(f"Failed to convert dict result to LetterOutput: {e}")
                        logger.error(f"Result data: {result}")
                        raise AIServiceError(f"Invalid result format from AI service: {str(e)}")
                elif isinstance(result, LetterOutput):
                    # Already a LetterOutput object
                    pass
                else:
                    # Unexpected type
                    logger.error(f"Unexpected result type: {type(result)}, value: {result}")
                    raise AIServiceError(f"Invalid response type: {type(result)}")
                
                # Additional validation
                if not result.Letter or len(result.Letter.strip()) < 50:
                    raise AIServiceError("Generated letter is too short or empty")
                
                logger.info(f"Letter generated successfully: {result.ID}")
                return result
                
            except Exception as e:
                logger.error(f"Letter generation failed for ID {context.letter_id}: {e}")
                raise AIServiceError(f"Failed to generate letter: {str(e)}")
    
    def validate_letter_content(self, letter: LetterOutput) -> bool:
        """
        Validate generated letter content meets quality standards.
        
        Args:
            letter: Generated letter to validate
            
        Returns:
            True if letter meets standards, False otherwise
        """
        try:
            # Check required elements
            required_elements = [
                "بسم الله الرحمن الرحيم",
                "السلام عليكم"
            ]
            
            content_lower = letter.Letter.lower()
            has_required = any(element.lower() in content_lower for element in required_elements)
            
            # Check minimum length
            min_length = len(letter.Letter.strip()) >= 100
            
            # Check has Arabic content
            has_arabic = any('\u0600' <= char <= '\u06FF' for char in letter.Letter)
            
            return has_required and min_length and has_arabic
            
        except Exception as e:
            logger.warning(f"Letter validation failed: {e}")
            return False
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics and health information."""
        return {
            "service": "ArabicLetterGenerationService",
            "model": self.config.ai.model_name,
            "temperature": self.config.ai.temperature,
            "timeout": self.config.ai.timeout,
            "status": "healthy"
        }

# Global service instance
_letter_service = None

def get_letter_service() -> ArabicLetterGenerationService:
    """Get the global letter generation service instance."""
    global _letter_service
    if _letter_service is None:
        _letter_service = ArabicLetterGenerationService()
    return _letter_service
