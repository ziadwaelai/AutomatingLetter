"""
Dedicated Session Storage Service
Separate service focused solely on session persistence and retrieval.
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import uuid
import logging

logger = logging.getLogger(__name__)

@dataclass
class SessionData:
    """Session data structure."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    context: str
    is_active: bool = True
    idempotency_key: Optional[str] = None
    messages: List[Dict] = field(default_factory=list)
    letter_versions: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "context": self.context,
            "is_active": self.is_active,
            "idempotency_key": self.idempotency_key,
            "messages": self.messages,
            "letter_versions": self.letter_versions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionData':
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            context=data["context"],
            is_active=data.get("is_active", True),
            idempotency_key=data.get("idempotency_key"),
            messages=data.get("messages", []),
            letter_versions=data.get("letter_versions", [])
        )

class SessionStorage:
    """
    Thread-safe session storage service.
    Handles all session persistence and retrieval operations.
    """
    
    def __init__(self, storage_file: str = "data/chat_sessions.json"):
        self.storage_file = storage_file
        self._sessions: Dict[str, SessionData] = {}
        self._lock = threading.RLock()  # Reentrant lock
        self._file_lock = threading.Lock()  # Separate lock for file operations
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(storage_file), exist_ok=True)
        
        # Load existing sessions
        self._load_from_disk()
        
        logger.info(f"SessionStorage initialized with {len(self._sessions)} sessions")
    
    def _load_from_disk(self) -> None:
        """Load sessions from disk storage and sync in-memory state."""
        try:
            with self._file_lock:
                if os.path.exists(self.storage_file):
                    with open(self.storage_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    loaded_sessions = {}
                    loaded_count = 0
                    
                    # Load all sessions from file into temporary dict
                    for session_data in data.values():
                        try:
                            session = SessionData.from_dict(session_data)
                            loaded_sessions[session.session_id] = session
                            loaded_count += 1
                        except Exception as e:
                            logger.error(f"Failed to load session {session_data.get('session_id', 'unknown')}: {e}")
                    
                    # Replace in-memory sessions completely with file contents
                    with self._lock:
                        old_count = len(self._sessions)
                        self._sessions = loaded_sessions
                        new_count = len(self._sessions)
                        
                        if old_count != new_count:
                            logger.info(f"Synced sessions from disk: {old_count} -> {new_count} sessions")
                        
                else:
                    logger.info("No existing session file found, clearing memory")
                    with self._lock:
                        self._sessions = {}
                        
        except Exception as e:
            logger.error(f"Failed to load sessions from disk: {e}")
            # Don't clear sessions on error, keep existing state
            logger.warning("Keeping existing in-memory sessions due to disk read error")
    
    def _save_to_disk(self) -> None:
        """Save all sessions to disk storage."""
        try:
            with self._lock:
                # Create a snapshot to avoid holding lock during file I/O
                sessions_snapshot = {
                    session_id: session.to_dict() 
                    for session_id, session in self._sessions.items()
                }
            
            # File I/O outside the memory lock
            with self._file_lock:
                # Use atomic write with temporary file
                temp_file = self.storage_file + '.tmp'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(sessions_snapshot, f, ensure_ascii=False, indent=2)
                
                # Atomic rename
                if os.path.exists(self.storage_file):
                    os.replace(temp_file, self.storage_file)
                else:
                    os.rename(temp_file, self.storage_file)
                
                logger.debug(f"Saved {len(sessions_snapshot)} sessions to disk")
                
        except Exception as e:
            logger.error(f"Failed to save sessions to disk: {e}")
            # Clean up temp file if it exists
            temp_file = self.storage_file + '.tmp'
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
    
    def create_session(self, context: str = "", idempotency_key: Optional[str] = None, 
                      timeout_minutes: int = 60) -> str:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + timedelta(minutes=timeout_minutes)
        
        session = SessionData(
            session_id=session_id,
            created_at=now,
            last_activity=now,
            expires_at=expires_at,
            context=context,
            idempotency_key=idempotency_key
        )
        
        with self._lock:
            self._sessions[session_id] = session
        
        # Save to disk immediately
        self._save_to_disk()
        
        logger.info(f"Created session {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get a session by ID."""
        # Reload from disk to get latest sessions from all workers
        self._load_from_disk()
        
        with self._lock:
            return self._sessions.get(session_id)
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists and is not expired."""
        # Reload from disk to get latest sessions from all workers
        self._load_from_disk()
        
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            # Check if expired (but don't delete here)
            if datetime.now() > session.expires_at:
                return False
                
            return session.is_active
    
    def list_sessions(self, include_expired: bool = False) -> List[Dict[str, Any]]:
        """List all sessions."""
        # Reload from disk to get latest sessions from all workers
        self._load_from_disk()
        
        now = datetime.now()
        sessions_info = []
        
        with self._lock:
            # Create snapshot to avoid lock during iteration
            sessions_snapshot = dict(self._sessions)
        
        for session_id, session in sessions_snapshot.items():
            is_expired = now > session.expires_at
            
            if not include_expired and is_expired:
                continue
            
            sessions_info.append({
                "session_id": session_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "is_active": session.is_active and not is_expired,
                "is_expired": is_expired,
                "message_count": len(session.messages),
                "letter_versions": len(session.letter_versions),
                "context": session.context[:100] + "..." if len(session.context) > 100 else session.context
            })
        
        logger.debug(f"Listed {len(sessions_info)} sessions (include_expired={include_expired})")
        return sessions_info
    
    def update_session_activity(self, session_id: str) -> bool:
        """Update last activity timestamp for a session."""
        # Reload from disk to get latest sessions from all workers
        self._load_from_disk()
        
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.last_activity = datetime.now()
                # Save to disk (could be debounced for performance)
                self._save_to_disk()
                return True
            return False
    
    def extend_session_expiration(self, session_id: str, new_expires_at: datetime) -> bool:
        """Update session expiration time."""
        # Reload from disk to get latest sessions from all workers
        self._load_from_disk()
        
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.expires_at = new_expires_at
                session.last_activity = datetime.now()
                self._save_to_disk()
                logger.info(f"Extended session {session_id} to {new_expires_at}")
                return True
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        # Reload from disk to get latest sessions from all workers
        self._load_from_disk()
        
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self._save_to_disk()
                logger.info(f"Deleted session {session_id}")
                return True
            return False
    
    def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """Clean up expired sessions with grace period."""
        now = datetime.now()
        grace_period = timedelta(minutes=5)  # 5-minute grace period
        
        expired_sessions = []
        
        with self._lock:
            # Find expired sessions
            for session_id, session in list(self._sessions.items()):
                if now > (session.expires_at + grace_period):
                    expired_sessions.append(session_id)
                    del self._sessions[session_id]
        
        if expired_sessions:
            self._save_to_disk()
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions: {expired_sessions}")
        else:
            logger.debug(f"No expired sessions to clean up (total: {len(self._sessions)})")
        
        return {
            "cleaned_sessions": len(expired_sessions),
            "remaining_sessions": len(self._sessions),
            "cleanup_time": now.isoformat(),
            "cleaned_session_ids": expired_sessions
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with self._lock:
            now = datetime.now()
            active_count = sum(
                1 for session in self._sessions.values()
                if session.is_active and now <= session.expires_at
            )
            
            return {
                "total_sessions": len(self._sessions),
                "active_sessions": active_count,
                "expired_sessions": len(self._sessions) - active_count,
                "storage_file": self.storage_file
            }
    
    def find_by_idempotency_key(self, idempotency_key: str) -> Optional[str]:
        """Find session by idempotency key."""
        with self._lock:
            for session_id, session in self._sessions.items():
                if (session.idempotency_key == idempotency_key and 
                    session.is_active and 
                    datetime.now() <= session.expires_at):
                    return session_id
            return None

# Global instance
_session_storage = None
_storage_lock = threading.Lock()

def get_session_storage() -> SessionStorage:
    """Get the global session storage instance (singleton)."""
    global _session_storage
    with _storage_lock:
        if _session_storage is None:
            _session_storage = SessionStorage()
        return _session_storage
