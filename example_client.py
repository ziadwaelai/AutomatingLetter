"""
Example client script for the Enhanced Interactive Chat API
This script demonstrates how to use the new chat endpoints.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:5000"  # Change this to your server URL
HEADERS = {"Content-Type": "application/json"}

def create_session(original_letter=None):
    """Create a new chat session."""
    url = f"{BASE_URL}/chat/session/create"
    data = {}
    if original_letter:
        data["original_letter"] = original_letter
    
    response = requests.post(url, headers=HEADERS, json=data)
    return response.json()

def edit_letter(session_id, letter, feedback):
    """Edit a letter using the session."""
    url = f"{BASE_URL}/chat/edit-letter"
    data = {
        "session_id": session_id,
        "letter": letter,
        "feedback": feedback
    }
    
    response = requests.post(url, headers=HEADERS, json=data)
    return response.json()

def ask_question(session_id, question, current_letter=None):
    """Ask a question about the letter."""
    url = f"{BASE_URL}/chat/ask"
    data = {
        "session_id": session_id,
        "question": question
    }
    if current_letter:
        data["current_letter"] = current_letter
    
    response = requests.post(url, headers=HEADERS, json=data)
    return response.json()

def get_session_info(session_id):
    """Get information about a session."""
    url = f"{BASE_URL}/chat/session/info/{session_id}"
    response = requests.get(url)
    return response.json()

def clear_session(session_id):
    """Clear a session."""
    url = f"{BASE_URL}/chat/session/clear/{session_id}"
    response = requests.delete(url)
    return response.json()

def get_sessions_count():
    """Get count of active sessions."""
    url = f"{BASE_URL}/chat/sessions/count"
    response = requests.get(url)
    return response.json()

def main():
    """Main example workflow."""
    print("🚀 Enhanced Interactive Chat API Example")
    print("=" * 40)
    
    # Original letter
    original_letter = """بسم الله الرحمن الرحيم

إدارة المدرسة المحترمة
السلام عليكم ورحمة الله وبركاته

نتقدم إليكم بطلب الموافقة على تنظيم فعالية خيرية في المدرسة لمساعدة الأسر المحتاجة.

وتفضلوا بقبول فائق الاحترام والتقدير،،،

إدارة الأنشطة"""
    
    try:
        # Step 1: Create session
        print("\n1. Creating chat session...")
        session_response = create_session(original_letter)
        
        if session_response.get("status") != "success":
            print(f"❌ Failed to create session: {session_response}")
            return
        
        session_id = session_response["session_id"]
        print(f"✅ Session created: {session_id}")
        
        # Step 2: Edit the letter
        print("\n2. Editing the letter...")
        edit_response = edit_letter(
            session_id, 
            original_letter, 
            "أضف تاريخ اليوم وغير كلمة 'المحترمة' إلى 'الموقرة'"
        )
        
        if edit_response.get("status") != "success":
            print(f"❌ Failed to edit letter: {edit_response}")
            return
        
        edited_letter = edit_response["edited_letter"]
        print("✅ Letter edited successfully")
        print(f"📝 Edited letter preview:\n{edited_letter[:200]}...\n")
        
        # Step 3: Ask a question
        print("3. Asking a question...")
        question_response = ask_question(
            session_id,
            "كيف يمكنني جعل هذا الخطاب أكثر إقناعاً؟",
            edited_letter
        )
        
        if question_response.get("status") != "success":
            print(f"❌ Failed to ask question: {question_response}")
            return
        
        answer = question_response["answer"]
        print("✅ Question answered successfully")
        print(f"💬 Answer: {answer[:200]}...\n")
        
        # Step 4: Make another edit based on the advice
        print("4. Making another edit...")
        second_edit_response = edit_letter(
            session_id,
            edited_letter,
            "أضف فقرة تشرح أهمية هذه الفعالية للمجتمع"
        )
        
        if second_edit_response.get("status") != "success":
            print(f"❌ Failed to make second edit: {second_edit_response}")
            return
        
        final_letter = second_edit_response["edited_letter"]
        print("✅ Second edit completed")
        print(f"📝 Final letter preview:\n{final_letter[:300]}...\n")
        
        # Step 5: Get session information
        print("5. Getting session information...")
        info_response = get_session_info(session_id)
        
        if info_response.get("status") == "success":
            print("✅ Session info retrieved:")
            print(f"   - Conversation length: {info_response['conversation_length']}")
            print(f"   - Created at: {info_response['created_at']}")
            print(f"   - Has original letter: {info_response['has_original_letter']}")
        
        # Step 6: Check active sessions count
        print("\n6. Checking active sessions...")
        count_response = get_sessions_count()
        if count_response.get("status") == "success":
            print(f"✅ Active sessions: {count_response['active_sessions']}")
        
        # Step 7: Clear the session
        print("\n7. Clearing session...")
        clear_response = clear_session(session_id)
        
        if clear_response.get("status") == "success":
            print("✅ Session cleared successfully")
        else:
            print(f"❌ Failed to clear session: {clear_response}")
        
        print("\n" + "=" * 40)
        print("🎉 Example completed successfully!")
        print("\nThe enhanced chat system allows for:")
        print("- 💭 Contextual conversations about letters")
        print("- 📝 Multiple edits with memory of previous changes")
        print("- ❓ Questions and advice about letter writing")
        print("- 🔄 Session management with automatic cleanup")
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Make sure the server is running on", BASE_URL)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_legacy_endpoint():
    """Test the legacy edit-letter endpoint for comparison."""
    print("\n🔄 Testing legacy endpoint for comparison...")
    
    url = f"{BASE_URL}/edit-letter"
    data = {
        "letter": "بسم الله الرحمن الرحيم\n\nهذا خطاب تجريبي.",
        "feedback": "أضف التحية في البداية"
    }
    
    try:
        response = requests.post(url, headers=HEADERS, json=data)
        result = response.json()
        
        if result.get("status") == "success":
            print("✅ Legacy endpoint still works")
            print(f"📝 Result: {result['edited_letter'][:100]}...")
        else:
            print(f"❌ Legacy endpoint failed: {result}")
    except Exception as e:
        print(f"❌ Legacy endpoint error: {e}")

if __name__ == "__main__":
    # Run the main example
    main()
    
    # Test legacy endpoint
    test_legacy_endpoint()
    
    print("\n📚 For more examples, check the README.md file")
    print("🔧 To run tests, execute: python UserFeedback/test_enhanced_chat.py")
