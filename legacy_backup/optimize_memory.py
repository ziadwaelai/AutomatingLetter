"""
Enhanced Memory Service Optimization Script
This script will:
1. Load existing memory data
2. Apply enhanced deduplication and normalization  
3. Optimize the instruction text quality
4. Test the enhanced memory service
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.memory_service import get_memory_service
import json
from pathlib import Path

def backup_original_memory():
    """Create backup of original memory file."""
    memory_file = Path("logs/simple_memory.json")
    backup_file = Path("logs/simple_memory_backup.json")
    
    if memory_file.exists():
        import shutil
        shutil.copy(memory_file, backup_file)
        print(f"✅ Backup created: {backup_file}")
        return True
    return False

def analyze_current_memory():
    """Analyze current memory state."""
    memory_file = Path("logs/simple_memory.json")
    
    if not memory_file.exists():
        print("❌ No memory file found")
        return
    
    with open(memory_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    instructions = data.get('instructions', [])
    print(f"\n📊 Current Memory Analysis:")
    print(f"Total instructions: {len(instructions)}")
    
    # Group by type
    by_type = {}
    for instr in instructions:
        instr_type = instr.get('instruction_type', 'unknown')
        if instr_type not in by_type:
            by_type[instr_type] = []
        by_type[instr_type].append(instr['instruction_text'])
    
    for instr_type, texts in by_type.items():
        print(f"\n🏷️ {instr_type.upper()} Instructions ({len(texts)}):")
        for i, text in enumerate(texts, 1):
            print(f"  {i}. {text}")
    
    # Identify potential duplicates
    print(f"\n🔍 Potential Duplicates Analysis:")
    for instr_type, texts in by_type.items():
        if len(texts) > 1:
            print(f"\n{instr_type} type has {len(texts)} instructions - checking for duplicates:")
            for i, text1 in enumerate(texts):
                for j, text2 in enumerate(texts[i+1:], i+1):
                    # Simple similarity check
                    words1 = set(text1.split())
                    words2 = set(text2.split())
                    if words1 and words2:
                        overlap = len(words1 & words2) / len(words1 | words2)
                        if overlap > 0.5:
                            print(f"  ⚠️ Similar: '{text1}' vs '{text2}' (similarity: {overlap:.2f})")

def optimize_memory():
    """Optimize memory using enhanced service."""
    print(f"\n🔧 Starting Memory Optimization...")
    
    try:
        # Get the enhanced memory service
        memory_service = get_memory_service()
        
        print(f"Memory service loaded: {type(memory_service).__name__}")
        
        # Run optimization
        removed_count = memory_service.optimize_memory()
        
        print(f"✅ Optimization complete! Removed {removed_count} duplicate instructions")
        
        # Get updated stats
        stats = memory_service.get_memory_stats()
        print(f"📈 Updated Stats: {stats}")
        
        # Get formatted instructions
        formatted = memory_service.get_formatted_instructions()
        print(f"\n📝 Optimized Instructions:")
        print(formatted)
        
        return True
        
    except Exception as e:
        print(f"❌ Optimization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_features():
    """Test enhanced memory features."""
    print(f"\n🧪 Testing Enhanced Features...")
    
    try:
        memory_service = get_memory_service()
        
        # Test similarity detection
        test_messages = [
            "اجعل الخطاب أكثر اختصاراً",  # Should be similar to existing
            "استخدم فقرات طويلة",  # New format instruction
            "أضف شكر في بداية الخطاب",  # New content instruction
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n{i}. Testing message: '{message}'")
            
            # Process the message
            memory_service.process_message_async("test-session", message)
            
            # Wait a moment for async processing
            import time
            time.sleep(2)
            
        # Check final stats
        final_stats = memory_service.get_memory_stats()
        print(f"\n📊 Final Stats After Testing: {final_stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Enhanced Memory Service Optimization")
    print("=" * 50)
    
    # Step 1: Backup original
    if backup_original_memory():
        print("✅ Original memory backed up")
    
    # Step 2: Analyze current state
    analyze_current_memory()
    
    # Step 3: Optimize memory
    if optimize_memory():
        print("✅ Memory optimization successful")
    else:
        print("❌ Memory optimization failed")
        exit(1)
    
    # Step 4: Test enhanced features
    if test_enhanced_features():
        print("✅ Enhanced features test successful")
    else:
        print("❌ Enhanced features test failed")
    
    print(f"\n🎉 Enhanced Memory Service Optimization Complete!")
    print("Check the optimized memory in logs/simple_memory.json")
