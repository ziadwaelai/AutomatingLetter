import logging
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Annotated
from dataclasses import dataclass
from pathlib import Path

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
    """Simple instruction model."""
    id: str
    text: str
    created_at: datetime
    usage_count: int = 0
    last_used: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "created_at": self.created_at.isoformat(),
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Instruction':
        return cls(
            id=data["id"],
            text=data["text"],
            created_at=datetime.fromisoformat(data["created_at"]),
            usage_count=data.get("usage_count", 0),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None
        )

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_message: str
    action_taken: Optional[str]

# Global memory file path - will be set by service
MEMORY_FILE = None

def _get_memory_file() -> Path:
    """Get memory file path."""
    global MEMORY_FILE
    if MEMORY_FILE is None:
        MEMORY_FILE = Path('logs/memory.json')
    return MEMORY_FILE

def _save_data_atomically(data: Dict[str, Any], file_path: Path):
    """Save data atomically to prevent corruption."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temporary file first
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', 
                                   dir=file_path.parent, 
                                   delete=False, suffix='.tmp') as tmp_file:
        json.dump(data, tmp_file, ensure_ascii=False, indent=2)
        tmp_file_path = tmp_file.name
    
    # Atomic move
    shutil.move(tmp_file_path, file_path)

@tool
def load_instructions() -> str:
    """Load all instructions from database."""
    try:
        memory_file = _get_memory_file()
        if memory_file.exists():
            with open(memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            instructions = data.get("instructions", [])
            if not instructions:
                return "لا توجد تعليمات محفوظة حالياً"
            
            result = "التعليمات المحفوظة حالياً:\n"
            for i, instr_data in enumerate(instructions, 1):
                result += f"{i}. {instr_data['text']}\n"
            return result
        else:
            return "لا توجد تعليمات محفوظة حالياً"
    except Exception as e:
        logger.error(f"Failed to load instructions: {e}")
        return "خطأ في تحميل التعليمات"

@tool
def add_instruction(instruction_text: str) -> str:
    """Add new instruction to database."""
    try:
        # Validate input
        if not instruction_text or not instruction_text.strip():
            return "النص المدخل فارغ"
        
        instruction_text = instruction_text.strip()
        memory_file = _get_memory_file()
        
        # Load existing instructions
        instructions = []
        if memory_file.exists():
            with open(memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                instructions = data.get("instructions", [])
        
        # Check for duplicates
        for instr_data in instructions:
            if _is_similar_text(instruction_text, instr_data['text']):
                return f"تعليم مشابه موجود بالفعل: {instr_data['text']}"
        
        # Add new instruction
        instruction_id = f"instr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        new_instruction = Instruction(
            id=instruction_id,
            text=instruction_text,
            created_at=datetime.now(),
            usage_count=0,
            last_used=datetime.now()
        )
        
        instructions.append(new_instruction.to_dict())
        
        # Save atomically
        data = {
            "instructions": instructions,
            "last_updated": datetime.now().isoformat()
        }
        _save_data_atomically(data, memory_file)
        
        logger.info(f"Added instruction: {instruction_text}")
        return f"تم إضافة التعليم: {instruction_text}"
        
    except Exception as e:
        logger.error(f"Failed to add instruction: {e}")
        return f"خطأ في إضافة التعليم: {e}"

@tool
def update_instruction(old_text: str, new_text: str) -> str:
    """Update existing instruction in database."""
    try:
        # Validate input
        if not old_text or not new_text or not old_text.strip() or not new_text.strip():
            return "النص المدخل فارغ"
        
        memory_file = _get_memory_file()
        if not memory_file.exists():
            return "لا توجد تعليمات لتحديثها"
        
        with open(memory_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        instructions = data.get("instructions", [])
        updated = False
        
        for instr_data in instructions:
            if _is_similar_text(old_text.strip(), instr_data['text']):
                instr_data['text'] = new_text.strip()
                instr_data['last_used'] = datetime.now().isoformat()
                updated = True
                break
        
        if updated:
            data['last_updated'] = datetime.now().isoformat()
            _save_data_atomically(data, memory_file)
            logger.info(f"Updated instruction: {old_text} -> {new_text}")
            return f"تم تحديث التعليم من '{old_text}' إلى '{new_text}'"
        else:
            return f"لم يتم العثور على التعليم: {old_text}"
            
    except Exception as e:
        logger.error(f"Failed to update instruction: {e}")
        return f"خطأ في تحديث التعليم: {e}"

@tool
def delete_instruction(instruction_text: str) -> str:
    """Delete instruction from database."""
    try:
        memory_file = _get_memory_file()
        if not memory_file.exists():
            return "لا توجد تعليمات لحذفها"
        
        with open(memory_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        instructions = data.get("instructions", [])
        original_count = len(instructions)
        
        # Remove matching instruction
        instructions = [
            instr for instr in instructions 
            if not _is_similar_text(instruction_text, instr['text'])
        ]
        
        if len(instructions) < original_count:
            data['instructions'] = instructions
            data['last_updated'] = datetime.now().isoformat()
            
            _save_data_atomically(data, memory_file)
            
            logger.info(f"Deleted instruction: {instruction_text}")
            return f"تم حذف التعليم: {instruction_text}"
        else:
            return f"لم يتم العثور على التعليم: {instruction_text}"
            
    except Exception as e:
        logger.error(f"Failed to delete instruction: {e}")
        return f"خطأ في حذف التعليم: {e}"

@tool 
def get_instructions_for_prompt() -> str:
    """Get formatted instructions for AI prompt."""
    try:
        memory_file = _get_memory_file()
        if not memory_file.exists():
            return ""
        
        with open(memory_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        instructions = data.get("instructions", [])
        if not instructions:
            return ""
        
        # Sort by usage and recency
        sorted_instructions = sorted(
            instructions,
            key=lambda x: (x.get('usage_count', 0), x.get('last_used', x['created_at'])),
            reverse=True
        )[:5]  # Top 5 instructions
        
        # Update usage stats (only if we actually have instructions to use)
        if sorted_instructions:
            for instr in sorted_instructions:
                instr['usage_count'] = instr.get('usage_count', 0) + 1
                instr['last_used'] = datetime.now().isoformat()
            
            # Save updated stats
            data['last_updated'] = datetime.now().isoformat()
            _save_data_atomically(data, memory_file)
        
        # Format for AI prompt
        formatted = ["## تعليمات من ذاكرة المستخدم:"]
        for instr in sorted_instructions:
            formatted.append(f"• {instr['text']}")
        
        return "\n".join(formatted) + "\n"
        
    except Exception as e:
        logger.error(f"Failed to get instructions: {e}")
        return ""

def _is_similar_text(text1: str, text2: str) -> bool:
    """Check if two texts are similar using word overlap."""
    if not text1 or not text2:
        return False
    
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return False
    
    overlap = len(words1 & words2)
    total = len(words1 | words2)
    
    return (overlap / total) > 0.5 if total > 0 else False

class MemoryService:
    """Simple memory service using LangGraph agent."""
    
    def __init__(self):
        self.config = get_config()
        self.agent = self._build_agent()
        logger.info("Memory service initialized with LangGraph agent")
    
    def _build_agent(self):
        """Build LangGraph agent with memory tools."""
        # Define tools
        tools = [
            load_instructions,
            add_instruction,
            update_instruction,
            delete_instruction,
            get_instructions_for_prompt
        ]
        
        # Create tool node
        tool_node = ToolNode(tools)
        
        # Create LLM
        llm = ChatOpenAI(
            model='gpt-4o-mini',
            temperature=0.1,
            openai_api_key=self.config.openai_api_key
        )
        
        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(tools)
        
        def agent_node(state: AgentState):
            """Agent decision node."""
            # Get current instructions first
            current_instructions = load_instructions.invoke({})
            
            prompt = f"""
أنت مساعد ذكي لإدارة ذاكرة التعليمات. حلل رسالة المستخدم واستخرج أي تعليمات مفيدة للمستقبل.

التعليمات الحالية:
{current_instructions}

رسالة المستخدم: {state['user_message']}

المهمة:
1. حلل الرسالة لاستخراج تعليمات مفيدة (مثل: طلبات تنسيق، أساليب كتابة، تفضيلات معينة)
2. إذا وجدت تعليم جديد مفيد، استخدم add_instruction لحفظه
3. إذا كان التعليم مشابه لموجود، استخدم update_instruction لتحديثه
4. ركز على التعليمات القابلة للتطبيق في المستقبل

أمثلة على التعليمات المفيدة:
- "إضافة فقرة شكر وتقدير"
- "استخدام توقيع رسمي مع المسمى الوظيفي"
- "الحفاظ على الطابع الرسمي"
- "إضافة تفاصيل إضافية"

قم بتحليل الرسالة واتخذ الإجراء المناسب:
"""
            
            response = llm_with_tools.invoke([{"role": "user", "content": prompt}])
            return {"messages": [response]}
        
        # Build graph
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tool_node)
        
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            lambda state: "tools" if state["messages"][-1].tool_calls else END,
        )
        workflow.add_edge("tools", END)
        
        return workflow.compile()
    
    def process_message(self, message: str):
        """Process message using LangGraph agent."""
        try:
            result = self.agent.invoke({
                "messages": [],
                "user_message": message,
                "action_taken": None
            })
            
            # Log the action taken
            if result.get("messages"):
                last_message = result["messages"][-1]
                if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                    tool_name = last_message.tool_calls[0]['name']
                    logger.info(f"Agent used tool: {tool_name}")
                    
        except Exception as e:
            logger.error(f"Agent processing failed: {e}")
    
    def process_message_async(self, session_id: str, message: str, context: str = ""):
        """Process message asynchronously for backward compatibility."""
        import threading
        
        def _process():
            try:
                self.process_message(message)
            except Exception as e:
                logger.error(f"Async memory processing failed: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=_process, daemon=True)
        thread.start()
        
    def clear_session_memory(self, session_id: str):
        """Clear session memory (no-op for global memory)."""
        logger.debug(f"Session memory clear requested: {session_id} (no-op for global memory)")
    
    def get_instructions_for_prompt(self, max_instructions: int = 5) -> str:
        """Get formatted instructions for AI prompt."""
        return get_instructions_for_prompt.invoke({})
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        try:
            memory_file = _get_memory_file()
            if not memory_file.exists():
                return {"total_instructions": 0, "last_updated": None}
            
            with open(memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            instructions = data.get("instructions", [])
            return {
                "total_instructions": len(instructions),
                "last_updated": data.get("last_updated")
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"total_instructions": 0, "last_updated": None}
    
    def format_instructions_for_prompt(self, category: str = None, session_id: str = None) -> str:
        """Main method for AI prompt integration."""
        return self.get_instructions_for_prompt()
    
    def get_formatted_instructions(self, category: str = None, session_id: str = None) -> str:
        """Get formatted instructions for display."""
        return self.get_instructions_for_prompt()

# Global service instance
_memory_service: Optional[MemoryService] = None

def get_memory_service() -> MemoryService:
    """Get the memory service instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service