"""
Session Manager Service
High-level session management operations built on top of SessionStorage.
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from .session_storage import get_session_storage, SessionData

logger = logging.getLogger(__name__)

class SessionManager:
    """
    High-level session management service.
    Provides business logic on top of the storage layer.
    """
    
    def __init__(self):
        self.storage = get_session_storage()
        self.session_timeout_minutes = 60
        
        # Background cleanup
        self.cleanup_thread = None
        self.cleanup_interval = 600  # 10 minutes
        self.shutdown_event = threading.Event()
        
        # Statistics
        self._total_sessions_created = 0
        self._total_messages_processed = 0
        self._stats_lock = threading.Lock()
        
        # Start background cleanup
        self._start_background_cleanup()
        
        logger.info("SessionManager initialized")
    
    def _start_background_cleanup(self):
        """Start background cleanup thread."""
        def cleanup_worker():
            while not self.shutdown_event.wait(self.cleanup_interval):
                try:
                    result = self.storage.cleanup_expired_sessions()
                    if result["cleaned_sessions"] > 0:
                        logger.info(f"Background cleanup completed: {result}")
                except Exception as e:
                    logger.error(f"Background cleanup error: {e}")
        
        self.cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        logger.info(f"Started background cleanup thread (interval: {self.cleanup_interval}s)")
    
    def create_session(self, initial_letter: Optional[str] = None, 
                      context: str = "", idempotency_key: Optional[str] = None) -> str:
        """Create a new session with optional initial letter."""
        
        # Check for existing session with idempotency key
        if idempotency_key:
            existing_session_id = self.storage.find_by_idempotency_key(idempotency_key)
            if existing_session_id:
                logger.info(f"Returning existing session for idempotency key: {existing_session_id}")
                return existing_session_id
        
        # Create new session
        session_id = self.storage.create_session(
            context=context,
            idempotency_key=idempotency_key,
            timeout_minutes=self.session_timeout_minutes
        )
        
        # Add initial letter version if provided
        if initial_letter:
            self.add_letter_version(session_id, initial_letter, "Initial letter")
        
        # Update statistics
        with self._stats_lock:
            self._total_sessions_created += 1
        
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive session information."""
        session = self.storage.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        now = datetime.now()
        is_expired = now > session.expires_at
        
        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "expires_at": session.expires_at,
            "is_active": session.is_active and not is_expired,
            "is_expired": is_expired,
            "message_count": len(session.messages),
            "letter_versions": len(session.letter_versions),
            "context": session.context,
            "messages": session.messages,
            "letter_versions": session.letter_versions
        }
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get raw session data for internal use."""
        session = self.storage.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "expires_at": session.expires_at,
            "is_active": session.is_active,
            "context": session.context,
            "messages": session.messages,
            "letter_versions": session.letter_versions,
            "idempotency_key": session.idempotency_key
        }
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists and is valid."""
        return self.storage.session_exists(session_id)
    
    def list_sessions(self, include_expired: bool = False) -> List[Dict[str, Any]]:
        """List all sessions."""
        return self.storage.list_sessions(include_expired=include_expired)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return self.storage.delete_session(session_id)
    
    def add_message(self, session_id: str, role: str, content: str, 
                   metadata: Optional[Dict] = None) -> bool:
        """Add a message to a session."""
        session = self.storage.get_session(session_id)
        if not session:
            return False
        
        if not self.storage.session_exists(session_id):
            return False
        
        message = {
            "id": f"msg_{len(session.messages) + 1}",
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        session.messages.append(message)
        self.storage.update_session_activity(session_id)
        
        # Update statistics
        with self._stats_lock:
            self._total_messages_processed += 1
        
        return True
    
    def add_letter_version(self, session_id: str, content: str, 
                          change_summary: str = "") -> bool:
        """Add a letter version to a session."""
        session = self.storage.get_session(session_id)
        if not session:
            return False
        
        if not self.storage.session_exists(session_id):
            return False
        
        version = {
            "version_id": f"v_{len(session.letter_versions) + 1}",
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "change_summary": change_summary
        }
        
        session.letter_versions.append(version)
        self.storage.update_session_activity(session_id)
        
        return True
    
    def get_chat_history(self, session_id: str, limit: int = 50, 
                        offset: int = 0) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        session = self.storage.get_session(session_id)
        if not session:
            return []
        
        messages = session.messages[offset:offset + limit]
        return [
            {
                "id": msg["id"],
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["timestamp"],
                "metadata": msg.get("metadata", {})
            }
            for msg in messages
        ]
    
    def extend_session(self, session_id: str, extend_minutes: Optional[int] = None) -> datetime:
        """Extend session expiration time."""
        # Check if session exists first
        if not self.storage.session_exists(session_id):
            raise ValueError(f"Session {session_id} not found")
        
        from datetime import timedelta
        extend_by = extend_minutes or self.session_timeout_minutes
        new_expires_at = datetime.now() + timedelta(minutes=extend_by)
        
        # Use the new method to properly update expires_at
        success = self.storage.extend_session_expiration(session_id, new_expires_at)
        if not success:
            raise ValueError(f"Failed to extend session {session_id}")
        
        return new_expires_at
    
    def manual_cleanup(self) -> Dict[str, Any]:
        """Manually trigger cleanup of expired sessions."""
        return self.storage.cleanup_expired_sessions()
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        storage_stats = self.storage.get_stats()
        
        with self._stats_lock:
            service_stats = {
                "total_sessions_created": self._total_sessions_created,
                "total_messages_processed": self._total_messages_processed,
                "session_timeout_minutes": self.session_timeout_minutes,
                "cleanup_interval_seconds": self.cleanup_interval
            }
        
        return {**storage_stats, **service_stats}
    
    def shutdown(self):
        """Shutdown the session manager."""
        logger.info("Shutting down SessionManager")
        self.shutdown_event.set()
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        logger.info("SessionManager shutdown complete")

# Global instance
_session_manager = None
_manager_lock = threading.Lock()

def get_session_manager() -> SessionManager:
    """Get the global session manager instance (singleton)."""
    global _session_manager
    with _manager_lock:
        if _session_manager is None:
            _session_manager = SessionManager()
        return _session_manager
