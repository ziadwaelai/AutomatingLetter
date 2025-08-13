"""
Complete AutomatingLetter Project Test Suite
===========================================

This module provides comprehensive testing for all components of the AutomatingLetter system.
Tests include unit tests, integration tests, and end-to-end workflow validation.
"""

import unittest
import requests
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

class AutomatingLetterTestSuite(unittest.TestCase):
    """Complete test suite for AutomatingLetter application."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment and configuration."""
        cls.base_url = "http://localhost:5000"
        cls.session_id = None
        cls.letter_id = None
        cls.pdf_id = None
        cls.test_user_id = f"test_user_{int(time.time())}"
        
        # Test data
        cls.test_message = "أريد كتابة خطاب شكر للمدير العام بأسلوب رسمي ومختصر"
        cls.test_letter_data = {
            "letter_type": "شكر",
            "recipient": "المدير العام", 
            "sender": "أحمد محمد الاختبار",
            "content_requirements": "خطاب شكر رسمي للمدير العام على الدعم المستمر",
            "style_preferences": "رسمي ومختصر",
            "additional_notes": "يرجى إضافة دعوة للتواصل في النهاية"
        }
        
        print(f"\n🧪 Starting AutomatingLetter Test Suite")
        print(f"📍 Base URL: {cls.base_url}")
        print(f"👤 Test User: {cls.test_user_id}")
        print("=" * 60)
    
    def setUp(self):
        """Set up for each test method."""
        self.start_time = time.time()
    
    def tearDown(self):
        """Clean up after each test method."""
        elapsed_time = time.time() - self.start_time
        print(f"   ⏱️  Test completed in {elapsed_time:.3f}s")
    
    # ========================================
    # UTILITY METHODS
    # ========================================
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     expected_status: int = 200) -> Dict[str, Any]:
        """Make HTTP request and validate response."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Validate status code
            self.assertEqual(response.status_code, expected_status,
                           f"Expected status {expected_status}, got {response.status_code}")
            
            # Parse JSON response
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                return {"raw_response": response.content}
                
        except requests.exceptions.RequestException as e:
            self.fail(f"Request failed: {e}")
    
    def _validate_success_response(self, response: Dict[str, Any], 
                                  required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Validate success response structure."""
        self.assertIn("status", response)
        self.assertEqual(response["status"], "success")
        self.assertIn("data", response)
        
        if required_fields:
            for field in required_fields:
                self.assertIn(field, response["data"], f"Missing required field: {field}")
        
        return response["data"]
    
    def _validate_error_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate error response structure."""
        self.assertIn("status", response)
        self.assertEqual(response["status"], "error")
        self.assertIn("error", response)
        self.assertIn("type", response["error"])
        self.assertIn("message", response["error"])
        
        return response["error"]
    
    # ========================================
    # CHAT SERVICE TESTS
    # ========================================
    
    def test_01_create_chat_session(self):
        """Test creating a new chat session."""
        print("\n🔄 Testing: Create Chat Session")
        
        data = {
            "user_id": self.test_user_id,
            "session_type": "letter_generation"
        }
        
        response = self._make_request("POST", "/api/v1/chat/session", data)
        data = self._validate_success_response(response, 
            ["session_id", "user_id", "session_type", "created_at", "message_count"])
        
        # Store session ID for subsequent tests
        AutomatingLetterTestSuite.session_id = data["session_id"]
        
        # Validate response data
        self.assertEqual(data["user_id"], self.test_user_id)
        self.assertEqual(data["session_type"], "letter_generation")
        self.assertEqual(data["message_count"], 0)
        self.assertIsInstance(data["session_id"], str)
        self.assertTrue(data["session_id"].startswith("session_"))
        
        print(f"   ✅ Session created: {data['session_id']}")
    
    def test_02_send_chat_message(self):
        """Test sending a message to chat session."""
        print("\n💬 Testing: Send Chat Message")
        
        self.assertIsNotNone(self.session_id, "Session ID not available from previous test")
        
        data = {
            "session_id": self.session_id,
            "message": self.test_message,
            "context": "formal_letter"
        }
        
        response = self._make_request("POST", "/api/v1/chat/message", data)
        response_data = self._validate_success_response(response,
            ["message_id", "session_id", "response", "timestamp"])
        
        # Validate response data
        self.assertEqual(response_data["session_id"], self.session_id)
        self.assertIsInstance(response_data["response"], str)
        self.assertTrue(len(response_data["response"]) > 0)
        self.assertIsInstance(response_data["message_id"], str)
        
        print(f"   ✅ Message sent and processed")
        print(f"   📝 Response preview: {response_data['response'][:50]}...")
    
    def test_03_get_all_sessions(self):
        """Test retrieving all chat sessions."""
        print("\n📋 Testing: Get All Sessions")
        
        response = self._make_request("GET", "/api/v1/chat/sessions")
        data = self._validate_success_response(response, ["sessions", "total_sessions"])
        
        # Validate session list
        self.assertIsInstance(data["sessions"], list)
        self.assertGreaterEqual(data["total_sessions"], 1)
        
        # Find our test session
        test_session = None
        for session in data["sessions"]:
            if session["session_id"] == self.session_id:
                test_session = session
                break
        
        self.assertIsNotNone(test_session, "Test session not found in session list")
        self.assertEqual(test_session["user_id"], self.test_user_id)
        
        print(f"   ✅ Found {data['total_sessions']} sessions including test session")
    
    # ========================================
    # MEMORY SERVICE TESTS
    # ========================================
    
    def test_04_get_memory_stats(self):
        """Test retrieving memory service statistics."""
        print("\n🧠 Testing: Memory Statistics")
        
        response = self._make_request("GET", "/api/v1/chat/memory/stats")
        data = self._validate_success_response(response,
            ["total_instructions", "active_instructions", "instruction_types"])
        
        # Validate memory stats
        self.assertIsInstance(data["total_instructions"], int)
        self.assertIsInstance(data["active_instructions"], int)
        self.assertIsInstance(data["instruction_types"], dict)
        self.assertGreaterEqual(data["total_instructions"], 0)
        
        print(f"   ✅ Memory stats: {data['total_instructions']} total instructions")
        print(f"   📊 Instruction types: {data['instruction_types']}")
    
    def test_05_get_formatted_instructions(self):
        """Test retrieving formatted memory instructions."""
        print("\n📝 Testing: Formatted Instructions")
        
        response = self._make_request("GET", "/api/v1/chat/memory/instructions")
        data = self._validate_success_response(response, ["instructions"])
        
        # Validate instructions format
        self.assertIsInstance(data["instructions"], str)
        
        if len(data["instructions"]) > 0:
            # Should contain Arabic text
            self.assertTrue(any(ord(char) > 127 for char in data["instructions"]),
                          "Instructions should contain Arabic text")
            print(f"   ✅ Retrieved formatted instructions ({len(data['instructions'])} chars)")
        else:
            print(f"   ⚠️  No instructions available yet")
    
    # ========================================
    # LETTER GENERATION TESTS
    # ========================================
    
    def test_06_generate_letter(self):
        """Test generating a new letter."""
        print("\n📄 Testing: Letter Generation")
        
        self.assertIsNotNone(self.session_id, "Session ID not available")
        
        data = {
            "session_id": self.session_id,
            **self.test_letter_data
        }
        
        response = self._make_request("POST", "/api/v1/letters/generate", data)
        response_data = self._validate_success_response(response,
            ["letter_id", "session_id", "letter_content", "metadata"])
        
        # Store letter ID for subsequent tests
        AutomatingLetterTestSuite.letter_id = response_data["letter_id"]
        
        # Validate letter data
        self.assertEqual(response_data["session_id"], self.session_id)
        self.assertIsInstance(response_data["letter_content"], str)
        self.assertTrue(len(response_data["letter_content"]) > 100,
                       "Letter content should be substantial")
        
        # Validate metadata
        metadata = response_data["metadata"]
        self.assertEqual(metadata["letter_type"], self.test_letter_data["letter_type"])
        self.assertEqual(metadata["recipient"], self.test_letter_data["recipient"])
        self.assertEqual(metadata["sender"], self.test_letter_data["sender"])
        self.assertIn("word_count", metadata)
        self.assertGreater(metadata["word_count"], 0)
        
        # Check for Arabic content
        self.assertTrue(any(ord(char) > 127 for char in response_data["letter_content"]),
                       "Letter should contain Arabic text")
        
        print(f"   ✅ Letter generated: {response_data['letter_id']}")
        print(f"   📊 Word count: {metadata['word_count']}")
        print(f"   📝 Content preview: {response_data['letter_content'][:50]}...")
    
    def test_07_get_letter_content(self):
        """Test retrieving letter content."""
        print("\n📖 Testing: Get Letter Content")
        
        self.assertIsNotNone(self.letter_id, "Letter ID not available from previous test")
        
        response = self._make_request("GET", f"/api/v1/letters/{self.letter_id}")
        data = self._validate_success_response(response,
            ["letter_id", "letter_content", "metadata"])
        
        # Validate retrieved data
        self.assertEqual(data["letter_id"], self.letter_id)
        self.assertIsInstance(data["letter_content"], str)
        self.assertTrue(len(data["letter_content"]) > 0)
        
        print(f"   ✅ Letter content retrieved successfully")
    
    def test_08_update_letter_content(self):
        """Test updating letter content."""
        print("\n✏️  Testing: Update Letter Content")
        
        self.assertIsNotNone(self.letter_id, "Letter ID not available")
        
        updated_content = (
            "بسم الله الرحمن الرحيم\n\n"
            "سعادة المدير العام المحترم\n\n"
            "السلام عليكم ورحمة الله وبركاته\n\n"
            "أتقدم إليكم بجزيل الشكر والامتنان على الدعم المتواصل والتوجيه السديد "
            "الذي تقدمونه لنا في جميع مراحل العمل.\n\n"
            "هذا المحتوى المحدث للاختبار.\n\n"
            "وتفضلوا بقبول فائق الاحترام والتقدير\n\n"
            "أحمد محمد الاختبار"
        )
        
        data = {
            "letter_content": updated_content,
            "update_reason": "تحديث المحتوى للاختبار"
        }
        
        response = self._make_request("PUT", f"/api/v1/letters/{self.letter_id}", data)
        response_data = self._validate_success_response(response,
            ["letter_id", "updated", "word_count", "updated_at"])
        
        # Validate update response
        self.assertEqual(response_data["letter_id"], self.letter_id)
        self.assertTrue(response_data["updated"])
        self.assertGreater(response_data["word_count"], 0)
        
        print(f"   ✅ Letter updated successfully")
        print(f"   📊 New word count: {response_data['word_count']}")
    
    # ========================================
    # PDF CONVERSION TESTS
    # ========================================
    
    def test_09_convert_letter_to_pdf(self):
        """Test converting letter to PDF."""
        print("\n📄 Testing: PDF Conversion")
        
        self.assertIsNotNone(self.letter_id, "Letter ID not available")
        
        data = {
            "letter_id": self.letter_id,
            "pdf_options": {
                "page_size": "A4",
                "margin": "normal",
                "font_size": "12pt",
                "include_header": True,
                "include_footer": False
            }
        }
        
        response = self._make_request("POST", "/api/v1/pdf/convert", data)
        response_data = self._validate_success_response(response,
            ["pdf_id", "letter_id", "pdf_url", "file_size", "created_at"])
        
        # Store PDF ID for subsequent tests
        AutomatingLetterTestSuite.pdf_id = response_data["pdf_id"]
        
        # Validate PDF data
        self.assertEqual(response_data["letter_id"], self.letter_id)
        self.assertIsInstance(response_data["file_size"], int)
        self.assertGreater(response_data["file_size"], 1000,
                          "PDF file should be substantial")
        self.assertTrue(response_data["pdf_url"].startswith("/api/v1/pdf/"))
        
        print(f"   ✅ PDF created: {response_data['pdf_id']}")
        print(f"   📊 File size: {response_data['file_size']} bytes")
        if "pages" in response_data:
            print(f"   📄 Pages: {response_data['pages']}")
    
    def test_10_download_pdf(self):
        """Test downloading PDF file."""
        print("\n⬇️  Testing: PDF Download")
        
        self.assertIsNotNone(self.pdf_id, "PDF ID not available from previous test")
        
        try:
            url = f"{self.base_url}/api/v1/pdf/{self.pdf_id}"
            response = requests.get(url, timeout=30)
            
            # Validate PDF download
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.headers.get('content-type', '').startswith('application/pdf'))
            self.assertGreater(len(response.content), 1000,
                              "Downloaded PDF should be substantial")
            
            print(f"   ✅ PDF downloaded successfully")
            print(f"   📊 Downloaded size: {len(response.content)} bytes")
            
        except requests.exceptions.RequestException as e:
            self.fail(f"PDF download failed: {e}")
    
    # ========================================
    # ARCHIVE MANAGEMENT TESTS
    # ========================================
    
    def test_11_list_archived_letters(self):
        """Test listing archived letters."""
        print("\n📚 Testing: Archive Listing")
        
        response = self._make_request("GET", "/api/v1/archive/letters?limit=10&offset=0")
        data = self._validate_success_response(response,
            ["letters", "total_letters", "limit", "offset"])
        
        # Validate archive data
        self.assertIsInstance(data["letters"], list)
        self.assertIsInstance(data["total_letters"], int)
        self.assertEqual(data["limit"], 10)
        self.assertEqual(data["offset"], 0)
        
        # Find our test letter
        test_letter = None
        for letter in data["letters"]:
            if letter["letter_id"] == self.letter_id:
                test_letter = letter
                break
        
        if test_letter:
            self.assertEqual(test_letter["letter_type"], self.test_letter_data["letter_type"])
            self.assertEqual(test_letter["recipient"], self.test_letter_data["recipient"])
            print(f"   ✅ Found test letter in archive")
        
        print(f"   📊 Total archived letters: {data['total_letters']}")
    
    def test_12_get_archived_letter(self):
        """Test retrieving specific archived letter."""
        print("\n📄 Testing: Archived Letter Retrieval")
        
        self.assertIsNotNone(self.letter_id, "Letter ID not available")
        
        response = self._make_request("GET", f"/api/v1/archive/letters/{self.letter_id}")
        data = self._validate_success_response(response,
            ["letter_id", "letter_content", "metadata"])
        
        # Validate archived letter data
        self.assertEqual(data["letter_id"], self.letter_id)
        self.assertIsInstance(data["letter_content"], str)
        self.assertTrue(len(data["letter_content"]) > 0)
        
        # Check metadata
        metadata = data["metadata"]
        self.assertEqual(metadata["letter_type"], self.test_letter_data["letter_type"])
        self.assertEqual(metadata["recipient"], self.test_letter_data["recipient"])
        
        print(f"   ✅ Archived letter retrieved successfully")
    
    # ========================================
    # ERROR HANDLING TESTS
    # ========================================
    
    def test_13_invalid_session_id(self):
        """Test handling of invalid session ID."""
        print("\n❌ Testing: Invalid Session ID")
        
        data = {
            "session_id": "invalid_session_12345",
            "message": "Test message"
        }
        
        response = self._make_request("POST", "/api/v1/chat/message", data, 
                                    expected_status=400)
        error = self._validate_error_response(response)
        
        self.assertIn("ValidationError", error["type"])
        print(f"   ✅ Invalid session ID properly rejected")
    
    def test_14_missing_required_fields(self):
        """Test handling of missing required fields."""
        print("\n❌ Testing: Missing Required Fields")
        
        data = {
            "session_id": self.session_id if self.session_id else "test_session"
            # Missing required fields for letter generation
        }
        
        response = self._make_request("POST", "/api/v1/letters/generate", data,
                                    expected_status=400)
        error = self._validate_error_response(response)
        
        self.assertIn("ValidationError", error["type"])
        print(f"   ✅ Missing fields properly rejected")
    
    def test_15_nonexistent_letter(self):
        """Test handling of non-existent letter ID."""
        print("\n❌ Testing: Non-existent Letter")
        
        response = self._make_request("GET", "/api/v1/letters/nonexistent_letter_123",
                                    expected_status=404)
        error = self._validate_error_response(response)
        
        self.assertIn("NotFound", error["type"])
        print(f"   ✅ Non-existent letter properly handled")
    
    # ========================================
    # PERFORMANCE TESTS
    # ========================================
    
    def test_16_response_time_performance(self):
        """Test API response time performance."""
        print("\n⚡ Testing: Response Time Performance")
        
        endpoints_to_test = [
            ("GET", "/api/v1/chat/memory/stats"),
            ("GET", "/api/v1/archive/letters"),
            ("GET", "/api/v1/chat/sessions")
        ]
        
        for method, endpoint in endpoints_to_test:
            start_time = time.time()
            response = self._make_request(method, endpoint)
            elapsed_time = time.time() - start_time
            
            # Performance assertion: most endpoints should respond within 2 seconds
            self.assertLess(elapsed_time, 2.0,
                          f"Endpoint {endpoint} took {elapsed_time:.3f}s (>2s limit)")
            
            print(f"   ✅ {method} {endpoint}: {elapsed_time:.3f}s")
    
    def test_17_memory_service_performance(self):
        """Test memory service loading performance."""
        print("\n🧠 Testing: Memory Service Performance")
        
        response = self._make_request("GET", "/api/v1/chat/memory/stats")
        data = self._validate_success_response(response)
        
        if "memory_loading_time" in data:
            loading_time = data["memory_loading_time"]
            # Memory service should load within 5 seconds
            self.assertLess(loading_time, 5.0,
                          f"Memory loading took {loading_time:.3f}s (>5s limit)")
            print(f"   ✅ Memory loading time: {loading_time:.3f}s")
        else:
            print(f"   ⚠️  Memory loading time not reported")
    
    # ========================================
    # CLEANUP TESTS
    # ========================================
    
    def test_18_cleanup_test_data(self):
        """Clean up test data (optional, depending on requirements)."""
        print("\n🧹 Testing: Cleanup Test Data")
        
        # Note: In a production environment, you might want to keep test data
        # or have a separate cleanup process. This test demonstrates cleanup capability.
        
        if self.letter_id:
            try:
                response = self._make_request("DELETE", f"/api/v1/archive/letters/{self.letter_id}")
                data = self._validate_success_response(response, ["letter_id", "deleted"])
                self.assertTrue(data["deleted"])
                print(f"   ✅ Test letter deleted: {self.letter_id}")
            except AssertionError:
                # Deletion might not be implemented or allowed
                print(f"   ⚠️  Letter deletion not available or failed")
        
        print(f"   ✅ Cleanup completed")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        print("\n" + "=" * 60)
        print("🎉 AutomatingLetter Test Suite Completed!")
        print(f"📊 Test Summary:")
        print(f"   👤 Test User: {cls.test_user_id}")
        if cls.session_id:
            print(f"   🔄 Session: {cls.session_id}")
        if cls.letter_id:
            print(f"   📄 Letter: {cls.letter_id}")
        if cls.pdf_id:
            print(f"   📄 PDF: {cls.pdf_id}")
        print("=" * 60)


def run_complete_test_suite():
    """Run the complete test suite with detailed reporting."""
    print("\n🚀 AutomatingLetter Complete Test Suite")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        print("✅ Server is running and accessible")
    except requests.exceptions.RequestException:
        print("❌ Server is not running. Please start the application first:")
        print("   python app.py")
        return False
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(AutomatingLetterTestSuite)
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    
    # Run tests
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"   {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"   {test}: {traceback.split('Exception:')[-1].strip()}")
    
    if not result.failures and not result.errors:
        print("\n🎉 ALL TESTS PASSED! AutomatingLetter is working perfectly!")
    
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == "__main__":
    success = run_complete_test_suite()
    sys.exit(0 if success else 1)
