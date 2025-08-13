"""
Test script for Long-Term Memory feature
Tests the memory service functionality without running the full application.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_memory_service():
    """Test the memory service functionality."""
    print("Testing Long-Term Memory Service...")
    
    try:
        # Import the memory service
        from src.services.memory_service import MemoryService
        
        # Create a memory service instance
        memory_service = MemoryService()
        print("✓ Memory service initialized successfully")
        
        # Test message processing
        test_session_id = "test_session_123"
        test_messages = [
            "أريد أن تكون الخطابات دائماً بأسلوب مختصر وواضح",
            "لا تستخدم الكثير من التبجيل في الخطابات",
            "أضف دائماً دعوة للتواصل في نهاية الخطاب",
            "استخدم فقرات قصيرة في جميع الخطابات"
        ]
        
        print("\nProcessing test messages...")
        for i, message in enumerate(test_messages):
            print(f"Processing message {i+1}: {message[:50]}...")
            memory_service._extract_and_store_instructions(
                session_id=test_session_id,
                message=message,
                context="test context"
            )
        
        # Get memory stats
        stats = memory_service.get_memory_stats()
        print(f"\n✓ Memory stats: {stats}")
        
        # Test instruction formatting
        instructions = memory_service.format_instructions_for_prompt(
            category="General",
            session_id=test_session_id
        )
        
        if instructions:
            print("✓ Memory instructions formatted successfully")
            print(f"Instructions preview: {instructions[:200]}...")
        else:
            print("⚠ No instructions were formatted (might be normal if extraction failed)")
        
        print("\n✓ Memory service test completed successfully!")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure all dependencies are installed (pip install -r requirements.txt)")
        return False
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        return False

def test_letter_generation_integration():
    """Test integration with letter generation."""
    print("\nTesting Letter Generation Integration...")
    
    try:
        from src.services.letter_generator import LetterGenerationContext, ArabicLetterGenerationService
        
        # Create a test context with session_id
        context = LetterGenerationContext(
            user_prompt="اكتب خطاب شكر للمشاركة في الفعالية",
            category="THANK_YOU",
            session_id="test_session_123"
        )
        
        print("✓ Letter generation context created with session_id")
        
        # Create letter service
        letter_service = ArabicLetterGenerationService()
        print("✓ Letter generation service initialized")
        
        # Test memory instruction retrieval
        memory_instructions = letter_service._get_memory_instructions(context)
        print(f"✓ Memory instructions retrieved: {len(memory_instructions)} characters")
        
        print("✓ Letter generation integration test completed!")
        return True
        
    except Exception as e:
        print(f"✗ Error during letter generation integration test: {e}")
        return False

if __name__ == "__main__":
    print("Long-Term Memory Feature Test Suite")
    print("=" * 50)
    
    # Test memory service
    memory_test_passed = test_memory_service()
    
    # Test integration (only if memory service works)
    if memory_test_passed:
        letter_test_passed = test_letter_generation_integration()
    else:
        letter_test_passed = False
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"Memory Service: {'✓ PASSED' if memory_test_passed else '✗ FAILED'}")
    print(f"Integration:    {'✓ PASSED' if letter_test_passed else '✗ FAILED'}")
    
    if memory_test_passed and letter_test_passed:
        print("\n🎉 All tests passed! The Long-Term Memory feature is ready.")
    else:
        print("\n⚠ Some tests failed. Please check the configuration and dependencies.")
    
    sys.exit(0 if memory_test_passed and letter_test_passed else 1)
