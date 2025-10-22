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
    Validate user credentials and return JWT token.

    Request Body:
        email: str - User email address
        password: str - User password

    Returns:
        JWT token if validation successful
    """
    with ErrorContext("validate_user_api"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400

            # Get required fields
            email = data.get('email')
            password = data.get('password')

            if not email:
                return jsonify({"error": "البريد الإلكتروني مطلوب"}), 400
            if not password:
                return jsonify({"error": "كلمة المرور مطلوبة"}), 400

            # Validate email format
            email = email.strip()
            if '@' not in email:
                return jsonify({"error": "صيغة البريد الإلكتروني غير صحيحة"}), 400

            # Validate user credentials
            user_service = get_user_management_service()
            success, client_info, user_info = user_service.login_user(email, password)

            if success and client_info and user_info:
                logger.info(f"User validated successfully: {email}")
                # Generate JWT token
                token = user_service._create_access_token(client_info, user_info, success)
                return jsonify({
                    "status": "success",
                    "token": token,
                    "message": "تم التحقق من المستخدم بنجاح"
                }), 200
            elif client_info and user_info and not success:
                # Check if user is inactive
                if user_info.status.lower() != "active":
                    logger.warning(f"User validation failed - user inactive: {email} (status: {user_info.status})")
                    return jsonify({
                        "status": "error",
                        "message": "الحساب غير مفعل",
                        "error": f"حالة الحساب: {user_info.status}"
                    }), 403
                # Invalid password
                logger.warning(f"User validation failed - invalid password: {email}")
                return jsonify({
                    "status": "error",
                    "message": "كلمة المرور غير صحيحة",
                    "error": "كلمة المرور غير صحيحة"
                }), 401
            elif client_info and not user_info:
                # User not found
                logger.warning(f"User validation failed - user not found: {email}")
                return jsonify({
                    "status": "error",
                    "message": "المستخدم غير موجود",
                    "error": "البريد الإلكتروني غير مسجل"
                }), 404
            else:
                # No matching client
                logger.warning(f"User validation failed - no matching client: {email}")
                return jsonify({
                    "status": "error",
                    "message": "لا يمكن التحقق من المستخدم",
                    "error": "لا يوجد عميل مطابق لهذا البريد الإلكتروني"
                }), 400

        except Exception as e:
            logger.error(f"User validation failed: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/create-user', methods=['POST'])
@measure_performance
def create_user():
    """
    Create a new user account.

    Request Body:
        email: str - User email address
        password: str - User password
        full_name: str - User's full name

    Returns:
        User creation result
    """
    with ErrorContext("create_user_api"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400

            # Get required fields
            email = data.get('email')
            password = data.get('password')
            full_name = data.get('full_name')

            if not email:
                return jsonify({"error": "البريد الإلكتروني مطلوب"}), 400
            if not password:
                return jsonify({"error": "كلمة المرور مطلوبة"}), 400
            if not full_name:
                return jsonify({"error": "الاسم الكامل مطلوب"}), 400

            # Validate email format
            email = email.strip()
            if '@' not in email:
                return jsonify({"error": "صيغة البريد الإلكتروني غير صحيحة"}), 400

            # Validate password strength (basic)
            if len(password) < 6:
                return jsonify({"error": "كلمة المرور يجب أن تكون 6 أحرف على الأقل"}), 400

            # Create user
            user_service = get_user_management_service()
            success, client_info, user_info = user_service.create_user(email, password, full_name)

            if success and client_info and user_info:
                logger.info(f"User created successfully: {email} for client {client_info.display_name}")
                return jsonify({
                    "status": "success",
                    "message": "تم إنشاء المستخدم بنجاح",
                    "user": user_info.to_dict(),
                    "client": {
                        "client_id": client_info.client_id,
                        "display_name": client_info.display_name
                    }
                }), 201
            elif client_info and user_info:
                # User already exists
                logger.warning(f"User creation failed - user already exists: {email}")
                return jsonify({
                    "status": "error",
                    "message": "المستخدم موجود بالفعل",
                    "error": "البريد الإلكتروني مسجل مسبقاً"
                }), 409
            else:
                # No matching client
                logger.warning(f"User creation failed - no matching client: {email}")
                return jsonify({
                    "status": "error",
                    "message": "لا يمكن إنشاء المستخدم",
                    "error": "لا يوجد عميل مطابق لهذا البريد الإلكتروني"
                }), 400

        except Exception as e:
            logger.error(f"User creation failed: {e}")
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
