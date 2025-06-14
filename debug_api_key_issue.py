#!/usr/bin/env python3
"""Debug why API key is not being detected."""

import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_api_key():
    """Debug API key detection issues."""
    print("=== API KEY DEBUG ===\n")
    
    # Test 1: Check override.yaml
    print("1. Checking override.yaml file...")
    override_path = os.path.join("app", "transcribe", "override.yaml")
    
    if os.path.exists(override_path):
        print(f"   ✅ Found: {override_path}")
        
        # Read and parse
        try:
            with open(override_path, 'r') as f:
                content = f.read()
                print(f"   File size: {len(content)} bytes")
                
            # Parse YAML
            data = yaml.safe_load(content)
            
            # Check for API key
            if 'OpenAI' in data and 'api_key' in data['OpenAI']:
                api_key = data['OpenAI']['api_key']
                if api_key and api_key not in ['null', 'YOUR_API_KEY']:
                    print(f"   ✅ API key found: {api_key[:10]}...{api_key[-4:]}")
                else:
                    print(f"   ❌ Invalid API key: {api_key}")
            else:
                print("   ❌ No OpenAI.api_key in YAML")
                print(f"   Keys found: {list(data.keys())}")
                
        except Exception as e:
            print(f"   ❌ Error parsing YAML: {e}")
    else:
        print(f"   ❌ Not found: {override_path}")
    
    # Test 2: Check environment variable
    print("\n2. Checking OPENAI_API_KEY environment variable...")
    env_key = os.getenv('OPENAI_API_KEY')
    if env_key:
        print(f"   ✅ Found: {env_key[:10]}...{env_key[-4:]}")
    else:
        print("   ❌ Not set")
    
    # Test 3: Check how configuration loads
    print("\n3. Testing configuration loading...")
    try:
        from tsutils import configuration
        config = configuration.Config().data
        
        # Check if OpenAI config exists
        if 'OpenAI' in config:
            openai_config = config['OpenAI']
            if 'api_key' in openai_config:
                loaded_key = openai_config['api_key']
                if loaded_key and loaded_key not in ['null', 'YOUR_API_KEY']:
                    print(f"   ✅ Config loaded API key: {loaded_key[:10]}...{loaded_key[-4:]}")
                else:
                    print(f"   ❌ Config has invalid key: {loaded_key}")
            else:
                print("   ❌ No api_key in OpenAI config")
        else:
            print("   ❌ No OpenAI section in config")
            
    except Exception as e:
        print(f"   ❌ Error loading config: {e}")
    
    # Test 4: Test OpenAI client creation
    print("\n4. Testing OpenAI client creation...")
    try:
        from openai import OpenAI
        
        # Method 1: With config
        try:
            client = OpenAI(api_key=config['OpenAI']['api_key'])
            print("   ✅ Client created with config API key")
        except Exception as e:
            print(f"   ❌ Failed with config key: {e}")
        
        # Method 2: With environment
        try:
            client = OpenAI()  # Uses OPENAI_API_KEY env var
            print("   ✅ Client created with environment variable")
        except Exception as e:
            print(f"   ❌ Failed with env var: {e}")
            
    except ImportError:
        print("   ❌ OpenAI module not installed")
    
    # Test 5: Check streaming_tts.py
    print("\n5. Checking how streaming_tts.py loads API key...")
    try:
        from app.transcribe.streaming_tts import OpenAITTS, TTSConfig
        
        # Check the code
        import inspect
        source = inspect.getsource(OpenAITTS.__init__)
        
        if "os.getenv" in source:
            print("   ℹ️  OpenAITTS uses: cfg.api_key or os.getenv('OPENAI_API_KEY')")
            
            # Try creating with config
            test_config = TTSConfig(provider="openai", voice="alloy", api_key=config['OpenAI']['api_key'])
            tts = OpenAITTS(test_config)
            print("   ✅ OpenAITTS created successfully")
        else:
            print("   ℹ️  Check OpenAITTS initialization code")
            
    except Exception as e:
        print(f"   ❌ Error checking streaming_tts: {e}")
    
    # Recommendations
    print("\n=== RECOMMENDATIONS ===")
    print("\n1. Set environment variable as backup:")
    print("   set OPENAI_API_KEY=your-actual-api-key-here")
    print("\n2. Or update the TTSConfig initialization to pass the API key")
    print("\n3. Make sure you're in the right directory when running tests")

if __name__ == "__main__":
    debug_api_key()