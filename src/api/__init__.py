"""
API package initialization.
Exports route blueprints and provides a unified API registration function.
"""

from flask import request, jsonify
from .letter_routes import letter_bp
from .chat_routes import chat_bp
from .archive_routes import archive_bp
from .whatsapp_routes import whatsapp_bp
from .user_routes import user_bp
from .submissions_routes import submissions_bp

__all__ = ['letter_bp', 'chat_bp', 'archive_bp', 'whatsapp_bp', 'user_bp', 'submissions_bp', 'register_api_routes']

def register_api_routes(app):
    """
    Register all API route blueprints with the Flask application.

    Args:
        app: Flask application instance
    """
    # Register blueprints
    app.register_blueprint(letter_bp)
    app.register_blueprint(chat_bp)  # Updated to use new session manager
    app.register_blueprint(archive_bp)
    app.register_blueprint(whatsapp_bp)  # WhatsApp integration routes
    app.register_blueprint(user_bp)  # User management routes
    app.register_blueprint(submissions_bp)  # Submissions data retrieval routes
    
    # Add global API error handlers
    @app.errorhandler(404)
    def api_not_found(error):
        if '/api/' in request.url:
            return jsonify({
                "error": "API endpoint not found",
                "message": "The requested API endpoint does not exist",
                "url": request.url
            }), 404
        # Let other 404s be handled normally
        return error
    
    @app.errorhandler(500)
    def api_internal_error(error):
        if '/api/' in request.url:
            return jsonify({
                "error": "Internal server error",
                "message": "An unexpected error occurred"
            }), 500
        # Let other 500s be handled normally
        return error
