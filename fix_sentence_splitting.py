#!/usr/bin/env python3
"""
Fix for sentence splitting issue - increases phrase timeout to allow longer sentences.
"""

import fileinput
import sys

def update_phrase_timeout():
    """Update PHRASE_TIMEOUT in audio_transcriber.py"""
    print("Updating PHRASE_TIMEOUT in audio_transcriber.py...")
    
    # Update audio_transcriber.py
    with fileinput.FileInput('app/transcribe/audio_transcriber.py', inplace=True) as file:
        for line in file:
            if line.strip().startswith('PHRASE_TIMEOUT = '):
                print('PHRASE_TIMEOUT = 5.0  # Increased from 3.05 to allow longer sentences')
            else:
                print(line, end='')
    
    print("✓ Updated PHRASE_TIMEOUT to 5.0 seconds")

def update_transcript_duration():
    """Update transcript_audio_duration_seconds in parameters.yaml"""
    print("\nUpdating transcript_audio_duration_seconds in parameters.yaml...")
    
    import yaml
    
    # Read current config
    with open('app/transcribe/parameters.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Update the value
    config['General']['transcript_audio_duration_seconds'] = 5
    
    # Write back
    with open('app/transcribe/parameters.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print("✓ Updated transcript_audio_duration_seconds to 5 seconds")

def main():
    print("=== Fixing Sentence Splitting Issue ===")
    print("This will increase audio segment timeout from 3 to 5 seconds")
    print("to prevent sentences from being split in the middle.\n")
    
    try:
        update_phrase_timeout()
        update_transcript_duration()
        
        print("\n✅ Success! Changes made:")
        print("1. PHRASE_TIMEOUT: 3.05 → 5.0 seconds")
        print("2. transcript_audio_duration_seconds: 3 → 5 seconds")
        print("\nThis should prevent sentences from being split.")
        print("Colleagues can now speak for up to 5 seconds per segment.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())