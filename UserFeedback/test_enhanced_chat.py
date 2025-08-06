"""
Test script for the Enhanced Interactive Chat System
Run this script to verify the chat system is working correctly.
"""

import sys
import os
import time
from datetime import datetime

# Add the parent directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from UserFeedback.enhanced_chat import InteractiveChatManager

def test_enhanced_chat():
    """Test the enhanced chat system functionality."""
    print("🚀 Testing Enhanced Interactive Chat System...")
    print("=" * 50)
    
    # Initialize chat manager
    try:
        chat_manager = InteractiveChatManager(
            session_timeout_minutes=1,  # Short timeout for testing
            cleanup_interval_minutes=1  # Frequent cleanup for testing
        )
        print("✅ Chat manager initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize chat manager: {e}")
        return False
    
    # Test 1: Create session
    print("\n📝 Test 1: Creating chat session...")
    try:
        original_letter = """بسم الله الرحمن الرحيم

الأستاذ / أحمد محمد
السلام عليكم ورحمة الله وبركاته

نتقدم إليكم بطلب موافقتكم على تنظيم فعالية خيرية في المدرسة.

وتفضلوا بقبول فائق الاحترام والتقدير،،،"""
        
        session_id = chat_manager.create_session(original_letter=original_letter)
        print(f"✅ Session created: {session_id}")
    except Exception as e:
        print(f"❌ Failed to create session: {e}")
        return False
    
    # Test 2: Edit letter
    print("\n✏️ Test 2: Editing letter...")
    try:
        feedback = "غير التاريخ إلى الغد وأضف رقم الهاتف في النهاية"
        result = chat_manager.edit_letter(session_id, original_letter, feedback)
        
        if result["status"] == "success":
            print("✅ Letter edited successfully")
            edited_letter = result["edited_letter"]
            print(f"📄 Edited letter preview: {edited_letter[:100]}...")
        else:
            print(f"❌ Failed to edit letter: {result['message']}")
            return False
    except Exception as e:
        print(f"❌ Error editing letter: {e}")
        return False
    
    # Test 3: Ask question
    print("\n❓ Test 3: Asking question about letter...")
    try:
        question = "كيف يمكنني جعل هذا الخطاب أكثر رسمية؟"
        result = chat_manager.chat_about_letter(session_id, question, edited_letter)
        
        if result["status"] == "success":
            print("✅ Question answered successfully")
            answer = result["answer"]
            print(f"💬 Answer preview: {answer[:100]}...")
        else:
            print(f"❌ Failed to answer question: {result['message']}")
            return False
    except Exception as e:
        print(f"❌ Error asking question: {e}")
        return False
    
    # Test 4: Get session info
    print("\n📊 Test 4: Getting session info...")
    try:
        info = chat_manager.get_session_info(session_id)
        
        if info["status"] == "success":
            print("✅ Session info retrieved successfully")
            print(f"   - Session ID: {info['session_id']}")
            print(f"   - Created at: {info['created_at']}")
            print(f"   - Conversation length: {info['conversation_length']}")
            print(f"   - Has original letter: {info['has_original_letter']}")
        else:
            print(f"❌ Failed to get session info: {info['message']}")
            return False
    except Exception as e:
        print(f"❌ Error getting session info: {e}")
        return False
    
    # Test 5: Active sessions count
    print("\n🔢 Test 5: Getting active sessions count...")
    try:
        count = chat_manager.get_active_sessions_count()
        print(f"✅ Active sessions: {count}")
    except Exception as e:
        print(f"❌ Error getting sessions count: {e}")
        return False
    
    # Test 6: Clear session
    print("\n🗑️ Test 6: Clearing session...")
    try:
        result = chat_manager.clear_session(session_id)
        
        if result["status"] == "success":
            print("✅ Session cleared successfully")
            
            # Verify session is gone
            info = chat_manager.get_session_info(session_id)
            if info["status"] == "error":
                print("✅ Session properly removed")
            else:
                print("❌ Session still exists after clearing")
                return False
        else:
            print(f"❌ Failed to clear session: {result['message']}")
            return False
    except Exception as e:
        print(f"❌ Error clearing session: {e}")
        return False
    
    # Test 7: Test backward compatibility
    print("\n🔄 Test 7: Testing backward compatibility...")
    try:
        from UserFeedback.interactive_chat import edit_letter_based_on_feedback
        
        test_letter = "بسم الله الرحمن الرحيم\n\nهذا خطاب تجريبي."
        test_feedback = "أضف التحية في البداية"
        
        edited = edit_letter_based_on_feedback(test_letter, test_feedback)
        print("✅ Backward compatibility works")
        print(f"📄 Result preview: {edited[:50]}...")
    except Exception as e:
        print(f"❌ Backward compatibility failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! Enhanced chat system is working correctly.")
    return True

def test_session_expiration():
    """Test session expiration functionality."""
    print("\n⏱️ Testing session expiration...")
    
    # Create manager with very short timeout
    chat_manager = InteractiveChatManager(
        session_timeout_minutes=0.01,  # 0.6 seconds
        cleanup_interval_minutes=0.01  # Cleanup every 0.6 seconds
    )
    
    # Create session
    session_id = chat_manager.create_session()
    print(f"Created session: {session_id}")
    
    # Wait for expiration
    print("Waiting for session to expire...")
    time.sleep(2)
    
    # Try to use expired session
    result = chat_manager.get_session_info(session_id)
    if result["status"] == "error":
        print("✅ Session properly expired")
        return True
    else:
        print("❌ Session didn't expire as expected")
        return False

if __name__ == "__main__":
    print("🧪 Enhanced Interactive Chat System Tests")
    print("========================================")
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key before running tests")
        sys.exit(1)
    
    # Run main tests
    success = test_enhanced_chat()
    
    if success:
        print("\n🔍 Running additional tests...")
        
        # Test session expiration (optional)
        try:
            expiration_success = test_session_expiration()
            if expiration_success:
                print("✅ Session expiration test passed")
            else:
                print("⚠️ Session expiration test failed")
        except Exception as e:
            print(f"⚠️ Session expiration test error: {e}")
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Testing completed successfully!")
        print("The enhanced chat system is ready for use.")
    else:
        print("❌ Testing failed. Please check the errors above.")
        sys.exit(1)
