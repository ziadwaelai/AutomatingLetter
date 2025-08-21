"""
New Session API Routes
Clean implementation using separate session management services.
"""

import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from ..services import get_session_manager
from ..utils import (
    ErrorContext,
    build_error_response,
    measure_performance
)

logger = logging.getLogger(__name__)

# Create blueprint for new session API
session_bp = Blueprint('sessions', __name__, url_prefix='/api/v1/sessions')

@session_bp.route('', methods=['POST'])
@measure_performance
def create_session():
    """
    Create a new session.
    
    Request Body (optional):
        initial_letter: str - Initial letter content
        context: str - Additional context for the session
        idempotency_key: str - Optional key to prevent duplicate creation
        
    Returns:
        Session ID and initial status
    """
    with ErrorContext("create_session"):
        try:
            data = request.get_json() or {}
            
            # Get idempotency key from body or headers
            idempotency_key = data.get('idempotency_key') or request.headers.get('X-Idempotency-Key')
            
            session_manager = get_session_manager()
            
            # Create session using the new session manager
            session_id = session_manager.create_session(
                initial_letter=data.get('initial_letter'),
                context=data.get('context', ''),
                idempotency_key=idempotency_key
            )
            
            logger.info(f"Created session: {session_id}")
            
            return jsonify({
                "status": "success",
                "session_id": session_id,
                "message": "Session created successfully",
                "expires_in": session_manager.session_timeout_minutes
            }), 201
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return jsonify(build_error_response(e)), 500

@session_bp.route('', methods=['GET'])
@measure_performance
def list_sessions():
    """
    List all active sessions.
    
    Query Parameters:
        include_expired: bool - Include expired sessions (default: false)
        
    Returns:
        List of active sessions
    """
    with ErrorContext("list_sessions"):
        try:
            include_expired = request.args.get('include_expired', 'false').lower() == 'true'
            
            session_manager = get_session_manager()
            sessions = session_manager.list_sessions(include_expired=include_expired)
            
            logger.debug(f"Listed {len(sessions)} sessions (include_expired={include_expired})")
            
            return jsonify({
                "status": "success",
                "sessions": sessions,
                "total": len(sessions),
                "include_expired": include_expired
            }), 200
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return jsonify(build_error_response(e)), 500

@session_bp.route('/<session_id>', methods=['GET'])
@measure_performance
def get_session_info(session_id: str):
    """
    Get session information.
    
    Args:
        session_id: Session ID
        
    Returns:
        Session information
    """
    with ErrorContext("get_session_info", {"session_id": session_id}):
        try:
            session_manager = get_session_manager()
            
            if not session_manager.session_exists(session_id):
                return jsonify({
                    "error": "Session not found",
                    "message": "Session does not exist or has expired"
                }), 404
            
            session_info = session_manager.get_session_info(session_id)
            
            return jsonify({
                "status": "success",
                "session_info": session_info
            }), 200
            
        except ValueError as e:
            return jsonify({
                "status": "not_found",
                "session_id": session_id,
                "message": str(e)
            }), 404
            
        except Exception as e:
            logger.error(f"Failed to get session info for {session_id}: {e}")
            return jsonify(build_error_response(e)), 500

@session_bp.route('/<session_id>', methods=['DELETE'])
@measure_performance
def delete_session(session_id: str):
    """
    Delete a session.
    
    Args:
        session_id: Session ID
        
    Returns:
        Deletion confirmation
    """
    with ErrorContext("delete_session", {"session_id": session_id}):
        try:
            session_manager = get_session_manager()
            
            if not session_manager.session_exists(session_id):
                return jsonify({
                    "error": "Session not found",
                    "message": "Session does not exist"
                }), 404
            
            # Delete session
            success = session_manager.delete_session(session_id)
            
            if success:
                logger.info(f"Deleted session: {session_id}")
                return jsonify({
                    "status": "success",
                    "message": "Session deleted successfully",
                    "session_id": session_id
                }), 200
            else:
                return jsonify({
                    "error": "Delete failed",
                    "message": "Failed to delete session"
                }), 500
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return jsonify(build_error_response(e)), 500

@session_bp.route('/<session_id>/extend', methods=['POST'])
@measure_performance
def extend_session(session_id: str):
    """
    Extend a session's expiration time.
    
    Args:
        session_id: Session ID
        
    Request Body (optional):
        extend_minutes: int - Minutes to extend (default: session timeout)
        
    Returns:
        New expiration time
    """
    with ErrorContext("extend_session", {"session_id": session_id}):
        try:
            data = request.get_json() or {}
            extend_minutes = data.get('extend_minutes')
            
            session_manager = get_session_manager()
            
            if not session_manager.session_exists(session_id):
                return jsonify({
                    "error": "Session not found",
                    "message": "Session does not exist"
                }), 404
            
            new_expiration = session_manager.extend_session(session_id, extend_minutes)
            
            return jsonify({
                "status": "success",
                "session_id": session_id,
                "new_expiration": new_expiration.isoformat(),
                "message": "Session extended successfully"
            }), 200
            
        except Exception as e:
            logger.error(f"Failed to extend session {session_id}: {e}")
            return jsonify(build_error_response(e)), 500

@session_bp.route('/cleanup', methods=['POST'])
@measure_performance
def manual_cleanup():
    """
    Manually trigger cleanup of expired sessions.
    
    Returns:
        Cleanup results
    """
    with ErrorContext("manual_cleanup"):
        try:
            session_manager = get_session_manager()
            cleanup_results = session_manager.manual_cleanup()
            
            return jsonify({
                "status": "success",
                "cleanup_results": cleanup_results
            }), 200
            
        except Exception as e:
            logger.error(f"Manual cleanup failed: {e}")
            return jsonify(build_error_response(e)), 500

@session_bp.route('/health', methods=['GET'])
@measure_performance
def health_check():
    """
    Health check endpoint for session service.
    
    Returns:
        Service health status
    """
    with ErrorContext("session_health_check"):
        try:
            session_manager = get_session_manager()
            service_stats = session_manager.get_service_stats()
            
            return jsonify({
                "status": "healthy",
                "service": "session_management",
                "stats": service_stats
            }), 200
            
        except Exception as e:
            logger.error(f"Session health check failed: {e}")
            return jsonify({
                "status": "unhealthy",
                "service": "session_management",
                "error": str(e)
            }), 503

# Error handlers for the blueprint
@session_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle Pydantic validation errors."""
    return jsonify({
        "error": "Validation failed",
        "details": error.errors()
    }), 400

@session_bp.errorhandler(404)
def handle_not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Not found",
        "message": "The requested resource was not found"
    }), 404

@session_bp.errorhandler(500)
def handle_internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500
