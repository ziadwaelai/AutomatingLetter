"""
PDF Generation Service
Handles PDF creation from letter content with customizable templates.
"""

import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, NamedTuple
import pdfkit
from jinja2 import Environment, FileSystemLoader, Template

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

class PDFService:
    """Service for generating PDFs from letter content."""
    
    def __init__(self):
        """Initialize PDF service."""
        self.config = get_config()
        self.templates_dir = Path(__file__).parent.parent.parent / "LetterToPdf" / "templates"
        self.output_dir = Path(tempfile.gettempdir()) / "letter_pdfs"
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
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
        
        logger.info("PDF service initialized")
    
    @service_error_handler
    def generate_pdf(
        self,
        title: str,
        content: str,
        template_name: str = "default_template",
        options: Optional[Dict[str, Any]] = None
    ) -> PDFGenerationResult:
        """
        Generate PDF from letter content.
        
        Args:
            title: Document title
            content: Letter content
            template_name: Template to use
            options: PDF generation options
            
        Returns:
            PDFGenerationResult with file information
        """
        with ErrorContext("pdf_generation", {"template": template_name}):
            timer = Timer()
            
            # Generate unique ID
            pdf_id = generate_letter_id()
            filename = f"{title.replace(' ', '_')}_{pdf_id}.pdf"
            output_path = self.output_dir / filename
            
            # Default PDF options
            pdf_options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None,
                'enable-local-file-access': None
            }
            
            # Update with custom options
            if options:
                pdf_options.update(options)
            
            try:
                # Generate HTML from template
                html_content = self._generate_html(
                    title=title,
                    content=content,
                    template_name=template_name
                )
                
                # Generate PDF
                pdfkit.from_string(
                    html_content,
                    str(output_path),
                    options=pdf_options
                )
                
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
                
                logger.info(f"PDF generated: {pdf_id} ({file_size} bytes) in {timer.elapsed():.2f}s")
                
                return result
                
            except Exception as e:
                # Clean up failed file
                if output_path.exists():
                    output_path.unlink()
                raise Exception(f"PDF generation failed: {e}")
    
    def _generate_html(self, title: str, content: str, template_name: str) -> str:
        """
        Generate HTML from template and content.
        
        Args:
            title: Document title
            content: Letter content
            template_name: Template name
            
        Returns:
            Rendered HTML content
        """
        try:
            # Load template
            template_file = f"{template_name}.html"
            template = self.jinja_env.get_template(template_file)
            
            # Prepare template variables
            template_vars = {
                'title': title,
                'content': content,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'arabic_date': self._format_arabic_date(datetime.now())
            }
            
            # Render template
            html_content = template.render(**template_vars)
            
            return html_content
            
        except Exception as e:
            logger.error(f"HTML generation failed for template {template_name}: {e}")
            # Fallback to simple HTML
            return self._generate_simple_html(title, content)
    
    def _generate_simple_html(self, title: str, content: str) -> str:
        """Generate simple HTML when template fails."""
        return f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                body {{
                    font-family: 'Traditional Arabic', 'Arial Unicode MS', Arial, sans-serif;
                    line-height: 1.6;
                    margin: 40px;
                    direction: rtl;
                    text-align: right;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid #333;
                    padding-bottom: 20px;
                }}
                .content {{
                    white-space: pre-wrap;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <p>التاريخ: {datetime.now().strftime('%Y-%m-%d')}</p>
            </div>
            <div class="content">{content}</div>
        </body>
        </html>
        """
    
    def _format_arabic_date(self, date: datetime) -> str:
        """Format date in Arabic."""
        arabic_months = [
            'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
            'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
        ]
        
        day = date.day
        month = arabic_months[date.month - 1]
        year = date.year
        
        return f"{day} {month} {year}"
    
    @service_error_handler
    def generate_html_preview(
        self,
        title: str,
        content: str,
        template_name: str = "default_template"
    ) -> str:
        """
        Generate HTML preview without creating PDF.
        
        Args:
            title: Document title
            content: Letter content
            template_name: Template name
            
        Returns:
            HTML content for preview
        """
        with ErrorContext("html_preview_generation"):
            return self._generate_html(title, content, template_name)
    
    @service_error_handler
    def generate_batch_pdfs(
        self,
        requests: List[PDFGenerationRequest]
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple PDFs in batch.
        
        Args:
            requests: List of PDF generation requests
            
        Returns:
            List of generation results
        """
        with ErrorContext("batch_pdf_generation"):
            results = []
            
            for i, request in enumerate(requests):
                try:
                    result = self.generate_pdf(
                        title=request.title,
                        content=request.content,
                        template_name=request.template_name,
                        options=request.options
                    )
                    
                    results.append({
                        "index": i,
                        "status": "success",
                        "pdf_id": result.pdf_id,
                        "filename": result.filename,
                        "file_size": result.file_size
                    })
                    
                except Exception as e:
                    logger.error(f"Batch PDF generation failed for request {i}: {e}")
                    results.append({
                        "index": i,
                        "status": "error",
                        "error": str(e)
                    })
            
            return results
    
    def get_pdf_info(self, pdf_id: str) -> Optional[PDFInfo]:
        """Get information about a generated PDF."""
        return self._pdf_cache.get(pdf_id)
    
    def pdf_exists(self, pdf_id: str) -> bool:
        """Check if PDF exists."""
        return pdf_id in self._pdf_cache
    
    def list_pdfs(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List generated PDFs.
        
        Args:
            limit: Maximum number of PDFs to return
            offset: Offset for pagination
            
        Returns:
            List of PDF information
        """
        all_pdfs = list(self._pdf_cache.values())
        all_pdfs.sort(key=lambda x: x.generated_at, reverse=True)
        
        paginated_pdfs = all_pdfs[offset:offset + limit]
        
        return [
            {
                "pdf_id": pdf.pdf_id,
                "filename": pdf.filename,
                "file_size": pdf.file_size,
                "generated_at": pdf.generated_at.isoformat(),
                "exists": os.path.exists(pdf.file_path)
            }
            for pdf in paginated_pdfs
        ]
    
    def delete_pdf(self, pdf_id: str) -> bool:
        """
        Delete a generated PDF.
        
        Args:
            pdf_id: PDF identifier
            
        Returns:
            True if deleted successfully
        """
        if pdf_id not in self._pdf_cache:
            return False
        
        pdf_info = self._pdf_cache[pdf_id]
        
        # Remove file
        try:
            if os.path.exists(pdf_info.file_path):
                os.unlink(pdf_info.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete PDF file {pdf_info.file_path}: {e}")
        
        # Remove from cache
        del self._pdf_cache[pdf_id]
        
        logger.info(f"Deleted PDF: {pdf_id}")
        return True
    
    def cleanup_old_pdfs(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Clean up old PDF files.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Cleanup results
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        deleted_count = 0
        failed_count = 0
        total_size_freed = 0
        
        # Find old PDFs
        old_pdf_ids = [
            pdf_id for pdf_id, pdf_info in self._pdf_cache.items()
            if pdf_info.generated_at < cutoff_time
        ]
        
        # Delete old PDFs
        for pdf_id in old_pdf_ids:
            pdf_info = self._pdf_cache[pdf_id]
            try:
                if os.path.exists(pdf_info.file_path):
                    total_size_freed += pdf_info.file_size
                    os.unlink(pdf_info.file_path)
                
                del self._pdf_cache[pdf_id]
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Failed to delete old PDF {pdf_id}: {e}")
                failed_count += 1
        
        logger.info(f"Cleanup completed: {deleted_count} PDFs deleted, {failed_count} failed")
        
        return {
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "total_size_freed": total_size_freed,
            "cutoff_time": cutoff_time.isoformat()
        }
    
    def get_available_templates(self) -> List[Dict[str, str]]:
        """Get list of available PDF templates."""
        templates = []
        
        if self.templates_dir.exists():
            for template_file in self.templates_dir.glob("*.html"):
                template_name = template_file.stem
                templates.append({
                    "name": template_name,
                    "filename": template_file.name,
                    "display_name": template_name.replace("_", " ").title()
                })
        
        # Add default template if none found
        if not templates:
            templates.append({
                "name": "default_template",
                "filename": "default_template.html",
                "display_name": "Default Template"
            })
        
        return templates
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "total_generated": self._generation_count,
            "cached_pdfs": len(self._pdf_cache),
            "total_size_mb": round(self._total_size / (1024 * 1024), 2),
            "output_directory": str(self.output_dir),
            "templates_available": len(self.get_available_templates())
        }

# Service instance management
_pdf_service: Optional[PDFService] = None

def get_pdf_service() -> PDFService:
    """Get or create PDF service instance."""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService()
    return _pdf_service
