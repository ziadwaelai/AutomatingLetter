"""
API Routes for Chat-based Letter Editing
Handles session-based chat functionality with memory management.
"""

import logging
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from ..models import (
    ChatEditLetterRequest,
    ChatEditResponse,
    ErrorResponse,
    ChatSessionStatus
)
from ..services import get_chat_service, get_sheets_service
from ..utils import (
    ErrorContext,
    build_error_response,
    validate_and_raise,
    measure_performance
)

logger = logging.getLogger(__name__)

# Create blueprint
chat_bp = Blueprint('chat', __name__, url_prefix='/api/v1/chat')

@chat_bp.route('/sessions', methods=['POST'])
@measure_performance
def create_chat_session():
    """
    Create a new chat session for letter editing.
    
    Request Body (optional):
        initial_letter: str - Initial letter content
        context: str - Additional context for the session
        idempotency_key: str - Optional key to prevent duplicate creation
        
    Returns:
        Session ID and initial status
    """
    with ErrorContext("create_chat_session"):
        try:
            data = request.get_json() or {}
            
            # Check for idempotency key to prevent duplicate creation
            idempotency_key = data.get('idempotency_key') or request.headers.get('X-Idempotency-Key')
            
            chat_service = get_chat_service()
            
            # If idempotency key provided, check if session already exists for this key
            if idempotency_key:
                existing_session = chat_service.find_session_by_idempotency_key(idempotency_key)
                if existing_session:
                    logger.info(f"Returning existing session for idempotency key {idempotency_key}: {existing_session}")
                    return jsonify({
                        "status": "success",
                        "session_id": existing_session,
                        "message": "Chat session already exists (idempotent)",
                        "expires_in": chat_service.session_timeout
                    }), 200  # Return 200 instead of 201 for existing session
            
            session_id = chat_service.create_session(
                initial_letter=data.get('initial_letter'),
                context=data.get('context', ''),
                idempotency_key=idempotency_key
            )
            
            logger.info(f"Created chat session: {session_id}")
            
            return jsonify({
                "status": "success",
                "session_id": session_id,
                "message": "Chat session created successfully",
                "expires_in": chat_service.session_timeout
            }), 201
            
        except Exception as e:
            logger.error(f"Failed to create chat session: {e}")
            return jsonify(build_error_response(e)), 500

@chat_bp.route('/sessions/<session_id>/edit', methods=['POST'])
@measure_performance
def edit_letter_chat(session_id: str):
    """
    Edit letter through chat interface.
    
    Args:
        session_id: Chat session ID
        
    Request Body:
        ChatEditLetterRequest: Chat message and editing instructions
        
    Returns:
        ChatResponse: Updated letter and chat response
    """
    with ErrorContext("edit_letter_chat", {"session_id": session_id}):
        try:
            if not request.is_json:
                return jsonify({"error": "Request must be JSON"}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            # Validate request
            try:
                chat_request = ChatEditLetterRequest(**data)
            except ValidationError as e:
                logger.warning(f"Validation error in chat edit: {e}")
                return jsonify({
                    "error": "Invalid request data",
                    "details": e.errors()
                }), 400
            
            # Process chat message
            chat_service = get_chat_service()
            
            # Check if session exists and is active
            if not chat_service.session_exists(session_id):
                return jsonify({
                    "error": "Session not found",
                    "message": "Chat session does not exist or has expired"
                }), 404
            
            # Process the editing request
            chat_response = chat_service.process_edit_request(
                session_id=session_id,
                message=chat_request.message,
                current_letter=chat_request.current_letter,
                editing_instructions=chat_request.editing_instructions,
                preserve_formatting=chat_request.preserve_formatting
            )
            
            logger.info(f"Processed chat edit for session {session_id}")
            
            return jsonify(chat_response.model_dump()), 200
            
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return jsonify(build_error_response(e)), 400
        except Exception as e:
            logger.error(f"Chat edit failed for session {session_id}: {e}")
            return jsonify(build_error_response(e)), 500

@chat_bp.route('/sessions/<session_id>/history', methods=['GET'])
@measure_performance
def get_chat_history(session_id: str):
    """
    Get chat history for a session.
    
    Args:
        session_id: Chat session ID
        
    Query Parameters:
        limit: int - Number of messages to return (default: 50)
        offset: int - Offset for pagination (default: 0)
        
    Returns:
        Chat history with messages and letter versions
    """
    with ErrorContext("get_chat_history", {"session_id": session_id}):
        try:
            # Get query parameters
            limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
            offset = max(int(request.args.get('offset', 0)), 0)
            
            chat_service = get_chat_service()
            
            # Check if session exists
            if not chat_service.session_exists(session_id):
                return jsonify({
                    "error": "Session not found",
                    "message": "Chat session does not exist or has expired"
                }), 404
            
            # Get chat history
            history = chat_service.get_chat_history(
                session_id=session_id,
                limit=limit,
                offset=offset
            )
            
            return jsonify({
                "status": "success",
                "session_id": session_id,
                "history": history,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": len(history)
                }
            }), 200
            
        except ValueError as e:
            return jsonify({
                "error": "Invalid parameters",
                "message": str(e)
            }), 400
        except Exception as e:
            logger.error(f"Failed to get chat history for session {session_id}: {e}")
            return jsonify(build_error_response(e)), 500

@chat_bp.route('/sessions/<session_id>/status', methods=['GET'])
def get_session_status(session_id: str):
    """
    Get status of a chat session.
    
    Args:
        session_id: Chat session ID
        
    Returns:
        Session status and metadata
    """
    try:
        chat_service = get_chat_service()
        
        # Atomic check - get session info directly, handle not found/expired in exception
        session_info = chat_service.get_session_info(session_id)
        
        return jsonify({
            "status": "success",
            "session_info": session_info
        }), 200
        
    except ValueError as e:
        # Session not found or expired
        return jsonify({
            "status": "not_found",
            "session_id": session_id,
            "message": str(e)
        }), 404
        
    except Exception as e:
        logger.error(f"Failed to get session status for {session_id}: {e}")
        return jsonify(build_error_response(e)), 500

@chat_bp.route('/sessions/<session_id>', methods=['DELETE'])
@measure_performance
def delete_chat_session(session_id: str):
    """
    Delete a chat session and clear its data.
    
    Args:
        session_id: Chat session ID
        
    Returns:
        Deletion confirmation
    """
    with ErrorContext("delete_chat_session", {"session_id": session_id}):
        try:
            chat_service = get_chat_service()
            
            if not chat_service.session_exists(session_id):
                return jsonify({
                    "error": "Session not found",
                    "message": "Chat session does not exist"
                }), 404
            
            # Delete session
            chat_service.delete_session(session_id)
            
            logger.info(f"Deleted chat session: {session_id}")
            
            return jsonify({
                "status": "success",
                "message": "Session deleted successfully",
                "session_id": session_id
            }), 200
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return jsonify(build_error_response(e)), 500

@chat_bp.route('/sessions', methods=['GET'])
def list_active_sessions():
    """
    List all active chat sessions.
    
    Query Parameters:
        include_expired: bool - Include expired sessions (default: false)
        
    Returns:
        List of active sessions
    """
    try:
        include_expired = request.args.get('include_expired', 'false').lower() == 'true'
        
        chat_service = get_chat_service()
        sessions = chat_service.list_sessions(include_expired=include_expired)
        
        return jsonify({
            "status": "success",
            "sessions": sessions,
            "total": len(sessions),
            "include_expired": include_expired
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return jsonify(build_error_response(e)), 500

@chat_bp.route('/sessions/<session_id>/extend', methods=['POST'])
def extend_session(session_id: str):
    """
    Extend a chat session's expiration time.
    
    Args:
        session_id: Chat session ID
        
    Request Body (optional):
        extend_minutes: int - Minutes to extend (default: session timeout)
        
    Returns:
        New expiration time
    """
    try:
        data = request.get_json() or {}
        extend_minutes = data.get('extend_minutes')
        
        chat_service = get_chat_service()
        
        if not chat_service.session_exists(session_id):
            return jsonify({
                "error": "Session not found",
                "message": "Chat session does not exist"
            }), 404
        
        new_expiration = chat_service.extend_session(session_id, extend_minutes)
        
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "new_expiration": new_expiration.isoformat(),
            "message": "Session extended successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to extend session {session_id}: {e}")
        return jsonify(build_error_response(e)), 500

@chat_bp.route('/cleanup', methods=['POST'])
def manual_cleanup():
    """
    Manually trigger cleanup of expired sessions.
    
    Returns:
        Cleanup results
    """
    try:
        chat_service = get_chat_service()
        cleanup_results = chat_service.cleanup_expired_sessions()
        
        return jsonify({
            "status": "success",
            "cleanup_results": cleanup_results
        }), 200
        
    except Exception as e:
        logger.error(f"Manual cleanup failed: {e}")
        return jsonify(build_error_response(e)), 500

@chat_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for chat service.
    
    Returns:
        Service health status
    """
    try:
        chat_service = get_chat_service()
        service_stats = chat_service.get_service_stats()
        
        return jsonify({
            "status": "healthy",
            "service": "chat_editing",
            "stats": service_stats
        }), 200
        
    except Exception as e:
        logger.error(f"Chat health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

# Error handlers for the blueprint
@chat_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle Pydantic validation errors."""
    return jsonify({
        "error": "Validation failed",
        "details": error.errors()
    }), 400

@chat_bp.route('/memory/stats', methods=['GET'])
@measure_performance
def get_memory_stats():
    """
    Get memory service statistics.
    
    Returns:
        Memory statistics including instruction counts and types
    """
    with ErrorContext("get_memory_stats"):
        try:
            from ..services import get_memory_service
            memory_service = get_memory_service()
            stats = memory_service.get_memory_stats()
            
            return jsonify({
                "status": "success",
                "data": stats
            }), 200
            
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return build_error_response(
                error="Failed to retrieve memory statistics",
                details={"error_message": str(e)},
                status_code=500
            )

@chat_bp.route('/memory/instructions', methods=['GET'])
@measure_performance  
def get_memory_instructions():
    """
    Get formatted memory instructions for a category/session.
    
    Query Parameters:
        category: str - Letter category (optional)
        session_id: str - Session ID (optional)
        
    Returns:
        Formatted memory instructions
    """
    with ErrorContext("get_memory_instructions"):
        try:
            category = request.args.get('category')
            session_id = request.args.get('session_id')
            
            from ..services import get_memory_service
            memory_service = get_memory_service()
            instructions_text = memory_service.format_instructions_for_prompt(
                category=category,
                session_id=session_id
            )
            
            return jsonify({
                "status": "success",
                "data": {
                    "instructions": instructions_text,
                    "category": category,
                    "session_id": session_id
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Failed to get memory instructions: {e}")
            return build_error_response(
                error="Failed to retrieve memory instructions",
                details={"error_message": str(e)},
                status_code=500
            )

# Error handlers
@chat_bp.errorhandler(404)
def handle_not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested chat endpoint does not exist"
    }), 404

@chat_bp.errorhandler(500)
def handle_internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error in chat API: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred in chat service"
    }), 500
