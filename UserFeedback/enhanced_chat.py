"""
Enhanced Interactive Chat Module with Memory Buffer and Session Management
This module provides chat functionality with conversation memory and automatic cleanup.
"""

import os
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from uuid import uuid4
import json

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ChatSession:
    """Represents a chat session with memory and metadata."""
    session_id: str
    memory: ConversationBufferWindowMemory
    created_at: datetime
    last_activity: datetime
    original_letter: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()
    
    def add_to_history(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to conversation history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        self.conversation_history.append(entry)
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired based on inactivity."""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)


class InteractiveChatManager:
    """
    Manages interactive chat sessions with memory buffer and automatic cleanup.
    Provides letter editing capabilities with conversation context.
    """
    
    def __init__(self, 
                 model_name: str = "gpt-4.1",
                 temperature: float = 0.2,
                 memory_window: int = 10,
                 session_timeout_minutes: int = 30,
                 cleanup_interval_minutes: int = 5):
        """
        Initialize the chat manager.
        
        Args:
            model_name: OpenAI model to use
            temperature: Model temperature
            memory_window: Number of recent messages to keep in memory
            session_timeout_minutes: Minutes before session expires
            cleanup_interval_minutes: Minutes between cleanup runs
        """
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        
        self.chat = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.memory_window = memory_window
        self.session_timeout_minutes = session_timeout_minutes
        self.cleanup_interval_minutes = cleanup_interval_minutes
        
        # Thread-safe session storage
        self.sessions: Dict[str, ChatSession] = {}
        self.sessions_lock = threading.RLock()
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        # Initialize prompt templates
        self._init_prompt_templates()
    
    def _init_prompt_templates(self):
        """Initialize prompt templates for different chat scenarios."""
        
        # Main letter editing prompt (aligned with AI generator instructions)
        self.edit_prompt = PromptTemplate(
            input_variables=["letter", "feedback", "conversation_context"],
            template="""أنت كاتب خطابات محترف ومساعد ذكي لشركة `نت زيرو`. مهمتك هي تعديل الخطاب بناءً على ملاحظات المستخدم مع الالتزام الصارم بجميع التعليمات المحددة أدناه.

# سياق المحادثة السابقة:
{conversation_context}

# تعليمات التعديل الصارمة:
1. ✅ **عدّل الخطاب فقط بناءً على الملاحظات المحددة.** لا تعيد كتابة أو تعديل أي جزء غير مذكور في الملاحظات.
2. ✅ **حافظ على نفس بنية وتنسيق الخطاب الأصلي.**
3. ✅ **حافظ على نفس الأسلوب واللغة العربية الفصحى.**
4. ✅ **احتفظ بجميع المعلومات التي لم تُذكر في الملاحظات.**
5. ⛔ **لا تضف عبارات تهنئة أو مناسبات أو ألقاب بروتوكولية إلا إذا طُلبت صراحة.**
6. ⛔ **تجنب العبارات المبالغ فيها مثل "نتشرف بمخاطبتكم" أو "يطيب لنا".**
7. ✅ **استخدم عبارات مباشرة ومهنية بحسب السياق.**
8. ✅ **في الخطابات الرسمية، أضف ثلاث فواصل (،،،) بعد عبارة الخاتمة.**
9. ✅ **في خطابات التهنئة، اجعل عبارة التهنئة في سطر مستقل.**
10. ⛔ **لا تضف أو تستنتج أي تواريخ أو مواعيد إلا إذا ذُكرت صراحة.**

# ملاحظات مهمة حول الإخراج:
- أرجع الخطاب المعدل فقط، بدون أي كلمات مقدمة أو تعليقات
- لا تضف جملاً مثل "الخطاب بعد التعديل" أو "فيما يلي الخطاب المعدل"
- لا تضف أي تعليقات ختامية أو توضيحات بعد الخطاب
- أرسل نص الخطاب فقط بدون أي إضافات

الخطاب الأصلي:
{letter}

الملاحظات المطلوب تطبيقها:
{feedback}
"""
        )
        
        # General chat prompt for questions and discussions
        self.chat_prompt = PromptTemplate(
            input_variables=["question", "conversation_context", "letter_context"],
            template="""أنت مساعد ذكي متخصص في كتابة الخطابات الرسمية العربية لشركة `نت زيرو`.

# سياق المحادثة:
{conversation_context}

# سياق الخطاب الحالي:
{letter_context}

# تعليمات الإجابة:
1. أجب على السؤال بوضوح ومهنية
2. اربط إجابتك بسياق الخطاب عند الإمكان
3. قدم اقتراحات عملية ومفيدة
4. استخدم اللغة العربية الفصحى
5. كن مختصراً ومفيداً

السؤال:
{question}
"""
        )
    
    def _start_cleanup_thread(self):
        """Start background thread for session cleanup."""
        def cleanup_sessions():
            while True:
                try:
                    time.sleep(self.cleanup_interval_minutes * 60)
                    self._cleanup_expired_sessions()
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_sessions, daemon=True)
        cleanup_thread.start()
        logger.info("Session cleanup thread started")
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions."""
        with self.sessions_lock:
            expired_sessions = [
                session_id for session_id, session in self.sessions.items()
                if session.is_expired(self.session_timeout_minutes)
            ]
            
            for session_id in expired_sessions:
                logger.info(f"Cleaning up expired session: {session_id}")
                del self.sessions[session_id]
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def create_session(self, original_letter: Optional[str] = None) -> str:
        """
        Create a new chat session.
        
        Args:
            original_letter: The original letter for editing context
            
        Returns:
            session_id: Unique session identifier
        """
        session_id = str(uuid4())
        
        memory = ConversationBufferWindowMemory(
            k=self.memory_window,
            return_messages=True
        )
        
        session = ChatSession(
            session_id=session_id,
            memory=memory,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            original_letter=original_letter
        )
        
        with self.sessions_lock:
            self.sessions[session_id] = session
        
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get session by ID, return None if not found or expired."""
        with self.sessions_lock:
            session = self.sessions.get(session_id)
            if session and not session.is_expired(self.session_timeout_minutes):
                session.update_activity()
                return session
            elif session:
                # Remove expired session
                del self.sessions[session_id]
                logger.info(f"Removed expired session: {session_id}")
        return None
    
    def edit_letter(self, session_id: str, current_letter: str, feedback: str) -> Dict[str, Any]:
        """
        Edit a letter based on feedback within a session context.
        
        Args:
            session_id: Session identifier
            current_letter: Current version of the letter
            feedback: User feedback for editing
            
        Returns:
            Dict containing edited letter and session info
        """
        session = self.get_session(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Session not found or expired",
                "session_expired": True
            }
        
        try:
            # Get conversation context
            conversation_context = self._get_conversation_context(session)
            
            # Generate edited letter
            prompt_input = {
                "letter": current_letter,
                "feedback": feedback,
                "conversation_context": conversation_context
            }
            
            response = self.chat.invoke([
                self.edit_prompt.format(**prompt_input)
            ])
            
            edited_letter = response.content.strip()
            
            # Add to session history
            session.add_to_history("user", f"تعديل: {feedback}")
            session.add_to_history("assistant", "تم تعديل الخطاب", {"edit_applied": True})
            
            # Add to memory
            session.memory.chat_memory.add_user_message(f"تعديل: {feedback}")
            session.memory.chat_memory.add_ai_message("تم تعديل الخطاب بناءً على ملاحظاتك")
            
            logger.info(f"Letter edited in session: {session_id}")
            
            return {
                "status": "success",
                "edited_letter": edited_letter,
                "session_id": session_id,
                "conversation_length": len(session.conversation_history)
            }
            
        except Exception as e:
            logger.error(f"Error editing letter in session {session_id}: {e}")
            return {
                "status": "error",
                "message": f"Error editing letter: {str(e)}"
            }
    
    def chat_about_letter(self, session_id: str, question: str, current_letter: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle general questions about the letter or writing.
        
        Args:
            session_id: Session identifier
            question: User's question
            current_letter: Current letter context
            
        Returns:
            Dict containing response and session info
        """
        session = self.get_session(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Session not found or expired",
                "session_expired": True
            }
        
        try:
            # Get conversation context
            conversation_context = self._get_conversation_context(session)
            letter_context = current_letter or session.original_letter or "لا يوجد خطاب حالي"
            
            prompt_input = {
                "question": question,
                "conversation_context": conversation_context,
                "letter_context": letter_context[:1000]  # Limit context length
            }
            
            response = self.chat.invoke([
                self.chat_prompt.format(**prompt_input)
            ])
            
            answer = response.content.strip()
            
            # Add to session history
            session.add_to_history("user", question)
            session.add_to_history("assistant", answer)
            
            # Add to memory
            session.memory.chat_memory.add_user_message(question)
            session.memory.chat_memory.add_ai_message(answer)
            
            logger.info(f"Question answered in session: {session_id}")
            
            return {
                "status": "success",
                "answer": answer,
                "session_id": session_id,
                "conversation_length": len(session.conversation_history)
            }
            
        except Exception as e:
            logger.error(f"Error in chat session {session_id}: {e}")
            return {
                "status": "error",
                "message": f"Error processing question: {str(e)}"
            }
    
    def _get_conversation_context(self, session: ChatSession) -> str:
        """Get formatted conversation context for prompts."""
        if not session.conversation_history:
            return "لا توجد محادثة سابقة"
        
        # Get last few messages for context
        recent_messages = session.conversation_history[-5:]
        context_parts = []
        
        for msg in recent_messages:
            role = "المستخدم" if msg["role"] == "user" else "المساعد"
            context_parts.append(f"{role}: {msg['content'][:200]}")  # Limit message length
        
        return "\n".join(context_parts)
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a session."""
        session = self.get_session(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Session not found or expired"
            }
        
        return {
            "status": "success",
            "session_id": session_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "conversation_length": len(session.conversation_history),
            "has_original_letter": session.original_letter is not None
        }
    
    def clear_session(self, session_id: str) -> Dict[str, Any]:
        """Manually clear a session."""
        with self.sessions_lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Manually cleared session: {session_id}")
                return {"status": "success", "message": "Session cleared"}
            else:
                return {"status": "error", "message": "Session not found"}
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        with self.sessions_lock:
            return len(self.sessions)


# Global instance for backward compatibility and easy access
chat_manager = InteractiveChatManager()

# Backward compatibility function
def edit_letter_based_on_feedback(letter: str, feedback: str) -> str:
    """
    Legacy function for backward compatibility.
    Creates a temporary session for single-use editing.
    """
    session_id = chat_manager.create_session(original_letter=letter)
    result = chat_manager.edit_letter(session_id, letter, feedback)
    
    # Clean up temporary session
    chat_manager.clear_session(session_id)
    
    if result["status"] == "success":
        return result["edited_letter"]
    else:
        raise Exception(result["message"])
