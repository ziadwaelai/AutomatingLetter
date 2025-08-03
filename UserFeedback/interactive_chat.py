import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it in your .env file.")

chat = ChatOpenAI(model="gpt-4.1", temperature=0.2, openai_api_key=os.getenv("OPENAI_API_KEY"))
def edit_letter_based_on_feedback(letter: str, feedback: str) -> str:
    prompt = PromptTemplate(
        input_variables=["letter", "feedback"],
        template="""تعديل الخطاب التالي فقط بناءً على الملاحظات المقدمة. لا تعيد كتابة أو تعديل أي جزء من الخطاب غير المذكور تحديداً في الملاحظات.

يجب أن تحافظ على:
1. نفس بنية وتنسيق الخطاب الأصلي
2. نفس الأسلوب واللغة 
3. نفس جميع المعلومات التي لم تُذكر في الملاحظات

ملاحظات مهمة:
- أرجع الخطاب المعدل فقط، بدون أي كلمات مقدمة أو تعليقات
- لا تضف أي جملة مثل "الخطاب بعد التعديل" أو "فيما يلي الخطاب المعدل"
- لا تضف أي تعليقات ختامية أو توضيحات بعد الخطاب
- أرسل نص الخطاب فقط بدون أي إضافات

الخطاب الأصلي:
{letter}

الملاحظات المطلوب تطبيقها فقط:
{feedback}

"""
    )
    response = chat.invoke([prompt.format(letter=letter, feedback=feedback)])
    print("Response from OpenAI:", response)
    return response.content