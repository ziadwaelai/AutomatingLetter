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
    measure_performance,
    get_token_manager,
    require_auth,
    require_admin
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
            phone_number = data.get('phone_number', '')  # Optional field

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
            success, client_info, user_info = user_service.create_user(email, password, full_name, phone_number)

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


@user_bp.route('/reset-password', methods=['POST'])
@measure_performance
def reset_password():
    """
    Reset user password (requires old password verification).
    User must provide current password to set a new one.

    Request Body:
        email: str - User email address
        old_password: str - Current password (for verification)
        new_password: str - New password to set

    Returns:
        Success or error message
    """
    with ErrorContext("reset_password_api"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400

            # Get required fields
            email = data.get('email')
            old_password = data.get('old_password')
            new_password = data.get('new_password')

            if not email:
                return jsonify({"error": "البريد الإلكتروني مطلوب"}), 400
            if not old_password:
                return jsonify({"error": "كلمة المرور الحالية مطلوبة"}), 400
            if not new_password:
                return jsonify({"error": "كلمة المرور الجديدة مطلوبة"}), 400

            # Validate email format
            email = email.strip()
            if '@' not in email:
                return jsonify({"error": "صيغة البريد الإلكتروني غير صحيحة"}), 400

            # Reset password
            user_service = get_user_management_service()
            success, message = user_service.reset_password(email, old_password, new_password)

            if success:
                logger.info(f"Password reset successfully for user: {email}")
                return jsonify({
                    "status": "success",
                    "message": message
                }), 200
            else:
                logger.warning(f"Password reset failed for user: {email} - {message}")
                return jsonify({
                    "status": "error",
                    "message": message
                }), 400

        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/forgot-password/request-token', methods=['POST'])
@measure_performance
def request_password_reset_token():
    """
    Request a password reset token (Step 1 of forgot password flow).
    Generates and stores a secure token for the user.

    Request Body:
        email: str - User email address

    Returns:
        Reset token (user should save this and use in next step)
    """
    with ErrorContext("request_password_reset_token_api"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400

            # Get email
            email = data.get('email', '').strip()

            if not email:
                return jsonify({"error": "البريد الإلكتروني مطلوب"}), 400

            # Validate email format
            if '@' not in email:
                return jsonify({"error": "صيغة البريد الإلكتروني غير صحيحة"}), 400

            # Check if user exists
            user_service = get_user_management_service()
            client_info = user_service.get_client_by_email(email)

            if not client_info:
                logger.warning(f"Password reset token request failed - no client for: {email}")
                return jsonify({
                    "status": "error",
                    "message": "لا يوجد عميل مطابق لهذا البريد الإلكتروني"
                }), 404

            # Verify user exists in client sheet
            user_info = user_service.get_user_details_from_client_sheet(client_info.sheet_id, email)
            if not user_info:
                logger.warning(f"Password reset token request failed - user not found: {email}")
                return jsonify({
                    "status": "error",
                    "message": "المستخدم غير موجود"
                }), 404

            # Generate token (valid for 1 hour)
            token_manager = get_token_manager()
            token = token_manager.generate_token(email, lifetime=3600)  # 1 hour

            logger.info(f"Password reset token generated for: {email}")
            return jsonify({
                "status": "success",
                "message": "تم إنشاء رمز إعادة تعيين كلمة المرور. الرمز صالح لمدة 1 ساعة",
                "token": token,
                "expires_in_seconds": 3600
            }), 200

        except Exception as e:
            logger.error(f"Password reset token request failed: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/forgot-password/verify-token', methods=['POST'])
@measure_performance
def verify_password_reset_token():
    """
    Verify a password reset token (Step 2 of forgot password flow).
    Checks if token is valid and not expired.

    Request Body:
        token: str - Password reset token

    Returns:
        Verification result
    """
    with ErrorContext("verify_password_reset_token_api"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400

            # Get token
            token = data.get('token', '').strip()

            if not token:
                return jsonify({"error": "الرمز مطلوب"}), 400

            # Validate token
            token_manager = get_token_manager()
            is_valid, message, email = token_manager.validate_token(token)

            if not is_valid:
                logger.warning(f"Token verification failed: {message}")
                return jsonify({
                    "status": "error",
                    "message": message
                }), 400

            # Token is valid
            logger.info(f"Token verified successfully for: {email}")
            return jsonify({
                "status": "success",
                "message": "الرمز صالح",
                "email": email
            }), 200

        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/forgot-password/reset', methods=['POST'])
@measure_performance
def reset_password_with_token():
    """
    Reset password using a valid token (Step 3 of forgot password flow).
    Requires a valid, non-expired token.

    Request Body:
        token: str - Password reset token
        new_password: str - New password to set

    Returns:
        Success or error message
    """
    with ErrorContext("reset_password_with_token_api"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400

            # Get token and password
            token = data.get('token', '').strip()
            new_password = data.get('new_password', '').strip()

            if not token:
                return jsonify({"error": "الرمز مطلوب"}), 400
            if not new_password:
                return jsonify({"error": "كلمة المرور الجديدة مطلوبة"}), 400

            # Validate password
            if len(new_password) < 6:
                return jsonify({"error": "كلمة المرور يجب أن تكون 6 أحرف على الأقل"}), 400

            # Verify token
            token_manager = get_token_manager()
            is_valid, message, email = token_manager.validate_token(token)

            if not is_valid:
                logger.warning(f"Password reset failed - invalid token: {message}")
                return jsonify({
                    "status": "error",
                    "message": message
                }), 400

            # Get user info to find sheet_id
            user_service = get_user_management_service()
            client_info = user_service.get_client_by_email(email)

            if not client_info:
                logger.error(f"Password reset failed - client not found for: {email}")
                return jsonify({
                    "status": "error",
                    "message": "لا يوجد عميل مطابق لهذا البريد الإلكتروني"
                }), 404

            # Update password
            user_service._update_user_password(client_info.sheet_id, email, new_password)

            # Mark token as used
            token_manager.use_token(token)

            logger.info(f"Password reset successfully using token for: {email}")
            return jsonify({
                "status": "success",
                "message": "تم تحديث كلمة المرور بنجاح"
            }), 200

        except Exception as e:
            logger.error(f"Password reset with token failed: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/admin/reset-password', methods=['POST'])
@measure_performance
@require_admin
@require_auth
def admin_reset_password(user_info):
    """
    Admin endpoint to reset user password without requiring the old password.
    Requires valid JWT token with admin role.

    Request Body:
        email: str - User email address to reset password for
        new_password: str - New password to set

    Returns:
        Success or error message

    Authentication:
        Requires JWT token with 'admin' role in Authorization header
    """
    with ErrorContext("admin_reset_password_api"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400

            # Get required fields
            email = data.get('email', '').strip()
            new_password = data.get('new_password', '').strip()

            if not email:
                return jsonify({"error": "البريد الإلكتروني مطلوب"}), 400
            if not new_password:
                return jsonify({"error": "كلمة المرور الجديدة مطلوبة"}), 400

            # Validate email format
            if '@' not in email:
                return jsonify({"error": "صيغة البريد الإلكتروني غير صحيحة"}), 400

            # Validate password strength
            if len(new_password) < 6:
                return jsonify({"error": "كلمة المرور يجب أن تكون 6 أحرف على الأقل"}), 400

            # Get user service
            user_service = get_user_management_service()

            # Get client info for the user
            client_info = user_service.get_client_by_email(email)
            if not client_info:
                logger.warning(f"Admin password reset failed - client not found for: {email}")
                return jsonify({
                    "status": "error",
                    "message": "لا يوجد عميل مطابق لهذا البريد الإلكتروني"
                }), 404

            # Verify user exists in client sheet
            user_details = user_service.get_user_details_from_client_sheet(client_info.sheet_id, email)
            if not user_details:
                logger.warning(f"Admin password reset failed - user not found: {email}")
                return jsonify({
                    "status": "error",
                    "message": "المستخدم غير موجود"
                }), 404

            # Update password
            user_service._update_user_password(client_info.sheet_id, email, new_password)

            # Log admin action
            admin_email = user_info.get('user', 'unknown')
            logger.info(f"Admin '{admin_email}' reset password for user: {email}")

            return jsonify({
                "status": "success",
                "message": "تم تحديث كلمة المرور بنجاح",
                "email": email,
                "admin": admin_email
            }), 200

        except Exception as e:
            logger.error(f"Admin password reset failed: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/admin/users', methods=['GET'])
@measure_performance
@require_admin
@require_auth
def admin_list_users(user_info):
    """
    List all users from a client.
    Admin endpoint to view all users.

    Query Parameters (optional):
        client_id: str - Filter by specific client (defaults to admin's client)

    Returns:
        List of all users with their details

    Authentication:
        Requires JWT token with 'admin' role
    """
    with ErrorContext("admin_list_users_api"):
        try:
            user_service = get_user_management_service()

            # Get admin's client info from their email in the token
            admin_email = user_info.get('user', {}).get('email')
            target_client = user_service.get_client_by_email(admin_email) if admin_email else None

            if not target_client:
                logger.warning(f"Admin list users failed - client not found for admin {admin_email}")
                return jsonify({
                    "status": "error",
                    "message": "لا يوجد عميل مطابق"
                }), 404

            client_id = target_client.client_id

            # Get all users from the client's sheet
            from ..services.google_services import get_sheets_service

            users_list = []
            try:
                sheets_service = get_sheets_service()
                with sheets_service.get_client_context() as sheets_client:
                    spreadsheet = sheets_client.open_by_key(target_client.sheet_id)

                    # Try to get the "Users" worksheet
                    try:
                        worksheet = spreadsheet.worksheet("Users")
                    except:
                        # If Users worksheet doesn't exist, use first worksheet
                        worksheet = spreadsheet.get_worksheet(0)

                    rows = worksheet.get_all_values()
                    headers = rows[0] if rows else []

                    # Format users for response
                    if len(rows) > 1:
                        # Skip header row
                        for row in rows[1:]:
                            if len(row) > 0:  # Skip empty rows
                                try:
                                    user_dict = {}
                                    for idx, header in enumerate(headers):
                                        if idx < len(row):
                                            user_dict[header] = row[idx]

                                    users_list.append({
                                        "email": user_dict.get('email', ''),
                                        "full_name": user_dict.get('full_name', ''),
                                        "phone_number": user_dict.get('PhoneNumber', ''),
                                        "role": user_dict.get('role', 'user'),
                                        "status": user_dict.get('status', 'inactive'),
                                        "created_at": user_dict.get('created_at', '')
                                    })
                                except Exception as e:
                                    logger.warning(f"Error parsing user row: {e}")
                                    continue
            except Exception as e:
                logger.error(f"Error reading users from sheet: {e}")
                return jsonify({
                    "status": "error",
                    "message": "فشل في قراءة البيانات"
                }), 500

            logger.info(f"Admin '{user_info.get('user', {}).get('email')}' listed {len(users_list)} users from client {client_id}")

            return jsonify({
                "status": "success",
                "count": len(users_list),
                "client_id": client_id,
                "users": users_list
            }), 200

        except Exception as e:
            logger.error(f"Admin list users failed: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/users', methods=['GET'])
@measure_performance
@require_auth
def list_users(user_info):
    """
    List all user emails from a client.
    Available to both admin and normal users - each user sees emails from their own client.

    Returns:
        List of user emails only from the user's client

    Authentication:
        Requires JWT token (both admin and normal users can access)
    """
    with ErrorContext("list_users_api"):
        try:
            user_service = get_user_management_service()

            # Get user's client info from their email in the token
            user_email = user_info.get('user', {}).get('email')
            target_client = user_service.get_client_by_email(user_email) if user_email else None

            if not target_client:
                logger.warning(f"List users failed - client not found for user {user_email}")
                return jsonify({
                    "status": "error",
                    "message": "لا يوجد عميل مطابق"
                }), 404

            client_id = target_client.client_id

            # Get all users from the client's sheet
            from ..services.google_services import get_sheets_service

            emails_list = []
            try:
                sheets_service = get_sheets_service()
                with sheets_service.get_client_context() as sheets_client:
                    spreadsheet = sheets_client.open_by_key(target_client.sheet_id)

                    # Try to get the "Users" worksheet
                    try:
                        worksheet = spreadsheet.worksheet("Users")
                    except:
                        # If Users worksheet doesn't exist, use first worksheet
                        worksheet = spreadsheet.get_worksheet(0)

                    rows = worksheet.get_all_values()

                    # Extract emails only
                    if len(rows) > 1:
                        # Skip header row
                        for row in rows[1:]:
                            if len(row) > 0:  # Skip empty rows
                                try:
                                    # Find email column (usually first column)
                                    email = row[0].strip() if row[0] else None
                                    if email:  # Only add non-empty emails
                                        emails_list.append(email)
                                except Exception as e:
                                    logger.warning(f"Error parsing email from row: {e}")
                                    continue
            except Exception as e:
                logger.error(f"Error reading users from sheet: {e}")
                return jsonify({
                    "status": "error",
                    "message": "فشل في قراءة البيانات"
                }), 500

            logger.info(f"User '{user_email}' listed {len(emails_list)} user emails from client {client_id}")

            return jsonify({
                "status": "success",
                "count": len(emails_list),
                "client_id": client_id,
                "emails": emails_list
            }), 200

        except Exception as e:
            logger.error(f"List users failed: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/admin/users/create', methods=['POST'])
@measure_performance
@require_admin
@require_auth
def admin_create_user(user_info):
    """
    Admin endpoint to create a new user.

    Request Body:
        email: str - User email address
        username: str - User's username
        phone_number: str - User's phone number (optional, can be empty)
        password: str - User's password
        role: str - User's role (e.g., 'admin', 'user')
        status: str - User's status (default: 'inactive')

    Returns:
        Created user information

    Authentication:
        Requires JWT token with 'admin' role
    """
    with ErrorContext("admin_create_user_api"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400

            # Get required fields
            email = data.get('email', '').strip()
            username = data.get('username', '').strip()
            phone_number = data.get('phone_number', '').strip()
            password = data.get('password', '').strip()
            role = data.get('role', 'user').strip()
            status = data.get('status', 'inactive').strip()

            # Validate required fields
            if not email:
                return jsonify({"error": "البريد الإلكتروني مطلوب"}), 400
            if not username:
                return jsonify({"error": "اسم المستخدم مطلوب"}), 400
            if not password:
                return jsonify({"error": "كلمة المرور مطلوبة"}), 400

            # Validate email format
            if '@' not in email:
                return jsonify({"error": "صيغة البريد الإلكتروني غير صحيحة"}), 400

            # Validate password strength
            if len(password) < 6:
                return jsonify({"error": "كلمة المرور يجب أن تكون 6 أحرف على الأقل"}), 400

            # Validate role
            if role.lower() not in ['admin', 'user']:
                return jsonify({"error": "الدور يجب أن يكون 'admin' أو 'user'"}), 400

            # Validate status
            if status.lower() not in ['active', 'inactive']:
                return jsonify({"error": "الحالة يجب أن تكون 'active' أو 'inactive'"}), 400

            # Get user service
            user_service = get_user_management_service()

            # Get admin's client info from their email in the token
            admin_email = user_info.get('user', {}).get('email')
            admin_client = user_service.get_client_by_email(admin_email) if admin_email else None

            if not admin_client:
                logger.warning(f"Admin create user failed - client not found for admin {admin_email}")
                return jsonify({
                    "status": "error",
                    "message": "لا يوجد عميل مطابق لهذا المسؤول"
                }), 404

            # Check if user already exists
            existing_user = user_service.get_user_details_from_client_sheet(admin_client.sheet_id, email)
            if existing_user:
                logger.warning(f"Admin create user failed - user already exists: {email}")
                return jsonify({
                    "status": "error",
                    "message": "المستخدم موجود بالفعل"
                }), 409

            # Create the user in the sheet
            from werkzeug.security import generate_password_hash
            from ..services.google_services import get_sheets_service
            from datetime import datetime

            hashed_password = generate_password_hash(password)

            # Add user to the sheet
            try:
                sheets_service = get_sheets_service()
                with sheets_service.get_client_context() as sheets_client:
                    spreadsheet = sheets_client.open_by_key(admin_client.sheet_id)

                    # Try to get the "Users" worksheet
                    try:
                        worksheet = spreadsheet.worksheet("Users")
                    except:
                        # If Users worksheet doesn't exist, use first worksheet
                        worksheet = spreadsheet.get_worksheet(0)

                    # Append the new user row
                    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
                    worksheet.append_row([
                        email,
                        username,  # full_name
                        phone_number,
                        role.lower(),
                        status.lower(),
                        timestamp,
                        hashed_password
                    ])
            except Exception as e:
                logger.error(f"Error adding user to sheet: {e}")
                return jsonify({
                    "status": "error",
                    "message": "فشل في إضافة المستخدم"
                }), 500

            # Log admin action
            admin_email = user_info.get('user', {}).get('email', 'unknown')
            logger.info(f"Admin '{admin_email}' created user: {email} with role: {role}")

            return jsonify({
                "status": "success",
                "message": "تم إنشاء المستخدم بنجاح",
                "email": email,
                "username": username,
                "phone_number": phone_number,
                "role": role.lower(),
                "status": status.lower(),
                "admin": admin_email
            }), 201

        except Exception as e:
            logger.error(f"Admin create user failed: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/admin/users/update', methods=['POST'])
@measure_performance
@require_admin
@require_auth
def admin_update_user(user_info):
    """
    Admin endpoint to update user information.

    Request Headers:
        X-User-Email: str - Email of user to update (in header)

    Request Body:
        username: str - Updated username (optional)
        phone_number: str - Updated phone number (optional)
        password: str - Updated password (optional)
        role: str - Updated role (optional)
        status: str - Updated status (optional)

    Returns:
        Updated user information

    Authentication:
        Requires JWT token with 'admin' role
    """
    with ErrorContext("admin_update_user_api"):
        try:
            # Get email from header
            target_email = request.headers.get('X-User-Email', '').strip()

            if not target_email:
                return jsonify({"error": "البريد الإلكتروني مطلوب في رأس الطلب X-User-Email"}), 400

            # Validate request data
            if not request.is_json:
                return jsonify({"error": "يجب أن يكون الطلب بصيغة JSON"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "لم يتم تقديم بيانات JSON"}), 400

            # Get optional update fields
            new_username = data.get('username', '').strip() if data.get('username') else None
            new_phone = data.get('phone_number', '').strip() if data.get('phone_number') else None
            new_password = data.get('password', '').strip() if data.get('password') else None
            new_role = data.get('role', '').strip().lower() if data.get('role') else None
            new_status = data.get('status', '').strip().lower() if data.get('status') else None

            # Validate password if provided
            if new_password and len(new_password) < 6:
                return jsonify({"error": "كلمة المرور يجب أن تكون 6 أحرف على الأقل"}), 400

            # Validate role if provided
            if new_role and new_role not in ['admin', 'user']:
                return jsonify({"error": "الدور يجب أن يكون 'admin' أو 'user'"}), 400

            # Validate status if provided
            if new_status and new_status not in ['active', 'inactive']:
                return jsonify({"error": "الحالة يجب أن تكون 'active' أو 'inactive'"}), 400

            # Get user service
            user_service = get_user_management_service()

            # Get admin's client info from their email in the token
            admin_email = user_info.get('user', {}).get('email')
            admin_client = user_service.get_client_by_email(admin_email) if admin_email else None

            if not admin_client:
                logger.warning(f"Admin update user failed - client not found for admin {admin_email}")
                return jsonify({
                    "status": "error",
                    "message": "لا يوجد عميل مطابق"
                }), 404

            # Get the target user
            target_user = user_service.get_user_details_from_client_sheet(admin_client.sheet_id, target_email)
            if not target_user:
                logger.warning(f"Admin update user failed - user not found: {target_email}")
                return jsonify({
                    "status": "error",
                    "message": "المستخدم غير موجود"
                }), 404

            # Update user in the sheet
            from ..services.google_services import get_sheets_service

            try:
                sheets_service = get_sheets_service()
                with sheets_service.get_client_context() as sheets_client:
                    spreadsheet = sheets_client.open_by_key(admin_client.sheet_id)

                    # Try to get the "Users" worksheet
                    try:
                        worksheet = spreadsheet.worksheet("Users")
                    except:
                        worksheet = spreadsheet.get_worksheet(0)

                    rows = worksheet.get_all_values()
                    headers = rows[0] if rows else []

                    # Find the target row
                    target_row = None
                    for idx, row in enumerate(rows[1:], start=2):  # Skip header row
                        if len(row) > 0 and row[0] == target_email:
                            target_row = idx
                            break

                    if not target_row:
                        logger.warning(f"Admin update user failed - could not find user row: {target_email}")
                        return jsonify({
                            "status": "error",
                            "message": "فشل تحديث المستخدم"
                        }), 500

                    # Update fields based on headers
                    updates = {}

                    if new_username:
                        try:
                            full_name_idx = headers.index('full_name')
                            worksheet.update_cell(target_row, full_name_idx + 1, new_username)
                            updates['username'] = new_username
                        except ValueError:
                            pass

                    if new_phone is not None:
                        try:
                            phone_idx = headers.index('PhoneNumber')
                            worksheet.update_cell(target_row, phone_idx + 1, new_phone)
                            updates['phone_number'] = new_phone
                        except ValueError:
                            pass

                    if new_role:
                        try:
                            role_idx = headers.index('role')
                            worksheet.update_cell(target_row, role_idx + 1, new_role)
                            updates['role'] = new_role
                        except ValueError:
                            pass

                    if new_status:
                        try:
                            status_idx = headers.index('status')
                            worksheet.update_cell(target_row, status_idx + 1, new_status)
                            updates['status'] = new_status
                        except ValueError:
                            pass

                    if new_password:
                        from werkzeug.security import generate_password_hash
                        hashed_password = generate_password_hash(new_password)
                        try:
                            password_idx = headers.index('password')
                            worksheet.update_cell(target_row, password_idx + 1, hashed_password)
                            updates['password'] = '***'
                        except ValueError:
                            pass

            except Exception as e:
                logger.error(f"Error updating user in sheet: {e}")
                return jsonify({
                    "status": "error",
                    "message": "خطأ في تحديث البيانات"
                }), 500

            # Log admin action
            admin_email = user_info.get('user', {}).get('email', 'unknown')
            logger.info(f"Admin '{admin_email}' updated user: {target_email} with updates: {updates}")

            return jsonify({
                "status": "success",
                "message": "تم تحديث المستخدم بنجاح",
                "email": target_email,
                "updates": updates,
                "admin": admin_email
            }), 200

        except Exception as e:
            logger.error(f"Admin update user failed: {e}")
            return jsonify(build_error_response(e)), 500


@user_bp.route('/admin/users/delete', methods=['DELETE'])
@measure_performance
@require_admin
@require_auth
def admin_delete_user(user_info):
    """
    Admin endpoint to delete a user.

    Request Headers:
        X-User-Email: str - Email of user to delete (in header)

    Returns:
        Deletion confirmation

    Authentication:
        Requires JWT token with 'admin' role
    """
    with ErrorContext("admin_delete_user_api"):
        try:
            # Get email from header
            target_email = request.headers.get('X-User-Email', '').strip()

            if not target_email:
                return jsonify({"error": "البريد الإلكتروني مطلوب في رأس الطلب X-User-Email"}), 400

            # Get user service
            user_service = get_user_management_service()

            # Get admin's client info from their email in the token
            admin_email = user_info.get('user', {}).get('email')
            admin_client = user_service.get_client_by_email(admin_email) if admin_email else None

            if not admin_client:
                logger.warning(f"Admin delete user failed - client not found for admin {admin_email}")
                return jsonify({
                    "status": "error",
                    "message": "لا يوجد عميل مطابق"
                }), 404

            # Get the target user
            target_user = user_service.get_user_details_from_client_sheet(admin_client.sheet_id, target_email)
            if not target_user:
                logger.warning(f"Admin delete user failed - user not found: {target_email}")
                return jsonify({
                    "status": "error",
                    "message": "المستخدم غير موجود"
                }), 404

            # Delete user from the sheet (delete the row)
            from ..services.google_services import get_sheets_service

            try:
                sheets_service = get_sheets_service()
                with sheets_service.get_client_context() as sheets_client:
                    spreadsheet = sheets_client.open_by_key(admin_client.sheet_id)

                    # Try to get the "Users" worksheet
                    try:
                        worksheet = spreadsheet.worksheet("Users")
                    except:
                        worksheet = spreadsheet.get_worksheet(0)

                    rows = worksheet.get_all_values()

                    # Find and delete the target row
                    for idx, row in enumerate(rows[1:], start=2):  # Skip header row
                        if len(row) > 0 and row[0] == target_email:
                            # Delete the row using delete_rows(index, number_of_rows)
                            # gspread uses 1-based indexing, so idx is already correct
                            worksheet.delete_rows(idx)  # Delete the row at idx
                            break
            except Exception as e:
                logger.error(f"Error deleting user from sheet: {e}")
                return jsonify({
                    "status": "error",
                    "message": "فشل في حذف المستخدم"
                }), 500

            # Log admin action
            admin_email = user_info.get('user', {}).get('email', 'unknown')
            logger.info(f"Admin '{admin_email}' deleted user: {target_email}")

            return jsonify({
                "status": "success",
                "message": "تم حذف المستخدم بنجاح",
                "email": target_email,
                "admin": admin_email
            }), 200

        except Exception as e:
            logger.error(f"Admin delete user failed: {e}")
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
