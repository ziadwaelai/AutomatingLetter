#!/usr/bin/env python3
"""
Comprehensive System Test for Session Management
Tests all CRUD operations and letter editing functionality.
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

BASE_URL = "https://128.140.37.194:5000"

class SessionSystemTest:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.test_sessions = []
        self.failed_tests = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages."""
        prefix = "✅" if level == "SUCCESS" else "❌" if level == "ERROR" else "🔍"
        print(f"{prefix} {message}")
        
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling."""
        url = f"{BASE_URL}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            return response
        except Exception as e:
            self.log(f"Request failed: {method} {endpoint} - {e}", "ERROR")
            raise
    
    def verify_session_count(self, expected_count: int, step: str) -> bool:
        """Verify the session count matches expected."""
        response = self.make_request("GET", "/api/v1/chat/sessions")
        if response.status_code != 200:
            self.log(f"Failed to get session list at {step}: {response.status_code}", "ERROR")
            return False
            
        data = response.json()
        actual_count = data.get("total", -1)
        
        if actual_count == expected_count:
            self.log(f"{step}: Session count correct ({actual_count})", "SUCCESS")
            return True
        else:
            self.log(f"{step}: Session count mismatch - Expected: {expected_count}, Got: {actual_count}", "ERROR")
            self.log(f"Sessions in response: {[s['session_id'] for s in data.get('sessions', [])]}")
            return False
    
    def test_1_initial_state(self) -> bool:
        """Test 1: Get initial session count."""
        self.log("=== TEST 1: Initial State ===")
        
        response = self.make_request("GET", "/api/v1/chat/sessions")
        if response.status_code != 200:
            self.log("Failed to get initial session list", "ERROR")
            return False
            
        data = response.json()
        initial_count = data.get("total", 0)
        self.log(f"Initial session count: {initial_count}")
        
        # Store initial sessions for cleanup
        for session in data.get("sessions", []):
            self.test_sessions.append(session["session_id"])
            
        return True
    
    def test_2_create_session(self) -> Dict[str, Any]:
        """Test 2: Create a new session."""
        self.log("=== TEST 2: Create Session ===")
        
        response = self.make_request("POST", "/api/v1/chat/sessions", 
                                   headers={"Content-Type": "application/json"},
                                   json={"context": "Test session for system testing"})
        
        if response.status_code != 201:
            self.log(f"Failed to create session: {response.status_code} - {response.text}", "ERROR")
            return None
            
        data = response.json()
        session_id = data.get("session_id")
        
        if not session_id:
            self.log("No session_id returned from create", "ERROR")
            return None
            
        self.log(f"Created session: {session_id}", "SUCCESS")
        self.test_sessions.append(session_id)
        
        # Verify session appears in list immediately
        time.sleep(0.2)  # Small delay for consistency
        response = self.make_request("GET", "/api/v1/chat/sessions")
        if response.status_code == 200:
            sessions = response.json().get("sessions", [])
            session_ids = [s["session_id"] for s in sessions]
            if session_id in session_ids:
                self.log("✅ Session appears in list immediately after creation", "SUCCESS")
            else:
                self.log("❌ Session NOT found in list after creation", "ERROR")
                self.log(f"Expected: {session_id}")
                self.log(f"Found: {session_ids}")
                return None
        
        return {"session_id": session_id, "data": data}
    
    def test_3_get_session_status(self, session_id: str) -> bool:
        """Test 3: Get session status."""
        self.log("=== TEST 3: Get Session Status ===")
        
        response = self.make_request("GET", f"/api/v1/chat/sessions/{session_id}/status")
        
        if response.status_code != 200:
            self.log(f"Failed to get session status: {response.status_code} - {response.text}", "ERROR")
            return False
            
        data = response.json()
        if data.get("session_id") == session_id:
            self.log(f"Session status retrieved successfully", "SUCCESS")
            return True
        else:
            self.log(f"Session status mismatch", "ERROR")
            return False
    
    def test_4_edit_letter(self, session_id: str) -> bool:
        """Test 4: Edit letter with session."""
        self.log("=== TEST 4: Edit Letter ===")
        
        edit_request = {
            "message": "Please write a simple letter of introduction",
            "current_letter": "",
            "editing_instructions": "Write a professional introduction letter",
            "preserve_formatting": True
        }
        
        response = self.make_request("POST", f"/api/v1/chat/sessions/{session_id}/edit",
                                   headers={"Content-Type": "application/json"},
                                   json=edit_request)
        
        if response.status_code != 200:
            self.log(f"Failed to edit letter: {response.status_code} - {response.text}", "ERROR")
            return False
            
        data = response.json()
        if "updated_letter" in data:
            self.log("Letter edited successfully", "SUCCESS")
            return True
        else:
            self.log("No updated_letter in response", "ERROR")
            return False
    
    def test_5_extend_session(self, session_id: str) -> bool:
        """Test 5: Extend session."""
        self.log("=== TEST 5: Extend Session ===")
        
        response = self.make_request("POST", f"/api/v1/chat/sessions/{session_id}/extend",
                                   headers={"Content-Type": "application/json"},
                                   json={})
        
        if response.status_code != 200:
            self.log(f"Failed to extend session: {response.status_code} - {response.text}", "ERROR")
            return False
            
        data = response.json()
        if "new_expiration" in data:
            self.log("Session extended successfully", "SUCCESS")
            return True
        else:
            self.log("No new_expiration in response", "ERROR")
            return False
    
    def test_6_delete_session(self, session_id: str) -> bool:
        """Test 6: Delete session and verify removal."""
        self.log("=== TEST 6: Delete Session ===")
        
        # First verify session exists
        response = self.make_request("GET", "/api/v1/chat/sessions")
        if response.status_code == 200:
            sessions_before = response.json().get("sessions", [])
            session_ids_before = [s["session_id"] for s in sessions_before]
            count_before = len(session_ids_before)
            
            if session_id not in session_ids_before:
                self.log(f"Session {session_id} not found before deletion!", "ERROR")
                return False
            else:
                self.log(f"Session found before deletion. Total sessions: {count_before}")
        
        # Delete the session
        response = self.make_request("DELETE", f"/api/v1/chat/sessions/{session_id}")
        
        if response.status_code not in [200, 204]:
            self.log(f"Failed to delete session: {response.status_code} - {response.text}", "ERROR")
            return False
        
        self.log("Delete request completed successfully")
        
        # Wait and verify session is removed from list
        time.sleep(0.5)  # Give time for deletion to propagate
        
        response = self.make_request("GET", "/api/v1/chat/sessions")
        if response.status_code == 200:
            sessions_after = response.json().get("sessions", [])
            session_ids_after = [s["session_id"] for s in sessions_after]
            count_after = len(session_ids_after)
            
            if session_id in session_ids_after:
                self.log(f"❌ Session {session_id} STILL EXISTS after deletion!", "ERROR")
                self.log(f"Sessions before: {session_ids_before}")
                self.log(f"Sessions after:  {session_ids_after}")
                return False
            else:
                self.log(f"✅ Session properly removed. Count before: {count_before}, after: {count_after}", "SUCCESS")
                return True
        else:
            self.log("Failed to verify deletion", "ERROR")
            return False
    
    def test_7_verify_session_gone(self, session_id: str) -> bool:
        """Test 7: Verify deleted session returns 404."""
        self.log("=== TEST 7: Verify Session Gone ===")
        
        # Try to get status of deleted session
        response = self.make_request("GET", f"/api/v1/chat/sessions/{session_id}/status")
        
        if response.status_code == 404:
            self.log("Deleted session correctly returns 404", "SUCCESS")
            return True
        else:
            self.log(f"Deleted session still accessible: {response.status_code}", "ERROR")
            return False
    
    def test_8_consistency_check(self) -> bool:
        """Test 8: Multiple consistency checks."""
        self.log("=== TEST 8: Consistency Check ===")
        
        # Add a small delay to allow any pending operations to complete
        time.sleep(1.0)
        
        counts = []
        for i in range(10):
            response = self.make_request("GET", "/api/v1/chat/sessions")
            if response.status_code == 200:
                count = response.json().get("total", -1)
                counts.append(count)
                time.sleep(0.2)  # Slightly longer delay between requests
            else:
                counts.append(-1)
        
        unique_counts = set(counts)
        if len(unique_counts) == 1:
            self.log(f"Consistency check passed: {counts[0]} sessions consistently", "SUCCESS")
            return True
        else:
            self.log(f"Consistency check failed: {counts}", "ERROR")
            return False
    
    def run_full_test(self):
        """Run the complete test suite."""
        self.log("🚀 Starting Comprehensive Session Management Test")
        self.log("=" * 60)
        
        start_time = time.time()
        tests_passed = 0
        total_tests = 8
        
        # Test 1: Initial state
        if self.test_1_initial_state():
            tests_passed += 1
        
        # Test 2: Create session
        session_info = self.test_2_create_session()
        if session_info:
            tests_passed += 1
            session_id = session_info["session_id"]
            
            # Test 3: Get session status
            if self.test_3_get_session_status(session_id):
                tests_passed += 1
            
            # Test 4: Edit letter
            if self.test_4_edit_letter(session_id):
                tests_passed += 1
            
            # Test 5: Extend session
            if self.test_5_extend_session(session_id):
                tests_passed += 1
            
            # Test 6: Delete session
            if self.test_6_delete_session(session_id):
                tests_passed += 1
                
                # Test 7: Verify deletion
                if self.test_7_verify_session_gone(session_id):
                    tests_passed += 1
        
        # Test 8: Consistency check
        if self.test_8_consistency_check():
            tests_passed += 1
        
        # Summary
        duration = time.time() - start_time
        self.log("=" * 60)
        self.log(f"🏁 Test Summary: {tests_passed}/{total_tests} tests passed")
        self.log(f"⏱️  Duration: {duration:.2f} seconds")
        
        if tests_passed == total_tests:
            self.log("🎉 ALL TESTS PASSED! System is working correctly.", "SUCCESS")
            return True
        else:
            self.log(f"💥 {total_tests - tests_passed} TESTS FAILED! System has issues.", "ERROR")
            return False


if __name__ == "__main__":
    test = SessionSystemTest()
    success = test.run_full_test()
    sys.exit(0 if success else 1)
