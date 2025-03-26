import os
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from datetime import datetime

def generate_arabic_letter(
    user_prompt: str, 
    reference_letter: str = None,
    title: str = None,
    recipient: str = None
) -> str:
   
    # Validate inputs
    if not user_prompt:
        raise ValueError("prompt is required for generating the letter.")

    # Initialize the language model
    llm = ChatOpenAI(model_name="gpt-4o", temperature=0.2)

    # Prepare additional context if title or recipient are provided
    additional_context = ""
    if title:
        additional_context += f"\nالعنوان أو المسمى الوظيفي: {title}"
    if recipient:
        additional_context += f"\nالمرسل إليه: {recipient}"

    # Add current date in Arabic
    current_date = datetime.now().strftime("%d %B %Y")
    additional_context += f"\nالتاريخ: {current_date}"

    # Create a comprehensive prompt template for Arabic letter
    prompt_template = PromptTemplate(
        template="""قم بإنشاء خطاب رسمي احترافي بناءً على التعليمات التالية:
التعليمات المقدمة: {user_prompt}
{reference_context}
{additional_context}

إرشادات كتابة الخطاب:
- التزم بأسلوب رسمي ومهني
- استخدم لغة عربية فصحى واضحة ودقيقة
- راعي القواعد التالية عند كتابة الخطاب:
  * ضع العنوان الكامل للمرسل إليه
  * اكتب التاريخ بالطريقة العربية
  * استخدم التحية المناسبة
  * اكتب متن الخطاب بشكل منظم وواضح
  * اختتم الخطاب بعبارة مناسبة
يُرجى مراعاة الدقة والأسلوب المهني في صياغة الخطاب:
""",
        input_variables=["user_prompt", "reference_context", "additional_context"]
    )

    # Prepare the reference context
    reference_context = (
        f"دليل أسلوب الخطاب المرجعي:\n{reference_letter}" 
        if reference_letter 
        else "لم يتم تقديم خطاب مرجعي. يُستخدم التنسيق القياسي للخطابات الرسمية."
    )

    # Generate the letter
    try:
        # Combine the prompt template with the language model
        letter_chain = prompt_template | llm

        # Generate the letter
        letter_response = letter_chain.invoke({
            "user_prompt": user_prompt,
            "reference_context": reference_context,
            "additional_context": additional_context
        })
        
        return letter_response.content
    except Exception as e:
        # Detailed error handling with Arabic error message
        error_message = f"error in generating the letter: {str(e)}"
        raise ValueError(error_message)
    
