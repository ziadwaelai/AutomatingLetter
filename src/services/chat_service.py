"""
Enhanced Chat Service
Provides session-based chat functionality with memory management for letter editing.
"""

import logging
import threading
import time
import uuid
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field, asdict
from threading import Lock

from ..config import get_config
from ..models import ChatEditResponse, ChatSessionStatus
from ..services import get_letter_service, LetterGenerationContext
from ..utils import (
    Timer,
    ErrorContext,
    service_error_handler
)

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """Represents a chat message in a session."""
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )

@dataclass
class LetterVersion:
    """Represents a version of a letter during editing."""
    version_id: str
    content: str
    timestamp: datetime
    change_summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version_id": self.version_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "change_summary": self.change_summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LetterVersion':
        """Create from dictionary."""
        return cls(
            version_id=data["version_id"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            change_summary=data.get("change_summary", "")
        )

@dataclass
class ChatSession:
    """Represents a chat session with memory and letter versions."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    context: str
    messages: List[ChatMessage] = field(default_factory=list)
    letter_versions: List[LetterVersion] = field(default_factory=list)
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "context": self.context,
            "messages": [msg.to_dict() for msg in self.messages],
            "letter_versions": [ver.to_dict() for ver in self.letter_versions],
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            context=data["context"],
            messages=[ChatMessage.from_dict(msg) for msg in data.get("messages", [])],
            letter_versions=[LetterVersion.from_dict(ver) for ver in data.get("letter_versions", [])],
            is_active=data.get("is_active", True)
        )

class ChatService:
    """Service for managing chat sessions and letter editing."""
    
    def __init__(self):
        """Initialize chat service."""
        self.config = get_config()
        
        # Session management with file persistence
        self.sessions: Dict[str, ChatSession] = {}
        self.session_lock = Lock()
        self.session_timeout = self.config.chat_session_timeout_minutes
        self.max_memory_size = self.config.chat_max_memory_size
        
        # File storage setup
        self.sessions_file = os.path.join("data", "chat_sessions.json")
        os.makedirs(os.path.dirname(self.sessions_file), exist_ok=True)
        
        # Background cleanup
        self.cleanup_thread = None
        self.cleanup_interval = 60  # 1 minute
        self.shutdown_event = threading.Event()
        
        # Service stats
        self._total_sessions = 0
        self._total_messages = 0
        self._active_sessions = 0
        
        # Memory service (lazy import to avoid circular dependency)
        self._memory_service = None
        
        # Load existing sessions from file
        self._load_sessions_from_file()
        
        # Start background cleanup
        self._start_cleanup_thread()
        
        logger.info("Chat service initialized with file persistence")
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread."""
        def cleanup_worker():
            while not self.shutdown_event.wait(self.cleanup_interval):
                try:
                    self.cleanup_expired_sessions()
                except Exception as e:
                    logger.error(f"Cleanup thread error: {e}")
        
        self.cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        logger.info("Started background cleanup thread")
    
    def _get_memory_service(self):
        """Get memory service instance (lazy import to avoid circular dependency)."""
        if self._memory_service is None:
            try:
                from .memory_service import get_memory_service
                self._memory_service = get_memory_service()
            except Exception as e:
                logger.warning(f"Failed to load memory service: {e}")
        return self._memory_service
    
    def _load_sessions_from_file(self):
        """Load sessions from JSON file."""
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for session_data in data.values():
                        session = ChatSession.from_dict(session_data)
                        self.sessions[session.session_id] = session
                        
                logger.info(f"Loaded {len(self.sessions)} sessions from file")
                self._active_sessions = len(self.sessions)
            else:
                logger.info("No existing sessions file found")
        except Exception as e:
            logger.error(f"Failed to load sessions from file: {e}")
            self.sessions = {}
    
    def _save_sessions_to_file(self):
        """Save sessions to JSON file."""
        try:
            sessions_data = {}
            for session_id, session in self.sessions.items():
                sessions_data[session_id] = session.to_dict()
            
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save sessions to file: {e}")
    
    def _save_session(self, session_id: str):
        """Save a single session to file (called after session changes)."""
        try:
            # Load existing data
            sessions_data = {}
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
            
            # Update with current session
            if session_id in self.sessions:
                sessions_data[session_id] = self.sessions[session_id].to_dict()
            elif session_id in sessions_data:
                # Session deleted, remove from file
                del sessions_data[session_id]
            
            # Save back to file
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save session {session_id} to file: {e}")
    
    @service_error_handler
    def create_session(
        self,
        initial_letter: Optional[str] = None,
        context: str = ""
    ) -> str:
        """
        Create a new chat session.
        
        Args:
            initial_letter: Initial letter content
            context: Additional context for the session
            
        Returns:
            Session ID
        """
        with ErrorContext("create_chat_session"):
            session_id = str(uuid.uuid4())
            now = datetime.now()
            expires_at = now + timedelta(minutes=self.session_timeout)
            
            session = ChatSession(
                session_id=session_id,
                created_at=now,
                last_activity=now,
                expires_at=expires_at,
                context=context
            )
            
            # Add initial letter version if provided
            if initial_letter:
                version = LetterVersion(
                    version_id=str(uuid.uuid4()),
                    content=initial_letter,
                    timestamp=now,
                    change_summary="Initial letter"
                )
                session.letter_versions.append(version)
            
            with self.session_lock:
                self.sessions[session_id] = session
                self._total_sessions += 1
                self._active_sessions += 1
                # Save to file immediately
                self._save_session(session_id)
            
            logger.info(f"Created chat session: {session_id}")
            return session_id
    
    @service_error_handler
    def process_edit_request(
        self,
        session_id: str,
        message: str,
        current_letter: str,
        editing_instructions: Optional[str] = None,
        preserve_formatting: bool = True
    ) -> ChatEditResponse:
        """
        Process a letter editing request through chat.
        
        Args:
            session_id: Chat session ID
            message: User message/request
            current_letter: Current letter content
            editing_instructions: Specific editing instructions
            preserve_formatting: Whether to preserve formatting
            
        Returns:
            ChatEditResponse with updated letter
        """
        with ErrorContext("process_edit_request", {"session_id": session_id}):
            timer = Timer()
            
            with self.session_lock:
                if session_id not in self.sessions:
                    raise ValueError(f"Session {session_id} not found")
                
                session = self.sessions[session_id]
                now = datetime.now()
                
                # Check if session is expired and remove it immediately
                if now > session.expires_at:
                    del self.sessions[session_id]
                    self._active_sessions -= 1
                    logger.info(f"Removed expired session during edit request: {session_id}")
                    raise ValueError(f"Session {session_id} has expired and was removed")
                
                # Update last activity
                session.last_activity = now
                # Save session after activity update
                self._save_session(session_id)
            
            # Add user message to session
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                role="user",
                content=message,
                timestamp=datetime.now(),
                metadata={
                    "editing_instructions": editing_instructions,
                    "preserve_formatting": preserve_formatting
                }
            )
            
            session.messages.append(user_message)
            
            # Process message for long-term memory (background)
            memory_service = self._get_memory_service()
            if memory_service:
                memory_service.process_message_async(
                    session_id=session_id,
                    message=message,
                    context=session.context
                )
            
            # Create editing prompt
            editing_prompt = self._create_editing_prompt(
                session=session,
                user_message=message,
                current_letter=current_letter,
                editing_instructions=editing_instructions
            )
            
            try:
                # Use letter service for AI processing
                letter_service = get_letter_service()
                
                # Create generation context for editing
                context = LetterGenerationContext(
                    user_prompt=editing_prompt,
                    recipient="",
                    member_info="",
                    is_first_contact=False,
                    reference_letter=current_letter,
                    category="تحرير",
                    writing_instructions="قم بتحرير الخطاب وفقاً للطلب مع المحافظة على الطابع الرسمي",
                    previous_letter_content=current_letter,
                    session_id=session_id
                )
                
                # Generate edited letter
                edited_result = letter_service.generate_letter(context)
                edited_letter = edited_result.Letter
                
                # Create change summary
                change_summary = self._generate_change_summary(
                    original=current_letter,
                    edited=edited_letter,
                    user_request=message
                )
                
                # Add new letter version
                new_version = LetterVersion(
                    version_id=str(uuid.uuid4()),
                    content=edited_letter,
                    timestamp=datetime.now(),
                    change_summary=change_summary
                )
                
                session.letter_versions.append(new_version)
                
                # Limit letter versions to prevent memory issues
                if len(session.letter_versions) > 10:
                    session.letter_versions = session.letter_versions[-10:]
                
                # Create assistant response
                assistant_message = ChatMessage(
                    id=str(uuid.uuid4()),
                    role="assistant",
                    content=f"تم تحرير الخطاب بناءً على طلبكم. {change_summary}",
                    timestamp=datetime.now(),
                    metadata={
                        "letter_version_id": new_version.version_id,
                        "processing_time": timer.elapsed()
                    }
                )
                
                session.messages.append(assistant_message)
                
                # Manage session memory
                self._manage_session_memory(session)
                
                # Update stats
                self._total_messages += 2  # user + assistant
                
                # Save session after processing
                self._save_session(session_id)
                
                # Create response
                response = ChatEditResponse(
                    session_id=session_id,
                    message_id=assistant_message.id,
                    response_text=assistant_message.content,
                    updated_letter=edited_letter,
                    change_summary=change_summary,
                    letter_version_id=new_version.version_id,
                    processing_time=timer.elapsed(),
                    status=ChatSessionStatus.ACTIVE.value
                )
                
                logger.info(f"Processed edit request for session {session_id} in {timer.elapsed():.2f}s")
                
                return response
                
            except Exception as e:
                logger.error(f"Edit processing failed for session {session_id}: {e}")
                
                # Add error message
                error_message = ChatMessage(
                    id=str(uuid.uuid4()),
                    role="assistant",
                    content=f"عذراً، حدث خطأ أثناء تحرير الخطاب: {str(e)}",
                    timestamp=datetime.now(),
                    metadata={"error": True}
                )
                
                session.messages.append(error_message)
                
                return ChatEditResponse(
                    session_id=session_id,
                    message_id=error_message.id,
                    response_text=error_message.content,
                    updated_letter=current_letter,  # Return original letter
                    change_summary="فشل في التحرير",
                    letter_version_id="error",
                    processing_time=timer.elapsed(),
                    status=ChatSessionStatus.ERROR.value
                )
    
    def _create_editing_prompt(
        self,
        session: ChatSession,
        user_message: str,
        current_letter: str,
        editing_instructions: Optional[str]
    ) -> str:
        """Create editing prompt for AI processing."""
        
        # Get recent conversation context
        recent_messages = session.messages[-6:] if len(session.messages) > 6 else session.messages
        conversation_context = "\n".join([
            f"{msg.role}: {msg.content}"
            for msg in recent_messages
        ])
        
        prompt = f"""
أنت مساعد ذكي متخصص في تحرير الخطابات الرسمية باللغة العربية.

السياق العام للجلسة: {session.context}

المحادثة السابقة:
{conversation_context}

الخطاب الحالي:
{current_letter}

طلب التحرير من المستخدم:
{user_message}

{f"تعليمات إضافية: {editing_instructions}" if editing_instructions else ""}

المطلوب:
1. احتفظ بالطابع الرسمي والمهني للخطاب
2. حافظ على التحية والختام المناسبين
3. اتبع قواعد اللغة العربية بدقة
4. قم بالتعديل المطلوب بدقة وعناية
5. احتفظ بالمعلومات المهمة في الخطاب الأصلي

قم بتحرير الخطاب وأرجعه محرراً ومُحسناً:
"""
        
        return prompt.strip()
    
    def _generate_change_summary(
        self,
        original: str,
        edited: str,
        user_request: str
    ) -> str:
        """Generate summary of changes made to the letter."""
        
        # Simple change detection
        original_words = set(original.split())
        edited_words = set(edited.split())
        
        added_words = len(edited_words - original_words)
        removed_words = len(original_words - edited_words)
        
        if added_words > 5 and removed_words > 5:
            return f"تم إعادة صياغة أجزاء من الخطاب ({added_words} كلمة مضافة، {removed_words} كلمة محذوفة)"
        elif added_words > 5:
            return f"تم إضافة محتوى جديد ({added_words} كلمة مضافة)"
        elif removed_words > 5:
            return f"تم تقليص المحتوى ({removed_words} كلمة محذوفة)"
        else:
            return "تم إجراء تعديلات طفيفة على النص"
    
    def _manage_session_memory(self, session: ChatSession):
        """Manage session memory to prevent excessive growth."""
        
        # Limit messages
        if len(session.messages) > self.max_memory_size:
            # Keep first 2 and last (max_memory_size - 2) messages
            session.messages = (
                session.messages[:2] + 
                session.messages[-(self.max_memory_size - 2):]
            )
        
        # Limit letter versions
        if len(session.letter_versions) > 10:
            session.letter_versions = session.letter_versions[-10:]
    
    def get_chat_history(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        
        with self.session_lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.sessions[session_id]
            
            # Get paginated messages
            messages = session.messages[offset:offset + limit]
            
            return [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata
                }
                for msg in messages
            ]
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists and is active."""
        with self.session_lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            # Check if session is expired
            if datetime.now() > session.expires_at:
                return False
            
            return session.is_active
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get detailed session information."""
        with self.session_lock:
            # Double-check session existence within the lock to prevent race conditions
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.sessions[session_id]
            now = datetime.now()
            is_expired = now > session.expires_at
            
            # Check if expired but don't delete here to prevent race conditions
            if is_expired:
                raise ValueError(f"Session {session_id} has expired")
            
            # Session is valid, return info
            return {
                "session_id": session_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "is_active": session.is_active,
                "is_expired": is_expired,
                "message_count": len(session.messages),
                "letter_versions": len(session.letter_versions),
                "context": session.context
            }
    
    def extend_session(
        self,
        session_id: str,
        extend_minutes: Optional[int] = None
    ) -> datetime:
        """Extend session expiration time."""
        with self.session_lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.sessions[session_id]
            
            if extend_minutes is None:
                extend_minutes = self.session_timeout
            
            new_expiration = datetime.now() + timedelta(minutes=extend_minutes)
            session.expires_at = new_expiration
            session.last_activity = datetime.now()
            
            # Save session after extending
            self._save_session(session_id)
            
            logger.info(f"Extended session {session_id} until {new_expiration}")
            
            return new_expiration
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        with self.session_lock:
            if session_id not in self.sessions:
                return False
            
            del self.sessions[session_id]
            self._active_sessions -= 1
            
            # Remove from file
            self._save_session(session_id)
            
            # Clear associated memory
            memory_service = self._get_memory_service()
            if memory_service:
                memory_service.clear_session_memory(session_id)
            
            logger.info(f"Deleted session: {session_id}")
            return True
    
    def list_sessions(self, include_expired: bool = False) -> List[Dict[str, Any]]:
        """List all sessions."""
        with self.session_lock:
            sessions_info = []
            now = datetime.now()
            
            for session_id, session in self.sessions.items():
                is_expired = now > session.expires_at
                
                if not include_expired and is_expired:
                    continue
                
                sessions_info.append({
                    "session_id": session_id,
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "is_active": session.is_active,
                    "is_expired": is_expired,
                    "message_count": len(session.messages),
                    "letter_versions": len(session.letter_versions)
                })
            
            return sessions_info
    
    def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """Clean up expired sessions."""
        with self.session_lock:
            now = datetime.now()
            expired_sessions = [
                session_id for session_id, session in self.sessions.items()
                if now > session.expires_at
            ]
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
                self._active_sessions -= 1
            
            # Save updated sessions to file if any were cleaned
            if expired_sessions:
                self._save_sessions_to_file()
            
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
            return {
                "cleaned_sessions": len(expired_sessions),
                "remaining_sessions": len(self.sessions),
                "cleanup_time": now.isoformat()
            }
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        with self.session_lock:
            return {
                "total_sessions_created": self._total_sessions,
                "active_sessions": len(self.sessions),
                "total_messages": self._total_messages,
                "session_timeout_minutes": self.session_timeout,
                "max_memory_size": self.max_memory_size,
                "cleanup_interval_seconds": self.cleanup_interval
            }
    
    def shutdown(self):
        """Shutdown the service gracefully."""
        logger.info("Shutting down chat service...")
        
        # Stop cleanup thread
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.shutdown_event.set()
            self.cleanup_thread.join(timeout=5)
        
        # Save sessions before clearing
        with self.session_lock:
            self._save_sessions_to_file()
            self.sessions.clear()
        
        logger.info("Chat service shutdown complete")

# Service instance management
_chat_service: Optional[ChatService] = None

def get_chat_service() -> ChatService:
    """Get or create chat service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
