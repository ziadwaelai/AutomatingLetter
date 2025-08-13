# Long-Term Memory Feature Documentation

## Overview

The Long-Term Memory feature adds intelligent instruction learning and retention to the AutomatingLetter application. When users interact with the chat system, an AI agent automatically analyzes messages to extract writing preferences and instructions, storing them for future use in letter generation.

## Key Features

### 🧠 Automatic Instruction Extraction
- **Background Processing**: Instructions are extracted asynchronously without blocking chat flow
- **Context-Aware**: Uses LangChain with GPT-3.5-turbo for intelligent instruction detection
- **Multi-Type Support**: Handles style, format, content, and preference instructions

### 💾 Persistent Memory Storage
- **File-Based Storage**: Instructions stored in `logs/user_memory.json`
- **Session Association**: Links instructions to specific chat sessions
- **Conflict Resolution**: Handles contradictory instructions automatically

### 🎯 Smart Integration
- **Seamless Chat Integration**: Works with existing chat endpoints without API changes
- **Letter Generation Enhancement**: Automatically includes relevant instructions in AI prompts
- **Scope Management**: Instructions can apply to all letters, specific categories, or one-time use

## Architecture

### Components

1. **MemoryService** (`src/services/memory_service.py`)
   - Core service managing instruction extraction and storage
   - Uses LangChain for AI-powered instruction detection
   - Handles memory persistence and retrieval

2. **ChatService Integration** (`src/services/chat_service.py`)
   - Modified to call memory processing in background
   - Passes session context to memory service
   - Cleans up memory when sessions are deleted

3. **Letter Generation Integration** (`src/services/letter_generator.py`)
   - Enhanced prompt template includes memory instructions
   - Context object extended with session_id parameter
   - Instructions formatted and injected into AI prompts

### Data Models

#### InstructionExtraction (Pydantic Model)
```python
class InstructionExtraction(BaseModel):
    has_instruction: bool
    instruction_type: str  # style, format, content, preference
    instruction_text: str
    priority: int         # 1-5 (5 = highest)
    scope: str           # all_letters, category_specific, one_time
    category: Optional[str]
    replaces_instruction: Optional[str]
```

#### MemoryInstruction (Dataclass)
```python
@dataclass
class MemoryInstruction:
    id: str
    instruction_text: str
    instruction_type: str
    priority: int
    scope: str
    category: Optional[str]
    created_at: datetime
    last_used: datetime
    usage_count: int = 0
    is_active: bool = True
    source_message: str = ""
```

## API Endpoints

### Memory Statistics
```http
GET /api/v1/chat/memory/stats
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "total_instructions": 10,
    "active_instructions": 8,
    "session_memories": 3,
    "instruction_types": {
      "style": 5,
      "format": 2,
      "content": 1
    },
    "scopes": {
      "all_letters": 6,
      "category_specific": 2
    }
  }
}
```

### Memory Instructions
```http
GET /api/v1/chat/memory/instructions?category=THANK_YOU&session_id=123
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "instructions": "# تعليمات وتفضيلات المستخدم المحفوظة\n**تفضيلات الأسلوب:**\n• استخدم أسلوباً مختصراً",
    "category": "THANK_YOU",
    "session_id": "123"
  }
}
```

## Usage Examples

### Example 1: Style Preferences
User message: *"أريد أن تكون جميع خطاباتي مختصرة وواضحة"*

**Extracted Instruction:**
- Type: `style`
- Scope: `all_letters`
- Priority: `4`
- Text: "استخدم أسلوباً مختصراً وواضحاً في جميع الخطابات"

### Example 2: Format Requirements
User message: *"لا تستخدم النقاط في خطابات الشكر"*

**Extracted Instruction:**
- Type: `format`
- Scope: `category_specific`
- Category: `THANK_YOU`
- Priority: `3`
- Text: "تجنب استخدام النقاط في خطابات الشكر"

### Example 3: Content Preferences
User message: *"أضف دائماً دعوة للتواصل في نهاية كل خطاب"*

**Extracted Instruction:**
- Type: `content`
- Scope: `all_letters`
- Priority: `5`
- Text: "أضف دعوة للتواصل في نهاية الخطاب"

## Integration Process

### 1. Chat Message Processing
```python
# When user sends a chat message:
chat_service.process_edit_request(...)
  ↓
# Background memory processing:
memory_service.process_message_async(session_id, message, context)
  ↓
# AI extraction:
extraction_chain.invoke({"user_message": message, "context": context})
  ↓
# Storage:
memory_service._store_instruction(session_id, extraction, original_message)
```

### 2. Letter Generation Enhancement
```python
# When generating letters:
letter_service.generate_letter(context)
  ↓
# Memory instructions retrieval:
memory_instructions = memory_service.format_instructions_for_prompt(
    category=context.category,
    session_id=context.session_id
)
  ↓
# Enhanced prompt:
prompt_template.format(
    user_prompt=user_prompt,
    memory_instructions=memory_instructions,
    # ... other variables
)
```

## Configuration

### Memory Service Settings
The memory service uses these configuration options:

- **Model**: GPT-3.5-turbo (for instruction extraction)
- **Temperature**: 0.1 (for consistent extraction)
- **Timeout**: 15 seconds
- **Storage**: `logs/user_memory.json`
- **Max Instructions per Query**: 10

### Scope Types

1. **all_letters**: Instructions apply to all future letters
2. **category_specific**: Instructions apply only to specific letter categories
3. **one_time**: Instructions apply only within the same session

### Priority Levels

- **5**: Critical preferences (always applied)
- **4**: Important preferences
- **3**: Standard preferences
- **2**: Minor preferences
- **1**: Suggestions

## Testing

### Automated Tests

1. **Memory Service Test** (`test_memory_feature.py`)
   - Tests instruction extraction and storage
   - Validates memory retrieval and formatting

2. **Complete Workflow Test** (`test_complete_workflow.py`)
   - Tests end-to-end integration
   - Validates chat service integration
   - Tests letter generation with memory

3. **API Endpoint Test** (`test_api_endpoints.py`)
   - Tests memory API endpoints
   - Validates session management
   - Tests real HTTP requests

### Running Tests
```bash
# Individual tests
python test_memory_feature.py
python test_complete_workflow.py
python test_api_endpoints.py

# Existing test compatibility
python test/test_chat.py
```

## Performance Considerations

### Background Processing
- Memory extraction runs asynchronously to avoid blocking chat responses
- Uses daemon threads for background processing
- Graceful error handling prevents memory issues from affecting main flow

### Memory Management
- Instructions are limited to prevent excessive memory usage
- Session memories are cleaned up when sessions are deleted
- File-based storage provides persistence without database overhead

### AI Usage Optimization
- Uses GPT-3.5-turbo (cheaper) for instruction extraction
- GPT-4 reserved for actual letter generation
- Short timeout and low temperature for efficient extraction

## Error Handling

### Graceful Degradation
- If memory service fails, chat and letter generation continue normally
- Error logging for debugging without user impact
- Lazy loading prevents startup failures

### Error Scenarios
1. **OpenAI API Errors**: Logged but don't block functionality
2. **Storage Errors**: Memory service degrades gracefully
3. **Parsing Errors**: Invalid instructions are discarded safely

## Future Enhancements

### Potential Improvements
1. **User Interface**: Web interface for managing stored instructions
2. **Import/Export**: Ability to backup and restore memory
3. **Analytics**: Usage statistics and instruction effectiveness
4. **Collaborative Memory**: Shared instructions across team members
5. **Advanced Conflict Resolution**: More sophisticated handling of contradictory instructions

### Scalability
1. **Database Storage**: Move from file-based to database storage
2. **Distributed Memory**: Support for multiple application instances
3. **Memory Optimization**: Advanced algorithms for instruction relevance

## Troubleshooting

### Common Issues

1. **Instructions Not Being Extracted**
   - Check OpenAI API key configuration
   - Verify message contains clear preferences
   - Check memory service logs for extraction errors

2. **Instructions Not Applied to Letters**
   - Ensure session_id is passed to letter generation
   - Verify instruction scope matches letter category
   - Check memory service initialization

3. **Memory File Corruption**
   - Delete `logs/user_memory.json` to reset memory
   - Check file permissions
   - Verify JSON format validity

### Debug Commands
```python
# Check memory stats
from src.services.memory_service import get_memory_service
memory_service = get_memory_service()
print(memory_service.get_memory_stats())

# Get instructions for debugging
instructions = memory_service.format_instructions_for_prompt(
    category="GENERAL",
    session_id="test_session"
)
print(instructions)
```

---

## Summary

The Long-Term Memory feature represents a significant enhancement to the AutomatingLetter application, providing intelligent, persistent learning capabilities that improve with use. The implementation maintains backward compatibility while adding powerful new functionality that enhances user experience through personalized letter generation.
