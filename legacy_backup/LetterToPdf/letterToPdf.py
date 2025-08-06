import openai
import os
import asyncio
from datetime import datetime
import pytz
from hijri_converter import Hijri, Gregorian
from playwright.async_api import async_playwright

class LetterPDF:
    def __init__(self, template_dir="templates"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.template_dir = template_dir

    def get_current_dates(self):
        """Get current date in both Gregorian (KSA timezone) and Hijri formats"""
        # Get current date in KSA timezone (UTC+3)
        ksa_tz = pytz.timezone('Asia/Riyadh')
        now_ksa = datetime.now(ksa_tz)
        
        # Format Gregorian date in Arabic
        gregorian_date = now_ksa.strftime("%Y/%m/%d")
        
        # Convert to Hijri date
        hijri_date = Gregorian(now_ksa.year, now_ksa.month, now_ksa.day).to_hijri()
        hijri_formatted = f"{hijri_date.year}/{hijri_date.month:02d}/{hijri_date.day:02d}"
        
        return {
            "gregorian": gregorian_date,
            "hijri": hijri_formatted,
            "gregorian_arabic": f"{now_ksa.day} / {now_ksa.month} / {now_ksa.year}",
            "hijri_arabic": f"{hijri_date.day} / {hijri_date.month} / {hijri_date.year}"
        }

    def load_template(self, template_filename="default_template.html"):
        path = os.path.join(self.template_dir, template_filename)
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    def fill_template_with_ai(self, html_template, letter_text="", id=""):
        dates = self.get_current_dates()
        
        prompt = f"""
You are a document automation expert. Your task is to fill an HTML template with exact content from a letter.

**CRITICAL RULES - DO NOT VIOLATE:**
1. Use ONLY the information provided in the letter content - do NOT add, modify, or invent any information
2. Extract text exactly as written in the letter content - preserve every word, sentence, and paragraph
3. DO NOT remove, summarize, or shorten any content from the letter
4. The template is ONLY for formatting - all letter content must be preserved completely
5. Match each section of the letter to the appropriate placeholder in the template
6. Return ONLY the final HTML with placeholders filled - no explanations, no extra text
7. Keep all HTML structure, styling, and formatting intact
8. If a placeholder cannot be filled from the letter content, leave it empty or use a dash (-)
9. For date placeholders, use the provided current dates below
10. PRESERVE ALL CONTENT - this is a formatter only, not a content editor

**AVAILABLE DATES:**
- Current Gregorian Date (KSA): {dates['gregorian_arabic']}
- Current Hijri Date: {dates['hijri_arabic']}

**DATE USAGE INSTRUCTIONS:**
- For document_date placeholder: Use BOTH dates in this format: "التاريخ الميلادي: {dates['gregorian_arabic']} - التاريخ الهجري: {dates['hijri_arabic']}"
- This will display both Gregorian and Hijri dates in the document header

**HTML Template:**
{html_template}

**Letter Content (use exactly as provided - DO NOT REMOVE ANYTHING):**
{letter_text}

**ID (for reference):**
{id}

Return only the filled HTML template with ALL letter content preserved:"""
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

    def save_pdf(self, template_filename="default_template.html", letter_text="", pdf_path="output.pdf", id=""):
        html_template = self.load_template(template_filename)
        html_code = self.fill_template_with_ai(html_template, letter_text, id)
        asyncio.run(self.html_to_pdf(html_code, pdf_path))
        return pdf_path

