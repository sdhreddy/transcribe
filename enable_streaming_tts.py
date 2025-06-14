#!/usr/bin/env python3
"""
Enable or disable streaming TTS in the configuration.
"""

import yaml
import sys
import os


def update_streaming_tts_config(enable=True):
    """Update parameters.yaml to enable/disable streaming TTS."""
    
    config_path = 'app/transcribe/parameters.yaml'
    
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        return False
    
    try:
        # Read current config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Update streaming TTS setting
        if 'General' not in config:
            config['General'] = {}
        
        config['General']['tts_streaming_enabled'] = enable
        
        # Ensure other TTS settings are present
        if enable:
            if 'tts_provider' not in config['General']:
                config['General']['tts_provider'] = 'openai'  # or 'gtts'
            if 'tts_voice' not in config['General']:
                config['General']['tts_voice'] = 'alloy'
            if 'tts_sample_rate' not in config['General']:
                config['General']['tts_sample_rate'] = 24000
            if 'tts_min_sentence_chars' not in config['General']:
                config['General']['tts_min_sentence_chars'] = 10
        
        # Write back
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Streaming TTS {'enabled' if enable else 'disabled'} in {config_path}")
        
        if enable:
            print("\nStreaming TTS configuration:")
            print(f"  Provider: {config['General']['tts_provider']}")
            print(f"  Voice: {config['General']['tts_voice']}")
            print(f"  Sample rate: {config['General']['tts_sample_rate']}Hz")
            print(f"  Min sentence chars: {config['General']['tts_min_sentence_chars']}")
            print("\n⚡ Audio will now start playing immediately as sentences complete!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating config: {e}")
        return False


def check_requirements():
    """Check if required packages are installed."""
    
    print("\nChecking requirements for streaming TTS...")
    
    requirements = {
        'pyaudio': 'Audio playback',
        'openai': 'OpenAI TTS provider',
        'gtts': 'Google TTS provider (fallback)'
    }
    
    missing = []
    
    for package, description in requirements.items():
        try:
            __import__(package)
            print(f"✅ {package} - {description}")
        except ImportError:
            print(f"❌ {package} - {description} (MISSING)")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("\nTo install:")
        if 'pyaudio' in missing:
            print("  Windows: Run install_pyaudio_windows.bat")
            print("  Linux: pip install pyaudio")
        for pkg in missing:
            if pkg != 'pyaudio':
                print(f"  pip install {pkg}")
    
    return len(missing) == 0


def main():
    """Main function."""
    
    print("=== Streaming TTS Configuration Tool ===\n")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'disable':
            update_streaming_tts_config(False)
            return
        elif sys.argv[1] == 'check':
            check_requirements()
            return
    
    # Check requirements first
    if not check_requirements():
        print("\n⚠️  Please install missing packages before enabling streaming TTS")
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            return
    
    print("\nThis will enable streaming TTS, which:")
    print("- Starts audio playback immediately as sentences complete")
    print("- Reduces TTS delay from 3 seconds to near-zero")
    print("- Uses OpenAI or Google TTS for speech synthesis")
    
    response = input("\nEnable streaming TTS? (Y/n): ")
    
    if response.lower() != 'n':
        update_streaming_tts_config(True)
        
        print("\n📝 To test:")
        print("1. Ensure your API key is configured")
        print("2. Run: python transcribe.py")
        print("3. Speak to a colleague (their voice will trigger responses)")
        print("4. Notice audio starts playing almost immediately!")
        
        print("\n🔄 To disable later, run: python enable_streaming_tts.py disable")
    else:
        print("\nStreaming TTS not enabled.")


if __name__ == '__main__':
    main()