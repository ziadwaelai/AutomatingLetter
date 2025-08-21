#!/usr/bin/env python3
"""
Comprehensive test script for session creation, interactive chat, and long-term memory system.
Tests the full workflow and verifies memory.json instruction insertion.
"""

import requests
import json
import time
import sys
from pathlib import Path
from datetime import datetime

class MemorySystemTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session_id = None
        self.memory_file = Path("logs/memory.json")
        
    def log(self, message):
        """Log with timestamp."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def check_memory_file_before(self):
        """Check memory.json state before tests."""
        self.log("=== Checking memory.json before tests ===")
        if self.memory_file.exists():
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                instructions = data.get("instructions", [])
                self.log(f"Current instructions count: {len(instructions)}")
                for i, instr in enumerate(instructions[:3], 1):
                    self.log(f"  {i}. {instr['text']} (used {instr.get('usage_count', 0)} times)")
        else:
            self.log("Memory file doesn't exist yet")
    
    def test_session_creation(self):
        """Test session creation."""
        self.log("=== Testing Session Creation ===")
        
        response = requests.post(f"{self.base_url}/api/v1/chat/sessions", 
                               json={
                                   "context": "Testing session creation and memory integration"
                               })
        
        if response.status_code == 201:
            data = response.json()
            self.session_id = data["session_id"]
            self.log(f"✓ Session created: {self.session_id}")
            self.log(f"  Expires in: {data['expires_in']} minutes")
            return True
        else:
            self.log(f"✗ Session creation failed: {response.status_code} - {response.text}")
            return False
    
    def test_session_status(self):
        """Test session status retrieval."""
        self.log("=== Testing Session Status ===")
        
        response = requests.get(f"{self.base_url}/api/v1/chat/sessions/{self.session_id}/status")
        
        if response.status_code == 200:
            data = response.json()
            self.log("✓ Session status retrieved")
            session_info = data["session_info"]
            self.log(f"  Created: {session_info['created_at']}")
            self.log(f"  Active: {session_info['is_active']}")
            self.log(f"  Expired: {session_info['is_expired']}")
            return True
        else:
            self.log(f"✗ Session status failed: {response.status_code} - {response.text}")
            return False
    
    def test_memory_integration_with_chat(self):
        """Test memory integration with chat editing."""
        self.log("=== Testing Memory Integration with Chat ===")
        
        # Test messages that should trigger memory processing
        test_messages = [
            {
                "message": "أريد إضافة فقرة شكر وتقدير في نهاية الخطاب",
                "current_letter": "بسم الله الرحمن الرحيم\n\nالسلام عليكم ورحمة الله وبركاته\n\nيسعدني أن أكتب لكم هذا الخطاب",
                "editing_instructions": "إضافة فقرة شكر مناسبة"
            },
            {
                "message": "اجعل التوقيع أكثر رسمية مع إضافة المسمى الوظيفي",
                "current_letter": "بسم الله الرحمن الرحيم\n\nالسلام عليكم ورحمة الله وبركاته\n\nيسعدني أن أكتب لكم هذا الخطاب\n\nوتقبلوا فائق الاحترام\nأحمد محمد",
                "editing_instructions": "تحسين التوقيع الرسمي"
            },
            {
                "message": "أضف بعض التفاصيل الإضافية حول الموضوع مع الحفاظ على الطابع الرسمي",
                "current_letter": "بسم الله الرحمن الرحيم\n\nالسلام عليكم ورحمة الله وبركاته\n\nأكتب إليكم بخصوص الموضوع المطروح",
                "editing_instructions": "إضافة تفاصيل وتوضيحات"
            }
        ]
        
        success_count = 0
        for i, test_data in enumerate(test_messages, 1):
            self.log(f"  Testing chat message {i}: {test_data['message'][:50]}...")
            
            response = requests.post(
                f"{self.base_url}/api/v1/chat/sessions/{self.session_id}/edit",
                json=test_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"  ✓ Chat edit {i} successful")
                self.log(f"    Processing time: {data.get('processing_time', 'N/A')} seconds")
                self.log(f"    Change summary: {data.get('change_summary', 'N/A')}")
                success_count += 1
            else:
                self.log(f"  ✗ Chat edit {i} failed: {response.status_code} - {response.text}")
            
            # Wait for async memory processing
            time.sleep(2)
        
        return success_count == len(test_messages)
    
    def test_memory_persistence(self):
        """Test if memory instructions are properly persisted."""
        self.log("=== Testing Memory Persistence ===")
        
        # Wait a bit more for async processing
        time.sleep(3)
        
        if self.memory_file.exists():
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                instructions = data.get("instructions", [])
                
                self.log(f"✓ Memory file exists with {len(instructions)} instructions")
                
                # Check for recent instructions
                recent_instructions = [
                    instr for instr in instructions
                    if datetime.fromisoformat(instr['created_at']).date() == datetime.now().date()
                ]
                
                self.log(f"  Recent instructions today: {len(recent_instructions)}")
                for instr in recent_instructions:
                    self.log(f"    - {instr['text']} (used {instr['usage_count']} times)")
                
                return len(instructions) > 0
        else:
            self.log("✗ Memory file doesn't exist after chat interactions")
            return False
    
    def test_memory_retrieval_api(self):
        """Test memory retrieval through API endpoints."""
        self.log("=== Testing Memory Retrieval API ===")
        
        # Test memory stats
        response = requests.get(f"{self.base_url}/api/v1/chat/memory/stats")
        if response.status_code == 200:
            stats = response.json()
            self.log("✓ Memory stats retrieved")
            self.log(f"  Total instructions: {stats['data']['total_instructions']}")
            self.log(f"  Last updated: {stats['data']['last_updated']}")
        else:
            self.log(f"✗ Memory stats failed: {response.status_code}")
            return False
        
        # Test memory instructions for prompt
        response = requests.get(f"{self.base_url}/api/v1/chat/memory/instructions")
        if response.status_code == 200:
            data = response.json()
            instructions_text = data['data']['instructions']
            self.log("✓ Memory instructions for prompt retrieved")
            self.log(f"  Instructions length: {len(instructions_text)} characters")
            if instructions_text:
                lines = instructions_text.split('\n')[:3]
                for line in lines:
                    if line.strip():
                        self.log(f"    {line}")
        else:
            self.log(f"✗ Memory instructions failed: {response.status_code}")
            return False
        
        return True
    
    def test_session_memory_lifecycle(self):
        """Test complete session memory lifecycle."""
        self.log("=== Testing Session Memory Lifecycle ===")
        
        # Multiple status checks to verify session stability
        for i in range(3):
            response = requests.get(f"{self.base_url}/api/v1/chat/sessions/{self.session_id}/status")
            if response.status_code == 200:
                self.log(f"  ✓ Status check {i+1}: Session still active")
            else:
                self.log(f"  ✗ Status check {i+1}: Session issue - {response.status_code}")
                return False
            time.sleep(1)
        
        # Get chat history
        response = requests.get(f"{self.base_url}/api/v1/chat/sessions/{self.session_id}/history")
        if response.status_code == 200:
            data = response.json()
            history = data["history"]
            self.log(f"✓ Chat history retrieved: {len(history)} messages")
            for msg in history[:2]:  # Show first 2 messages
                self.log(f"    {msg['role']}: {msg['content'][:50]}...")
        else:
            self.log(f"✗ Chat history failed: {response.status_code}")
            return False
        
        return True
    
    def test_memory_agent_functionality(self):
        """Test the memory agent's decision-making."""
        self.log("=== Testing Memory Agent Functionality ===")
        
        # Direct memory service test (if accessible)
        try:
            # This would require internal access - we'll test through API instead
            self.log("  Testing through API endpoints...")
            
            # Test instruction retrieval formatting
            response = requests.get(f"{self.base_url}/api/v1/chat/memory/instructions?category=تحرير")
            if response.status_code == 200:
                data = response.json()
                self.log("✓ Category-specific instructions retrieved")
                return True
            else:
                self.log(f"  Basic instructions test: {response.status_code}")
                return response.status_code == 200
        except Exception as e:
            self.log(f"  Memory agent test error: {e}")
            return False
    
    def cleanup_test_session(self):
        """Clean up test session."""
        self.log("=== Cleaning Up Test Session ===")
        
        if self.session_id:
            response = requests.delete(f"{self.base_url}/api/v1/chat/sessions/{self.session_id}")
            if response.status_code == 200:
                self.log("✓ Test session deleted")
            else:
                self.log(f"  Session deletion warning: {response.status_code}")
    
    def run_full_test(self):
        """Run complete test suite."""
        self.log("Starting Comprehensive Memory System Test")
        self.log("=" * 60)
        
        # Pre-test checks
        self.check_memory_file_before()
        
        # Core functionality tests
        tests = [
            ("Session Creation", self.test_session_creation),
            ("Session Status", self.test_session_status),
            ("Memory Integration with Chat", self.test_memory_integration_with_chat),
            ("Memory Persistence", self.test_memory_persistence),
            ("Memory Retrieval API", self.test_memory_retrieval_api),
            ("Session Memory Lifecycle", self.test_session_memory_lifecycle),
            ("Memory Agent Functionality", self.test_memory_agent_functionality),
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
                status = "✓ PASS" if result else "✗ FAIL"
                self.log(f"{status} - {test_name}")
            except Exception as e:
                results[test_name] = False
                self.log(f"✗ ERROR - {test_name}: {e}")
            
            self.log("-" * 40)
        
        # Cleanup
        self.cleanup_test_session()
        
        # Final report
        self.log("TEST RESULTS SUMMARY")
        self.log("=" * 60)
        passed = sum(results.values())
        total = len(results)
        
        for test_name, result in results.items():
            status = "✓" if result else "✗"
            self.log(f"{status} {test_name}")
        
        self.log(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            self.log("All tests passed! Memory system is working correctly.")
            return True
        else:
            self.log("Some tests failed. Check the logs above for details.")
            return False

if __name__ == "__main__":
    # Allow custom base URL
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    tester = MemorySystemTester(base_url)
    success = tester.run_full_test()
    
    sys.exit(0 if success else 1)