"""
Test script for the Long-Term Memory API endpoints
Tests the new memory endpoints through HTTP requests.
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_memory_endpoints():
    """Test the memory-related API endpoints."""
    print("Testing Long-Term Memory API Endpoints...")
    print("=" * 50)
    
    # Test 1: Check memory stats endpoint
    print("\n1. Testing memory stats endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/chat/memory/stats")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Memory stats: {data['data']}")
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Request failed: {e}")
    
    # Test 2: Create a chat session and process some messages
    print("\n2. Testing chat session with memory processing...")
    try:
        # Create session
        session_response = requests.post(f"{BASE_URL}/api/v1/chat/sessions", json={
            "context": "Testing memory integration"
        })
        
        if session_response.status_code not in [200, 201]:
            print(f"✗ Failed to create session: {session_response.text}")
            return
        
        session_data = session_response.json()
        session_id = session_data['session_id']  # Direct access, not nested in 'data'
        print(f"✓ Created session: {session_id}")
        
        # Test letter content
        test_letter = """بسم الله الرحمن الرحيم

إلى الأستاذ أحمد محمد
المحترم

السلام عليكم ورحمة الله وبركاته

نشكرك على مشاركتك في الفعالية.

وتفضل بقبول فائق الاحترام والتقدير.

مع التحية
إدارة نت زيرو"""
        
        # Process edit with memory instruction
        edit_request = {
            "message": "اجعل هذا الخطاب أقصر. أريد أن تكون جميع خطاباتي مختصرة دائماً",
            "current_letter": test_letter,
            "preserve_formatting": True
        }
        
        edit_response = requests.post(f"{BASE_URL}/api/v1/chat/sessions/{session_id}/edit", json=edit_request)
        
        if edit_response.status_code == 200:
            edit_data = edit_response.json()
            print(f"✓ Edit processed: {edit_data['status']}")
            print(f"   Change summary: {edit_data['change_summary']}")
        else:
            print(f"✗ Edit failed: {edit_response.text}")
        
        # Wait for async processing
        time.sleep(3)
        
        # Check memory stats again
        print("\n3. Testing memory stats after processing...")
        stats_response = requests.get(f"{BASE_URL}/api/v1/chat/memory/stats")
        if stats_response.status_code == 200:
            new_stats = stats_response.json()
            print(f"✓ Updated memory stats: {new_stats['data']}")
        
        # Test memory instructions endpoint
        print("\n4. Testing memory instructions endpoint...")
        instructions_response = requests.get(f"{BASE_URL}/api/v1/chat/memory/instructions", params={
            "session_id": session_id
        })
        
        if instructions_response.status_code == 200:
            instructions_data = instructions_response.json()
            instructions_text = instructions_data['data']['instructions']
            if instructions_text:
                print(f"✓ Retrieved instructions ({len(instructions_text)} characters)")
                print(f"   Preview: {instructions_text[:150]}...")
            else:
                print("ℹ No instructions found (might still be processing)")
        else:
            print(f"✗ Instructions request failed: {instructions_response.text}")
        
        # Clean up session
        delete_response = requests.delete(f"{BASE_URL}/api/v1/chat/sessions/{session_id}")
        if delete_response.status_code == 200:
            print(f"✓ Session deleted: {session_id}")
        
    except Exception as e:
        print(f"✗ Session test failed: {e}")

def test_letter_generation_integration():
    """Test letter generation with memory integration."""
    print("\n5. Testing letter generation integration...")
    
    try:
        # First, create a session and add some instructions
        session_response = requests.post(f"{BASE_URL}/api/v1/chat/sessions", json={
            "context": "Testing letter generation with memory"
        })
        
        if session_response.status_code not in [200, 201]:
            print(f"✗ Failed to create session for letter test")
            return
        
        session_data = session_response.json()
        session_id = session_data['session_id']
        
        # Add some memory instructions through chat
        test_letter = "خطاب اختبار"
        
        instructions = [
            "استخدم أسلوباً مختصراً في كل الخطابات",
            "أضف دائماً دعوة للتواصل في النهاية"
        ]
        
        for instruction in instructions:
            edit_request = {
                "message": instruction,
                "current_letter": test_letter,
                "preserve_formatting": True
            }
            
            requests.post(f"{BASE_URL}/api/v1/chat/sessions/{session_id}/edit", json=edit_request)
        
        # Wait for processing
        time.sleep(3)
        
        # Now test regular letter generation (should not include memory since it's not chat-based)
        letter_request = {
            "category": "THANK_YOU",
            "recipient": "الأستاذ محمد أحمد",
            "prompt": "شكر على المشاركة في ورشة العمل",
            "is_first": True
        }
        
        letter_response = requests.post(f"{BASE_URL}/api/v1/letters/generate", json=letter_request)
        
        if letter_response.status_code == 200:
            letter_data = letter_response.json()
            print(f"✓ Letter generated: {letter_data['Title']}")
            print(f"   Content preview: {letter_data['Letter'][:150]}...")
        else:
            print(f"✗ Letter generation failed: {letter_response.text}")
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/v1/chat/sessions/{session_id}")
        
    except Exception as e:
        print(f"✗ Letter generation test failed: {e}")

if __name__ == "__main__":
    print("Long-Term Memory API Endpoint Tests")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✓ Server is running (status: {response.status_code})")
    except requests.exceptions.RequestException:
        print("✗ Server is not running or not accessible")
        print("Please start the server with: python app.py")
        exit(1)
    
    # Run tests
    test_memory_endpoints()
    test_letter_generation_integration()
    
    print("\n" + "=" * 60)
    print("🎉 API endpoint tests completed!")
    print("Check the output above for any issues.")
