"""
Enhanced Simplified Long-Term Memory Service
Manages user instructions and writing preferences for letter generation.
Features: Advanced duplicate detection, Arabic text normalization, instruction optimization
"""

import logging
import json
import threading
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from threading import Lock
from pathlib import Path
from difflib import SequenceMatcher

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from ..config import get_config
from ..utils import ErrorContext, service_error_handler

logger = logging.getLogger(__name__)

class EnhancedInstructionExtraction(BaseModel):
    """Enhanced model for extracted instructions from user messages."""
    has_instruction: bool = Field(description="Whether the message contains a writing instruction")
    instruction_text_arabic: str = Field(description="The instruction in clear, formal Arabic")
    instruction_type: str = Field(description="Type: style, format, content")

@dataclass
class EnhancedMemoryInstruction:
    """Enhanced stored memory instruction with normalization."""
    id: str
    instruction_text: str  # Always in formal Arabic
    instruction_type: str  # style, format, content
    normalized_text: str   # Normalized for comparison
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
            "normalized_text": self.normalized_text,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
            "usage_count": self.usage_count,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedMemoryInstruction':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            instruction_text=data["instruction_text"],
            instruction_type=data["instruction_type"],
            normalized_text=data.get("normalized_text", data["instruction_text"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]),
            usage_count=data.get("usage_count", 0),
            is_active=data.get("is_active", True)
        )

class EnhancedMemoryService:
    """Enhanced service for managing user instructions and preferences with advanced deduplication."""
    
    def __init__(self):
        """Initialize enhanced memory service."""
        self.config = get_config()
        self.memory_lock = Lock()
        self.memory_file = Path("logs/simple_memory.json")
        
        # Instruction storage - enhanced with normalization
        self.instructions: Dict[str, EnhancedMemoryInstruction] = {}
        
        # AI components for instruction extraction
        self.parser = JsonOutputParser(pydantic_object=EnhancedInstructionExtraction)
        self.extraction_chain = self._build_extraction_chain()
        
        # Load existing memory
        self._load_memory()
        
        logger.info("Enhanced Memory service initialized")
    
    def _build_extraction_chain(self):
        """Build the simplified LangChain for instruction extraction."""
        template = """
أنت مساعد ذكي متخصص في استخراج تعليمات الكتابة من رسائل المستخدمين.

مهمتك: تحليل الرسالة وتحديد التعليمات الخاصة بكتابة الخطابات.

أنواع التعليمات:
1. **style** (الأسلوب): مثل "اكتب بأسلوب مختصر" أو "استخدم لغة رسمية"
2. **format** (التنسيق): مثل "استخدم فقرات قصيرة" أو "تجنب النقاط"
3. **content** (المحتوى): مثل "أضف دعوة للتواصل" أو "اذكر الشكر"

رسالة المستخدم:
{user_message}

تعليمات مهمة:
- إذا وجدت تعليماً عاماً للخطابات، اكتبه بالعربية البسيطة
- تجاهل الطلبات المؤقتة لخطاب واحد فقط
- اجمع التعليمات المشابهة في تعليم واحد واضح

أمثلة:
- "اجعل الخطاب أقصر. أريد خطاباتي مختصرة" → "اكتب خطابات مختصرة"
- "أضف دعوة للتواصل في النهاية دائماً" → "أضف دعوة للتواصل في نهاية كل خطاب"

{format_instructions}
"""
        
        prompt = PromptTemplate.from_template(
            template,
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        llm = ChatOpenAI(
            model="gpt-4.1-nano",
            temperature=0.1,
            openai_api_key=self.config.openai_api_key,
            timeout=15,
            max_retries=2
        )
        
        return prompt | llm | self.parser
    
    def _normalize_arabic_text(self, text: str) -> str:
        """Normalize Arabic text for better comparison and storage."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Normalize Arabic characters
        # Replace various forms of alef
        text = re.sub(r'[آأإ]', 'ا', text)
        # Replace various forms of yaa
        text = re.sub(r'[ى]', 'ي', text)
        # Replace various forms of taa marbouta
        text = re.sub(r'[ة]', 'ه', text)
        
        # Remove diacritics (tashkeel)
        arabic_diacritics = re.compile(r'[\u064B-\u065F\u0670\u0640]')
        text = arabic_diacritics.sub('', text)
        
        # Standardize common instruction patterns
        standardizations = {
            r'اجعل.*مختصر.*': 'اكتب خطابات مختصرة',
            r'اجعل.*قصير.*': 'اكتب خطابات مختصرة', 
            r'اجعل.*مهذب.*': 'اكتب بأسلوب مهذب',
            r'اجعل.*رسمي.*': 'اكتب بأسلوب رسمي',
            r'اجعل.*مختصر.*ورسمي.*': 'اكتب خطابات مختصرة ورسمية',
        }
        
        for pattern, replacement in standardizations.items():
            if re.search(pattern, text, re.IGNORECASE):
                text = replacement
                break
        
        return text.strip()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two Arabic texts."""
        # Normalize both texts
        norm1 = self._normalize_arabic_text(text1)
        norm2 = self._normalize_arabic_text(text2)
        
        # Use sequence matcher for similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Additional semantic checks for Arabic instructions
        keywords1 = set(norm1.split())
        keywords2 = set(norm2.split())
        
        # Check for keyword overlap
        if keywords1 and keywords2:
            keyword_similarity = len(keywords1 & keywords2) / len(keywords1 | keywords2)
            # Weighted average of sequence similarity and keyword similarity
            similarity = (similarity * 0.6) + (keyword_similarity * 0.4)
        
        return similarity
    
    def _load_memory(self):
        """Load memory from file."""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for instruction_data in data.get("instructions", []):
                    instruction = EnhancedMemoryInstruction.from_dict(instruction_data)
                    self.instructions[instruction.id] = instruction
                    
                logger.info(f"Loaded {len(self.instructions)} instructions from simplified memory")
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
                "version": "2.0-simplified"
            }
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"Saved {len(self.instructions)} instructions to simplified memory")
            
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def _has_similar_instruction(self, new_instruction: str, instruction_type: str) -> Optional[str]:
        """Check if a similar instruction already exists."""
        for existing_id, existing_instr in self.instructions.items():
            if (existing_instr.instruction_type == instruction_type and 
                existing_instr.is_active):
                
                # Simple similarity check - contains same key words
                new_words = set(new_instruction.split())
                existing_words = set(existing_instr.instruction_text.split())
                
                # If 70% of words overlap, consider it similar
                overlap = len(new_words & existing_words)
                total_unique = len(new_words | existing_words)
                
                if total_unique > 0 and (overlap / total_unique) > 0.7:
                    return existing_id
        
        return None
    
    @service_error_handler
    def process_message_async(self, session_id: str, message: str, context: str = ""):
        """
        Process a message asynchronously to extract instructions.
        """
        def _process():
            try:
                with ErrorContext("process_memory_message", {"session_id": session_id}):
                    self._extract_and_store_instructions(message)
            except Exception as e:
                logger.error(f"Background memory processing failed: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=_process, daemon=True)
        thread.start()
    
    def _extract_and_store_instructions(self, message: str):
        """Extract and store instructions from a message."""
        try:
            # Use the extraction chain
            result = self.extraction_chain.invoke({
                "user_message": message
            })
            
            if not isinstance(result, dict):
                logger.warning(f"Unexpected extraction result type: {type(result)}")
                return
            
            extraction = EnhancedInstructionExtraction(**result)
            
            if extraction.has_instruction and extraction.instruction_text_arabic.strip():
                self._store_instruction(extraction)
                
        except Exception as e:
            logger.error(f"Failed to extract instructions from message: {e}")
    
    def _store_instruction(self, extraction: EnhancedInstructionExtraction):
        """Store a new instruction in memory with enhanced normalization."""
        with self.memory_lock:
            instruction_text = extraction.instruction_text_arabic.strip()
            normalized_text = self._normalize_arabic_text(instruction_text)
            
            # Check for similar existing instructions using enhanced similarity
            similar_id = self._find_similar_instruction(normalized_text, extraction.instruction_type)
            
            if similar_id:
                # Update existing instruction instead of creating duplicate
                existing = self.instructions[similar_id]
                existing.last_used = datetime.now()
                existing.usage_count += 1
                # Update to better version if new text is more formal
                if len(instruction_text) > len(existing.instruction_text):
                    existing.instruction_text = instruction_text
                    existing.normalized_text = normalized_text
                logger.info(f"Updated existing similar instruction: {similar_id}")
            else:
                # Create new instruction
                instruction_id = f"instr_{extraction.instruction_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                instruction = EnhancedMemoryInstruction(
                    id=instruction_id,
                    instruction_text=instruction_text,
                    instruction_type=extraction.instruction_type,
                    normalized_text=normalized_text,
                    created_at=datetime.now(),
                    last_used=datetime.now()
                )
                
                self.instructions[instruction_id] = instruction
                logger.info(f"Stored new instruction: {instruction_id} - {instruction_text}")
                
            # Save to file
            self._save_memory()
    
    def _find_similar_instruction(self, normalized_text: str, instruction_type: str) -> Optional[str]:
        """Find existing similar instruction using enhanced similarity detection."""
        for existing_id, existing_instr in self.instructions.items():
            if (existing_instr.instruction_type == instruction_type and 
                existing_instr.is_active):
                
                # Calculate similarity
                similarity = self._calculate_similarity(normalized_text, existing_instr.normalized_text)
                
                # If similarity is above threshold, consider it duplicate
                if similarity > 0.85:  # Higher threshold for better accuracy
                    return existing_id
        
        return None
    
    def optimize_memory(self):
        """Optimize stored instructions by removing duplicates and enhancing quality."""
        with self.memory_lock:
            logger.info("Starting memory optimization...")
            
            # Group instructions by type
            grouped_instructions = {}
            for instr in self.instructions.values():
                if instr.instruction_type not in grouped_instructions:
                    grouped_instructions[instr.instruction_type] = []
                grouped_instructions[instr.instruction_type].append(instr)
            
            # Process each group for duplicates
            optimized_instructions = {}
            
            for instr_type, instrs in grouped_instructions.items():
                # Sort by usage count and creation date (most used and recent first)
                instrs.sort(key=lambda x: (x.usage_count, x.created_at), reverse=True)
                
                kept_instructions = []
                for instr in instrs:
                    # Check if this instruction is similar to any already kept
                    is_duplicate = False
                    for kept in kept_instructions:
                        if self._calculate_similarity(instr.normalized_text, kept.normalized_text) > 0.85:
                            # This is a duplicate, merge usage counts into the kept one
                            kept.usage_count += instr.usage_count
                            kept.last_used = max(kept.last_used, instr.last_used)
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        # Enhance the instruction text
                        instr.instruction_text = self._normalize_arabic_text(instr.instruction_text)
                        instr.normalized_text = self._normalize_arabic_text(instr.instruction_text)
                        kept_instructions.append(instr)
                        optimized_instructions[instr.id] = instr
            
            # Update memory with optimized instructions
            removed_count = len(self.instructions) - len(optimized_instructions)
            self.instructions = optimized_instructions
            
            # Save optimized memory
            self._save_memory()
            
            logger.info(f"Memory optimization complete. Removed {removed_count} duplicate instructions.")
            return removed_count

    def get_relevant_instructions(self, max_instructions: int = 5) -> List[EnhancedMemoryInstruction]:
        """Get relevant instructions for letter generation."""
        with self.memory_lock:
            active_instructions = [
                instr for instr in self.instructions.values() 
                if instr.is_active
            ]
            
            # Sort by usage frequency and recency
            active_instructions.sort(
                key=lambda x: (x.usage_count, x.last_used),
                reverse=True
            )
            
            # Update usage stats
            now = datetime.now()
            for instruction in active_instructions[:max_instructions]:
                instruction.last_used = now
                instruction.usage_count += 1
            
            # Save updated stats
            if active_instructions:
                self._save_memory()
            
            return active_instructions[:max_instructions]
    
    def format_instructions_for_prompt(self, category: str = None, session_id: str = None) -> str:
        """Format relevant instructions for inclusion in letter generation prompt."""
        instructions = self.get_relevant_instructions()
        
        if not instructions:
            return ""
        
        # Group by type
        style_instructions = []
        format_instructions = []
        content_instructions = []
        
        for instruction in instructions:
            if instruction.instruction_type == "style":
                style_instructions.append(f"• {instruction.instruction_text}")
            elif instruction.instruction_type == "format":
                format_instructions.append(f"• {instruction.instruction_text}")
            elif instruction.instruction_type == "content":
                content_instructions.append(f"• {instruction.instruction_text}")
        
        # Build formatted output
        output_parts = []
        
        if style_instructions:
            output_parts.append("**تفضيلات الأسلوب:**\n" + "\n".join(style_instructions))
        
        if format_instructions:
            output_parts.append("**تفضيلات التنسيق:**\n" + "\n".join(format_instructions))
        
        if content_instructions:
            output_parts.append("**تفضيلات المحتوى:**\n" + "\n".join(content_instructions))
        
        if output_parts:
            return "# تعليمات المستخدم المحفوظة\n\n" + "\n\n".join(output_parts)
        
        return ""
    
    def get_formatted_instructions(self, category: str = None, session_id: str = None) -> str:
        """Get formatted instructions for display or API response."""
        return self.format_instructions_for_prompt(category, session_id)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory service statistics."""
        with self.memory_lock:
            active_instructions = [i for i in self.instructions.values() if i.is_active]
            
            return {
                "total_instructions": len(self.instructions),
                "active_instructions": len(active_instructions),
                "instruction_types": {
                    instr_type: len([i for i in active_instructions if i.instruction_type == instr_type])
                    for instr_type in set(i.instruction_type for i in active_instructions)
                }
            }
    
    def clear_session_memory(self, session_id: str):
        """Clear memory associated with a session - simplified version does nothing since no session association."""
        logger.debug(f"Session memory clear requested for: {session_id} (simplified version - no action needed)")

# Global service instance
_memory_service: Optional[EnhancedMemoryService] = None

def get_memory_service() -> EnhancedMemoryService:
    """Get the global memory service instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = EnhancedMemoryService()
    return _memory_service
