#!/usr/bin/env python3
"""
Multi-Worker Consistency Test
Tests session operations across multiple gunicorn workers to detect sync issues.
"""

import requests
import json
import time
import sys
from typing import Set, List, Dict
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

BASE_URL = "https://128.140.37.194:5000"

class MultiWorkerTest:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling."""
        url = f"{BASE_URL}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=5, **kwargs)
            return response
        except Exception as e:
            print(f"❌ Request failed: {method} {endpoint} - {e}")
            raise
    
    def test_session_consistency(self, iterations: int = 20) -> Dict[str, List]:
        """Test session listing consistency across multiple workers."""
        print(f"🔍 Testing session consistency across {iterations} requests...")
        
        session_counts = []
        session_lists = []
        
        for i in range(iterations):
            response = self.make_request("GET", "/api/v1/chat/sessions")
            if response.status_code == 200:
                data = response.json()
                count = data.get("total", -1)
                session_ids = [s["session_id"] for s in data.get("sessions", [])]
                
                session_counts.append(count)
                session_lists.append(set(session_ids))
                
                print(f"Request {i+1:2d}: {count} sessions - {session_ids}")
            else:
                print(f"Request {i+1:2d}: ERROR {response.status_code}")
                session_counts.append(-1)
                session_lists.append(set())
            
            time.sleep(0.1)  # Small delay between requests
        
        # Analyze results
        unique_counts = set(session_counts)
        unique_session_sets = set(frozenset(s) for s in session_lists)
        
        print(f"\n📊 Analysis:")
        print(f"Unique counts: {unique_counts}")
        print(f"Unique session sets: {len(unique_session_sets)}")
        
        if len(unique_counts) == 1 and len(unique_session_sets) == 1:
            print("✅ Perfect consistency!")
            return {"consistent": True, "counts": session_counts}
        else:
            print("❌ Inconsistency detected!")
            
            # Show which sessions appear/disappear
            all_sessions = set()
            for session_set in session_lists:
                all_sessions.update(session_set)
            
            print(f"\nAll sessions seen: {len(all_sessions)}")
            for session_id in all_sessions:
                appearances = sum(1 for s in session_lists if session_id in s)
                if appearances != len(session_lists):
                    print(f"  {session_id}: appeared in {appearances}/{len(session_lists)} requests")
            
            return {"consistent": False, "counts": session_counts, "session_lists": session_lists}
    
    def test_delete_operation(self, session_id: str = None) -> bool:
        """Test session deletion and verify it's properly removed."""
        if not session_id:
            # Create a test session first
            print("🔍 Creating test session for deletion...")
            response = self.make_request("POST", "/api/v1/chat/sessions",
                                       headers={"Content-Type": "application/json"},
                                       json={"context": "Test session for deletion"})
            if response.status_code != 201:
                print(f"❌ Failed to create test session: {response.status_code}")
                return False
            
            session_id = response.json().get("session_id")
            print(f"✅ Created test session: {session_id}")
        
        # Verify session exists in multiple requests
        print(f"\n🔍 Verifying session {session_id} exists across workers...")
        found_count = 0
        for i in range(5):
            response = self.make_request("GET", "/api/v1/chat/sessions")
            if response.status_code == 200:
                session_ids = [s["session_id"] for s in response.json().get("sessions", [])]
                if session_id in session_ids:
                    found_count += 1
                    print(f"  Request {i+1}: ✅ Found")
                else:
                    print(f"  Request {i+1}: ❌ NOT found")
            time.sleep(0.2)
        
        if found_count == 0:
            print(f"❌ Session {session_id} not found in any request before deletion")
            return False
        elif found_count < 5:
            print(f"⚠️  Session {session_id} only found in {found_count}/5 requests before deletion")
        else:
            print(f"✅ Session consistently found in all requests")
        
        # Delete the session
        print(f"\n🗑️  Deleting session {session_id}...")
        response = self.make_request("DELETE", f"/api/v1/chat/sessions/{session_id}")
        if response.status_code not in [200, 204]:
            print(f"❌ Delete failed: {response.status_code} - {response.text}")
            return False
        
        print("✅ Delete request completed")
        
        # Wait and verify deletion across multiple workers
        print(f"\n🔍 Verifying session {session_id} is deleted across all workers...")
        time.sleep(1.0)  # Give time for deletion to propagate
        
        found_after_delete = 0
        for i in range(10):  # Test more requests to catch inconsistencies
            response = self.make_request("GET", "/api/v1/chat/sessions")
            if response.status_code == 200:
                session_ids = [s["session_id"] for s in response.json().get("sessions", [])]
                if session_id in session_ids:
                    found_after_delete += 1
                    print(f"  Request {i+1}: ❌ STILL EXISTS")
                else:
                    print(f"  Request {i+1}: ✅ Properly deleted")
            time.sleep(0.2)
        
        if found_after_delete == 0:
            print(f"✅ Session properly deleted from all workers")
            return True
        else:
            print(f"❌ Session still exists in {found_after_delete}/10 requests after deletion!")
            return False
    
    def check_json_file_sync(self):
        """Check if JSON file matches API responses."""
        print("🔍 Checking JSON file synchronization...")
        
        # Get sessions from API
        response = self.make_request("GET", "/api/v1/chat/sessions")
        if response.status_code != 200:
            print("❌ Failed to get sessions from API")
            return False
        
        api_sessions = set(s["session_id"] for s in response.json().get("sessions", []))
        print(f"API reports: {len(api_sessions)} sessions")
        
        # Get sessions from JSON file
        try:
            with open("/home/shobbak/AutomatingLetter/data/chat_sessions.json", "r") as f:
                file_data = json.load(f)
                file_sessions = set(file_data.keys())
                print(f"JSON file has: {len(file_sessions)} sessions")
                
                # Compare
                if api_sessions == file_sessions:
                    print("✅ API and JSON file are in sync")
                    return True
                else:
                    print("❌ API and JSON file are NOT in sync!")
                    print(f"Only in API: {api_sessions - file_sessions}")
                    print(f"Only in file: {file_sessions - api_sessions}")
                    return False
        except Exception as e:
            print(f"❌ Failed to read JSON file: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run comprehensive multi-worker tests."""
        print("🚀 Starting Multi-Worker Consistency Test")
        print("=" * 60)
        
        # Test 1: Basic consistency
        print("\n=== TEST 1: Session Listing Consistency ===")
        result1 = self.test_session_consistency(20)
        
        # Test 2: JSON file sync
        print("\n=== TEST 2: JSON File Synchronization ===")
        result2 = self.check_json_file_sync()
        
        # Test 3: Delete operation
        print("\n=== TEST 3: Delete Operation Consistency ===")
        result3 = self.test_delete_operation()
        
        # Final consistency check
        print("\n=== TEST 4: Final Consistency Check ===")
        result4 = self.test_session_consistency(15)
        
        # Summary
        print("\n" + "=" * 60)
        print("🏁 Multi-Worker Test Summary:")
        print(f"  Session Consistency: {'✅ PASS' if result1['consistent'] else '❌ FAIL'}")
        print(f"  JSON File Sync:      {'✅ PASS' if result2 else '❌ FAIL'}")
        print(f"  Delete Consistency:  {'✅ PASS' if result3 else '❌ FAIL'}")
        print(f"  Final Consistency:   {'✅ PASS' if result4['consistent'] else '❌ FAIL'}")
        
        all_passed = result1['consistent'] and result2 and result3 and result4['consistent']
        
        if all_passed:
            print("\n🎉 ALL TESTS PASSED! Multi-worker system is consistent.")
        else:
            print("\n💥 SOME TESTS FAILED! Multi-worker sync issues detected.")
        
        return all_passed


if __name__ == "__main__":
    test = MultiWorkerTest()
    success = test.run_comprehensive_test()
    sys.exit(0 if success else 1)
