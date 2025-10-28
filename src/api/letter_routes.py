"""
API Routes for Letter Generation
Handles all letter generation related endpoints with proper validation and error handling.
"""

import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from ..models import (
    GenerateLetterRequest, 
    LetterOutput,
    ErrorResponse,
    SuccessResponse
)
from ..services import get_letter_service, get_sheets_service, LetterGenerationContext
from ..services.usage_tracking_service import get_usage_tracking_service
from ..utils import (
    ErrorContext,
    build_error_response,
    validate_and_raise,
    measure_performance,
    require_auth,
    get_user_from_token,
    get_token_manager
)

logger = logging.getLogger(__name__)
from ..utils import SpecializedLogger

# Create blueprint
letter_bp = Blueprint('letter', __name__, url_prefix='/api/v1/letter')

@letter_bp.route('/generate', methods=['POST'])
@measure_performance
@require_auth
def generate_letter(user_info):
    """
    Generate a new letter based on user input.
    Requires JWT authentication.
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Request Body:
        GenerateLetterRequest: Letter generation parameters
        letterType: Type of letter (used to load instructions and template)
        
    Returns:
        LetterOutput: Generated letter with metadata
    """
    with ErrorContext("generate_letter_api"):
        try:
            # Extract sheet_id and user email from JWT token
            sheet_id = user_info.get('sheet_id')
            user_email = user_info.get('user', {}).get('email', 'unknown')

            if not sheet_id:
                return build_error_response("معرف الجدول غير موجود في التوكن", 400)

            # Check if JWT token is expired (validate token expiration time from JWT)
            import time
            token_exp = user_info.get('exp')
            if token_exp:
                current_time = time.time()
                if current_time > token_exp:
                    logger.warning(f"JWT token expired for user: {user_email}")
                    return jsonify({
                        "status": "error",
                        "message": "انتهت صلاحية التوكن. يرجى تسجيل الدخول مرة أخرى"
                    }), 401

            logger.info(f"Letter generation request from user: {user_email}, sheet: {sheet_id}")
            
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400
            
            # Parse and validate request
            try:
                letter_request = GenerateLetterRequest(**data)
            except ValidationError as e:
                logger.warning(f"Validation error in letter generation: {e}")
                return jsonify({
                    "error": "بيانات الطلب غير صحيحة",
                    "details": e.errors()
                }), 400
            
            # Check quota limit before generating letter
            try:
                usage_service = get_usage_tracking_service()
                quota_check = usage_service.check_quota(sheet_id)
                
                if quota_check["status"] == "exceeded":
                    logger.warning(f"User {user_email} exceeded monthly quota: {quota_check}")
                    return jsonify({
                        "error": "تم تجاوز حد الخطابات الشهري",
                        "message": quota_check.get("reason", "Monthly letter quota has been reached"),
                        "quota_info": {
                            "current_count": quota_check.get("current_count", 0),
                            "quota_limit": quota_check.get("quota_limit")
                        }
                    }), 429  # 429 Too Many Requests
                
                logger.debug(f"Quota check passed for user {user_email}: {quota_check}")
                
            except Exception as e:
                logger.warning(f"Error checking quota: {e}, proceeding with generation")
                # Continue with generation if quota check fails (fail open)
            
            # Get letter category for loading instructions and template
            letter_category = letter_request.category.value
            member_name = letter_request.member_name or ""
            
            # Get letter configuration from user's sheet using old behavior (Ideal, Instructions, Info sheets)
            try:
                sheets_service = get_sheets_service()
                
                # Load from user's sheets using the same old behavior
                # Searches: Ideal (template), Instructions (instructions), Info (member info)
                letter_config = sheets_service.get_letter_config_by_category_from_sheet_id(
                    sheet_id=sheet_id,
                    category=letter_category,
                    member_name=member_name
                )
                
                logger.info(f"Loaded letter config from sheet {sheet_id} for category: {letter_category}")
                
            except Exception as e:
                logger.warning(f"Could not fetch letter config from user's sheet: {e}")
                # Fallback to defaults
                letter_config = {
                    "letter": "",
                    "instruction": "اكتب خطاباً رسمياً باللغة العربية",
                    "member_info": ""
                }
            
            # Create generation context
            context = LetterGenerationContext(
                user_prompt=letter_request.prompt,
                recipient=letter_request.recipient,
                member_info=letter_config.get("member_info", "غير محدد"),
                is_first_contact=letter_request.is_first,
                reference_letter=letter_config.get("letter"),
                category=letter_request.category.value,
                writing_instructions=letter_config.get("instruction"),
                recipient_title=letter_request.recipient_title,
                recipient_job_title=letter_request.recipient_job_title,
                organization_name=letter_request.organization_name,
                previous_letter_content=letter_request.previous_letter_content,
                previous_letter_id=letter_request.previous_letter_id,
                session_id=letter_request.session_id,
                sheet_id=sheet_id  # Pass user's sheet_id for memory instructions
            )
            
            # Generate letter
            letter_service = get_letter_service()
            letter_output = letter_service.generate_letter(context)
            
            logger.info(f"Letter generated successfully: {letter_output.ID}")
            
            # Track token usage and cost
            try:
                usage_service = get_usage_tracking_service()
                
                # Build the full prompt that was sent to the LLM
                prompt_template = letter_service._get_prompt_template()
                prompt_input = {
                    "user_prompt": context.user_prompt,
                    "reference_context": context.reference_letter or "",
                    "additional_context": letter_service._build_context_string(context),
                    "member_info": context.member_info,
                    "writing_instructions": context.writing_instructions or "",
                    "letter_id": context.letter_id,
                    "current_date": letter_service._get_memory_instructions(context),  # This gets date and instructions
                    "previous_letter_info": f"الخطاب السابق: {context.previous_letter_content}" if context.previous_letter_content else ""
                }
                
                # Estimate token usage
                prompt_text = str(prompt_input)
                response_text = letter_output.Letter
                
                usage_estimate = usage_service.estimate_usage(
                    prompt=prompt_text,
                    response=response_text,
                    model="gpt-4o"  # Adjust based on your config
                )
                
                # Update usage statistics in the Usage sheet
                update_result = usage_service.update_usage(
                    sheet_id=sheet_id,
                    tokens_used=usage_estimate["total_tokens"],
                    cost_usd=usage_estimate["cost_usd"]
                )
                
                logger.info(f"Usage tracked for letter {letter_output.ID}: {usage_estimate['total_tokens']} tokens, ${usage_estimate['cost_usd']:.6f}")
                
                # Add usage info to response
                response_data = letter_output.model_dump()
                response_data["usage"] = {
                    "input_tokens": usage_estimate["input_tokens"],
                    "output_tokens": usage_estimate["output_tokens"],
                    "total_tokens": usage_estimate["total_tokens"],
                    "cost_usd": usage_estimate["cost_usd"]
                }
                
                return jsonify(response_data), 200
                
            except Exception as e:
                logger.warning(f"Failed to track usage: {e}")
                # Still return the letter even if usage tracking fails
                response_data = letter_output.model_dump()
                response_data["usage_error"] = str(e)
                return jsonify(response_data), 200
            
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return jsonify(build_error_response(e)), 400
        except Exception as e:
            logger.error(f"Letter generation failed: {e}")
            return jsonify(build_error_response(e)), 500

@letter_bp.route('/validate', methods=['POST'])
@measure_performance
def validate_letter():
    """
    Validate letter content for quality and structure.
    
    Request Body:
        letter: str - Letter content to validate
        
    Returns:
        Validation results and suggestions
    """
    with ErrorContext("validate_letter_api"):
        try:
            data = request.get_json()
            if not data or 'letter' not in data:
                return jsonify({"error": "محتوى الخطاب مطلوب"}), 400
            
            letter_content = data['letter']
            if not letter_content or not letter_content.strip():
                return jsonify({"error": "محتوى الخطاب لا يمكن أن يكون فارغاً"}), 400
            
            # Create a mock LetterOutput for validation
            mock_letter = LetterOutput(
                ID="validation",
                Title="تحقق",
                Letter=letter_content,
                Date="validation"
            )
            
            letter_service = get_letter_service()
            is_valid = letter_service.validate_letter_content(mock_letter)
            
            # Additional checks
            word_count = len(letter_content.split())
            has_arabic = any('\u0600' <= char <= '\u06FF' for char in letter_content)
            has_bismillah = "بسم الله الرحمن الرحيم" in letter_content
            has_greeting = any(greeting in letter_content for greeting in ["السلام عليكم", "تحية طيبة"])
            
            validation_results = {
                "is_valid": is_valid,
                "checks": {
                    "has_arabic_content": has_arabic,
                    "has_bismillah": has_bismillah,
                    "has_greeting": has_greeting,
                    "sufficient_length": word_count >= 20
                },
                "metrics": {
                    "word_count": word_count,
                    "character_count": len(letter_content),
                    "line_count": len(letter_content.split('\n'))
                },
                "suggestions": []
            }
            
            # Generate suggestions
            if not has_arabic:
                validation_results["suggestions"].append("الخطاب يجب أن يحتوي على نص عربي")
            if not has_bismillah:
                validation_results["suggestions"].append("يُنصح بإضافة البسملة في بداية الخطاب")
            if not has_greeting:
                validation_results["suggestions"].append("يُنصح بإضافة التحية المناسبة")
            if word_count < 20:
                validation_results["suggestions"].append("الخطاب قصير جداً، يُنصح بإضافة المزيد من التفاصيل")
            
            return jsonify({
                "status": "success",
                "validation": validation_results
            }), 200
            
        except Exception as e:
            logger.error(f"Letter validation failed: {e}")
            return jsonify(build_error_response(e)), 500

@letter_bp.route('/categories', methods=['GET'])
def get_letter_categories():
    """
    Get available letter categories.
    
    Returns:
        List of available letter categories
    """
    try:
        from ..models import LetterCategory
        
        categories = [
            {
                "value": category.value,
                "display_name": category.value,
                "description": f"فئة {category.value}"
            }
            for category in LetterCategory
        ]
        
        return jsonify({
            "status": "success",
            "categories": categories
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        return jsonify(build_error_response(e)), 500

@letter_bp.route('/templates/<category>', methods=['GET'])
@measure_performance
def get_letter_template(category: str):
    """
    Get letter template for a specific category.
    
    Args:
        category: Letter category
        
    Returns:
        Template information for the category
    """
    with ErrorContext("get_letter_template", {"category": category}):
        try:
            sheets_service = get_sheets_service()
            letter_config = sheets_service.get_letter_config_by_category(category)
            
            template_info = {
                "category": category,
                "reference_letter": letter_config.get("letter", ""),
                "instructions": letter_config.get("instruction", ""),
                "has_template": bool(letter_config.get("letter"))
            }
            
            return jsonify({
                "status": "success",
                "template": template_info
            }), 200
            
        except Exception as e:
            logger.error(f"Failed to get template for category {category}: {e}")
            return jsonify(build_error_response(e)), 500

@letter_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for letter generation service.
    
    Returns:
        Service health status
    """
    try:
        letter_service = get_letter_service()
        service_stats = letter_service.get_service_stats()
        
        return jsonify({
            "status": "healthy",
            "service": "letter_generation",
            "stats": service_stats,
            "timestamp": logging.Formatter().formatTime(logging.LogRecord(
                name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
            ))
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

# Error handlers for the blueprint
@letter_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle Pydantic validation errors."""
    return jsonify({
        "error": "Validation failed",
        "details": error.errors()
    }), 400

@letter_bp.route('/<letter_id>', methods=['GET'])
@measure_performance
@require_auth
def get_letter_by_id(letter_id, user_info):
    """
    Get a letter by its ID from the user's Submissions sheet.
    Requires JWT authentication to get sheet_id.

    Args:
        letter_id: The unique letter identifier (e.g., LET-20251028-12345)

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        Letter details with metadata
    """
    with ErrorContext("get_letter_by_id", {"letter_id": letter_id}):
        try:
            # Extract sheet_id and user email from JWT token
            sheet_id = user_info.get('sheet_id')
            user_email = user_info.get('user', {}).get('email', 'unknown')

            if not sheet_id:
                SpecializedLogger.log_action(
                    action_type='letter.retrieval',
                    user_email=user_email,
                    action='Get letter failed - no sheet_id',
                    details={'letter_id': letter_id},
                    status='failure'
                )
                return build_error_response("معرف الجدول غير موجود في التوكن", 400)

            # Validate letter_id format
            if not letter_id or not letter_id.startswith('LET-'):
                SpecializedLogger.log_action(
                    action_type='letter.retrieval',
                    user_email=user_email,
                    action='Get letter failed - invalid letter_id format',
                    details={'letter_id': letter_id},
                    status='failure'
                )
                return build_error_response("معرف الخطاب غير صحيح", 400)

            logger.info(f"Letter retrieval request: {letter_id} by user: {user_email}, sheet: {sheet_id}")

            # Get the letter from the user's Submissions sheet
            sheets_service = get_sheets_service()

            try:
                # Access the user's spreadsheet
                with sheets_service.get_client_context() as client:
                    spreadsheet = client.open_by_key(sheet_id)
                    submissions_sheet = spreadsheet.worksheet("Submissions")

                    # Get all records from Submissions sheet
                    records = submissions_sheet.get_all_records()

                    # Find the letter with matching ID
                    letter_record = None
                    for record in records:
                        if record.get('ID') == letter_id:
                            letter_record = record
                            break

                    if not letter_record:
                        SpecializedLogger.log_action(
                            action_type='letter.retrieval',
                            user_email=user_email,
                            action='Get letter failed - not found',
                            details={'letter_id': letter_id},
                            status='failure'
                        )
                        return jsonify({
                            "status": "error",
                            "message": "الخطاب غير موجود",
                            "letter_id": letter_id
                        }), 404

                    # Log successful retrieval
                    SpecializedLogger.log_action(
                        action_type='letter.retrieval',
                        user_email=user_email,
                        action='Get letter successful',
                        details={
                            'letter_id': letter_id,
                            'letter_type': letter_record.get('Letter_type'),
                            'recipient': letter_record.get('Recipient_name')
                        },
                        status='success'
                    )

                    logger.info(f"Letter retrieved successfully: {letter_id}")

                    return jsonify({
                        "status": "success",
                        "letter": letter_record
                    }), 200

            except Exception as e:
                logger.error(f"Error retrieving letter from sheet: {e}")
                return build_error_response(f"خطأ في جلب الخطاب: {str(e)}", 500)

        except Exception as e:
            logger.error(f"Letter retrieval failed: {e}")
            SpecializedLogger.log_action(
                action_type='letter.retrieval',
                user_email=user_info.get('user', {}).get('email', 'unknown'),
                action='Get letter error',
                details={'letter_id': letter_id, 'error': str(e)},
                status='failure'
            )
            return build_error_response(e), 500


@letter_bp.route('/<letter_id>', methods=['DELETE'])
@measure_performance
@require_auth
def delete_letter_by_id(letter_id, user_info):
    """
    Delete a letter by its ID from the user's Submissions sheet.
    Only the user who created the letter can delete it.
    Requires JWT authentication to get sheet_id.

    Args:
        letter_id: The unique letter identifier (e.g., LET-20251028-12345)

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        Confirmation of deletion
    """
    with ErrorContext("delete_letter_by_id", {"letter_id": letter_id}):
        try:
            # Extract sheet_id and user email from JWT token
            sheet_id = user_info.get('sheet_id')
            user_email = user_info.get('user', {}).get('email', 'unknown')

            if not sheet_id:
                SpecializedLogger.log_action(
                    action_type='letter.deletion',
                    user_email=user_email,
                    action='Delete letter failed - no sheet_id',
                    details={'letter_id': letter_id},
                    status='failure'
                )
                return build_error_response("معرف الجدول غير موجود في التوكن", 400)

            # Validate letter_id format
            if not letter_id or not letter_id.startswith('LET-'):
                SpecializedLogger.log_action(
                    action_type='letter.deletion',
                    user_email=user_email,
                    action='Delete letter failed - invalid letter_id format',
                    details={'letter_id': letter_id},
                    status='failure'
                )
                return build_error_response("معرف الخطاب غير صحيح", 400)

            logger.info(f"Letter deletion request: {letter_id} by user: {user_email}, sheet: {sheet_id}")

            # Delete the letter from the user's Submissions sheet
            sheets_service = get_sheets_service()

            try:
                # Access the user's spreadsheet
                with sheets_service.get_client_context() as client:
                    spreadsheet = client.open_by_key(sheet_id)
                    submissions_sheet = spreadsheet.worksheet("Submissions")

                    # Get all records from Submissions sheet
                    records = submissions_sheet.get_all_records()

                    # Find the letter with matching ID
                    letter_row_index = None
                    letter_record = None
                    for idx, record in enumerate(records):  # idx starts from 0
                        if record.get('ID') == letter_id:
                            letter_record = record
                            letter_row_index = idx + 2  # +2 because row 1 is headers, +1 for 1-indexed in gspread
                            break

                    if not letter_record:
                        SpecializedLogger.log_action(
                            action_type='letter.deletion',
                            user_email=user_email,
                            action='Delete letter failed - not found',
                            details={'letter_id': letter_id},
                            status='failure'
                        )
                        return jsonify({
                            "status": "error",
                            "message": "الخطاب غير موجود",
                            "letter_id": letter_id
                        }), 404

                    # Delete the row from the sheet (delete_rows uses 1-indexed row numbers)
                    submissions_sheet.delete_rows(letter_row_index)

                    # Log successful deletion
                    SpecializedLogger.log_action(
                        action_type='letter.deletion',
                        user_email=user_email,
                        action='Delete letter successful',
                        details={
                            'letter_id': letter_id,
                            'letter_type': letter_record.get('Letter_type'),
                            'recipient': letter_record.get('Recipient_name')
                        },
                        status='success'
                    )

                    logger.info(f"Letter deleted successfully: {letter_id}")

                    return jsonify({
                        "status": "success",
                        "message": "تم حذف الخطاب بنجاح",
                        "letter_id": letter_id
                    }), 200

            except Exception as e:
                logger.error(f"Error deleting letter from sheet: {e}")
                return build_error_response(f"خطأ في حذف الخطاب: {str(e)}", 500)

        except Exception as e:
            logger.error(f"Letter deletion failed: {e}")
            SpecializedLogger.log_action(
                action_type='letter.deletion',
                user_email=user_info.get('user', {}).get('email', 'unknown'),
                action='Delete letter error',
                details={'letter_id': letter_id, 'error': str(e)},
                status='failure'
            )
            return build_error_response(e), 500


@letter_bp.errorhandler(404)
def handle_not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist"
    }), 404

@letter_bp.errorhandler(405)
def handle_method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({
        "error": "Method not allowed",
        "message": "The requested method is not allowed for this endpoint"
    }), 405

@letter_bp.errorhandler(500)
def handle_internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500
