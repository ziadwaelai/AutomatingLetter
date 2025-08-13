"""
Test script for Simplified Long-Term Memory feature
Tests the new simplified memory service functionality.
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

def test_simplified_memory_service():
    """Test the simplified memory service functionality."""
    print("Testing Simplified Long-Term Memory Service...")
    
    try:
        # Import the simplified memory service
        from src.services.memory_service import SimplifiedMemoryService
        
        # Create a memory service instance
        memory_service = SimplifiedMemoryService()
        print("✓ Simplified memory service initialized successfully")
        
        # Test message processing with Arabic instructions
        test_messages = [
            "أريد أن تكون جميع خطاباتي مختصرة وواضحة",
            "استخدم فقرات قصيرة في كل الخطابات",
            "أضف دائماً دعوة للتواصل في نهاية الخطاب",
            "اكتب بأسلوب رسمي ومهذب"
        ]
        
        print("\nProcessing test messages...")
        for i, message in enumerate(test_messages):
            print(f"Processing message {i+1}: {message}")
            memory_service._extract_and_store_instructions(message)
        
        # Wait a moment for processing
        import time
        time.sleep(2)
        
        # Get memory stats
        stats = memory_service.get_memory_stats()
        print(f"\n✓ Memory stats: {stats}")
        
        # Test instruction formatting
        instructions = memory_service.format_instructions_for_prompt()
        
        if instructions:
            print("✓ Memory instructions formatted successfully")
            print(f"Instructions:\n{instructions}")
        else:
            print("⚠ No instructions were formatted")
        
        print("\n✓ Simplified memory service test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration_with_chat():
    """Test integration with chat service."""
    print("\nTesting Chat Integration...")
    
    try:
        from src.services.chat_service import ChatService
        from src.services.memory_service import get_memory_service
        
        # Create services
        chat_service = ChatService()
        memory_service = get_memory_service()
        
        print("✓ Services initialized successfully")
        
        # Create a chat session
        session_id = chat_service.create_session(
            initial_letter="",
            context="Testing simplified memory integration"
        )
        print(f"✓ Chat session created: {session_id}")
        
        # Test letter with instructions
        test_letter = """بسم الله الرحمن الرحيم

إلى الأستاذ أحمد محمد
المحترم

السلام عليكم ورحمة الله وبركاته

نشكرك على مشاركتك في الفعالية.

وتفضل بقبول فائق الاحترام والتقدير.

مع التحية
إدارة نت زيرو"""
        
        # Test edit request with clear instruction
        edit_request = "اجعل الخطاب أقصر. أريد أن تكون جميع خطاباتي المستقبلية مختصرة ومفيدة"
        
        print(f"\nProcessing edit request: {edit_request}")
        
        response = chat_service.process_edit_request(
            session_id=session_id,
            message=edit_request,
            current_letter=test_letter,
            editing_instructions=None,
            preserve_formatting=True
        )
        
        print(f"✓ Edit processed: {response.status}")
        
        # Wait for async processing
        import time
        time.sleep(3)
        
        # Check memory stats
        stats = memory_service.get_memory_stats()
        print(f"✓ Updated memory stats: {stats}")
        
        # Test memory instructions retrieval
        instructions = memory_service.format_instructions_for_prompt()
        
        if instructions:
            print("✓ Instructions retrieved for future letters:")
            print(f"{instructions}")
        else:
            print("ℹ No instructions found")
        
        # Clean up
        chat_service.delete_session(session_id)
        print(f"✓ Session cleaned up: {session_id}")
        
        print("✓ Chat integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error during chat integration test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Simplified Long-Term Memory Feature Test Suite")
    print("=" * 60)
    
    # Test memory service
    memory_test_passed = test_simplified_memory_service()
    
    # Test integration (only if memory service works)
    if memory_test_passed:
        chat_test_passed = test_integration_with_chat()
    else:
        chat_test_passed = False
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"Simplified Memory Service: {'✓ PASSED' if memory_test_passed else '✗ FAILED'}")
    print(f"Chat Integration:          {'✓ PASSED' if chat_test_passed else '✗ FAILED'}")
    
    if memory_test_passed and chat_test_passed:
        print("\n🎉 All tests passed! The Simplified Long-Term Memory feature is ready.")
    else:
        print("\n⚠ Some tests failed. Please check the configuration and dependencies.")
    
    sys.exit(0 if memory_test_passed and chat_test_passed else 1)
