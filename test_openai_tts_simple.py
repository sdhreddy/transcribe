#!/usr/bin/env python3
"""Simple test to debug OpenAI TTS issue."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_openai_tts():
    """Test OpenAI TTS with proper error handling."""
    print("=== Testing OpenAI TTS ===\n")
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            import yaml
            with open("app/transcribe/override.yaml", 'r') as f:
                override = yaml.safe_load(f)
                api_key = override.get('OpenAI', {}).get('api_key')
                if api_key:
                    print("✓ API key found in override.yaml")
        except Exception as e:
            print(f"Error reading override.yaml: {e}")
            return
    else:
        print("✓ API key found in environment")
    
    if not api_key:
        print("❌ No API key found!")
        return
    
    print(f"API key length: {len(api_key)} chars")
    print(f"API key starts with: {api_key[:7]}...")
    
    # Test OpenAI connection
    try:
        from openai import OpenAI
        print("\n1. Testing OpenAI client creation...")
        client = OpenAI(api_key=api_key)
        print("✓ OpenAI client created")
        
        print("\n2. Testing TTS API call...")
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input="Hello, this is a test.",
            response_format="mp3"  # Try MP3 first
        )
        print("✓ TTS API call successful (MP3)")
        
        print("\n3. Testing PCM format...")
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input="Testing PCM format.",
            response_format="pcm"
        )
        
        chunk_count = 0
        for chunk in response.iter_bytes(chunk_size=4096):
            chunk_count += 1
            if chunk_count == 1:
                print(f"✓ First chunk received, size: {len(chunk)} bytes")
                break
        
        print(f"✓ Streaming works! Received {chunk_count} chunk(s)")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        
        # Common issues
        if "401" in str(e) or "Unauthorized" in str(e):
            print("\nDiagnosis: Invalid API key")
            print("Solution: Check your OpenAI API key in override.yaml")
        elif "rate_limit" in str(e).lower():
            print("\nDiagnosis: Rate limit exceeded")
            print("Solution: Wait a bit or check your OpenAI account")
        elif "connection" in str(e).lower():
            print("\nDiagnosis: Network connection issue")
            print("Solution: Check internet connection and firewall")
        elif "insufficient_quota" in str(e):
            print("\nDiagnosis: OpenAI account has no credits")
            print("Solution: Add credits to your OpenAI account")
        else:
            print("\nCheck:")
            print("1. OpenAI API key is valid")
            print("2. OpenAI account has credits")
            print("3. Network connection is working")
            print("4. No firewall blocking OpenAI API")
            
        # Try to get more details
        import traceback
        print("\nFull error trace:")
        traceback.print_exc()


def check_openai_version():
    """Check OpenAI library version."""
    print("\n=== OpenAI Library Check ===")
    try:
        import openai
        print(f"OpenAI version: {openai.__version__}")
        
        # Check if it's a recent version
        version_parts = openai.__version__.split('.')
        major = int(version_parts[0])
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        
        if major >= 1 and minor >= 0:
            print("✓ OpenAI library version is good")
        else:
            print("⚠️  Consider upgrading: pip install --upgrade openai")
            
    except Exception as e:
        print(f"Error checking version: {e}")


if __name__ == "__main__":
    check_openai_version()
    test_openai_tts()
    
    print("\n" + "="*50)
    print("\nIf the test fails, common solutions:")
    print("1. Verify API key: Make sure it starts with 'sk-'")
    print("2. Check account: https://platform.openai.com/account/usage")
    print("3. Update library: pip install --upgrade openai")
    print("4. Test network: ping api.openai.com")