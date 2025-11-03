"""
Archive API Routes
Handles letter archiving, PDF generation, Google Drive upload, and logging.
"""

import logging
import threading
import os
from typing import Dict, Any
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from ..models import (
    ArchiveLetterRequest,
    UpdateLetterRequest,
    ArchiveResponse,
    ErrorResponse,
    SuccessResponse
)
from ..services import get_drive_logger_service, get_enhanced_pdf_service, get_enhanced_docx_service
from ..utils import (
    ErrorContext,
    build_error_response,
    validate_and_raise,
    measure_performance
)

logger = logging.getLogger(__name__)

# Create blueprint
archive_bp = Blueprint('archive', __name__, url_prefix='/api/v1/archive')

@archive_bp.route('/letter', methods=['POST'])
@measure_performance
def archive_letter():
    """
    Archive letter to PDF, upload to Google Drive, and log to sheets.
    Process runs in background and returns immediately.
    """
    try:
        # Validate request
        data = request.get_json()
        if not data:
            return build_error_response("لم يتم تقديم بيانات JSON", 400)
        
        # Validate required fields
        required_fields = ['letter_content', 'ID']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            field_names_ar = {'letter_content': 'محتوى الخطاب', 'ID': 'رقم الخطاب'}
            missing_ar = [field_names_ar.get(field, field) for field in missing_fields]
            return build_error_response(f"الحقول المطلوبة مفقودة: {', '.join(missing_ar)}", 400)
        
        # Extract data with defaults
        letter_content = data.get('letter_content', '')
        letter_type = data.get('letter_type', 'General')
        recipient = data.get('recipient', '')
        title = data.get('title', 'undefined')
        is_first = data.get('is_first', False)
        letter_id = data.get('ID', '')
        template = data.get('template', 'default_template')
        username = data.get('username', 'unknown')
        
        # Get Google Drive folder ID from environment variables
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        if not folder_id:
            return build_error_response("لم يتم تكوين معرف مجلد Google Drive", 500)
        
        # Start background processing
        background_thread = threading.Thread(
            target=process_letter_archive_in_background,
            args=(template, letter_content, letter_id, letter_type, recipient, title, is_first, folder_id, username)
        )
        background_thread.daemon = True
        background_thread.start()
        
        # Return immediate success response
        response = ArchiveResponse(
            status="success",
            message=f"Letter archiving started for ID: {letter_id}",
            processing="background",
            letter_id=letter_id
        )
        
        logger.info(f"Letter archiving initiated for ID: {letter_id}")
        return jsonify(response.model_dump()), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in letter archiving: {e}")
        return build_error_response(f"خطأ في التحقق من البيانات: {e}", 400)
    except Exception as e:
        logger.error(f"Letter archiving failed: {e}")
        return build_error_response(f"خطأ في الأرشفة: {str(e)}", 500)

@archive_bp.route('/letter/docx', methods=['POST'])
@measure_performance
def archive_letter_docx():
    """
    Archive letter to DOCX with PDF-matching styling, upload to Google Drive, and log to sheets.
    Process runs in background and returns immediately.
    """
    try:
        # Validate request
        data = request.get_json()
        if not data:
            return build_error_response("لم يتم تقديم بيانات JSON", 400)

        # Validate required fields
        required_fields = ['letter_content', 'ID']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            field_names_ar = {'letter_content': 'محتوى الخطاب', 'ID': 'رقم الخطاب'}
            missing_ar = [field_names_ar.get(field, field) for field in missing_fields]
            return build_error_response(f"الحقول المطلوبة مفقودة: {', '.join(missing_ar)}", 400)

        # Extract data with defaults
        letter_content = data.get('letter_content', '')
        letter_type = data.get('letter_type', 'General')
        recipient = data.get('recipient', '')
        title = data.get('title', 'undefined')
        is_first = data.get('is_first', False)
        letter_id = data.get('ID', '')
        document_id = data.get('document_id', '')
        username = data.get('username', 'unknown')

        # Get Google Drive folder ID from environment variables
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        if not folder_id:
            return build_error_response("لم يتم تكوين معرف مجلد Google Drive", 500)

        # Start background processing
        background_thread = threading.Thread(
            target=process_letter_archive_docx_in_background,
            args=(letter_content, letter_id, letter_type, recipient, title, is_first, folder_id, username, document_id)
        )
        background_thread.daemon = True
        background_thread.start()

        # Return immediate success response
        response = ArchiveResponse(
            status="success",
            message=f"Letter DOCX archiving started for ID: {letter_id}",
            processing="background",
            letter_id=letter_id
        )

        logger.info(f"Letter DOCX archiving initiated for ID: {letter_id}")
        return jsonify(response.model_dump()), 200

    except ValidationError as e:
        logger.warning(f"Validation error in letter DOCX archiving: {e}")
        return build_error_response(f"خطأ في التحقق من البيانات: {e}", 400)
    except Exception as e:
        logger.error(f"Letter DOCX archiving failed: {e}")
        return build_error_response(f"خطأ في الأرشفة: {str(e)}", 500)

def process_letter_archive_docx_in_background(
    letter_content: str,
    letter_id: str,
    letter_type: str,
    recipient: str,
    title: str,
    is_first: bool,
    folder_id: str,
    username: str,
    document_id: str = ""
) -> None:
    """
    Process letter DOCX archiving in background thread.

    Args:
        letter_content: Content of the letter
        letter_id: Unique letter ID
        letter_type: Type/category of letter
        recipient: Letter recipient
        title: Letter title
        is_first: Whether this is first communication
        folder_id: Google Drive folder ID
        username: Username of creator
        document_id: Document ID number
    """
    try:
        logger.info(f"Starting background DOCX archiving for letter ID: {letter_id}")

        # Get services
        docx_service = get_enhanced_docx_service()
        drive_logger = get_drive_logger_service()

        # Generate DOCX
        logger.info(f"Generating DOCX for letter ID: {letter_id}")
        docx_result = docx_service.generate_docx(
            title=title,
            content=letter_content,
            recipient=recipient,
            letter_id=letter_id,
            document_id=document_id
        )

        logger.info(f"DOCX generated successfully: {docx_result.filename}")

        # Archive to Drive and log to sheets
        logger.info(f"Uploading DOCX to Drive and logging for letter ID: {letter_id}")
        archive_result = drive_logger.save_letter_to_drive_and_log(
            letter_file_path=docx_result.file_path,
            letter_content=letter_content,
            letter_type=letter_type,
            recipient=recipient,
            title=title,
            is_first=is_first,
            folder_id=folder_id,
            letter_id=letter_id,
            username=username
        )

        # Clean up temporary DOCX file
        try:
            drive_logger.cleanup_temp_file(docx_result.file_path)
        except Exception as cleanup_error:
            logger.warning(f"Error cleaning up temporary DOCX file for {letter_id}: {cleanup_error}")

        if archive_result["status"] == "success":
            logger.info(f"Background DOCX archiving completed successfully for letter ID: {letter_id}")
            logger.info(f"Drive URL: {archive_result.get('file_url', 'N/A')}")
        else:
            logger.error(f"Background DOCX archiving failed for letter ID: {letter_id}: {archive_result.get('message', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Error in background DOCX archiving for letter ID {letter_id}: {str(e)}", exc_info=True)

def process_letter_archive_in_background(
    template: str,
    letter_content: str,
    letter_id: str,
    letter_type: str,
    recipient: str,
    title: str,
    is_first: bool,
    folder_id: str,
    username: str
) -> None:
    """
    Process letter archiving in background thread.
    
    Args:
        template: Template name for PDF generation
        letter_content: Content of the letter
        letter_id: Unique letter ID
        letter_type: Type/category of letter
        recipient: Letter recipient
        title: Letter title
        is_first: Whether this is first communication
        folder_id: Google Drive folder ID
        username: Username of creator
    """
    try:
        logger.info(f"Starting background archiving for letter ID: {letter_id}")
        
        # Get services
        pdf_service = get_enhanced_pdf_service()
        drive_logger = get_drive_logger_service()
        
        # Generate PDF
        logger.info(f"Generating PDF for letter ID: {letter_id}")
        pdf_result = pdf_service.generate_pdf(
            title=title,
            content=letter_content,
            template_name=template
        )
        
        logger.info(f"PDF generated successfully: {pdf_result.filename}")
        
        # Archive to Drive and log to sheets
        logger.info(f"Uploading to Drive and logging for letter ID: {letter_id}")
        archive_result = drive_logger.save_letter_to_drive_and_log(
            letter_file_path=pdf_result.file_path,
            letter_content=letter_content,
            letter_type=letter_type,
            recipient=recipient,
            title=title,
            is_first=is_first,
            folder_id=folder_id,
            letter_id=letter_id,
            username=username
        )
        
        # Clean up temporary PDF file
        try:
            drive_logger.cleanup_temp_file(pdf_result.file_path)
        except Exception as cleanup_error:
            logger.warning(f"Error cleaning up temporary file for {letter_id}: {cleanup_error}")
        
        if archive_result["status"] == "success":
            logger.info(f"Background archiving completed successfully for letter ID: {letter_id}")
            logger.info(f"Drive URL: {archive_result.get('file_url', 'N/A')}")
        else:
            logger.error(f"Background archiving failed for letter ID: {letter_id}: {archive_result.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error in background archiving for letter ID {letter_id}: {str(e)}", exc_info=True)

@archive_bp.route('/status/<letter_id>', methods=['GET'])
def get_archive_status(letter_id: str):
    """
    Get archiving status for a letter.
    Note: This is a placeholder - in a production system, you would track status in a database.
    """
    try:
        # For now, return a simple response
        # In production, check database for actual status
        return jsonify({
            "letter_id": letter_id,
            "status": "processing",
            "message": "Archive status tracking not implemented yet"
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting archive status for {letter_id}: {e}")
        return build_error_response(f"Error getting status: {str(e)}", 500)

@archive_bp.route('/update/status/<letter_id>', methods=['GET'])
def get_update_status(letter_id: str):
    """
    Get update status for a letter.
    Note: This is a placeholder - in a production system, you would track status in a database.
    """
    try:
        # For now, return a simple response
        # In production, check database for actual status
        return jsonify({
            "letter_id": letter_id,
            "operation": "update",
            "status": "processing",
            "message": "Update status tracking not implemented yet",
            "endpoint": f"/api/v1/archive/update/status/{letter_id}"
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting update status for {letter_id}: {e}")
        return build_error_response(f"Error getting update status: {str(e)}", 500)

@archive_bp.route('/health', methods=['GET'])
def health_check():
    """Archive service health check."""
    try:
        # Check services
        pdf_service = get_enhanced_pdf_service()
        drive_logger = get_drive_logger_service()
        
        return jsonify({
            "service": "archive",
            "status": "healthy",
            "components": {
                "pdf_service": pdf_service.get_service_stats(),
                "drive_logger": "initialized"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Archive health check failed: {e}")
        return jsonify({
            "service": "archive",
            "status": "unhealthy",
            "error": str(e)
        }), 503

@archive_bp.route('/update', methods=['PUT'])
@measure_performance
def update_letter():
    """
    Update existing letter: regenerate PDF and update Google Sheets row.
    
    Request Body:
        UpdateLetterRequest: Contains letter_id, content, and optional template
        
    Returns:
        Success response with processing status
    """
    with ErrorContext("update_letter_api"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400
            
            # Parse and validate request
            try:
                update_request = UpdateLetterRequest(**data)
            except ValidationError as e:
                logger.warning(f"Validation error in letter update: {e}")
                return jsonify({
                    "error": "بيانات الطلب غير صحيحة",
                    "details": e.errors()
                }), 400
            
            # Get Google Drive folder ID from environment variables
            folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
            if not folder_id:
                return build_error_response("لم يتم تكوين معرف مجلد Google Drive", 500)
            
            # Start background processing
            background_thread = threading.Thread(
                target=process_letter_update_in_background,
                args=(update_request.letter_id, update_request.content, update_request.template, folder_id)
            )
            background_thread.daemon = True
            background_thread.start()
            
            # Return immediate success response
            response = {
                "status": "success",
                "message": f"Letter update started for ID: {update_request.letter_id}",
                "processing": "background",
                "letter_id": update_request.letter_id,
                "template": update_request.template
            }
            
            logger.info(f"Letter update initiated for ID: {update_request.letter_id}")
            return jsonify(response), 200
            
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return jsonify(build_error_response(e)), 400
        except Exception as e:
            logger.error(f"Letter update failed: {e}")
            return jsonify(build_error_response(e)), 500

def process_letter_update_in_background(
    letter_id: str,
    new_content: str, 
    template: str,
    folder_id: str
) -> None:
    """
    Process letter update in background thread.
    
    Args:
        letter_id: ID of the letter to update
        new_content: New letter content
        template: Template name for PDF generation
        folder_id: Google Drive folder ID
    """
    try:
        logger.info(f"Starting background update for letter ID: {letter_id}")
        
        # Get drive logger service
        drive_logger = get_drive_logger_service()
        
        # Update letter: generate new PDF, upload to Drive, and update sheet
        result = drive_logger.update_letter_pdf_and_log(
            letter_id=letter_id,
            new_content=new_content,
            folder_id=folder_id,
            template=template
        )
        
        if result["status"] == "success":
            logger.info(f"Background update completed successfully for letter ID: {letter_id}")
            logger.info(f"New Drive URL: {result.get('file_url', 'N/A')}")
        else:
            logger.error(f"Background update failed for letter ID: {letter_id}: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error in background update for letter ID {letter_id}: {str(e)}", exc_info=True)

# Legacy endpoint for backward compatibility
@archive_bp.route('/upload-pdf', methods=['POST'])
def legacy_upload_pdf():
    """Legacy endpoint for PDF upload - redirects to new archive endpoint."""
    logger.warning("Legacy endpoint /upload-pdf used - please migrate to /api/v1/archive/letter")
    return archive_letter()
