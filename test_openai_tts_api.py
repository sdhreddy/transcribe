#!/usr/bin/env python3
"""Test OpenAI TTS API to verify the correct parameters."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_openai_tts_stream_parameter():
    """Test if OpenAI TTS supports stream parameter."""
    print("=== TESTING OPENAI TTS API ===\n")
    
    try:
        from openai import OpenAI
        
        # Check OpenAI client version
        import openai as openai_module
        print(f"OpenAI SDK version: {openai_module.__version__}")
        
        # Test 1: Without stream parameter
        print("\n1. Testing WITHOUT stream parameter...")
        client = OpenAI()
        
        try:
            resp = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input="Test without stream.",
                response_format="pcm"
            )
            print("   ✅ Works without stream parameter")
            
            # Test iter_bytes
            first_chunk = next(resp.iter_bytes(chunk_size=4096))
            print(f"   ✅ iter_bytes works: {len(first_chunk)} bytes")
            
        except Exception as e:
            print(f"   ❌ Error: {type(e).__name__}: {e}")
        
        # Test 2: With stream parameter
        print("\n2. Testing WITH stream=True parameter...")
        try:
            resp = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input="Test with stream.",
                response_format="pcm",
                stream=True  # This might not be supported
            )
            print("   ✅ Works with stream=True parameter")
            
            # Test iteration
            first_chunk = next(resp.iter_bytes(chunk_size=4096))
            print(f"   ✅ iter_bytes works: {len(first_chunk)} bytes")
            
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                print(f"   ❌ stream parameter NOT supported: {e}")
            else:
                print(f"   ❌ Other error: {e}")
        except Exception as e:
            print(f"   ❌ Error: {type(e).__name__}: {e}")
        
        # Test 3: Check what type of response we get
        print("\n3. Checking response type...")
        resp = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input="Type check.",
            response_format="pcm"
        )
        print(f"   Response type: {type(resp).__name__}")
        print(f"   Has iter_bytes: {hasattr(resp, 'iter_bytes')}")
        print(f"   Has content: {hasattr(resp, 'content')}")
        print(f"   Has read: {hasattr(resp, 'read')}")
        
    except ImportError:
        print("❌ OpenAI not installed in virtual environment")
        print("   Run: pip install openai")
    except Exception as e:
        print(f"❌ Test failed: {type(e).__name__}: {e}")
        
        if "api_key" in str(e).lower():
            print("\nMake sure OPENAI_API_KEY is set or in override.yaml")

if __name__ == "__main__":
    test_openai_tts_stream_parameter()