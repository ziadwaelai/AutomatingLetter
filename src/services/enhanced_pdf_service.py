"""
Enhanced PDF Generation Service using AI and Playwright
Handles PDF creation from letter content with customizable templates.
"""

import logging
import os
import tempfile
import uuid
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, NamedTuple
from jinja2 import Environment, FileSystemLoader
import openai
import pytz
from hijri_converter import Hijri, Gregorian
from playwright.async_api import async_playwright

from ..config import get_config
from ..models import PDFGenerationRequest, PDFResponse
from ..utils import (
    Timer,
    ErrorContext,
    service_error_handler,
    generate_letter_id
)

logger = logging.getLogger(__name__)

class PDFInfo(NamedTuple):
    """Information about a generated PDF."""
    pdf_id: str
    filename: str
    file_path: str
    file_size: int
    generated_at: datetime

class PDFGenerationResult(NamedTuple):
    """Result of PDF generation."""
    pdf_id: str
    filename: str
    file_path: str
    file_size: int
    generated_at: datetime

class EnhancedPDFService:
    """Enhanced PDF generation service using AI and Playwright."""
    
    def __init__(self):
        """Initialize Enhanced PDF service."""
        self.config = get_config()
        self.templates_dir = Path(__file__).parent.parent.parent / "LetterToPdf" / "templates"
        self.output_dir = Path(tempfile.gettempdir()) / "letter_pdfs"
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize OpenAI client
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True
        )
        
        # PDF storage (in production, use database)
        self._pdf_cache: Dict[str, PDFInfo] = {}
        
        # Service stats
        self._generation_count = 0
        self._total_size = 0
        
        logger.info("Enhanced PDF service initialized")
    
    def get_current_dates(self) -> Dict[str, str]:
        """Get current date in both Gregorian (KSA timezone) and Hijri formats."""
        try:
            # Get current date in KSA timezone (UTC+3)
            ksa_tz = pytz.timezone('Asia/Riyadh')
            now_ksa = datetime.now(ksa_tz)
            
            # Format Gregorian date
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
        except Exception as e:
            logger.warning(f"Error getting dates, using fallback: {e}")
            # Fallback to simple date
            now = datetime.now()
            return {
                "gregorian": now.strftime("%Y/%m/%d"),
                "hijri": now.strftime("%Y/%m/%d"),
                "gregorian_arabic": f"{now.day} / {now.month} / {now.year}",
                "hijri_arabic": f"{now.day} / {now.month} / {now.year}"
            }
    
    def load_template(self, template_filename: str = "default_template.html") -> str:
        """Load HTML template from file."""
        try:
            template_path = self.templates_dir / template_filename
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_filename}")
                
            with open(template_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error loading template {template_filename}: {e}")
            raise
    
    def fill_template_with_ai(self, html_template: str, letter_text: str = "", letter_id: str = "") -> str:
        """Fill HTML template with letter content using AI."""
        try:
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
{letter_id}

Return only the filled HTML template with ALL letter content preserved:"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a precise document template filler. Use only the exact information provided in the letter content. Do not add, modify, or invent any information."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.1,
            )
            
            html = response.choices[0].message.content.strip()
            
            # Clean up markdown formatting if present
            if html.startswith("```html"):
                html = html.replace("```html", "").replace("```", "").strip()
            
            return html
            
        except Exception as e:
            logger.error(f"Error filling template with AI: {e}")
            raise
    
    async def html_to_pdf_async(self, html_content: str, pdf_path: str) -> None:
        """Convert HTML to PDF using Playwright."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                await page.set_content(html_content)
                await page.pdf(path=pdf_path, format="A4", print_background=True)
                await browser.close()
        except Exception as e:
            logger.error(f"Error converting HTML to PDF: {e}")
            raise
    
    def html_to_pdf(self, html_content: str, pdf_path: str) -> None:
        """Convert HTML to PDF synchronously."""
        asyncio.run(self.html_to_pdf_async(html_content, pdf_path))
    
    @service_error_handler
    def generate_pdf(
        self,
        title: str,
        content: str,
        template_name: str = "default_template",
        options: Optional[Dict[str, Any]] = None
    ) -> PDFGenerationResult:
        """
        Generate PDF from letter content using AI template filling.
        
        Args:
            title: Document title
            content: Letter content
            template_name: Template to use
            options: PDF generation options (ignored in this implementation)
            
        Returns:
            PDFGenerationResult with file information
        """
        with ErrorContext("pdf_generation", {"template": template_name}):
            timer = Timer()
            
            # Generate unique ID
            pdf_id = generate_letter_id()
            
            # Sanitize filename - remove Arabic characters and special characters
            import re
            safe_title = re.sub(r'[^\w\s-]', '', title.replace(' ', '_'))
            safe_title = re.sub(r'[\u0600-\u06FF]', 'letter', safe_title)  # Replace Arabic with 'letter'
            if not safe_title or safe_title.isspace():
                safe_title = "document"
            
            filename = f"{safe_title}_{pdf_id}.pdf"
            output_path = self.output_dir / filename
            
            try:
                # Load template
                template_filename = f"{template_name}.html" if not template_name.endswith('.html') else template_name
                html_template = self.load_template(template_filename)
                
                # Fill template with AI
                html_content = self.fill_template_with_ai(html_template, content, pdf_id)
                
                # Generate PDF
                self.html_to_pdf(html_content, str(output_path))
                
                # Get file size
                file_size = output_path.stat().st_size
                
                # Create result
                result = PDFGenerationResult(
                    pdf_id=pdf_id,
                    filename=filename,
                    file_path=str(output_path),
                    file_size=file_size,
                    generated_at=datetime.now()
                )
                
                # Cache PDF info
                self._pdf_cache[pdf_id] = PDFInfo(
                    pdf_id=pdf_id,
                    filename=filename,
                    file_path=str(output_path),
                    file_size=file_size,
                    generated_at=result.generated_at
                )
                
                # Update stats
                self._generation_count += 1
                self._total_size += file_size
                
                logger.info(f"PDF generated successfully: {filename} ({file_size} bytes) in {timer.elapsed():.2f}s")
                return result
                
            except Exception as e:
                logger.error(f"PDF generation failed: {e}")
                # Clean up on error
                if output_path.exists():
                    try:
                        output_path.unlink()
                    except Exception:
                        pass
                raise
    
    def get_pdf_info(self, pdf_id: str) -> Optional[PDFInfo]:
        """Get information about a generated PDF."""
        return self._pdf_cache.get(pdf_id)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "service": "enhanced_pdf_generation",
            "stats": {
                "pdfs_generated": self._generation_count,
                "total_size_bytes": self._total_size,
                "cached_pdfs": len(self._pdf_cache),
                "output_directory": str(self.output_dir),
                "templates_directory": str(self.templates_dir),
                "templates_available": len(list(self.templates_dir.glob("*.html"))) if self.templates_dir.exists() else 0
            }
        }
    
    def cleanup_old_pdfs(self, max_age_hours: int = 24) -> int:
        """
        Clean up old PDF files.
        
        Args:
            max_age_hours: Maximum age in hours for PDF files
            
        Returns:
            Number of files cleaned up
        """
        cleaned_count = 0
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Clean cache
        to_remove = []
        for pdf_id, info in self._pdf_cache.items():
            if info.generated_at < cutoff_time:
                to_remove.append(pdf_id)
                # Try to remove file
                try:
                    if os.path.exists(info.file_path):
                        os.remove(info.file_path)
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Could not remove old PDF file {info.file_path}: {e}")
        
        # Remove from cache
        for pdf_id in to_remove:
            del self._pdf_cache[pdf_id]
        
        logger.info(f"Cleaned up {cleaned_count} old PDF files")
        return cleaned_count

# Service instance
_enhanced_pdf_service = None

def get_enhanced_pdf_service() -> EnhancedPDFService:
    """Get or create enhanced PDF service instance."""
    global _enhanced_pdf_service
    if _enhanced_pdf_service is None:
        _enhanced_pdf_service = EnhancedPDFService()
    return _enhanced_pdf_service
