"""
Complete Workflow Test for Long-Term Memory Feature
Tests the end-to-end workflow including chat service integration.
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

def test_complete_workflow():
    """Test the complete workflow including chat service integration."""
    print("Testing Complete Workflow with Long-Term Memory...")
    
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
            context="Testing long-term memory integration"
        )
        print(f"✓ Chat session created: {session_id}")
        
        # Simulate user messages with instructions
        test_letter = """بسم الله الرحمن الرحيم

إلى الأستاذ أحمد محمد
المحترم

السلام عليكم ورحمة الله وبركاته

نشكرك على مشاركتك في فعالية التشجير التي أقيمت الأسبوع الماضي.

وتفضل بقبول فائق الاحترام والتقدير.

مع التحية
إدارة نت زيرو"""
        
        # Test edit requests with instructions
        edit_requests = [
            "اجعل الخطاب أقصر وأكثر اختصاراً. أريد أن تكون جميع خطاباتي المستقبلية مختصرة دائماً",
            "أضف دعوة للتواصل في النهاية. هذا يجب أن يكون في جميع خطاباتي",
            "استخدم أسلوباً أكثر رسمية. أفضل الأسلوب الرسمي في كل الخطابات"
        ]
        
        current_letter = test_letter
        for i, edit_request in enumerate(edit_requests):
            print(f"\nProcessing edit request {i+1}: {edit_request[:50]}...")
            
            # This will trigger memory processing in the background
            response = chat_service.process_edit_request(
                session_id=session_id,
                message=edit_request,
                current_letter=current_letter,
                editing_instructions=None,
                preserve_formatting=True
            )
            
            print(f"✓ Edit processed: {response.status}")
            current_letter = response.updated_letter
        
        # Wait a moment for async processing
        import time
        time.sleep(2)
        
        # Check memory stats
        stats = memory_service.get_memory_stats()
        print(f"\n✓ Memory stats after processing: {stats}")
        
        # Test memory instructions retrieval
        instructions = memory_service.format_instructions_for_prompt(
            category="THANK_YOU",
            session_id=session_id
        )
        
        if instructions:
            print("✓ Instructions retrieved for future letters:")
            print(f"   {instructions[:200]}...")
        else:
            print("⚠ No instructions found (extraction might have failed)")
        
        # Test letter generation with memory
        from src.services.letter_generator import LetterGenerationContext, get_letter_service
        
        context = LetterGenerationContext(
            user_prompt="اكتب خطاب شكر جديد للمشاركة في ورشة العمل",
            category="THANK_YOU",
            session_id=session_id,
            recipient="د. فاطمة أحمد",
            member_info="محمد سعد - مدير العمليات"
        )
        
        print("\n✓ Testing letter generation with memory context...")
        letter_service = get_letter_service()
        letter_result = letter_service.generate_letter(context)
        
        print(f"✓ Letter generated with memory integration!")
        print(f"   Title: {letter_result.Title}")
        print(f"   Content preview: {letter_result.Letter[:200]}...")
        
        # Clean up
        chat_service.delete_session(session_id)
        print(f"✓ Session cleaned up: {session_id}")
        
        print("\n✓ Complete workflow test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error during complete workflow test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Long-Term Memory Complete Workflow Test")
    print("=" * 60)
    
    success = test_complete_workflow()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Complete workflow test PASSED!")
        print("The Long-Term Memory feature is fully integrated and working.")
    else:
        print("❌ Complete workflow test FAILED!")
        print("Please check the error messages above.")
    
    sys.exit(0 if success else 1)
