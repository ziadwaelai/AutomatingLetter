"""
UserFeedback Module - Interactive Chat System
===========================================

This module provides enhanced interactive chat functionality for letter editing
with memory buffer, session management, and automatic cleanup.

Main Components:
- enhanced_chat.py: Core chat manager with session functionality
- interactive_chat.py: Legacy compatibility layer
- test_enhanced_chat.py: Test suite for the system
- README.md: Comprehensive documentation

Quick Start:
-----------

# For new implementations (recommended):
from UserFeedback.enhanced_chat import chat_manager

session_id = chat_manager.create_session()
result = chat_manager.edit_letter(session_id, letter, feedback)

# For backward compatibility:
from UserFeedback.interactive_chat import edit_letter_based_on_feedback

edited = edit_letter_based_on_feedback(letter, feedback)

Features:
--------
- Session-based conversations with memory
- Context-aware letter editing
- Automatic session cleanup
- Thread-safe operations
- RESTful API endpoints
- Backward compatibility

API Endpoints:
-------------
- POST /chat/session/create - Create new session
- POST /chat/edit-letter - Edit letter with session
- POST /chat/ask - Ask questions about letters
- GET /chat/session/info/{id} - Get session information
- DELETE /chat/session/clear/{id} - Clear session
- GET /chat/sessions/count - Get active sessions count
"""

from .enhanced_chat import InteractiveChatManager, chat_manager
from .interactive_chat import (
    edit_letter_based_on_feedback,
    create_chat_session,
    edit_letter_with_session,
    ask_about_letter,
    get_session_info,
    clear_session
)

__version__ = "1.0.0"
__author__ = "AutomatingLetter Team"

__all__ = [
    # Main classes
    "InteractiveChatManager",
    "chat_manager",
    
    # Legacy functions
    "edit_letter_based_on_feedback",
    
    # Enhanced functions
    "create_chat_session",
    "edit_letter_with_session", 
    "ask_about_letter",
    "get_session_info",
    "clear_session"
]
