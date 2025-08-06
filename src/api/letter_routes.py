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
from ..utils import (
    ErrorContext,
    build_error_response,
    validate_and_raise,
    measure_performance
)

logger = logging.getLogger(__name__)

# Create blueprint
letter_bp = Blueprint('letter', __name__, url_prefix='/api/v1/letter')

@letter_bp.route('/generate', methods=['POST'])
@measure_performance
def generate_letter():
    """
    Generate a new letter based on user input.
    
    Request Body:
        GenerateLetterRequest: Letter generation parameters
        
    Returns:
        LetterOutput: Generated letter with metadata
    """
    with ErrorContext("generate_letter_api"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "Request must be JSON"}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            # Parse and validate request
            try:
                letter_request = GenerateLetterRequest(**data)
            except ValidationError as e:
                logger.warning(f"Validation error in letter generation: {e}")
                return jsonify({
                    "error": "Invalid request data",
                    "details": e.errors()
                }), 400
            
            # Get letter configuration
            try:
                sheets_service = get_sheets_service()
                letter_config = sheets_service.get_letter_config_by_category(
                    letter_request.category.value,
                    letter_request.member_name or ""
                )
            except Exception as e:
                logger.warning(f"Could not fetch letter config: {e}")
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
                previous_letter_id=letter_request.previous_letter_id
            )
            
            # Generate letter
            letter_service = get_letter_service()
            letter_output = letter_service.generate_letter(context)
            
            logger.info(f"Letter generated successfully: {letter_output.ID}")
            
            return jsonify(letter_output.model_dump()), 200
            
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
                return jsonify({"error": "Letter content is required"}), 400
            
            letter_content = data['letter']
            if not letter_content or not letter_content.strip():
                return jsonify({"error": "Letter content cannot be empty"}), 400
            
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
