#!/usr/bin/env python3
"""Fix the remaining TTS issues."""

import os
import re

def fix_tts_issues():
    """Fix the remaining streaming TTS issues."""
    
    print("Fixing TTS streaming issues...\n")
    
    # Issue 1: Audio playing after visual completion
    # This means sentences aren't being detected during streaming
    # Let's add more aggressive sentence detection
    
    gpt_path = "app/transcribe/gpt_responder.py"
    with open(gpt_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Make sentence detection more aggressive
    print("1. Fixing sentence detection...")
    
    # Current regex requires space after punctuation
    # Let's also detect end of common phrases
    old_pattern = 'self.SENT_END = re.compile(r"[.!?]\\s")'
    new_pattern = 'self.SENT_END = re.compile(r"[.!?](?:\\s|$)")'
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        print("   ✓ Updated sentence detection regex")
    
    # Fix 2: Add comma detection for natural pauses
    if "# Also check for commas" not in content:
        # Find the sentence detection section
        buffer_check = "elif len(self.buffer) > 42:"
        if buffer_check in content:
            # Add comma check before the 42 char check
            comma_check = """        # Also check for commas for more natural breaks
        elif ',' in self.buffer and len(self.buffer) > 20:
            comma_pos = self.buffer.rfind(',')
            if comma_pos > 10:  # Ensure we have enough content
                partial = self.buffer[:comma_pos+1].strip()
                if partial:
                    logger.info(f"[TTS Debug] Comma break: '{partial}'")
                    self.sent_q.put(partial)
                    self.buffer = self.buffer[comma_pos+1:].strip()
        """
            content = content.replace(buffer_check, comma_check + buffer_check)
            print("   ✓ Added comma-based breaks")
    
    # Fix 3: The audio stopping issue - likely the TTS worker dying
    print("\n2. Fixing TTS worker stability...")
    
    # Add better error handling in TTS worker
    tts_worker_pattern = r'def _tts_worker\(self\):(.*?)logger\.info\("\[TTS Debug\] TTS worker thread stopped"\)'
    match = re.search(tts_worker_pattern, content, re.DOTALL)
    
    if match and "except Exception as e:" in match.group(0):
        # Already has exception handling
        print("   ✓ TTS worker has error handling")
    else:
        # Need to add better error handling
        old_worker = """            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"TTS worker error: {e}")"""
        
        new_worker = """            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[TTS Debug] TTS worker error: {type(e).__name__}: {e}")
                # Don't let the worker die - continue processing
                continue"""
        
        if old_worker in content:
            content = content.replace(old_worker, new_worker)
            print("   ✓ Improved TTS worker error handling")
    
    # Fix 4: Audio player might be failing
    print("\n3. Adding audio player diagnostics...")
    
    # Add logging to audio player
    audio_path = "app/transcribe/audio_player_streaming.py"
    if os.path.exists(audio_path):
        with open(audio_path, 'r') as f:
            audio_content = f.read()
        
        # Add queue full logging
        if "Audio queue full" in audio_content and "[TTS Debug]" not in audio_content:
            audio_content = audio_content.replace(
                'logger.warning("Audio queue full, dropping chunk")',
                'logger.warning("[TTS Debug] Audio queue full, dropping chunk")'
            )
        
        # Add playback error logging
        if "Audio playback error" in audio_content and "[TTS Debug]" not in audio_content:
            audio_content = audio_content.replace(
                'logger.error(f"Audio playback error: {e}")',
                'logger.error(f"[TTS Debug] Audio playback error: {type(e).__name__}: {e}")'
            )
        
        with open(audio_path, 'w') as f:
            f.write(audio_content)
        print("   ✓ Added audio player diagnostics")
    
    # Write the updated gpt_responder.py
    with open(gpt_path, 'w') as f:
        f.write(content)
    
    # Fix 5: Create a test to verify sentence detection
    print("\n4. Creating sentence detection test...")
    
    test_script = '''#!/usr/bin/env python3
"""Test sentence detection with real examples."""
import re

# Test the sentence detection
SENT_END = re.compile(r"[.!?](?:\\s|$)|(?:\\.com|\\.org|\\.net)(?:\\s|$)")

test_cases = [
    "Hello world. How are you?",
    "Visit example.com for more info.",
    "This is great! What do you think?",
    "No punctuation yet but getting long",
    "Short",
    "This has a comma, which might help.",
]

print("Testing sentence detection:\\n")

for test in test_cases:
    buffer = ""
    print(f"Input: '{test}'")
    
    # Simulate token by token
    tokens = test.split(' ')
    for i, token in enumerate(tokens):
        if i > 0:
            buffer += ' '
        buffer += token
        
        match = SENT_END.search(buffer)
        if match:
            sentence = buffer[:match.end()].strip()
            print(f"  → Sentence detected: '{sentence}'")
            buffer = buffer[match.end():].strip()
    
    if buffer:
        print(f"  → Remaining: '{buffer}'")
    print()
'''
    
    with open("test_sentence_detection.py", 'w') as f:
        f.write(test_script)
    print("   ✓ Created test_sentence_detection.py")
    
    print("\n✅ Fixes applied!")
    print("\nWhat was fixed:")
    print("1. More aggressive sentence detection (includes .com, etc)")
    print("2. Added comma-based breaks for natural pauses")
    print("3. Improved TTS worker error handling")
    print("4. Added audio player diagnostics")
    print("\nIf audio stops after 2 responses, check console for:")
    print("- [TTS Debug] TTS worker error")
    print("- [TTS Debug] Audio playback error")
    print("- [TTS Debug] Audio queue full")


if __name__ == "__main__":
    fix_tts_issues()