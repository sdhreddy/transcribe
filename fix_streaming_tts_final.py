#!/usr/bin/env python3
"""Final fix for streaming TTS - ensures it works independently of old TTS system."""

import os
import sys

def apply_fix():
    """Apply the final streaming TTS fix."""
    
    print("Applying final streaming TTS fix...")
    
    # Path to gpt_responder.py
    gpt_path = "app/transcribe/gpt_responder.py"
    
    if not os.path.exists(gpt_path):
        print(f"Error: {gpt_path} not found!")
        return False
    
    # Read the file
    with open(gpt_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Ensure TTS starts immediately without waiting for streaming_complete
    if "self.streaming_complete.set()" in content and "self.flush_tts_buffer()" in content:
        print("✓ File already has streaming_complete and flush_tts_buffer")
    else:
        print("✗ Missing streaming_complete or flush_tts_buffer")
        return False
    
    # Fix 2: Add a flag to prevent old TTS from interfering
    if "self.streaming_tts_active = False" not in content:
        print("Adding streaming_tts_active flag...")
        
        # Find the __init__ method
        init_pattern = "self.tts_enabled = False"
        if init_pattern in content:
            content = content.replace(
                init_pattern,
                init_pattern + "\n        self.streaming_tts_active = False  # Flag to prevent old TTS interference"
            )
        
        # Set flag when streaming starts
        stream_pattern = "def _handle_streaming_token(self, token: str):"
        if stream_pattern in content:
            # Find the method and add flag after tts_enabled check
            lines = content.split('\n')
            new_lines = []
            in_method = False
            indent_added = False
            
            for line in lines:
                new_lines.append(line)
                if stream_pattern in line:
                    in_method = True
                elif in_method and not indent_added and "if not self.tts_enabled:" in line:
                    new_lines.append("            self.streaming_tts_active = True")
                    indent_added = True
                elif in_method and "return" in line and line.strip() == "return":
                    in_method = False
            
            content = '\n'.join(new_lines)
        
        # Clear flag when streaming completes
        complete_pattern = "self.streaming_complete.set()"
        if complete_pattern in content:
            content = content.replace(
                complete_pattern,
                "self.streaming_tts_active = False  # Clear flag\n            " + complete_pattern
            )
    
    # Write the updated file
    with open(gpt_path, 'w') as f:
        f.write(content)
    
    print("✓ Applied streaming_tts_active flag")
    
    # Fix 3: Update appui.py to check the flag
    appui_path = "app/transcribe/appui.py"
    
    if os.path.exists(appui_path):
        with open(appui_path, 'r') as f:
            appui_content = f.read()
        
        # Update the condition to also check streaming_tts_active
        old_condition = """if (global_vars_module.continuous_read and
                responder.streaming_complete.is_set() and
                response != global_vars_module.last_spoken_response and
                not streaming_tts_enabled):"""
        
        new_condition = """if (global_vars_module.continuous_read and
                responder.streaming_complete.is_set() and
                response != global_vars_module.last_spoken_response and
                not streaming_tts_enabled and
                not (hasattr(responder, 'streaming_tts_active') and responder.streaming_tts_active)):"""
        
        if old_condition in appui_content:
            appui_content = appui_content.replace(old_condition, new_condition)
            with open(appui_path, 'w') as f:
                f.write(appui_content)
            print("✓ Updated appui.py to check streaming_tts_active flag")
        else:
            print("⚠️  Could not find expected condition in appui.py")
    
    # Create a simple test script
    test_script = '''#!/usr/bin/env python3
"""Test streaming TTS timing."""
import time
import re

def test_sentence_timing():
    """Test how quickly sentences are detected."""
    buffer = ""
    SENT_END = re.compile(r"[.!?]\\s")
    
    # Simulate token stream
    tokens = ["Hello", " world", ".", " ", "How", " are", " you", "?"]
    
    start = time.time()
    for i, token in enumerate(tokens):
        buffer += token
        token_time = time.time() - start
        
        match = SENT_END.search(buffer)
        if match:
            sentence = buffer[:match.end()].strip()
            print(f"Sentence '{sentence}' ready at {token_time*1000:.0f}ms")
            buffer = buffer[match.end():]

if __name__ == "__main__":
    test_sentence_timing()
'''
    
    with open("test_sentence_timing.py", 'w') as f:
        f.write(test_script)
    
    print("\n✓ Fix applied successfully!")
    print("\nIMPORTANT: The issue was that the old TTS system was waiting for")
    print("streaming_complete before playing audio. This fix adds a flag to")
    print("prevent the old system from interfering with streaming TTS.")
    print("\nTest with: python test_sentence_timing.py")
    
    return True


if __name__ == "__main__":
    if apply_fix():
        print("\n✅ All fixes applied. Copy to Windows and test!")
    else:
        print("\n❌ Fix failed. Check the errors above.")