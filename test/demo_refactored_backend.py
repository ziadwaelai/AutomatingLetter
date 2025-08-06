"""
Quick Demo Script for Refactored Backend
Demonstrates the new architecture components working together.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def demo_config():
    """Demo the configuration system."""
    print("🔧 Configuration System Demo")
    print("-" * 40)
    
    from src.config import get_config
    config = get_config()
    
    print(f"✅ Debug Mode: {config.debug_mode}")
    print(f"✅ Host: {config.host}:{config.port}")
    print(f"✅ Chat Timeout: {config.chat_session_timeout_minutes} minutes")
    print(f"✅ Features: Chat={config.enable_chat}, PDF={config.enable_pdf_generation}")
    print()

def demo_models():
    """Demo the Pydantic models."""
    print("📊 Data Models Demo")
    print("-" * 40)
    
    from src.models import GenerateLetterRequest, LetterOutput, ChatEditLetterRequest
    
    # Demo letter request
    request = GenerateLetterRequest(
        category="General",
        recipient="أحمد محمد",
        prompt="أكتب خطاب شكر وتقدير",
        is_first=True,
        member_name="سعد العتيبي"
    )
    print(f"✅ Letter Request: {request.category} -> {request.recipient}")
    
    # Demo letter output
    output = LetterOutput(
        ID="LET-20241212-12345",
        Title="خطاب شكر وتقدير",
        Letter="بسم الله الرحمن الرحيم...",
        Date="2024-12-12"
    )
    print(f"✅ Letter Output: {output.ID} - {output.Title}")
    
    # Demo chat request
    chat_req = ChatEditLetterRequest(
        message="أضف فقرة في النهاية",
        current_letter="النص الحالي",
        editing_instructions="حافظ على الطابع الرسمي"
    )
    print(f"✅ Chat Request: {chat_req.message[:20]}...")
    print()

def demo_utils():
    """Demo utility functions."""
    print("🔧 Utilities Demo")
    print("-" * 40)
    
    from src.utils import generate_letter_id, Timer, ErrorContext
    
    # Demo ID generation
    letter_id = generate_letter_id()
    print(f"✅ Generated ID: {letter_id}")
    
    # Demo Timer
    timer = Timer("Demo Operation")
    timer.start_time = timer.start_time or __import__('time').time()
    elapsed = timer.elapsed()
    print(f"✅ Timer works: {elapsed:.3f}s elapsed")
    
    # Demo ErrorContext
    try:
        with ErrorContext("demo_operation", {"test": "value"}):
            print("✅ ErrorContext: No errors occurred")
    except Exception as e:
        print(f"❌ ErrorContext error: {e}")
    
    print()

def demo_flask_app():
    """Demo Flask application."""
    print("🌐 Flask Application Demo")
    print("-" * 40)
    
    try:
        from app import create_app
        app = create_app()
        
        print(f"✅ Flask app created: {app.name}")
        
        # Show available routes
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        api_routes = [r for r in routes if r.startswith('/api/')]
        
        print(f"✅ Total routes: {len(routes)}")
        print(f"✅ API routes: {len(api_routes)}")
        
        # Show key API endpoints
        key_endpoints = [
            '/api/v1/letter/generate',
            '/api/v1/chat/sessions',
            '/api/v1/pdf/generate'
        ]
        
        for endpoint in key_endpoints:
            if endpoint in routes:
                print(f"✅ Endpoint available: {endpoint}")
            else:
                print(f"❌ Endpoint missing: {endpoint}")
        
        print()
        
    except Exception as e:
        print(f"❌ Flask app error: {e}")
        print()

def demo_services():
    """Demo service architecture (without external dependencies)."""
    print("⚙️ Services Architecture Demo")
    print("-" * 40)
    
    try:
        # Test service imports (may fail without API keys)
        from src.services import (
            get_letter_service,
            get_chat_service,
            get_pdf_service,
            get_sheets_service
        )
        print("✅ All service imports successful")
        
        # Test service statistics (should work without external deps)
        try:
            chat_service = get_chat_service()
            stats = chat_service.get_service_stats()
            print(f"✅ Chat service stats: {stats['total_sessions_created']} sessions created")
        except Exception as e:
            print(f"⚠️  Chat service demo: {e}")
        
        try:
            pdf_service = get_pdf_service()
            templates = pdf_service.get_available_templates()
            print(f"✅ PDF service: {len(templates)} templates available")
        except Exception as e:
            print(f"⚠️  PDF service demo: {e}")
        
    except Exception as e:
        print(f"⚠️  Services demo error (expected without API keys): {e}")
    
    print()

def main():
    """Run the complete demo."""
    print("🎉 AutomatingLetter - Refactored Backend Demo")
    print("=" * 60)
    print()
    
    # Run all demos
    demo_config()
    demo_models()
    demo_utils()
    demo_flask_app()
    demo_services()
    
    print("🎯 Demo Complete!")
    print("=" * 60)
    print()
    print("🚀 To start the development server:")
    print("   python new_app.py")
    print()
    print("🔗 Key endpoints to test:")
    print("   GET  http://localhost:5000/health")
    print("   POST http://localhost:5000/api/v1/letter/generate")
    print("   POST http://localhost:5000/api/v1/chat/sessions")
    print()
    print("📖 See REFACTORED_BACKEND_GUIDE.md for complete documentation")

if __name__ == '__main__':
    main()
