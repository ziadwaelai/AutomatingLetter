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
    return ChatOpenAI(model_name="gpt-4o", temperature=0, openai_api_key=OPENAI_API_KEY)


def _build_additional_context(title: str, recipient: str) -> str:
    """Construct additional context for the letter, including title, recipient, and current date."""
    context_parts = []
    if title:
        context_parts.append(f"Letter Title: {title}")
    if recipient:
        context_parts.append(f"Recipient: {recipient}")
    context_parts.append(f"Date: {datetime.now().strftime('%d %B %Y')}")
    return "\n".join(context_parts)


def _build_prompt_template() -> PromptTemplate:
    """Return a prompt template for generating formal Arabic letters."""
    template = """
You are a professional Arabic letter writer. Generate a letter using Modern Standard Arabic, maintaining a formal and consistent tone and structure.

Letter Details:
Prompt: {user_prompt}
Style Reference: {reference_context}
Context: {additional_context}

Writing Instructions:
{writing_instructions}

Make sure to:
- Follow a clear and professional format
- Use polished and precise language
- Reflect the tone and structure seen in the reference letter, unless overridden by user input
"""
    return PromptTemplate(
        template=template,
        input_variables=["user_prompt", "reference_context", "additional_context", "writing_instructions"]
    )


def generate_arabic_letter(
    user_prompt: str,
    reference_letter: str = None,
    title: str = None,
    recipient: str = None,
    writing_instructions: str = None
) -> str:
    """
    Generate a consistent, professional Arabic letter.

    Args:
        user_prompt (str): Main instruction describing what the letter should say.
        reference_letter (str, optional): A model letter to guide style and structure.
        title (str, optional): Title of the letter (e.g., "طلب شهادة خبرة").
        recipient (str, optional): Name of the recipient.
        writing_instructions (str): Explicit instructions to guide tone, structure, and style.

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
        additional_context = _build_additional_context(title, recipient)
        prompt_template = _build_prompt_template()

        reference_context = (
            reference_letter
            if reference_letter else
            "Use a standard Arabic formal letter format if no style reference is provided."
        )

        chain = prompt_template | llm
        result = chain.invoke({
            "user_prompt": user_prompt,
            "reference_context": reference_context,
            "additional_context": additional_context,
            "writing_instructions": writing_instructions
        })

        return result.content

    except Exception as e:
        raise RuntimeError(f"Letter generation failed: {e}")
