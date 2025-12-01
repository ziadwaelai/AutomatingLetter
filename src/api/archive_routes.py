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

@archive_bp.route('/letter/docx', methods=['POST'])
@measure_performance
def archive_letter_docx():
    """
    Archive letter to DOCX file, upload to Google Drive, and log to sheets.
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
        username = data.get('username', 'unknown')
        output_path = data.get('output_path', None)  # User can provide custom path

        # Get Google Drive folder ID from environment variables (optional for DOCX)
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

        # Start background processing
        background_thread = threading.Thread(
            target=process_letter_docx_archive_in_background,
            args=(letter_content, letter_id, letter_type, recipient, title, is_first, folder_id, username, output_path),
            name=f"DocxArchiveThread-{letter_id}"
        )
        background_thread.daemon = False
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

def process_letter_docx_archive_in_background(
    letter_content: str,
    letter_id: str,
    letter_type: str,
    recipient: str,
    title: str,
    is_first: bool,
    folder_id: str,
    username: str,
    output_path: str = None
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
        folder_id: Google Drive folder ID (optional)
        username: Username of creator
        output_path: Custom output path for DOCX file
    """
    temp_docx_path = None
    try:
        logger.info(f"Starting background DOCX archiving for letter ID: {letter_id}")

        # Get services
        docx_service = get_enhanced_docx_service()
        drive_logger = get_drive_logger_service()

        # Parse raw letter content and create DOCX
        logger.info(f"Creating DOCX document for letter ID: {letter_id}")
        try:
            # Parse raw letter content using GPT-4o
            parsed_data = docx_service._parse_raw_letter_content(letter_content)

            # Create document with parsed data and letter ID
            docx_service.create_from_json(parsed_data, letter_id=letter_id)

            # Determine output path
            if output_path:
                # User provided custom path - use it as-is
                temp_docx_path = output_path
                logger.info(f"Using custom output path: {output_path}")
            else:
                # Use default temp directory with letter ID
                import tempfile
                temp_dir = tempfile.gettempdir()
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                if not safe_title:
                    safe_title = f"letter_{letter_id}"
                temp_docx_path = os.path.join(temp_dir, f"{safe_title}_{letter_id}.docx")
                logger.info(f"Using default temp path: {temp_docx_path}")

            # Save DOCX file
            saved_path = docx_service.save(temp_docx_path)
            logger.info(f"DOCX generated successfully: {saved_path}")

        except Exception as docx_error:
            logger.error(f"Error during DOCX generation: {str(docx_error)}", exc_info=True)
            raise

        # Upload to Drive if folder_id is provided
        if folder_id:
            logger.info(f"Uploading DOCX to Drive and logging for letter ID: {letter_id}")
            try:
                archive_result = drive_logger.save_letter_to_drive_and_log(
                    letter_file_path=temp_docx_path,
                    letter_content=letter_content,
                    letter_type=letter_type,
                    recipient=recipient,
                    title=title,
                    is_first=is_first,
                    folder_id=folder_id,
                    letter_id=letter_id,
                    username=username
                )

                if archive_result.get("status") == "success":
                    logger.info(f"DOCX archived to Drive successfully for letter ID: {letter_id}")
                    logger.info(f"Drive URL: {archive_result.get('file_url', 'N/A')}")
                else:
                    logger.error(f"Drive upload failed for letter ID: {letter_id}: {archive_result.get('message', 'Unknown error')}")

            except Exception as archive_error:
                logger.error(f"Error during Drive upload: {str(archive_error)}", exc_info=True)
        else:
            logger.info(f"No Google Drive folder ID provided, skipping Drive upload for letter ID: {letter_id}")

        # Clean up temporary file only if it's in temp directory
        if temp_docx_path and tempfile.gettempdir() in temp_docx_path:
            try:
                if os.path.exists(temp_docx_path):
                    drive_logger.cleanup_temp_file(temp_docx_path)
                    logger.debug(f"Cleaned up temporary file: {temp_docx_path}")
            except Exception as cleanup_error:
                logger.warning(f"Error cleaning up temporary DOCX file: {cleanup_error}")
        else:
            logger.info(f"DOCX file saved at: {temp_docx_path}")

        logger.info(f"DOCX archiving completed for letter ID: {letter_id}")

    except Exception as e:
        logger.error(f"CRITICAL ERROR in background DOCX archiving for letter ID {letter_id}: {str(e)}", exc_info=True)

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
                args=(
                    update_request.letter_id,
                    update_request.content,
                    update_request.template,
                    folder_id,
                    update_request.include_signature,
                    update_request.signature_image_url,
                    update_request.signature_name,
                    update_request.signature_job_title,
                    update_request.signature_section_title
                )
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
    folder_id: str,
    include_signature: bool = False,
    signature_image_url: str = None,
    signature_name: str = None,
    signature_job_title: str = None,
    signature_section_title: str = "التوقيع"
) -> None:
    """
    Process letter update in background thread.

    Args:
        letter_id: ID of the letter to update
        new_content: New letter content
        template: Template name for PDF generation
        folder_id: Google Drive folder ID
        include_signature: Whether to include signature section (default: False)
        signature_image_url: Google Drive URL for signature image (optional)
        signature_name: Name of the signer (optional)
        signature_job_title: Job title of the signer (optional)
        signature_section_title: Custom signature section title (default: "التوقيع")
    """
    try:
        logger.info(f"Starting background update for letter ID: {letter_id}")
        logger.debug(f"[BACKGROUND] DEBUG: include_signature={include_signature}")

        # Get drive logger service
        drive_logger = get_drive_logger_service()

        # Update letter: generate new PDF, upload to Drive, and update sheet
        result = drive_logger.update_letter_pdf_and_log(
            letter_id=letter_id,
            new_content=new_content,
            folder_id=folder_id,
            template=template,
            include_signature=include_signature,
            signature_image_url=signature_image_url,
            signature_name=signature_name,
            signature_job_title=signature_job_title,
            signature_section_title=signature_section_title
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
