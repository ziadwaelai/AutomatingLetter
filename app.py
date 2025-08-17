"""
Refactored Flask Application
Modern, scalable backend with proper service architecture.
"""

import logging
import os
import sys
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import get_config, setup_logging
from src.api import register_api_routes
from src.services import get_chat_service, get_letter_service, get_enhanced_pdf_service, get_sheets_service
from src.utils import build_error_response

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

def create_app() -> Flask:
    """
    Create and configure Flask application.
    
    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    
    # Load configuration
    config = get_config()
    
    # Configure Flask
    app.config['DEBUG'] = config.debug_mode
    app.config['SECRET_KEY'] = config.flask_secret_key
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Enable CORS
    CORS(app, origins=config.cors_origins)
    
    # Register API routes
    register_api_routes(app)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Application health check."""
        try:
            # Test services
            services_status = {
                'letter_service': 'healthy',
                'chat_service': 'healthy',
                'pdf_service': 'healthy',
                'sheets_service': 'healthy'
            }
            
            # Quick service checks
            try:
                get_letter_service().get_service_stats()
            except Exception as e:
                services_status['letter_service'] = f'unhealthy: {str(e)}'
            
            try:
                get_chat_service().get_service_stats()
            except Exception as e:
                services_status['chat_service'] = f'unhealthy: {str(e)}'
            
            try:
                get_enhanced_pdf_service().get_service_stats()
            except Exception as e:
                services_status['pdf_service'] = f'unhealthy: {str(e)}'
            
            try:
                get_sheets_service().get_connection_status()
            except Exception as e:
                services_status['sheets_service'] = f'unhealthy: {str(e)}'
            
            overall_status = 'healthy' if all(
                status == 'healthy' for status in services_status.values()
            ) else 'degraded'
            
            return jsonify({
                'status': overall_status,
                'timestamp': datetime.now().isoformat(),
                'services': services_status,
                'version': '2.0.0'
            }), 200 if overall_status == 'healthy' else 503
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 503
    
    # Root endpoint
    @app.route('/')
    def root():
        """Root endpoint with API information."""
        return jsonify({
            'service': 'Automating Letter Creation API',
            'version': '2.0.0',
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'endpoints': {
                'health': '/health',
                'letter_generation': '/api/v1/letter',
                'chat_editing': '/api/v1/chat',
                'pdf_generation': '/api/v1/pdf',
                'archive': '/api/v1/archive'
            },
            'documentation': {
                'swagger': '/api/docs',
                'postman': 'See README.md for Postman collection'
            }
        })
    
    # Global error handlers
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 errors."""
        return jsonify({
            'error': 'Bad Request',
            'message': 'The request could not be understood by the server'
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 errors."""
        return jsonify({
            'error': 'Method Not Allowed',
            'message': 'The method is not allowed for the requested URL'
        }), 405
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Handle 413 errors."""
        return jsonify({
            'error': 'Request Entity Too Large',
            'message': 'The uploaded file is too large'
        }), 413
    
    @app.errorhandler(429)
    def too_many_requests(error):
        """Handle 429 errors."""
        return jsonify({
            'error': 'Too Many Requests',
            'message': 'Rate limit exceeded'
        }), 429
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
    
    # Request logging middleware
    @app.before_request
    def log_request_info():
        """Log request information."""
        if config.log_requests and request.endpoint != 'health':
            logger.info(f"{request.method} {request.url} - {request.remote_addr}")
    
    @app.after_request
    def log_response_info(response):
        """Log response information."""
        if config.log_requests and request.endpoint != 'health':
            logger.info(f"Response: {response.status_code} - {request.endpoint}")
        return response
    
    return app

# Backward compatibility: Legacy endpoints
def create_legacy_app() -> Flask:
    """
    Create Flask app with legacy endpoint compatibility.
    This allows gradual migration from old endpoints.
    """
    app = create_app()
    
    # Legacy letter generation endpoint
    @app.route('/generate_letter', methods=['POST'])
    def legacy_generate_letter():
        """Legacy letter generation endpoint."""
        logger.warning("Legacy endpoint /generate_letter used - please migrate to /api/v1/letter/generate")
        
        # Redirect to new endpoint
        from flask import redirect, url_for
        return redirect(url_for('letter.generate_letter'), code=307)
    
    # Legacy chat endpoint  
    @app.route('/edit_letter', methods=['POST'])
    def legacy_edit_letter():
        """Legacy letter editing endpoint."""
        logger.warning("Legacy endpoint /edit_letter used - please migrate to /api/v1/chat/sessions/{id}/edit")
        
        # For legacy support, create a temporary session
        try:
            data = request.get_json()
            chat_service = get_chat_service()
            session_id = chat_service.create_session()
            
            # Process edit request
            response = chat_service.process_edit_request(
                session_id=session_id,
                message=data.get('message', ''),
                current_letter=data.get('current_letter', ''),
                editing_instructions=data.get('editing_instructions')
            )
            
            # Return in legacy format
            return jsonify({
                'status': 'success',
                'updated_letter': response.updated_letter,
                'response': response.response_text,
                'session_id': session_id
            })
            
        except Exception as e:
            logger.error(f"Legacy edit endpoint error: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    # Legacy archive endpoint
    @app.route('/archive-letter', methods=['POST'])
    def legacy_archive_letter():
        """Legacy letter archiving endpoint."""
        logger.warning("Legacy endpoint /archive-letter used - please migrate to /api/v1/archive/letter")
        
        # Redirect to new endpoint
        from flask import redirect, url_for
        return redirect(url_for('archive.archive_letter'), code=307)
    
    return app

def run_development_server(app=None):
    """Run development server with auto-reload."""
    config = get_config()
    
    if app is None:
        if config.legacy_endpoints:
            app = create_legacy_app()
            logger.info("Running with legacy endpoint compatibility")
        else:
            app = create_app()
    
    logger.info(f"Starting development server on {config.host}:{config.port}")
    
    try:
        app.run(
            host=config.host,
            port=config.port,
            debug=config.debug_mode,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

def run_production_server():
    """Run production server with gunicorn."""
    config = get_config()
    
    logger.info("Creating production application")
    
    if config.legacy_endpoints:
        return create_legacy_app()
    else:
        return create_app()

# For gunicorn
app = None

def get_app():
    """Get Flask application instance for gunicorn."""
    global app
    if app is None:
        app = run_production_server()
    return app

if __name__ == '__main__':
    # Determine if we're in development or production
    if os.getenv('FLASK_ENV') == 'production':
        app = run_production_server()
    else:
        app = create_app()
        run_development_server(app)
