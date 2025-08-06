"""
API Routes for PDF Generation
Handles PDF conversion and management functionality.
"""

import logging
import os
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, send_file
from pydantic import ValidationError
import tempfile

from ..models import (
    PDFGenerationRequest,
    PDFResponse,
    ErrorResponse
)
from ..services import get_pdf_service, get_drive_service
from ..utils import (
    ErrorContext,
    build_error_response,
    measure_performance
)

logger = logging.getLogger(__name__)

# Create blueprint
pdf_bp = Blueprint('pdf', __name__, url_prefix='/api/v1/pdf')

@pdf_bp.route('/generate', methods=['POST'])
@measure_performance
def generate_pdf():
    """
    Generate PDF from letter content.
    
    Request Body:
        PDFGenerationRequest: PDF generation parameters
        
    Returns:
        PDFResponse: PDF generation results with download URL
    """
    with ErrorContext("generate_pdf_api"):
        try:
            if not request.is_json:
                return jsonify({"error": "Request must be JSON"}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            # Validate request
            try:
                pdf_request = PDFGenerationRequest(**data)
            except ValidationError as e:
                logger.warning(f"Validation error in PDF generation: {e}")
                return jsonify({
                    "error": "Invalid request data",
                    "details": e.errors()
                }), 400
            
            # Generate PDF
            pdf_service = get_pdf_service()
            pdf_result = pdf_service.generate_pdf(
                title=pdf_request.title,
                content=pdf_request.content,
                template_name=pdf_request.template_name,
                options=pdf_request.options
            )
            
            # Upload to Google Drive if requested
            drive_url = None
            if pdf_request.upload_to_drive:
                try:
                    drive_service = get_drive_service()
                    drive_url = drive_service.upload_pdf(
                        pdf_result.file_path,
                        pdf_result.filename
                    )
                    logger.info(f"PDF uploaded to Drive: {drive_url}")
                except Exception as e:
                    logger.warning(f"Failed to upload PDF to Drive: {e}")
            
            # Create response
            response = PDFResponse(
                pdf_id=pdf_result.pdf_id,
                filename=pdf_result.filename,
                file_size=pdf_result.file_size,
                download_url=f"/api/v1/pdf/download/{pdf_result.pdf_id}",
                drive_url=drive_url,
                generated_at=pdf_result.generated_at
            )
            
            logger.info(f"PDF generated successfully: {pdf_result.pdf_id}")
            
            return jsonify(response.model_dump()), 200
            
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return jsonify(build_error_response(e)), 400
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return jsonify(build_error_response(e)), 500

@pdf_bp.route('/download/<pdf_id>', methods=['GET'])
@measure_performance
def download_pdf(pdf_id: str):
    """
    Download generated PDF file.
    
    Args:
        pdf_id: PDF identifier
        
    Returns:
        PDF file for download
    """
    with ErrorContext("download_pdf", {"pdf_id": pdf_id}):
        try:
            pdf_service = get_pdf_service()
            
            # Get PDF file path
            pdf_info = pdf_service.get_pdf_info(pdf_id)
            if not pdf_info:
                return jsonify({
                    "error": "PDF not found",
                    "message": "The requested PDF does not exist or has expired"
                }), 404
            
            # Check if file exists
            if not os.path.exists(pdf_info.file_path):
                return jsonify({
                    "error": "File not found",
                    "message": "PDF file no longer exists on server"
                }), 404
            
            # Send file
            return send_file(
                pdf_info.file_path,
                as_attachment=True,
                download_name=pdf_info.filename,
                mimetype='application/pdf'
            )
            
        except Exception as e:
            logger.error(f"PDF download failed for {pdf_id}: {e}")
            return jsonify(build_error_response(e)), 500

@pdf_bp.route('/templates', methods=['GET'])
def get_pdf_templates():
    """
    Get available PDF templates.
    
    Returns:
        List of available PDF templates
    """
    try:
        pdf_service = get_pdf_service()
        templates = pdf_service.get_available_templates()
        
        return jsonify({
            "status": "success",
            "templates": templates
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get PDF templates: {e}")
        return jsonify(build_error_response(e)), 500

@pdf_bp.route('/preview', methods=['POST'])
@measure_performance
def preview_pdf():
    """
    Generate PDF preview (HTML version).
    
    Request Body:
        title: str - Document title
        content: str - Document content
        template_name: str - Template to use (optional)
        
    Returns:
        HTML preview of the PDF
    """
    with ErrorContext("preview_pdf"):
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            title = data.get('title', '')
            content = data.get('content', '')
            template_name = data.get('template_name', 'default_template')
            
            if not content:
                return jsonify({"error": "Content is required"}), 400
            
            pdf_service = get_pdf_service()
            html_preview = pdf_service.generate_html_preview(
                title=title,
                content=content,
                template_name=template_name
            )
            
            return jsonify({
                "status": "success",
                "html_preview": html_preview
            }), 200
            
        except Exception as e:
            logger.error(f"PDF preview generation failed: {e}")
            return jsonify(build_error_response(e)), 500

@pdf_bp.route('/batch', methods=['POST'])
@measure_performance
def generate_batch_pdfs():
    """
    Generate multiple PDFs in batch.
    
    Request Body:
        requests: List[PDFGenerationRequest] - List of PDF generation requests
        
    Returns:
        Batch generation results
    """
    with ErrorContext("generate_batch_pdfs"):
        try:
            data = request.get_json()
            if not data or 'requests' not in data:
                return jsonify({"error": "Requests list is required"}), 400
            
            requests_data = data['requests']
            if not isinstance(requests_data, list) or len(requests_data) == 0:
                return jsonify({"error": "Requests must be a non-empty list"}), 400
            
            if len(requests_data) > 10:  # Limit batch size
                return jsonify({"error": "Batch size cannot exceed 10 requests"}), 400
            
            # Validate all requests
            pdf_requests = []
            for i, req_data in enumerate(requests_data):
                try:
                    pdf_request = PDFGenerationRequest(**req_data)
                    pdf_requests.append(pdf_request)
                except ValidationError as e:
                    return jsonify({
                        "error": f"Invalid request at index {i}",
                        "details": e.errors()
                    }), 400
            
            # Process batch
            pdf_service = get_pdf_service()
            batch_results = pdf_service.generate_batch_pdfs(pdf_requests)
            
            logger.info(f"Batch PDF generation completed: {len(batch_results)} PDFs")
            
            return jsonify({
                "status": "success",
                "results": batch_results,
                "total_generated": len(batch_results)
            }), 200
            
        except Exception as e:
            logger.error(f"Batch PDF generation failed: {e}")
            return jsonify(build_error_response(e)), 500

@pdf_bp.route('/list', methods=['GET'])
def list_generated_pdfs():
    """
    List recently generated PDFs.
    
    Query Parameters:
        limit: int - Number of PDFs to return (default: 20)
        offset: int - Offset for pagination (default: 0)
        
    Returns:
        List of generated PDFs with metadata
    """
    try:
        limit = min(int(request.args.get('limit', 20)), 100)  # Max 100
        offset = max(int(request.args.get('offset', 0)), 0)
        
        pdf_service = get_pdf_service()
        pdfs = pdf_service.list_pdfs(limit=limit, offset=offset)
        
        return jsonify({
            "status": "success",
            "pdfs": pdfs,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(pdfs)
            }
        }), 200
        
    except ValueError as e:
        return jsonify({
            "error": "Invalid parameters",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Failed to list PDFs: {e}")
        return jsonify(build_error_response(e)), 500

@pdf_bp.route('/<pdf_id>', methods=['DELETE'])
@measure_performance
def delete_pdf(pdf_id: str):
    """
    Delete a generated PDF.
    
    Args:
        pdf_id: PDF identifier
        
    Returns:
        Deletion confirmation
    """
    with ErrorContext("delete_pdf", {"pdf_id": pdf_id}):
        try:
            pdf_service = get_pdf_service()
            
            if not pdf_service.pdf_exists(pdf_id):
                return jsonify({
                    "error": "PDF not found",
                    "message": "The requested PDF does not exist"
                }), 404
            
            # Delete PDF
            pdf_service.delete_pdf(pdf_id)
            
            logger.info(f"Deleted PDF: {pdf_id}")
            
            return jsonify({
                "status": "success",
                "message": "PDF deleted successfully",
                "pdf_id": pdf_id
            }), 200
            
        except Exception as e:
            logger.error(f"Failed to delete PDF {pdf_id}: {e}")
            return jsonify(build_error_response(e)), 500

@pdf_bp.route('/cleanup', methods=['POST'])
def cleanup_old_pdfs():
    """
    Clean up old PDF files.
    
    Request Body (optional):
        max_age_hours: int - Maximum age in hours (default: 24)
        
    Returns:
        Cleanup results
    """
    try:
        data = request.get_json() or {}
        max_age_hours = data.get('max_age_hours', 24)
        
        pdf_service = get_pdf_service()
        cleanup_results = pdf_service.cleanup_old_pdfs(max_age_hours)
        
        return jsonify({
            "status": "success",
            "cleanup_results": cleanup_results
        }), 200
        
    except Exception as e:
        logger.error(f"PDF cleanup failed: {e}")
        return jsonify(build_error_response(e)), 500

@pdf_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for PDF service.
    
    Returns:
        Service health status
    """
    try:
        pdf_service = get_pdf_service()
        service_stats = pdf_service.get_service_stats()
        
        return jsonify({
            "status": "healthy",
            "service": "pdf_generation",
            "stats": service_stats
        }), 200
        
    except Exception as e:
        logger.error(f"PDF health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

# Error handlers for the blueprint
@pdf_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle Pydantic validation errors."""
    return jsonify({
        "error": "Validation failed",
        "details": error.errors()
    }), 400

@pdf_bp.errorhandler(404)
def handle_not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested PDF endpoint does not exist"
    }), 404

@pdf_bp.errorhandler(413)
def handle_file_too_large(error):
    """Handle file too large errors."""
    return jsonify({
        "error": "File too large",
        "message": "The PDF content is too large to process"
    }), 413

@pdf_bp.errorhandler(500)
def handle_internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error in PDF API: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred in PDF service"
    }), 500
