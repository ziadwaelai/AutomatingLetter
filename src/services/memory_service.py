import logging
import json
import tempfile
import shutil
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Annotated, Set
from dataclasses import dataclass, field
from pathlib import Path
from functools import lru_cache
from collections import defaultdict

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from ..config import get_config

logger = logging.getLogger(__name__)

@dataclass
class Instruction:
    """Optimized instruction model with enhanced features."""
    id: str
    text: str
    created_at: datetime
    usage_count: int = 0
    last_used: Optional[datetime] = None
    category: str = "general"
    keywords: Set[str] = field(default_factory=set)
    effectiveness_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "created_at": self.created_at.isoformat(),
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "category": self.category,
            "keywords": list(self.keywords),
            "effectiveness_score": self.effectiveness_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Instruction':
        return cls(
            id=data["id"],
            text=data["text"],
            created_at=datetime.fromisoformat(data["created_at"]),
            usage_count=data.get("usage_count", 0),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            category=data.get("category", "general"),
            keywords=set(data.get("keywords", [])),
            effectiveness_score=data.get("effectiveness_score", 1.0)
        )
    
    def extract_keywords(self) -> Set[str]:
        """Extract keywords from instruction text."""
        import re
        # Extract Arabic keywords (remove common stop words)
        stop_words = {"في", "من", "إلى", "على", "مع", "هذا", "هذه", "التي", "الذي", "كل", "بعض"}
        words = re.findall(r'\b\w+\b', self.text.lower())
        keywords = {word for word in words if len(word) > 2 and word not in stop_words}
        self.keywords = keywords
        return keywords

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_message: str
    action_taken: Optional[str]
    instruction_operation: Optional[str]  # create, update, delete, list

# Optimized memory management with caching
class MemoryCache:
    """Thread-safe memory cache with automatic invalidation."""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes TTL
        self._cache = {}
        self._lock = threading.RLock()
        self._ttl = ttl_seconds
        self._last_modified = {}
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                timestamp, value = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    return value
                else:
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any):
        with self._lock:
            self._cache[key] = (time.time(), value)
    
    def invalidate(self, key: str = None):
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()

# Global instances
MEMORY_FILE = None
_memory_cache = MemoryCache()

def _get_memory_file() -> Path:
    """Get memory file path with caching."""
    global MEMORY_FILE
    if MEMORY_FILE is None:
        MEMORY_FILE = Path('logs/memory.json')
    return MEMORY_FILE

def _load_instructions_cached() -> List[Dict[str, Any]]:
    """Load instructions with caching for better performance."""
    cache_key = "instructions"
    cached = _memory_cache.get(cache_key)
    
    if cached is not None:
        return cached
    
    memory_file = _get_memory_file()
    instructions = []
    
    try:
        if memory_file.exists():
            with open(memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            instructions = data.get("instructions", [])
        
        _memory_cache.set(cache_key, instructions)
        return instructions
    except Exception as e:
        logger.error(f"Failed to load instructions: {e}")
        return []

def _save_data_atomically(data: Dict[str, Any], file_path: Path):
    """Save data atomically to prevent corruption with cache invalidation."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temporary file first
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', 
                                   dir=file_path.parent, 
                                   delete=False, suffix='.tmp') as tmp_file:
        json.dump(data, tmp_file, ensure_ascii=False, indent=2)
        tmp_file_path = tmp_file.name
    
    # Atomic move
    shutil.move(tmp_file_path, file_path)
    
    # Invalidate cache
    _memory_cache.invalidate("instructions")
    logger.debug("Memory cache invalidated after save")

@tool
def load_instructions() -> str:
    """Load all instructions from database with optimized performance."""
    try:
        instructions = _load_instructions_cached()
        
        if not instructions:
            return "لا توجد تعليمات محفوظة حالياً"
        
        # Sort by effectiveness and usage
        sorted_instructions = sorted(
            instructions,
            key=lambda x: (x.get('effectiveness_score', 1.0), x.get('usage_count', 0)),
            reverse=True
        )
        
        result = "التعليمات المحفوظة حالياً:\n"
        for i, instr_data in enumerate(sorted_instructions, 1):
            usage = instr_data.get('usage_count', 0)
            effectiveness = instr_data.get('effectiveness_score', 1.0)
            result += f"{i}. {instr_data['text']} (استخدام: {usage}, فعالية: {effectiveness:.1f})\n"
        return result
        
    except Exception as e:
        logger.error(f"Failed to load instructions: {e}")
        return "خطأ في تحميل التعليمات"

@tool
def add_instruction(instruction_text: str, category: str = "general") -> str:
    """Add new instruction to database with enhanced features."""
    try:
        # Validate input
        if not instruction_text or not instruction_text.strip():
            return "النص المدخل فارغ"
        
        instruction_text = instruction_text.strip()
        
        # Load existing instructions
        instructions = _load_instructions_cached()
        
        # Check for duplicates with improved similarity detection
        for instr_data in instructions:
            if _is_similar_text(instruction_text, instr_data['text'], threshold=0.8):
                # Update existing instruction instead of creating duplicate
                instr_data['usage_count'] = instr_data.get('usage_count', 0) + 1
                instr_data['last_used'] = datetime.now().isoformat()
                instr_data['effectiveness_score'] = min(instr_data.get('effectiveness_score', 1.0) + 0.1, 5.0)
                
                # Save updates
                data = {
                    "instructions": instructions,
                    "last_updated": datetime.now().isoformat(),
                    "stats": {"total_instructions": len(instructions)}
                }
                _save_data_atomically(data, _get_memory_file())
                
                return f"تم تحديث تعليم مشابه موجود: {instr_data['text']}"
        
        # Create new instruction
        instruction_id = f"instr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        new_instruction = Instruction(
            id=instruction_id,
            text=instruction_text,
            created_at=datetime.now(),
            usage_count=1,
            last_used=datetime.now(),
            category=category
        )
        
        # Extract keywords
        new_instruction.extract_keywords()
        
        instructions.append(new_instruction.to_dict())
        
        # Save atomically
        data = {
            "instructions": instructions,
            "last_updated": datetime.now().isoformat(),
            "stats": {"total_instructions": len(instructions)}
        }
        _save_data_atomically(data, _get_memory_file())
        
        logger.info(f"Added instruction: {instruction_text}")
        return f"تم إضافة التعليم الجديد: {instruction_text}"
        
    except Exception as e:
        logger.error(f"Failed to add instruction: {e}")
        return f"خطأ في إضافة التعليم: {e}"

@tool
def update_instruction(old_text: str, new_text: str) -> str:
    """Update existing instruction in database with improved matching."""
    try:
        # Validate input
        if not old_text or not new_text or not old_text.strip() or not new_text.strip():
            return "النص المدخل فارغ"
        
        instructions = _load_instructions_cached()
        
        if not instructions:
            return "لا توجد تعليمات لتحديثها"
        
        updated = False
        best_match = None
        best_similarity = 0
        
        # Find best matching instruction
        for instr_data in instructions:
            similarity = _calculate_similarity(old_text.strip(), instr_data['text'])
            if similarity > best_similarity and similarity > 0.6:  # 60% threshold
                best_similarity = similarity
                best_match = instr_data
        
        if best_match:
            old_value = best_match['text']
            best_match['text'] = new_text.strip()
            best_match['last_used'] = datetime.now().isoformat()
            best_match['usage_count'] = best_match.get('usage_count', 0) + 1
            best_match['effectiveness_score'] = min(best_match.get('effectiveness_score', 1.0) + 0.2, 5.0)
            
            # Update keywords if instruction object
            if 'keywords' in best_match:
                instr_obj = Instruction.from_dict(best_match)
                instr_obj.text = new_text.strip()
                instr_obj.extract_keywords()
                best_match = instr_obj.to_dict()
            
            # Save updates
            data = {
                "instructions": instructions,
                "last_updated": datetime.now().isoformat(),
                "stats": {"total_instructions": len(instructions)}
            }
            _save_data_atomically(data, _get_memory_file())
            
            logger.info(f"Updated instruction: {old_value} -> {new_text}")
            return f"تم تحديث التعليم من '{old_value}' إلى '{new_text}' (تشابه: {best_similarity:.1%})"
        else:
            return f"لم يتم العثور على تعليم مشابه لـ: {old_text}"
            
    except Exception as e:
        logger.error(f"Failed to update instruction: {e}")
        return f"خطأ في تحديث التعليم: {e}"

@tool
def delete_instruction(instruction_text: str) -> str:
    """Delete instruction from database with improved matching."""
    try:
        instructions = _load_instructions_cached()
        
        if not instructions:
            return "لا توجد تعليمات لحذفها"
        
        original_count = len(instructions)
        deleted_instruction = None
        
        # Find and remove best matching instruction
        remaining_instructions = []
        for instr in instructions:
            if _is_similar_text(instruction_text, instr['text'], threshold=0.7):
                deleted_instruction = instr['text']
            else:
                remaining_instructions.append(instr)
        
        if len(remaining_instructions) < original_count:
            # Save updates
            data = {
                "instructions": remaining_instructions,
                "last_updated": datetime.now().isoformat(),
                "stats": {"total_instructions": len(remaining_instructions)}
            }
            _save_data_atomically(data, _get_memory_file())
            
            logger.info(f"Deleted instruction: {deleted_instruction}")
            return f"تم حذف التعليم: {deleted_instruction}"
        else:
            return f"لم يتم العثور على تعليم مطابق لـ: {instruction_text}"
            
    except Exception as e:
        logger.error(f"Failed to delete instruction: {e}")
        return f"خطأ في حذف التعليم: {e}"

@tool 
def get_instructions_for_prompt() -> str:
    """Get formatted instructions for AI prompt with intelligent selection."""
    try:
        instructions = _load_instructions_cached()
        
        if not instructions:
            return ""
        
        # Sort by effectiveness, usage, and recency
        sorted_instructions = sorted(
            instructions,
            key=lambda x: (
                x.get('effectiveness_score', 1.0) * 0.4 +
                min(x.get('usage_count', 0) / 10, 3.0) * 0.4 +
                (1.0 if x.get('last_used') and 
                 (datetime.now() - datetime.fromisoformat(x['last_used'])).days < 7 
                 else 0.5) * 0.2
            ),
            reverse=True
        )[:8]  # Top 8 instructions
        
        # Update usage stats for selected instructions
        current_time = datetime.now().isoformat()
        for instr in sorted_instructions:
            instr['usage_count'] = instr.get('usage_count', 0) + 1
            instr['last_used'] = current_time
        
        # Save updated stats
        if sorted_instructions:
            data = {
                "instructions": instructions,
                "last_updated": current_time,
                "stats": {"total_instructions": len(instructions)}
            }
            _save_data_atomically(data, _get_memory_file())
        
        # Format for AI prompt with categories
        categories = defaultdict(list)
        for instr in sorted_instructions:
            category = instr.get('category', 'general')
            categories[category].append(instr)
        
        formatted = ["## تعليمات من ذاكرة المستخدم:"]
        
        for category, instrs in categories.items():
            if category != 'general':
                formatted.append(f"\n### {category}:")
            for instr in instrs:
                effectiveness = instr.get('effectiveness_score', 1.0)
                usage = instr.get('usage_count', 0)
                formatted.append(f"• {instr['text']} (فعالية: {effectiveness:.1f}, استخدام: {usage})")
        
        return "\n".join(formatted) + "\n"
        
    except Exception as e:
        logger.error(f"Failed to get instructions: {e}")
        return ""

def _calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using multiple methods."""
    if not text1 or not text2:
        return 0.0
    
    # Normalize texts
    text1, text2 = text1.lower().strip(), text2.lower().strip()
    
    if text1 == text2:
        return 1.0
    
    # Jaccard similarity (word-based)
    words1, words2 = set(text1.split()), set(text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    jaccard = len(words1 & words2) / len(words1 | words2)
    
    # Character-based similarity (for Arabic text)
    from difflib import SequenceMatcher
    char_similarity = SequenceMatcher(None, text1, text2).ratio()
    
    # Combined similarity
    return (jaccard * 0.6 + char_similarity * 0.4)

def _is_similar_text(text1: str, text2: str, threshold: float = 0.75) -> bool:
    """Check if two texts are similar with configurable threshold."""
    similarity = _calculate_similarity(text1, text2)
    return similarity >= threshold

class MemoryService:
    """Optimized memory service with enhanced user message handling."""
    
    def __init__(self):
        self.config = get_config()
        self.agent = self._build_agent()
        self._processing_lock = threading.Lock()
        self._last_processed = {}
        logger.info("Optimized memory service initialized")
    
    def _build_agent(self):
        """Build optimized LangGraph agent with memory tools."""
        # Define enhanced tools
        tools = [
            load_instructions,
            add_instruction,
            update_instruction,
            delete_instruction,
            get_instructions_for_prompt
        ]
        
        # Create tool node
        tool_node = ToolNode(tools)
        
        # Create optimized LLM
        llm = ChatOpenAI(
            model='gpt-4o-mini',
            temperature=0.1,
            openai_api_key=self.config.openai_api_key,
            timeout=30,
            max_retries=2
        )
        
        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(tools)
        
        def agent_node(state: AgentState):
            """Enhanced agent decision node with better instruction extraction."""
            
            user_msg = state['user_message']
            operation = state.get('instruction_operation', 'analyze')
            
            # Get current instructions for context
            current_instructions = load_instructions.invoke({})
            
            # Enhanced prompt for better user message understanding
            prompt = f"""
أنت خبير في إدارة ذاكرة التعليمات للمساعد الذكي. حلل رسالة المستخدم بدقة واستخرج المعلومات المفيدة.

التعليمات الحالية:
{current_instructions}

رسالة المستخدم: "{user_msg}"

المهمة المطلوبة: {operation}

قواعد العمل:
1. ابحث عن تعليمات قابلة للتطبيق في المستقبل (أساليب كتابة، تنسيق، تفضيلات)
2. تجنب الطلبات المؤقتة أو الخاصة بحالة واحدة
3. استخدم add_instruction للتعليمات الجديدة المفيدة
4. استخدم update_instruction لتحسين تعليم موجود
5. استخدم delete_instruction لحذف تعليم غير مرغوب
6. ركز على الجودة وليس الكمية

أمثلة على تعليمات مفيدة:
- "إضافة فقرة شكر وتقدير في نهاية الخطاب"
- "استخدام التوقيع الرسمي مع المسمى الوظيفي"
- "الحفاظ على الطابع الرسمي في المراسلات"
- "إضافة التاريخ والمكان بشكل واضح"
- "استخدام الخط العريض للعناوين المهمة"

أمثلة على ما يجب تجنبه:
- طلبات محددة بتاريخ أو شخص معين
- معلومات مؤقتة أو متغيرة
- تفاصيل تقنية معقدة

حلل الرسالة واتخذ الإجراء المناسب:
"""
            
            try:
                response = llm_with_tools.invoke([{"role": "user", "content": prompt}])
                return {"messages": [response]}
            except Exception as e:
                logger.error(f"Agent processing error: {e}")
                return {"messages": []}
        
        # Build optimized graph
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tool_node)
        
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            lambda state: "tools" if state["messages"] and state["messages"][-1].tool_calls else END,
        )
        workflow.add_edge("tools", END)
        
        return workflow.compile()
    
    def process_message(self, message: str, operation: str = "analyze") -> Dict[str, Any]:
        """Process message with enhanced analysis and deduplication."""
        
        # Prevent duplicate processing
        message_hash = str(hash(message.strip().lower()))
        
        with self._processing_lock:
            last_time = self._last_processed.get(message_hash)
            if last_time and (time.time() - last_time) < 10:  # 10 second cooldown
                logger.debug(f"Skipping duplicate message processing: {message[:50]}...")
                return {"status": "skipped", "reason": "duplicate"}
        
        try:
            result = self.agent.invoke({
                "messages": [],
                "user_message": message,
                "action_taken": None,
                "instruction_operation": operation
            })
            
            # Log the action taken
            actions_taken = []
            if result.get("messages"):
                for msg in result["messages"]:
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            tool_name = tool_call['name']
                            actions_taken.append(tool_name)
                            logger.info(f"Agent used tool: {tool_name} for message: {message[:50]}...")
            
            # Update last processed time
            with self._processing_lock:
                self._last_processed[message_hash] = time.time()
                
                # Cleanup old entries (keep last 100)
                if len(self._last_processed) > 100:
                    oldest_items = sorted(self._last_processed.items(), key=lambda x: x[1])[:20]
                    for item_hash, _ in oldest_items:
                        del self._last_processed[item_hash]
            
            return {
                "status": "processed",
                "actions": actions_taken,
                "message_preview": message[:100] + "..." if len(message) > 100 else message
            }
                    
        except Exception as e:
            logger.error(f"Enhanced agent processing failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def process_message_async(self, session_id: str, message: str, context: str = ""):
        """Process message asynchronously with improved error handling."""
        
        def _process():
            try:
                # Determine operation based on context
                operation = "analyze"
                if "update" in context.lower() or "modify" in context.lower():
                    operation = "update"
                elif "delete" in context.lower() or "remove" in context.lower():
                    operation = "delete"
                elif "add" in context.lower() or "create" in context.lower():
                    operation = "create"
                
                result = self.process_message(message, operation)
                
                if result["status"] == "error":
                    logger.error(f"Async processing failed for session {session_id}: {result['error']}")
                elif result["status"] == "processed":
                    logger.info(f"Async processing completed for session {session_id}: {result['actions']}")
                    
            except Exception as e:
                logger.error(f"Async memory processing failed for session {session_id}: {e}")
        
        # Run in daemon thread to prevent blocking
        thread = threading.Thread(target=_process, daemon=True)
        thread.start()
        
    def clear_session_memory(self, session_id: str):
        """Clear session memory (no-op for global memory with logging)."""
        logger.debug(f"Session memory clear requested: {session_id} (global memory system - no action needed)")
    
    def get_instructions_for_prompt(self, max_instructions: int = 8) -> str:
        """Get optimized formatted instructions for AI prompt."""
        try:
            return get_instructions_for_prompt.invoke({})
        except Exception as e:
            logger.error(f"Failed to get instructions for prompt: {e}")
            return ""
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        try:
            instructions = _load_instructions_cached()
            
            if not instructions:
                return {
                    "total_instructions": 0, 
                    "last_updated": None,
                    "cache_hits": 0,
                    "avg_effectiveness": 0.0
                }
            
            total_usage = sum(instr.get('usage_count', 0) for instr in instructions)
            avg_effectiveness = sum(instr.get('effectiveness_score', 1.0) for instr in instructions) / len(instructions)
            
            # Category distribution
            categories = defaultdict(int)
            for instr in instructions:
                categories[instr.get('category', 'general')] += 1
            
            return {
                "total_instructions": len(instructions),
                "total_usage": total_usage,
                "avg_effectiveness": round(avg_effectiveness, 2),
                "categories": dict(categories),
                "last_updated": datetime.now().isoformat(),
                "top_instruction": max(instructions, key=lambda x: x.get('usage_count', 0))['text'][:50] + "..." if instructions else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}
    
    def format_instructions_for_prompt(self, category: str = None, session_id: str = None) -> str:
        """Enhanced method for AI prompt integration - returns ALL instructions regardless of category."""
        try:
            instructions = _load_instructions_cached()
            
            if not instructions:
                return ""
            
            # Use ALL instructions without category filtering
            return self._format_all_instructions(instructions)
            
        except Exception as e:
            logger.error(f"Failed to format instructions: {e}")
            return ""
    
    def _format_all_instructions(self, instructions: List[Dict[str, Any]]) -> str:
        """Format ALL instructions for AI prompt - just the text without categories."""
        try:
            if not instructions:
                return ""
            
            # Sort by effectiveness, usage, and recency
            sorted_instructions = sorted(
                instructions,
                key=lambda x: (
                    x.get('effectiveness_score', 1.0) * 0.4 +
                    min(x.get('usage_count', 0) / 10, 3.0) * 0.4 +
                    (1.0 if x.get('last_used') and 
                     (datetime.now() - datetime.fromisoformat(x['last_used'])).days < 7 
                     else 0.5) * 0.2
                ),
                reverse=True
            )[:8]  # Top 8 instructions
            
            # Update usage stats for selected instructions
            current_time = datetime.now().isoformat()
            for instr in sorted_instructions:
                instr['usage_count'] = instr.get('usage_count', 0) + 1
                instr['last_used'] = current_time
            
            # Save updated stats (need to reload full instructions list to update)
            if sorted_instructions:
                all_instructions = _load_instructions_cached()
                # Update the stats in the original instructions list
                instr_ids = {instr['id']: instr for instr in all_instructions}
                for updated_instr in sorted_instructions:
                    if updated_instr['id'] in instr_ids:
                        instr_ids[updated_instr['id']]['usage_count'] = updated_instr['usage_count']
                        instr_ids[updated_instr['id']]['last_used'] = updated_instr['last_used']
                
                data = {
                    "instructions": all_instructions,
                    "last_updated": current_time,
                    "stats": {"total_instructions": len(all_instructions)}
                }
                _save_data_atomically(data, _get_memory_file())
            
            # Format for AI prompt - just the instruction text
            formatted = ["## تعليمات من ذاكرة المستخدم:"]
            
            for instr in sorted_instructions:
                formatted.append(f"• {instr['text']}")
            
            return "\n".join(formatted) + "\n"
            
        except Exception as e:
            logger.error(f"Failed to format all instructions: {e}")
            return ""
    
    def _format_filtered_instructions(self, instructions: List[Dict[str, Any]]) -> str:
        """Format filtered instructions for AI prompt with intelligent selection."""
        try:
            if not instructions:
                return ""
            
            # Sort by effectiveness, usage, and recency
            sorted_instructions = sorted(
                instructions,
                key=lambda x: (
                    x.get('effectiveness_score', 1.0) * 0.4 +
                    min(x.get('usage_count', 0) / 10, 3.0) * 0.4 +
                    (1.0 if x.get('last_used') and 
                     (datetime.now() - datetime.fromisoformat(x['last_used'])).days < 7 
                     else 0.5) * 0.2
                ),
                reverse=True
            )[:8]  # Top 8 instructions
            
            # Update usage stats for selected instructions
            current_time = datetime.now().isoformat()
            for instr in sorted_instructions:
                instr['usage_count'] = instr.get('usage_count', 0) + 1
                instr['last_used'] = current_time
            
            # Save updated stats (need to reload full instructions list to update)
            if sorted_instructions:
                all_instructions = _load_instructions_cached()
                # Update the stats in the original instructions list
                instr_ids = {instr['id']: instr for instr in all_instructions}
                for updated_instr in sorted_instructions:
                    if updated_instr['id'] in instr_ids:
                        instr_ids[updated_instr['id']]['usage_count'] = updated_instr['usage_count']
                        instr_ids[updated_instr['id']]['last_used'] = updated_instr['last_used']
                
                data = {
                    "instructions": all_instructions,
                    "last_updated": current_time,
                    "stats": {"total_instructions": len(all_instructions)}
                }
                _save_data_atomically(data, _get_memory_file())
            
            # Format for AI prompt with categories
            categories = defaultdict(list)
            for instr in sorted_instructions:
                category = instr.get('category', 'general')
                categories[category].append(instr)
            
            formatted = ["## تعليمات من ذاكرة المستخدم:"]
            
            for category, instrs in categories.items():
                if category != 'general':
                    formatted.append(f"\n### {category}:")
                for instr in instrs:
                    effectiveness = instr.get('effectiveness_score', 1.0)
                    usage = instr.get('usage_count', 0)
                    formatted.append(f"• {instr['text']} (فعالية: {effectiveness:.1f}, استخدام: {usage})")
            
            return "\n".join(formatted) + "\n"
            
        except Exception as e:
            logger.error(f"Failed to format filtered instructions: {e}")
            return ""
    
    def get_formatted_instructions(self, category: str = None, session_id: str = None) -> str:
        """Get formatted instructions for display with enhanced features."""
        return self.format_instructions_for_prompt(category, session_id)

# Global service instance
_memory_service: Optional[MemoryService] = None

def get_memory_service() -> MemoryService:
    """Get the memory service instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service