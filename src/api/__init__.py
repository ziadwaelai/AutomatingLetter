"""
API package initialization.
Exports route blueprints and provides a unified API registration function.
"""

from flask import request, jsonify
from .letter_routes import letter_bp
from .chat_routes import chat_bp
from .archive_routes import archive_bp

__all__ = ['letter_bp', 'chat_bp', 'archive_bp', 'register_api_routes']

def register_api_routes(app):
    """
    Register all API route blueprints with the Flask application.
    
    Args:
        app: Flask application instance
    """
    # Register blueprints
    app.register_blueprint(letter_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(archive_bp)
    
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
