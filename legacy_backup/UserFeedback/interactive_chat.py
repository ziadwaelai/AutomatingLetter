"""
Interactive Chat Module - Legacy Version
This module provides backward compatibility for the enhanced chat system.
For new implementations, use enhanced_chat.py directly.
"""

import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

# Import the enhanced chat manager
from .enhanced_chat import chat_manager

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it in your .env file.")

# Legacy chat instance for backward compatibility
chat = ChatOpenAI(model="gpt-4.1", temperature=0.2, openai_api_key=os.getenv("OPENAI_API_KEY"))

def edit_letter_based_on_feedback(letter: str, feedback: str) -> str:
    """
    Legacy function for backward compatibility.
    This function now uses the enhanced chat manager but maintains the same interface.
    
    For new implementations, consider using the enhanced chat system with sessions.
    """
    # Create a temporary session for this edit
    session_id = chat_manager.create_session(original_letter=letter)
    
    try:
        result = chat_manager.edit_letter(session_id, letter, feedback)
        
        if result["status"] == "success":
            return result["edited_letter"]
        else:
            raise Exception(result["message"])
    
    finally:
        # Clean up the temporary session
        chat_manager.clear_session(session_id)


# Enhanced functions for direct use (optional)
def create_chat_session(original_letter: str = None) -> str:
    """Create a new chat session and return session ID."""
    return chat_manager.create_session(original_letter=original_letter)

def edit_letter_with_session(session_id: str, current_letter: str, feedback: str) -> dict:
    """Edit letter using an existing session."""
    return chat_manager.edit_letter(session_id, current_letter, feedback)

def ask_about_letter(session_id: str, question: str, current_letter: str = None) -> dict:
    """Ask a question about the letter in a session context."""
    return chat_manager.chat_about_letter(session_id, question, current_letter)

def get_session_info(session_id: str) -> dict:
    """Get information about a session."""
    return chat_manager.get_session_info(session_id)

def clear_session(session_id: str) -> dict:
    """Clear a session manually."""
    return chat_manager.clear_session(session_id)