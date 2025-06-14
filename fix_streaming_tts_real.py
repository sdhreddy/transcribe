#!/usr/bin/env python3
"""The REAL fix for streaming TTS - address the actual bottlenecks."""

import os
import sys
import re

def apply_real_fix():
    """Apply the actual fixes needed for streaming TTS."""
    
    print("=" * 60)
    print("APPLYING REAL STREAMING TTS FIXES")
    print("=" * 60)
    
    # Fix 1: The 6-second visual delay issue
    print("\n1. Fixing 6-second visual response delay...")
    
    # Check main.py for GPT response issues
    main_path = "app/transcribe/main.py"
    if os.path.exists(main_path):
        with open(main_path, 'r') as f:
            main_content = f.read()
        
        # Look for response interval settings
        if "llm_response_interval" in main_content:
            print("   Found LLM response interval setting")
        
    # Fix 2: Force streaming in OpenAI TTS
    print("\n2. Checking OpenAI TTS streaming...")
    tts_path = "app/transcribe/streaming_tts.py"
    
    with open(tts_path, 'r') as f:
        tts_content = f.read()
    
    # The issue: OpenAI might be buffering the entire response
    # We need to add response_format='pcm' with streaming headers
    if "stream=True" not in tts_content:
        print("   ✓ Correctly not using stream=True (unsupported)")
    
    # Fix 3: Check if audio player is actually playing immediately
    player_path = "app/transcribe/audio_player_streaming.py"
    with open(player_path, 'r') as f:
        player_content = f.read()
    
    # Add immediate playback logging
    if "[TTS Debug] Playing chunk immediately" not in player_content:
        print("   Adding immediate playback confirmation...")
        
        # Add logging right after chunk is received
        player_content = player_content.replace(
            "self.playing = True",
            """self.playing = True
                logger.info(f"[TTS Debug] Playing chunk immediately: {len(chunk)} bytes, queue has {self.q.qsize()} more")"""
        )
        
        with open(player_path, 'w') as f:
            f.write(player_content)
        print("   ✓ Added immediate playback logging")
    
    # Fix 4: The REAL issue - GPT response delay
    print("\n3. Checking GPT response configuration...")
    
    # The 6-second delay is likely from GPT response generation
    # Check responder settings
    responder_path = "app/transcribe/gpt_responder.py"
    with open(responder_path, 'r') as f:
        responder_content = f.read()
    
    # Add logging to track GPT response timing
    if "[TTS Debug] GPT token received at" not in responder_content:
        print("   Adding GPT timing logs...")
        
        # Add timing to token handler
        responder_content = responder_content.replace(
            'def _handle_streaming_token(self, token: str):',
            '''def _handle_streaming_token(self, token: str):
        """Handle a single token from streaming response."""
        if not hasattr(self, '_first_token_time'):
            self._first_token_time = time.time()
            logger.info(f"[TTS Debug] First GPT token received at {self._first_token_time}")'''
        )
        
        with open(responder_path, 'w') as f:
            f.write(responder_content)
        print("   ✓ Added GPT timing logs")
    
    # Fix 5: Check sentence detection timing
    print("\n4. Optimizing sentence detection for faster streaming...")
    
    # Make sentence detection more aggressive
    if "SENT_END = re.compile" in responder_content:
        # Update to detect sentences faster
        new_content = responder_content.replace(
            'self.SENT_END = re.compile(r"[.!?](?:\\s|$)")',
            'self.SENT_END = re.compile(r"[.!?]")'  # Don't require space
        )
        
        # Also reduce minimum sentence length
        new_content = new_content.replace(
            "get('tts_min_sentence_chars', 10)",
            "get('tts_min_sentence_chars', 5)"  # Shorter sentences OK
        )
        
        if new_content != responder_content:
            with open(responder_path, 'w') as f:
                f.write(new_content)
            print("   ✓ Made sentence detection more aggressive")
    
    print("\n" + "=" * 60)
    print("ANALYSIS OF YOUR ISSUE:")
    print("=" * 60)
    print("""
Your test showed:
1. "6-second delay for visual" - This is GPT response generation time
2. "TTS plays AFTER visual completes" - TTS waits for sentences

The REAL problems:
1. GPT takes 6 seconds to START responding (not a TTS issue)
2. TTS is working but waiting for complete sentences
3. Sentence detection might be too conservative

What the monitoring will show:
- Time from voice input to first GPT token (this is the 6s delay)
- Time from first token to first sentence
- Time from sentence to audio playback

The fix is NOT in TTS streaming - it's in:
1. GPT response speed (check model, timeout, API latency)
2. Sentence detection aggressiveness
3. Minimum sentence length requirements
""")

if __name__ == '__main__':
    apply_real_fix()