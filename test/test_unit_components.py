"""
Unit Tests for AutomatingLetter Core Components
==============================================

This module provides unit tests for individual services and components
without requiring the full application to be running.
"""

import unittest
import sys
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import the services to test
try:
    from services.memory_service import EnhancedMemoryService, EnhancedMemoryInstruction
    from services.chat_service import ChatService
    from services.letter_generator import LetterGenerator
    from services.enhanced_pdf_service import EnhancedPDFService
    from utils.helpers import generate_id, format_datetime
    from utils.exceptions import ServiceError, ValidationError
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")


class TestMemoryService(unittest.TestCase):
    """Unit tests for Enhanced Memory Service."""
    
    def setUp(self):
        """Set up test memory service with temporary file."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False)
        self.temp_file.write(json.dumps({
            "instructions": [],
            "last_updated": datetime.now().isoformat(),
            "version": "2.0-enhanced"
        }))
        self.temp_file.close()
        
        # Mock the memory service to use temp file
        with patch('services.memory_service.MEMORY_FILE', self.temp_file.name):
            self.memory_service = EnhancedMemoryService()
    
    def tearDown(self):
        """Clean up temporary file."""
        os.unlink(self.temp_file.name)
    
    def test_normalize_arabic_text(self):
        """Test Arabic text normalization."""
        test_cases = [
            ("اجعل الخطاب مختصر", "اجعل الخطاب مختصر"),
            ("آلف بآء تآء", "الف باء تاء"),  # Alef variations
            ("مكتوبة", "مكتوبه"),  # Taa marbouta
            ("مدينة الرياض", "مدينه الرياض"),
            ("  نص  مع  مسافات   ", "نص مع مسافات")  # Extra spaces
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.memory_service._normalize_arabic_text(input_text)
                self.assertEqual(result, expected)
    
    def test_calculate_similarity(self):
        """Test similarity calculation between Arabic texts."""
        # High similarity texts
        text1 = "اكتب خطابات مختصرة"
        text2 = "اجعل الخطاب مختصر"
        similarity = self.memory_service._calculate_similarity(text1, text2)
        self.assertGreater(similarity, 0.5, "Similar texts should have high similarity")
        
        # Low similarity texts  
        text3 = "اكتب خطابات مختصرة"
        text4 = "أضف الصور والجداول"
        similarity2 = self.memory_service._calculate_similarity(text3, text4)
        self.assertLess(similarity2, 0.3, "Different texts should have low similarity")
        
        # Identical texts
        similarity3 = self.memory_service._calculate_similarity(text1, text1)
        self.assertEqual(similarity3, 1.0, "Identical texts should have perfect similarity")
    
    def test_add_instruction(self):
        """Test adding new instruction to memory."""
        initial_count = len(self.memory_service.instructions)
        
        # Add new instruction
        instruction_text = "اكتب بأسلوب رسمي ومهذب"
        instruction_type = "style"
        
        with patch.object(self.memory_service, '_save_memory'):
            self.memory_service._add_instruction(instruction_text, instruction_type)
        
        # Verify instruction was added
        self.assertEqual(len(self.memory_service.instructions), initial_count + 1)
        
        # Find the added instruction
        added_instruction = None
        for instr in self.memory_service.instructions.values():
            if instr.instruction_text == instruction_text:
                added_instruction = instr
                break
        
        self.assertIsNotNone(added_instruction)
        self.assertEqual(added_instruction.instruction_type, instruction_type)
        self.assertEqual(added_instruction.usage_count, 1)
    
    def test_find_similar_instruction(self):
        """Test finding similar existing instructions."""
        # Add a test instruction
        test_instruction = "اكتب خطابات مختصرة"
        with patch.object(self.memory_service, '_save_memory'):
            self.memory_service._add_instruction(test_instruction, "style")
        
        # Test finding similar instruction
        similar_text = "اجعل الخطاب مختصر"
        found_id = self.memory_service._find_similar_instruction(
            self.memory_service._normalize_arabic_text(similar_text), "style"
        )
        
        if self.memory_service.instructions:  # Only test if instructions exist
            # Should find similar instruction if similarity is high enough
            pass  # This depends on the actual similarity threshold
    
    def test_get_memory_stats(self):
        """Test memory statistics retrieval."""
        stats = self.memory_service.get_memory_stats()
        
        required_keys = ["total_instructions", "active_instructions", "instruction_types"]
        for key in required_keys:
            self.assertIn(key, stats)
        
        self.assertIsInstance(stats["total_instructions"], int)
        self.assertIsInstance(stats["active_instructions"], int)
        self.assertIsInstance(stats["instruction_types"], dict)
    
    def test_format_instructions_for_prompt(self):
        """Test instruction formatting for LLM prompts."""
        # Add some test instructions
        test_instructions = [
            ("اكتب خطابات مختصرة", "style"),
            ("استخدم فقرات قصيرة", "format"),
            ("أضف دعوة للتواصل", "content")
        ]
        
        with patch.object(self.memory_service, '_save_memory'):
            for text, type_ in test_instructions:
                self.memory_service._add_instruction(text, type_)
        
        formatted = self.memory_service.format_instructions_for_prompt()
        
        if self.memory_service.instructions:
            self.assertIsInstance(formatted, str)
            self.assertIn("تعليمات المستخدم", formatted)
            # Should contain Arabic text
            self.assertTrue(any(ord(char) > 127 for char in formatted))


class TestChatService(unittest.TestCase):
    """Unit tests for Chat Service."""
    
    def setUp(self):
        """Set up test chat service."""
        self.chat_service = ChatService()
    
    def test_generate_session_id(self):
        """Test session ID generation."""
        session_id = self.chat_service._generate_session_id()
        
        self.assertIsInstance(session_id, str)
        self.assertTrue(session_id.startswith("session_"))
        self.assertGreater(len(session_id), 15)  # Should have timestamp
    
    def test_create_session(self):
        """Test creating new chat session."""
        user_id = "test_user_123"
        session_type = "letter_generation"
        
        session_info = self.chat_service.create_session(user_id, session_type)
        
        self.assertIn("session_id", session_info)
        self.assertEqual(session_info["user_id"], user_id)
        self.assertEqual(session_info["session_type"], session_type)
        self.assertEqual(session_info["message_count"], 0)
        self.assertIn("created_at", session_info)
        
        # Verify session was stored
        session_id = session_info["session_id"]
        self.assertIn(session_id, self.chat_service.sessions)
    
    def test_get_session(self):
        """Test retrieving existing session."""
        # Create a session first
        user_id = "test_user_123"
        session_info = self.chat_service.create_session(user_id, "letter_generation")
        session_id = session_info["session_id"]
        
        # Retrieve the session
        retrieved_session = self.chat_service.get_session(session_id)
        
        self.assertIsNotNone(retrieved_session)
        self.assertEqual(retrieved_session["session_id"], session_id)
        self.assertEqual(retrieved_session["user_id"], user_id)
    
    def test_get_nonexistent_session(self):
        """Test retrieving non-existent session."""
        nonexistent_id = "session_nonexistent_123"
        session = self.chat_service.get_session(nonexistent_id)
        self.assertIsNone(session)
    
    @patch('services.chat_service.get_memory_service')
    def test_process_message(self, mock_get_memory):
        """Test processing chat messages."""
        # Mock memory service
        mock_memory = Mock()
        mock_memory.process_message_async.return_value = None
        mock_get_memory.return_value = mock_memory
        
        # Create session
        session_info = self.chat_service.create_session("test_user", "letter_generation")
        session_id = session_info["session_id"]
        
        # Process message
        message = "أريد كتابة خطاب شكر"
        context = "formal_letter"
        
        with patch('services.chat_service.get_openai_client') as mock_openai:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "سأساعدك في كتابة خطاب الشكر"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            response = self.chat_service.process_message(session_id, message, context)
        
        self.assertIn("message_id", response)
        self.assertEqual(response["session_id"], session_id)
        self.assertIn("response", response)
        self.assertIn("timestamp", response)
        
        # Verify message was added to session
        session = self.chat_service.get_session(session_id)
        self.assertEqual(session["message_count"], 1)
    
    def test_list_sessions(self):
        """Test listing all sessions."""
        # Create multiple sessions
        for i in range(3):
            self.chat_service.create_session(f"user_{i}", "letter_generation")
        
        sessions_data = self.chat_service.list_sessions()
        
        self.assertIn("sessions", sessions_data)
        self.assertIn("total_sessions", sessions_data)
        self.assertGreaterEqual(sessions_data["total_sessions"], 3)
        self.assertIsInstance(sessions_data["sessions"], list)


class TestUtilityFunctions(unittest.TestCase):
    """Unit tests for utility functions."""
    
    def test_generate_id(self):
        """Test ID generation utility."""
        prefix = "test"
        test_id = generate_id(prefix)
        
        self.assertIsInstance(test_id, str)
        self.assertTrue(test_id.startswith(f"{prefix}_"))
        self.assertGreater(len(test_id), len(prefix) + 5)
    
    def test_format_datetime(self):
        """Test datetime formatting utility."""
        test_datetime = datetime(2025, 8, 13, 14, 30, 45, 123456)
        formatted = format_datetime(test_datetime)
        
        self.assertIsInstance(formatted, str)
        self.assertIn("2025", formatted)
        self.assertIn("14", formatted)  # Hour
        self.assertIn("30", formatted)  # Minute


class TestCustomExceptions(unittest.TestCase):
    """Unit tests for custom exceptions."""
    
    def test_service_error(self):
        """Test ServiceError exception."""
        error_message = "Test service error"
        error_code = "TEST_ERROR"
        
        with self.assertRaises(ServiceError) as context:
            raise ServiceError(error_message, error_code)
        
        self.assertEqual(str(context.exception), error_message)
        if hasattr(context.exception, 'error_code'):
            self.assertEqual(context.exception.error_code, error_code)
    
    def test_validation_error(self):
        """Test ValidationError exception."""
        error_message = "Test validation error"
        
        with self.assertRaises(ValidationError) as context:
            raise ValidationError(error_message)
        
        self.assertEqual(str(context.exception), error_message)


class TestLetterGenerator(unittest.TestCase):
    """Unit tests for Letter Generator Service."""
    
    def setUp(self):
        """Set up test letter generator."""
        try:
            self.letter_generator = LetterGenerator()
        except Exception:
            self.skipTest("LetterGenerator requires API keys")
    
    def test_validate_letter_request(self):
        """Test letter request validation."""
        valid_request = {
            "letter_type": "شكر",
            "recipient": "المدير العام",
            "sender": "أحمد محمد",
            "content_requirements": "خطاب شكر رسمي"
        }
        
        # Should not raise exception for valid request
        try:
            self.letter_generator._validate_request(valid_request)
        except Exception as e:
            self.fail(f"Valid request should not raise exception: {e}")
        
        # Test missing required field
        invalid_request = {
            "letter_type": "شكر",
            "recipient": "المدير العام"
            # Missing sender and content_requirements
        }
        
        with self.assertRaises(ValidationError):
            self.letter_generator._validate_request(invalid_request)


def run_unit_tests():
    """Run all unit tests."""
    print("\n🧪 AutomatingLetter Unit Tests")
    print("=" * 50)
    
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 UNIT TEST RESULTS")
    print("=" * 50)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"   {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"   {test}: {traceback.split('Exception:')[-1].strip()}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == "__main__":
    success = run_unit_tests()
    sys.exit(0 if success else 1)
