"""
Data Models for the AutomatingLetter Application
Pydantic models for request/response validation and data structure.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from enum import Enum

class LetterCategory(str, Enum):
    """Enumeration of letter categories."""
    NEW_LETTER = "خطاب جديد"
    CONGRATULATION = "تهنئة"
    SUPPLEMENTARY = "خطاب إلحاقي"
    CONFRANCE = "جدولة اجتماع"
    REPLAY = "خطاب رد على خطاب من الجهة"
    INVITATION = "دعوة حضور"
    REQUEST = "طلب"

class LetterStatus(str, Enum):
    """Enumeration of letter processing status."""
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"

class ChatSessionStatus(str, Enum):
    """Enumeration of chat session status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    ERROR = "error"
    PROCESSING = "processing"

# Request Models
class GenerateLetterRequest(BaseModel):
    """Request model for letter generation."""
    category: LetterCategory
    recipient: str = Field(..., min_length=1, max_length=200)
    prompt: str = Field(..., min_length=10, max_length=2000)
    is_first: bool = Field(..., description="Whether this is the first communication")
    member_name: Optional[str] = Field(None, max_length=100)
    recipient_job_title: Optional[str] = Field(None, max_length=100)
    recipient_title: Optional[str] = Field(None, max_length=50)
    organization_name: Optional[str] = Field(None, max_length=100)
    previous_letter_content: Optional[str] = Field(None, max_length=5000)
    previous_letter_id: Optional[str] = Field(None, max_length=50)
    session_id: Optional[str] = Field(None, max_length=50, description="Optional session ID for memory context")
    
    @validator('prompt')
    def validate_prompt(cls, v):
        """Validate prompt content."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v.strip()

class EditLetterRequest(BaseModel):
    """Request model for letter editing."""
    letter: str = Field(..., min_length=10, max_length=10000)
    feedback: str = Field(..., min_length=5, max_length=1000)
    
    @validator('letter', 'feedback')
    def validate_content(cls, v):
        """Validate content is not empty."""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()

class ChatEditLetterRequest(BaseModel):
    """Request model for chat-based letter editing."""
    message: str = Field(..., min_length=1, max_length=1000, description="User message/editing request")
    current_letter: str = Field(..., min_length=0, max_length=10000, description="Current letter content (can be empty for new letters)")
    editing_instructions: Optional[str] = Field(None, max_length=500, description="Specific editing instructions")
    preserve_formatting: bool = Field(default=True, description="Whether to preserve letter formatting")
    
    @validator('message')
    def validate_message(cls, v):
        """Validate message is not empty."""
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v
    
    @validator('current_letter')
    def validate_current_letter(cls, v):
        """Validate current letter - can be empty for new letters."""
        # Allow empty letters for new letter creation
        return v
        return v.strip()

class ChatQuestionRequest(BaseModel):
    """Request model for chat questions."""
    session_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=5, max_length=500)
    current_letter: Optional[str] = Field(None, max_length=10000)

class CreateSessionRequest(BaseModel):
    """Request model for creating chat sessions."""
    original_letter: Optional[str] = Field(None, max_length=10000)

class ArchiveLetterRequest(BaseModel):
    """Request model for archiving letters."""
    letter_content: str = Field(..., min_length=10)
    letter_type: str = Field(default="General")
    recipient: str = Field(..., min_length=1)
    title: str = Field(default="undefined")
    is_first: bool = Field(default=False)
    ID: str = Field(..., min_length=1)
    template: str = Field(default="default_template.html")
    username: str = Field(default="unknown")

# Response Models
class LetterOutput(BaseModel):
    """Response model for generated letters."""
    ID: str = Field(..., description="Unique identifier for the letter")
    Title: str = Field(..., description="Title of the letter in Arabic")
    Letter: str = Field(..., description="Full content of the letter in formal Arabic")
    Date: str = Field(..., description="Date the letter was generated")

class EditLetterResponse(BaseModel):
    """Response model for letter editing."""
    status: str = Field(..., description="Operation status")
    edited_letter: str = Field(..., description="The edited letter content")

class ChatResponse(BaseModel):
    """Base response model for chat operations."""
    status: str = Field(..., description="Operation status")
    session_id: str = Field(..., description="Session identifier")
    conversation_length: int = Field(..., description="Number of messages in conversation")

class ChatEditResponse(BaseModel):
    """Response model for chat-based letter editing."""
    session_id: str = Field(..., description="Session identifier")
    message_id: str = Field(..., description="Message identifier")
    response_text: str = Field(..., description="AI response text")
    updated_letter: str = Field(..., description="The updated letter content")
    change_summary: str = Field(..., description="Summary of changes made")
    letter_version_id: str = Field(..., description="Version identifier for the letter")
    processing_time: float = Field(..., description="Processing time in seconds")
    status: str = Field(..., description="Session status")

class ChatQuestionResponse(ChatResponse):
    """Response model for chat questions."""
    answer: str = Field(..., description="AI response to the question")

class SessionInfo(BaseModel):
    """Response model for session information."""
    status: str
    session_id: str
    created_at: str
    last_activity: str
    conversation_length: int
    has_original_letter: bool

class CreateSessionResponse(BaseModel):
    """Response model for session creation."""
    status: str
    session_id: str
    message: str

class ArchiveResponse(BaseModel):
    """Response model for letter archiving."""
    status: str
    message: str
    processing: Optional[str] = None
    file_id: Optional[str] = None
    file_url: Optional[str] = None

class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now)

class SuccessResponse(BaseModel):
    """Generic success response model."""
    status: str = Field(default="success")
    message: str
    data: Optional[Dict[str, Any]] = None

# Internal Models
class ChatSession(BaseModel):
    """Internal model for chat sessions."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    original_letter: Optional[str] = None
    conversation_count: int = 0
    is_active: bool = True

class LetterLog(BaseModel):
    """Internal model for letter logging."""
    timestamp: datetime
    letter_id: str
    category: str
    recipient: str
    title: str
    is_first_communication: bool
    content_preview: str
    status: LetterStatus
    user_info: Optional[Dict[str, Any]] = None

class APIMetrics(BaseModel):
    """Model for API performance metrics."""
    endpoint: str
    method: str
    response_time_ms: float
    status_code: int
    timestamp: datetime
    session_id: Optional[str] = None
    error_message: Optional[str] = None

# PDF Models
class PDFGenerationRequest(BaseModel):
    """Request model for PDF generation."""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=10, max_length=50000)
    template_name: str = Field(default="default_template", max_length=50)
    upload_to_drive: bool = Field(default=False)
    options: Optional[Dict[str, Any]] = Field(default=None)
    
    @validator('content')
    def validate_content(cls, v):
        """Validate content is not empty."""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()

class PDFResponse(BaseModel):
    """Response model for PDF generation."""
    pdf_id: str = Field(..., description="Unique identifier for the PDF")
    filename: str = Field(..., description="Generated filename")
    file_size: int = Field(..., description="File size in bytes")
    download_url: str = Field(..., description="URL to download the PDF")
    drive_url: Optional[str] = Field(None, description="Google Drive URL if uploaded")
    generated_at: datetime = Field(..., description="Generation timestamp")

# Validation Schemas
class LetterValidation:
    """Validation utilities for letter content."""
    
    @staticmethod
    def validate_arabic_content(content: str) -> bool:
        """Validate if content contains Arabic text."""
        arabic_chars = any('\u0600' <= char <= '\u06FF' for char in content)
        return arabic_chars
    
    @staticmethod
    def validate_letter_structure(content: str) -> bool:
        """Validate basic letter structure."""
        required_elements = [
            "بسم الله الرحمن الرحيم",  # Bismillah
            "السلام عليكم",          # Greeting
        ]
        return any(element in content for element in required_elements)
    
    @staticmethod
    def estimate_letter_length(content: str) -> Dict[str, int]:
        """Estimate letter metrics."""
        words = len(content.split())
        lines = len(content.split('\n'))
        chars = len(content)
        
        return {
            "words": words,
            "lines": lines,
            "characters": chars,
            "estimated_reading_time_seconds": words * 0.5  # Rough estimate
        }
