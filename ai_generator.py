import os
from datetime import datetime
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY is missing. Please set it in your environment variables.")


def _initialize_model() -> ChatOpenAI:
    """Initialize and return the OpenAI language model."""
    return ChatOpenAI(model_name="gpt-4.1-2025-04-14", temperature=0.3, openai_api_key=OPENAI_API_KEY)


def _build_additional_context(title: str, recipient: str, isFirst: bool) -> str:
    """Construct additional context for the letter, including title, recipient, and current date."""
    context_parts = []
    if title:
        context_parts.append(f"Letter Title: {title}")
    if recipient:
        context_parts.append(f"Recipient: {recipient}")
    if isFirst:
        context_parts.append(f"This is the first communication with the recipient")
    context_parts.append(f"Date: {datetime.now().strftime('%d %B %Y')}")
    return "\n".join(context_parts)


def _build_prompt_template() -> PromptTemplate:
    """Return a prompt template for generating formal Arabic letters."""
    template = """
أنت كاتب خطابات محترف. مهمتك كتابة خطاب رسمي باللغة العربية الفصحى، مع الالتزام الكامل بالأسلوب الرسمي والهيكل الاحترافي.

# تفاصيل الخطاب:
- **الغرض/الموضوع:** {user_prompt}
- **النموذج المرجعي:** {reference_context}
- **العناصر السياقية:** {additional_context}

# تعليمات الكتابة:
{writing_instructions}

## الشروط:
- استخدم لغة عربية فصحى رسمية وواضحة.
- اتبع الهيكل والأسلوب الموجود في الخطاب المرجعي (إن وجد)، إلا إذا طلب المستخدم خلاف ذلك.
- التزم بجميع التعليمات المذكورة أعلاه بدقة.
- لا تخرج عن موضوع الخطاب أو تضف معلومات غير مطلوبة.
- يجب أن يكون الرد عبارة عن نص الخطاب فقط، دون أي شرح أو مقدمات إضافية.

## ملاحظات:
- إذا لم يوجد نموذج مرجعي، استخدم أفضل الممارسات في كتابة الخطابات الرسمية العربية.
- إذا كان هذا أول تواصل مع الجهة، وضّح ذلك في الخطاب.

# أجب فقط بنص الخطاب النهائي باللغة العربية.
"""
    return PromptTemplate(
        template=template,
        input_variables=[
            "user_prompt",
            "reference_context",
            "additional_context",
            "writing_instructions",
            "isFirst"
        ]
    )


def generate_arabic_letter(
    user_prompt: str,
    reference_letter_context: str = None,
    title: str = None,
    recipient: str = None,
    writing_instructions: str = None,
    isFirst: bool = False
) -> str:
    """
    Generate a consistent, professional Arabic letter.

    Args:
        user_prompt (str): Main instruction describing what the letter should say.
        reference_letter (str, optional): A model letter to guide style and structure.
        title (str, optional): Title of the letter (e.g., "طلب شهادة خبرة").
        recipient (str, optional): Name of the recipient.
        writing_instructions (str): Explicit instructions to guide tone, structure, and style.
        isFirst (bool, optional): Whether this is the first communication with the recipient.

    Returns:
        str: The generated Arabic letter.
    """
    if not user_prompt:
        raise ValueError("A prompt is required to generate the letter.")

    if not writing_instructions:
        writing_instructions = (
            "Please ensure the letter is formal, clear, and adheres to the standard Arabic letter format."
        )
        print("No writing instructions provided. Using default instructions.")
    try:
        llm = _initialize_model()
        additional_context = _build_additional_context(title, recipient, isFirst)
        prompt_template = _build_prompt_template()

        reference_context = (
            reference_letter_context
            if reference_letter_context else
            "Use a standard Arabic formal letter format if no style reference is provided."
        )

        chain = prompt_template | llm
        result = chain.invoke({
            "user_prompt": user_prompt,
            "reference_context": reference_context,
            "additional_context": additional_context,
            "writing_instructions": writing_instructions,
            "isFirst": isFirst
        })

        return result.content

    except Exception as e:
        raise RuntimeError(f"Letter generation failed: {e}")
