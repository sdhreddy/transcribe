#!/usr/bin/env python3
"""Test if OpenAI TTS actually supports stream=True parameter."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_streaming_parameter():
    """Test if OpenAI TTS supports stream=True parameter."""
    print("=== Testing OpenAI TTS stream=True Parameter ===\n")
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            import yaml
            with open("app/transcribe/override.yaml", 'r') as f:
                override = yaml.safe_load(f)
                api_key = override.get('OpenAI', {}).get('api_key')
        except Exception:
            pass
    
    if not api_key:
        print("❌ No API key found!")
        return
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        print("1. Testing WITHOUT stream=True parameter...")
        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input="Test without streaming.",
                response_format="pcm"
            )
            print("✓ Works without stream parameter")
            print(f"   Response type: {type(response)}")
            
            # Test if response can be iterated
            chunk_count = 0
            for chunk in response.iter_bytes(chunk_size=1024):
                chunk_count += 1
                if chunk_count == 1:
                    print(f"   First chunk size: {len(chunk)} bytes")
            print(f"   Total chunks: {chunk_count}")
            
        except Exception as e:
            print(f"❌ Failed: {type(e).__name__}: {e}")
        
        print("\n2. Testing WITH stream=True parameter...")
        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input="Test with streaming enabled.",
                response_format="pcm",
                stream=True  # ← This is what we're testing
            )
            print("✓ stream=True parameter accepted")
            print(f"   Response type: {type(response)}")
            
            # Test if response can be iterated differently
            chunk_count = 0
            if hasattr(response, '__iter__'):
                print("   Response is iterable")
                for chunk in response:
                    chunk_count += 1
                    if chunk_count == 1:
                        print(f"   First chunk type: {type(chunk)}")
                        if hasattr(chunk, '__len__'):
                            print(f"   First chunk size: {len(chunk)} bytes")
                    if chunk_count > 5:
                        break
                print(f"   Received {chunk_count}+ chunks")
            else:
                print("   Response is NOT directly iterable")
                
        except TypeError as e:
            if "unexpected keyword argument 'stream'" in str(e):
                print("❌ OpenAI TTS does NOT support stream=True parameter!")
                print("   This is the root cause of the issue.")
            else:
                print(f"❌ TypeError: {e}")
        except Exception as e:
            print(f"❌ Failed: {type(e).__name__}: {e}")
            
        print("\n3. Checking OpenAI library documentation...")
        print("   Inspecting speech.create method signature...")
        try:
            import inspect
            sig = inspect.signature(client.audio.speech.create)
            print(f"   Parameters: {list(sig.parameters.keys())}")
            
            # Check if 'stream' is in parameters
            if 'stream' in sig.parameters:
                print("   ✓ 'stream' parameter exists in method signature")
            else:
                print("   ❌ 'stream' parameter NOT found in method signature")
                
        except Exception as e:
            print(f"   Could not inspect: {e}")
            
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_streaming_parameter()
    
    print("\n" + "="*50)
    print("\nConclusion:")
    print("If stream=True is not supported, the fix is to remove it from streaming_tts.py")
    print("The OpenAI response already supports chunk-based iteration without it.")