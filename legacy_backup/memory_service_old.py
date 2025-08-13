"""
Simplified Long-Term Memory Service
Manages user instructions and writing preferences for letter generation.
"""

import logging
import json
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from threading import Lock
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from ..config import get_config
from ..utils import ErrorContext, service_error_handler

logger = logging.getLogger(__name__)

class SimpleInstructionExtraction(BaseModel):
    """Simplified model for extracted instructions from user messages."""
    has_instruction: bool = Field(description="Whether the message contains a writing instruction")
    instruction_text_arabic: str = Field(description="The instruction in clear Arabic")
    instruction_type: str = Field(description="Type: style, format, content")
    applies_to_all: bool = Field(description="Whether this applies to all future letters")

@dataclass
class SimpleMemoryInstruction:
    """Simplified stored memory instruction."""
    id: str
    instruction_text: str  # Always in Arabic
    instruction_type: str  # style, format, content
    created_at: datetime
    last_used: datetime
    usage_count: int = 0
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "instruction_text": self.instruction_text,
            "instruction_type": self.instruction_type,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
            "usage_count": self.usage_count,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimpleMemoryInstruction':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            instruction_text=data["instruction_text"],
            instruction_type=data["instruction_type"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]),
            usage_count=data.get("usage_count", 0),
            is_active=data.get("is_active", True)
        )

class MemoryService:
    """Service for managing long-term user instructions and preferences."""
    
    def __init__(self):
        """Initialize memory service."""
        self.config = get_config()
        self.memory_lock = Lock()
        self.memory_file = Path("logs/user_memory.json")
        
        # Instruction storage
        self.instructions: Dict[str, MemoryInstruction] = {}
        self.session_memories: Dict[str, List[str]] = {}  # session_id -> instruction_ids
        
        # AI components for instruction extraction
        self.parser = JsonOutputParser(pydantic_object=InstructionExtraction)
        self.extraction_chain = self._build_extraction_chain()
        
        # Load existing memory
        self._load_memory()
        
        logger.info("Memory service initialized")
    
    def _build_extraction_chain(self):
        """Build the LangChain for instruction extraction."""
        template = """
أنت مساعد ذكي متخصص في تحليل رسائل المستخدمين لاستخراج التعليمات والتفضيلات المتعلقة بكتابة الخطابات.

مهمتك هي تحليل الرسالة التالية وتحديد ما إذا كانت تحتوي على تعليمات أو تفضيلات يجب تذكرها لاستخدامها في الخطابات المستقبلية.

أنواع التعليمات التي يجب البحث عنها:
1. **تفضيلات الأسلوب**: مثل "استخدم أسلوباً أكثر رسمية" أو "اجعل النبرة أكثر ودية"
2. **تفضيلات التنسيق**: مثل "لا تستخدم النقاط" أو "اجعل الفقرات قصيرة"
3. **تفضيلات المحتوى**: مثل "أضف دائماً تهنئة في النهاية" أو "تجنب الشكر المفرط"
4. **قواعد شخصية**: مثل "لا تذكر الأرقام الشخصية" أو "استخدم لغة بسيطة"
5. **تفضيلات الخاتمة**: مثل "استخدم خاتمة مختصرة" أو "أضف دعوة للتواصل"

رسالة المستخدم:
{user_message}

السياق (إذا متوفر):
{context}

تعليمات التحليل:
- ركز على التعليمات الصريحة أو المضمنة
- تجاهل الطلبات المؤقتة (مثل "غير هذه الكلمة في هذا الخطاب فقط")
- ابحث عن أنماط التفضيلات العامة
- حدد مستوى الأولوية حسب قوة التعبير
- حدد النطاق (جميع الخطابات، فئة معينة، أم مرة واحدة)

{format_instructions}
"""
        
        prompt = PromptTemplate.from_template(
            template,
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        llm = ChatOpenAI(
            model="gpt-4o",  # Use a simpler model for extraction
            temperature=0.1,
            openai_api_key=self.config.openai_api_key,
            timeout=15,
            max_retries=2
        )
        
        return prompt | llm | self.parser
    
    def _load_memory(self):
        """Load memory from file."""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for instruction_data in data.get("instructions", []):
                    instruction = MemoryInstruction.from_dict(instruction_data)
                    self.instructions[instruction.id] = instruction
                    
                logger.info(f"Loaded {len(self.instructions)} instructions from memory")
            else:
                logger.info("No existing memory file found, starting fresh")
                
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            self.instructions = {}
    
    def _save_memory(self):
        """Save memory to file."""
        try:
            # Ensure directory exists
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "instructions": [instr.to_dict() for instr in self.instructions.values()],
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"Saved {len(self.instructions)} instructions to memory")
            
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    @service_error_handler
    def process_message_async(self, session_id: str, message: str, context: str = ""):
        """
        Process a message asynchronously to extract instructions.
        This runs in the background without blocking the main chat flow.
        """
        def _process():
            try:
                with ErrorContext("process_memory_message", {"session_id": session_id}):
                    self._extract_and_store_instructions(session_id, message, context)
            except Exception as e:
                logger.error(f"Background memory processing failed: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=_process, daemon=True)
        thread.start()
    
    def _extract_and_store_instructions(self, session_id: str, message: str, context: str):
        """Extract and store instructions from a message."""
        try:
            # Use the extraction chain
            result = self.extraction_chain.invoke({
                "user_message": message,
                "context": context
            })
            
            if not isinstance(result, dict):
                logger.warning(f"Unexpected extraction result type: {type(result)}")
                return
            
            extraction = InstructionExtraction(**result)
            
            if extraction.has_instruction:
                self._store_instruction(session_id, extraction, message)
                
        except Exception as e:
            logger.error(f"Failed to extract instructions from message: {e}")
    
    def _store_instruction(self, session_id: str, extraction: InstructionExtraction, original_message: str):
        """Store a new instruction in memory."""
        with self.memory_lock:
            # Generate unique ID
            instruction_id = f"instr_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.instructions)}"
            
            # Check for conflicts
            if extraction.replaces_instruction:
                old_instruction_id = extraction.replaces_instruction
                if old_instruction_id in self.instructions:
                    self.instructions[old_instruction_id].is_active = False
                    logger.info(f"Deactivated conflicting instruction: {old_instruction_id}")
            
            # Create new instruction
            instruction = MemoryInstruction(
                id=instruction_id,
                instruction_text=extraction.instruction_text,
                instruction_type=extraction.instruction_type,
                priority=extraction.priority,
                scope=extraction.scope,
                category=extraction.category,
                created_at=datetime.now(),
                last_used=datetime.now(),
                source_message=original_message
            )
            
            self.instructions[instruction_id] = instruction
            
            # Associate with session
            if session_id not in self.session_memories:
                self.session_memories[session_id] = []
            self.session_memories[session_id].append(instruction_id)
            
            # Save to file
            self._save_memory()
            
            logger.info(f"Stored new instruction: {instruction_id} - {extraction.instruction_text[:50]}...")
    
    def get_relevant_instructions(
        self, 
        category: str = None,
        session_id: str = None,
        max_instructions: int = 10
    ) -> List[MemoryInstruction]:
        """Get relevant instructions for letter generation."""
        with self.memory_lock:
            relevant_instructions = []
            
            for instruction in self.instructions.values():
                if not instruction.is_active:
                    continue
                
                # Check scope
                if instruction.scope == "all_letters":
                    relevant_instructions.append(instruction)
                elif instruction.scope == "category_specific" and instruction.category == category:
                    relevant_instructions.append(instruction)
                elif instruction.scope == "one_time" and session_id:
                    # One-time instructions only apply to the session they were created in
                    if session_id in self.session_memories:
                        if instruction.id in self.session_memories[session_id]:
                            relevant_instructions.append(instruction)
            
            # Sort by priority (highest first) and usage frequency
            relevant_instructions.sort(
                key=lambda x: (x.priority, x.usage_count),
                reverse=True
            )
            
            # Update usage stats
            now = datetime.now()
            for instruction in relevant_instructions[:max_instructions]:
                instruction.last_used = now
                instruction.usage_count += 1
            
            # Save updated stats
            if relevant_instructions:
                self._save_memory()
            
            return relevant_instructions[:max_instructions]
    
    def format_instructions_for_prompt(
        self, 
        category: str = None,
        session_id: str = None
    ) -> str:
        """Format relevant instructions for inclusion in letter generation prompt."""
        instructions = self.get_relevant_instructions(category, session_id)
        
        if not instructions:
            return ""
        
        formatted_sections = {
            "style": [],
            "format": [],
            "content": [],
            "preference": [],
            "other": []
        }
        
        # Categorize instructions
        for instruction in instructions:
            section = formatted_sections.get(instruction.instruction_type, formatted_sections["other"])
            section.append(f"• {instruction.instruction_text}")
        
        # Build formatted output
        output_parts = []
        
        if formatted_sections["style"]:
            output_parts.append("**تفضيلات الأسلوب:**\n" + "\n".join(formatted_sections["style"]))
        
        if formatted_sections["format"]:
            output_parts.append("**تفضيلات التنسيق:**\n" + "\n".join(formatted_sections["format"]))
        
        if formatted_sections["content"]:
            output_parts.append("**تفضيلات المحتوى:**\n" + "\n".join(formatted_sections["content"]))
        
        if formatted_sections["preference"]:
            output_parts.append("**تفضيلات عامة:**\n" + "\n".join(formatted_sections["preference"]))
        
        if formatted_sections["other"]:
            output_parts.append("**تعليمات أخرى:**\n" + "\n".join(formatted_sections["other"]))
        
        if output_parts:
            return "# تعليمات وتفضيلات المستخدم المحفوظة\n\n" + "\n\n".join(output_parts)
        
        return ""
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory service statistics."""
        with self.memory_lock:
            active_instructions = [i for i in self.instructions.values() if i.is_active]
            
            return {
                "total_instructions": len(self.instructions),
                "active_instructions": len(active_instructions),
                "session_memories": len(self.session_memories),
                "instruction_types": {
                    instr_type: len([i for i in active_instructions if i.instruction_type == instr_type])
                    for instr_type in set(i.instruction_type for i in active_instructions)
                },
                "scopes": {
                    scope: len([i for i in active_instructions if i.scope == scope])
                    for scope in set(i.scope for i in active_instructions)
                }
            }
    
    def clear_session_memory(self, session_id: str):
        """Clear memory associated with a session."""
        with self.memory_lock:
            if session_id in self.session_memories:
                del self.session_memories[session_id]
                logger.debug(f"Cleared memory for session: {session_id}")

# Global service instance
_memory_service: Optional[MemoryService] = None

def get_memory_service() -> MemoryService:
    """Get the global memory service instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
