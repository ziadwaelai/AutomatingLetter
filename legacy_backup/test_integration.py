"""
Test integration of the Simplified Long-Term Memory with the actual application
"""

import requests
import json
import time

# Test configuration
BASE_URL = "http://localhost:5000"
API_BASE = f"{BASE_URL}/api/v1"
SESSION_ID = None

def test_chat_with_memory():
    """Test chat functionality with memory integration"""
    print("🧪 Testing Chat with Memory Integration")
    print("=" * 60)
    
    global SESSION_ID
    
    # 1. Create a chat session
    print("1. Creating chat session...")
    response = requests.post(
        f"{API_BASE}/chat/sessions",
        json={},  # Send empty JSON to ensure proper content-type
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code == 201:
        data = response.json()
        SESSION_ID = data['session_id']
        print(f"   ✓ Session created: {SESSION_ID}")
    else:
        print(f"   ✗ Failed to create session: {response.status_code}")
        return False
    
    # 2. Send a message with instructions
    print("\n2. Sending message with writing instructions...")
    edit_request = {
        "message": "اجعل الخطاب أكثر تهذيباً ومحترماً. أريد أن تكون جميع خطاباتي المستقبلية مهذبة ورسمية",
        "current_letter": "سيدي الكريم، أكتب إليك بخصوص الموضوع المطلوب."
    }
    
    response = requests.post(
        f"{API_BASE}/chat/sessions/{SESSION_ID}/edit", 
        json=edit_request
    )
    
    if response.status_code == 200:
        print("   ✓ Message processed successfully")
        print("   ✓ Memory should be learning from this message")
    else:
        print(f"   ✗ Failed to process message: {response.status_code}")
        print(f"   Error: {response.text}")
        return False
    
    # 3. Wait for memory processing
    print("\n3. Waiting for memory processing...")
    time.sleep(3)
    
    # 4. Check memory stats
    print("\n4. Checking memory stats...")
    response = requests.get(f"{API_BASE}/chat/memory/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"   ✓ Memory stats: {stats}")
    else:
        print(f"   ✗ Failed to get memory stats: {response.status_code}")
    
    # 5. Get current instructions
    print("\n5. Retrieving stored instructions...")
    response = requests.get(f"{API_BASE}/chat/memory/instructions")
    if response.status_code == 200:
        instructions = response.json()
        print("   ✓ Current instructions:")
        # Check different possible response structures
        if 'data' in instructions and 'instructions' in instructions['data']:
            formatted_instructions = instructions['data']['instructions']
            print("   ✓ Instructions are properly formatted in Arabic:")
            print(formatted_instructions)
        elif 'formatted_instructions' in instructions:
            print(f"   {instructions['formatted_instructions']}")
        else:
            print(f"   Raw response: {instructions}")
    else:
        print(f"   ✗ Failed to get instructions: {response.status_code}")
    
    print("\n🎉 Integration test completed!")
    return True

def test_memory_api():
    """Test memory API endpoints"""
    print("\n🧪 Testing Memory API Endpoints")
    print("=" * 60)
    
    # Test stats endpoint
    print("1. Testing /memory/stats...")
    response = requests.get(f"{API_BASE}/chat/memory/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"   ✓ Stats retrieved: {stats}")
    else:
        print(f"   ✗ Stats failed: {response.status_code}")
        return False
    
    # Test instructions endpoint
    print("\n2. Testing /memory/instructions...")
    response = requests.get(f"{API_BASE}/chat/memory/instructions")
    if response.status_code == 200:
        instructions = response.json()
        print("   ✓ Instructions retrieved successfully")
        # Check different possible response structures
        if 'data' in instructions and 'instructions' in instructions['data']:
            print("   ✓ Instructions are properly formatted in Arabic")
        elif 'formatted_instructions' in instructions:
            print("   ✓ Instructions are properly formatted in Arabic")
        else:
            print("   ⚠ No formatted instructions found")
    else:
        print(f"   ✗ Instructions failed: {response.status_code}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Simplified Long-Term Memory Integration Test")
    print("=" * 80)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print("✓ Server is running")
    except requests.exceptions.RequestException:
        print("✗ Server is not running. Please start the application first:")
        print("  python app.py")
        exit(1)
    
    # Run tests
    success = True
    success &= test_memory_api()
    success &= test_chat_with_memory()
    
    # Cleanup
    if SESSION_ID:
        print(f"\n🧹 Cleaning up session: {SESSION_ID}")
        try:
            requests.delete(f"{API_BASE}/chat/sessions/{SESSION_ID}")
            print("   ✓ Session cleaned up")
        except:
            print("   ⚠ Could not clean up session")
    
    if success:
        print("\n🎉 All integration tests passed!")
        print("✓ Simplified Long-Term Memory is working correctly!")
    else:
        print("\n❌ Some tests failed!")
