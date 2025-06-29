import openai
import os
import asyncio
from playwright.async_api import async_playwright

class LetterPDF:
    def __init__(self, template_dir="templates"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.template_dir = template_dir

    def load_template(self, template_filename="default_template.html"):
        path = os.path.join(self.template_dir, template_filename)
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    def fill_template_with_ai(self, html_template, letter_text):
        prompt = f"""
You are a document automation expert. Your task is to fill an HTML template with exact content from a letter.

**STRICT RULES:**
1. Use ONLY the information provided in the letter content - do NOT add, modify, or invent any information
2. Extract text exactly as written in the letter content
3. Match each section of the letter to the appropriate placeholder in the template
4. Return ONLY the final HTML with placeholders filled - no explanations, no extra text
5. Keep all HTML structure, styling, and formatting intact
6. If a placeholder cannot be filled from the letter content, leave it empty or use a dash (-)

**HTML Template:**
{html_template}

**Letter Content (use exactly as provided):**
{letter_text}

Return only the filled HTML template:"""
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a precise document template filler. Use only the exact information provided in the letter content. Do not add, modify, or invent any information."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.1,
        )
        html = response.choices[0].message.content.strip()
        if html.startswith("```html"):
            html = html.replace("```html", "").replace("```", "").strip()
        return html

    async def html_to_pdf(self, html_code, pdf_path):
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html_code)
            await page.pdf(path=pdf_path, format="A4", print_background=True)
            await browser.close()

    def save_pdf(self, template_filename="default_template.html", letter_text="", pdf_path="output.pdf"):
        html_template = self.load_template(template_filename)
        html_code = self.fill_template_with_ai(html_template, letter_text)
        asyncio.run(self.html_to_pdf(html_code, pdf_path))
        return pdf_path

