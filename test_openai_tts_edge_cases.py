#!/usr/bin/env python3
"""Test OpenAI TTS with edge cases."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_edge_cases():
    """Test various text inputs to OpenAI TTS."""
    print("=== Testing OpenAI TTS Edge Cases ===\n")
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            import yaml
            with open("app/transcribe/override.yaml", 'r') as f:
                override = yaml.safe_load(f)
                api_key = override.get('OpenAI', {}).get('api_key')
        except:
            pass
    
    if not api_key:
        print("No API key found!")
        return
    
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    # Test cases that might cause issues
    test_cases = [
        "Hello world.",  # Simple
        "Based on the error message,",  # Ends with comma
        "Try running pip install pyaudio",  # No punctuation
        "This is a test. And another sentence.",  # Multiple sentences
        "Short",  # Very short
        "",  # Empty (should error)
    ]
    
    for i, text in enumerate(test_cases):
        if not text:
            print(f"\nTest {i+1}: Empty text (skipping)")
            continue
            
        print(f"\nTest {i+1}: '{text}'")
        try:
            start = time.time()
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                response_format="pcm"
            )
            
            # Get audio data
            audio_data = b""
            for chunk in response.iter_bytes(chunk_size=4096):
                audio_data += chunk
            
            elapsed = time.time() - start
            print(f"  ✓ Success: {len(audio_data)} bytes in {elapsed:.2f}s")
            
        except Exception as e:
            print(f"  ✗ Error: {type(e).__name__}: {e}")
    
    print("\n" + "="*50)
    print("If certain texts fail, that might explain why TTS stops!")


if __name__ == "__main__":
    test_edge_cases()