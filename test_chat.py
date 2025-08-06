#!/usr/bin/env python3
"""
Test script for chat service functionality
"""

import requests
import json

# Base URL
BASE_URL = "http://localhost:5000"

def test_chat_workflow():
    """Test the complete chat workflow"""
    
    print("🧪 Testing Chat Service Workflow")
    print("=" * 50)
    
    # Step 1: Create a chat session
    print("\n1️⃣ Creating chat session...")
    session_data = {
        "initial_letter": "بسم الله الرحمن الرحيم\n\nالسلام عليكم ورحمة الله وبركاته\n\nأتقدم إليكم بهذا الخطاب للتعبير عن موضوع مهم",
        "context": "خطاب رسمي للشؤون الإدارية"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/sessions",
            headers={"Content-Type": "application/json"},
            json=session_data,
            timeout=10
        )
        
        if response.status_code == 201:
            session_info = response.json()
            session_id = session_info["session_id"]
            print(f"✅ Session created: {session_id}")
            print(f"📋 Response: {json.dumps(session_info, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ Failed to create session: {response.status_code}")
            print(f"📋 Error: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Exception during session creation: {e}")
        return
    
    # Step 2: Edit letter via chat
    print(f"\n2️⃣ Editing letter via chat (Session: {session_id})...")
    edit_data = {
        "message": "أضف فقرة شكر وتقدير في نهاية الخطاب مع إضافة التوقيع",
        "current_letter": "بسم الله الرحمن الرحيم\n\nالسلام عليكم ورحمة الله وبركاته\n\nأتقدم إليكم بهذا الخطاب للتعبير عن موضوع مهم",
        "editing_instructions": "حافظ على الطابع الرسمي والمهني للخطاب",
        "preserve_formatting": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/sessions/{session_id}/edit",
            headers={"Content-Type": "application/json"},
            json=edit_data,
            timeout=30
        )
        
        if response.status_code == 200:
            edit_result = response.json()
            print(f"✅ Letter edited successfully!")
            print(f"📋 Response: {json.dumps(edit_result, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ Failed to edit letter: {response.status_code}")
            print(f"📋 Error: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Exception during letter editing: {e}")
        return
    
    # Step 3: Get session status
    print(f"\n3️⃣ Getting session status...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/chat/sessions/{session_id}/status",
            timeout=10
        )
        
        if response.status_code == 200:
            status_info = response.json()
            print(f"✅ Session status retrieved!")
            print(f"📋 Status: {json.dumps(status_info, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ Failed to get status: {response.status_code}")
            print(f"📋 Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception during status check: {e}")
    
    print(f"\n🎉 Chat workflow test completed!")

if __name__ == "__main__":
    test_chat_workflow()
