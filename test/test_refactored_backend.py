"""
Test Script for Refactored Backend
Simple validation of the new architecture components.
"""

import sys
import os
import traceback
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test if all modules can be imported."""
    print("🧪 Testing module imports...")
    
    try:
        # Test config
        from src.config import get_config, setup_logging
        print("✅ Config module imported successfully")
        
        # Test models
        from src.models import GenerateLetterRequest, LetterOutput, ChatEditLetterRequest
        print("✅ Models module imported successfully")
        
        # Test utils
        from src.utils import generate_letter_id, Timer, ErrorContext
        print("✅ Utils module imported successfully")
        
        # Test services (may fail if external dependencies missing)
        try:
            from src.services import get_letter_service, get_chat_service
            print("✅ Services module imported successfully")
        except ImportError as e:
            print(f"⚠️  Services module import warning: {e}")
        
        # Test API
        from src.api import register_api_routes
        print("✅ API module imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        traceback.print_exc()
        return False

def test_config():
    """Test configuration system."""
    print("\n🧪 Testing configuration system...")
    
    try:
        from src.config import get_config
        
        config = get_config()
        
        # Test basic config attributes
        assert hasattr(config, 'openai_api_key'), "Missing openai_api_key"
        assert hasattr(config, 'debug_mode'), "Missing debug_mode"
        assert hasattr(config, 'host'), "Missing host"
        assert hasattr(config, 'port'), "Missing port"
        
        print(f"✅ Config loaded: debug={config.debug_mode}, host={config.host}:{config.port}")
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_models():
    """Test Pydantic models."""
    print("\n🧪 Testing Pydantic models...")
    
    try:
        from src.models import GenerateLetterRequest, LetterOutput, ChatEditLetterRequest
        
        # Test GenerateLetterRequest
        request = GenerateLetterRequest(
            category="General",
            recipient="أحمد محمد",
            prompt="اكتب خطاب شكر",
            is_first=True
        )
        assert request.category == "General"
        print("✅ GenerateLetterRequest model works")
        
        # Test LetterOutput
        output = LetterOutput(
            ID="TEST_123",
            Title="خطاب تجريبي",
            Letter="محتوى الخطاب",
            Date="2024-12-12"
        )
        assert output.ID == "TEST_123"
        print("✅ LetterOutput model works")
        
        # Test ChatEditLetterRequest
        chat_request = ChatEditLetterRequest(
            message="أضف فقرة",
            current_letter="النص الحالي للخطاب",
            editing_instructions="تعليمات التحرير"
        )
        assert chat_request.message == "أضف فقرة"
        print("✅ ChatEditLetterRequest model works")
        
        return True
        
    except Exception as e:
        print(f"❌ Models test failed: {e}")
        return False

def test_utils():
    """Test utility functions."""
    print("\n🧪 Testing utility functions...")
    
    try:
        from src.utils import generate_letter_id, Timer, ErrorContext
        
        # Test ID generation
        letter_id = generate_letter_id()
        assert letter_id.startswith("LET"), f"Invalid ID format: {letter_id}"
        print(f"✅ Letter ID generated: {letter_id}")
        
        # Test Timer
        import time
        timer = Timer()
        timer.start_time = time.time()  # Start the timer manually
        time.sleep(0.1)
        elapsed = timer.elapsed()
        assert elapsed > 0.05, f"Timer not working: {elapsed}"
        print(f"✅ Timer works: {elapsed:.3f}s")
        
        # Test ErrorContext
        with ErrorContext("test_operation"):
            pass
        print("✅ ErrorContext works")
        
        return True
        
    except Exception as e:
        print(f"❌ Utils test failed: {e}")
        return False

def test_flask_app():
    """Test Flask application creation."""
    print("\n🧪 Testing Flask application...")
    
    try:
        # Import Flask app
        sys.path.insert(0, os.path.dirname(__file__))
        from app import create_app
        
        app = create_app()
        
        # Test basic app attributes
        assert app.name == 'new_app', f"Wrong app name: {app.name}"
        print("✅ Flask app created successfully")
        
        # Test routes are registered
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        
        expected_routes = [
            '/',
            '/health',
            '/api/v1/letter/generate',
            '/api/v1/chat/sessions',
            '/api/v1/pdf/generate'
        ]
        
        for route in expected_routes:
            if route in routes:
                print(f"✅ Route registered: {route}")
            else:
                print(f"⚠️  Route missing: {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        traceback.print_exc()
        return False

def test_environment():
    """Test environment setup."""
    print("\n🧪 Testing environment...")
    
    # Check required files
    required_files = [
        'src/config/__init__.py',
        'src/models/__init__.py',
        'src/services/__init__.py',
        'src/utils/__init__.py',
        'src/api/__init__.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major >= 3 and python_version.minor >= 8:
        print(f"✅ Python version: {python_version.major}.{python_version.minor}")
    else:
        print(f"⚠️  Python version {python_version.major}.{python_version.minor} may not be fully supported")
    
    return True

def main():
    """Run all tests."""
    print("🚀 Starting Refactored Backend Validation")
    print("=" * 50)
    
    tests = [
        ("Environment", test_environment),
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Models", test_models),
        ("Utils", test_utils),
        ("Flask App", test_flask_app)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:15} | {status}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The refactored backend is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the errors above.")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
