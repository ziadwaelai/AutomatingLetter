"""
API Routes for User Management
Handles user authentication, client lookup, and access validation.
"""

import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify

from ..services import get_user_management_service
from ..utils import (
    ErrorContext,
    build_error_response,
    measure_performance
)

logger = logging.getLogger(__name__)

# Create blueprint
user_bp = Blueprint('user', __name__, url_prefix='/api/v1/user')


@user_bp.route('/validate', methods=['POST'])
@measure_performance
def validate_user():
    """
    Validate user access based on email.

    Request Body:
        email: str - User email address

    Returns:
        Validation result with client information
    """
    with ErrorContext("validate_user_api"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400

            # Get email from request
            email = data.get('email')
            if not email:
                return jsonify({"error": "البريد الإلكتروني مطلوب"}), 400

            # Validate email format
            email = email.strip()
            if '@' not in email:
                return jsonify({"error": "صيغة البريد الإلكتروني غير صحيحة"}), 400

            # Validate user access
            user_service = get_user_management_service()
            has_access, client_info = user_service.validate_user_access(email)

            if has_access and client_info:
                logger.info(f"User validated successfully: {email}")
                # Generate JWT token
                token = user_service._create_access_token(client_info, has_access)
                return jsonify({
                    "status": "success",
                    "token": token,
                    "message": "تم التحقق من المستخدم بنجاح"
                }), 200
            else:
                logger.warning(f"User validation failed: {email}")
                return jsonify({
                    "status": "error",
                    "has_access": False,
                    "message": "المستخدم غير مصرح له بالوصول",
                    "error": "لا يوجد عميل مطابق لهذا البريد الإلكتروني"
                }), 403

        except Exception as e:
            logger.error(f"User validation failed: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/client', methods=['POST'])
@measure_performance
def get_client_info():
    """
    Get client information by user email.

    Request Body:
        email: str - User email address

    Returns:
        Client information including sheet ID and drive ID
    """
    with ErrorContext("get_client_info_api"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400

            # Get email from request
            email = data.get('email')
            if not email:
                return jsonify({"error": "البريد الإلكتروني مطلوب"}), 400

            # Get client info
            user_service = get_user_management_service()
            client_info = user_service.get_client_by_email(email)

            if client_info:
                logger.info(f"Client info retrieved for: {email}")
                return jsonify({
                    "status": "success",
                    "client": client_info.to_dict()
                }), 200
            else:
                logger.warning(f"No client found for: {email}")
                return jsonify({
                    "status": "error",
                    "message": "لا يوجد عميل مطابق لهذا البريد الإلكتروني"
                }), 404

        except Exception as e:
            logger.error(f"Failed to get client info: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/clients', methods=['GET'])
@measure_performance
def get_all_clients():
    """
    Get all clients from master sheet.
    Admin endpoint for listing all available clients.

    Returns:
        List of all clients
    """
    with ErrorContext("get_all_clients_api"):
        try:
            user_service = get_user_management_service()
            clients = user_service.get_all_clients()

            clients_data = [client.to_dict() for client in clients]

            logger.info(f"Retrieved {len(clients)} clients")
            return jsonify({
                "status": "success",
                "count": len(clients_data),
                "clients": clients_data
            }), 200

        except Exception as e:
            logger.error(f"Failed to get all clients: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/cache/clear', methods=['POST'])
@measure_performance
def clear_cache():
    """
    Clear user management cache.
    Admin endpoint for forcing cache refresh.

    Returns:
        Success message
    """
    with ErrorContext("clear_cache_api"):
        try:
            user_service = get_user_management_service()
            user_service.clear_cache()

            logger.info("User management cache cleared")
            return jsonify({
                "status": "success",
                "message": "تم مسح ذاكرة التخزين المؤقت بنجاح"
            }), 200

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for user management service.

    Returns:
        Service health status
    """
    try:
        user_service = get_user_management_service()
        service_stats = user_service.get_service_stats()

        return jsonify({
            "status": "healthy",
            "service": "user_management",
            "stats": service_stats
        }), 200

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503


# Error handlers for the blueprint
@user_bp.errorhandler(404)
def handle_not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "نقطة النهاية غير موجودة",
        "message": "نقطة النهاية المطلوبة غير موجودة"
    }), 404


@user_bp.errorhandler(405)
def handle_method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({
        "error": "الطريقة غير مسموحة",
        "message": "الطريقة المطلوبة غير مسموحة لنقطة النهاية هذه"
    }), 405


@user_bp.errorhandler(500)
def handle_internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "خطأ داخلي في الخادم",
        "message": "حدث خطأ غير متوقع"
    }), 500
