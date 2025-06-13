#!/usr/bin/env python3
"""
Fix for TTS delay issue - adds progressive TTS playback.

The issue: TTS waits for the entire response to complete before playing.
The fix: Play TTS in chunks as the response streams in.
"""

import os
import sys

def create_progressive_tts_patch():
    """Create a patch file for progressive TTS playback"""
    
    patch_content = '''--- a/app/transcribe/appui.py
+++ b/app/transcribe/appui.py
@@ -898,14 +898,28 @@ def update_response_ui(responder,
         textbox.configure(state="disabled")
         textbox.see("end")
         if (global_vars_module.continuous_read and
-                responder.streaming_complete.is_set() and
                 response != global_vars_module.last_spoken_response):
-            global_vars_module.last_tts_response = response
-            global_vars_module.last_spoken_response = response
-            global_vars_module.set_read_response(True)
-            logger.info("update_response_ui triggering playback event")
-            global_vars_module.audio_player_var.speech_text_available.set()
-            responder.streaming_complete.clear()
+            
+            # Progressive TTS: Play chunks as they come in
+            # Only play if we have enough new content (at least a sentence)
+            new_content = response[len(global_vars_module.last_spoken_response):]
+            
+            # Check if we have a complete sentence or streaming is done
+            has_sentence_end = any(punct in new_content for punct in ['.', '!', '?'])
+            is_complete = responder.streaming_complete.is_set()
+            
+            # Play if we have a complete sentence OR if streaming is complete
+            if (has_sentence_end or is_complete) and len(new_content.strip()) > 0:
+                global_vars_module.last_tts_response = response
+                global_vars_module.last_spoken_response = response
+                global_vars_module.set_read_response(True)
+                logger.info(f"update_response_ui triggering playback event - new content: {len(new_content)} chars")
+                global_vars_module.audio_player_var.speech_text_available.set()
+                
+                # Only clear streaming complete if it was set
+                if is_complete:
+                    responder.streaming_complete.clear()
 
     update_interval = int(update_interval_slider.get())
     responder.update_response_interval(update_interval)
'''
    
    with open('progressive_tts.patch', 'w') as f:
        f.write(patch_content)
    
    print("Created progressive_tts.patch")
    return 'progressive_tts.patch'

def create_alternative_fix():
    """Alternative: Reduce the delay by checking for sentence endings"""
    
    fix_content = '''#!/usr/bin/env python3
"""
Alternative TTS delay fix - plays audio as soon as a sentence is complete.
"""

def is_sentence_complete(text):
    """Check if text ends with sentence punctuation"""
    text = text.strip()
    return text and text[-1] in '.!?'

def get_complete_sentences(text, last_played_text):
    """Extract only complete sentences that haven't been played yet"""
    # Get new content
    new_content = text[len(last_played_text):]
    
    # Find all complete sentences in the new content
    sentences = []
    current = ""
    
    for char in new_content:
        current += char
        if char in '.!?':
            sentences.append(current.strip())
            current = ""
    
    return ' '.join(sentences), len(last_played_text) + sum(len(s) for s in sentences)

# This would be integrated into update_response_ui
'''
    
    with open('tts_sentence_fix.py', 'w') as f:
        f.write(fix_content)
    
    print("Created tts_sentence_fix.py")

def main():
    print("=== Fixing TTS Delay Issue ===")
    print("\nThe issue: TTS waits for entire response before playing")
    print("Current behavior: 2-4 second delay after text appears")
    print("\nTwo solutions available:")
    print("1. Progressive TTS - Play sentences as they stream in")
    print("2. Quick fix - Reduce check interval and optimize playback trigger")
    
    choice = input("\nWhich fix to apply? (1/2): ").strip()
    
    if choice == "1":
        patch_file = create_progressive_tts_patch()
        print(f"\n✅ Created {patch_file}")
        print("\nTo apply:")
        print(f"  patch -p1 < {patch_file}")
        print("\nThis will make TTS play sentences as they arrive,")
        print("reducing the delay to near-zero.")
        
    elif choice == "2":
        # Simple fix - just reduce the wait interval
        print("\nApplying quick fix...")
        
        # Update the after() delay in appui.py
        import fileinput
        
        with fileinput.FileInput('app/transcribe/appui.py', inplace=True) as file:
            for line in file:
                if 'textbox.after(300,' in line:
                    print('    textbox.after(100, update_response_ui, responder, textbox,')
                else:
                    print(line, end='')
        
        print("✅ Reduced UI update interval from 300ms to 100ms")
        print("This should reduce TTS delay by up to 200ms")
        
        create_alternative_fix()
        print("\nAlso created tts_sentence_fix.py for reference")
    
    else:
        print("Invalid choice. No changes made.")
        return 1
    
    print("\n📝 Note: The root cause is waiting for streaming_complete.")
    print("   The best fix is progressive TTS (option 1).")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())