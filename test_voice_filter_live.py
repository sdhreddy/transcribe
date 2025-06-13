#!/usr/bin/env python3
"""Quick test to verify voice filter is working correctly"""

import sys
import time
import numpy as np
import sounddevice as sd
from pathlib import Path
import yaml

sys.path.append(str(Path(__file__).parent))
from app.transcribe.voice_filter import VoiceFilter

def quick_test():
    # Load current config
    with open('app/transcribe/parameters.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    profile = config['General']['voice_filter_profile']
    threshold = float(config['General']['voice_filter_threshold'])
    inverted = config['General'].get('inverted_voice_response', 'Yes') == 'Yes'
    
    print("="*60)
    print("VOICE FILTER QUICK TEST")
    print("="*60)
    print(f"Current settings:")
    print(f"  Profile: {profile}")
    print(f"  Threshold: {threshold}")
    print(f"  Inverted logic: {inverted}")
    print(f"  (AI responds to: {'colleagues only' if inverted else 'user only'})")
    print("="*60)
    
    # Initialize voice filter
    vf = VoiceFilter(profile, threshold)
    
    if not vf.inference or vf.user_embedding is None:
        print("\nERROR: Voice filter not properly initialized!")
        print("Check HuggingFace token and voice profile.")
        return
    
    print("\nPress Ctrl+C to exit\n")
    
    try:
        while True:
            input("Press Enter to record 3 seconds...")
            print("🎙️  Recording...")
            
            audio = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype='float32')
            sd.wait()
            
            # Check voice
            is_user, confidence = vf.is_user_voice(audio.flatten(), 16000)
            distance = 1.0 - confidence
            should_respond = vf.should_respond(is_user, inverted)
            
            print(f"\nResults:")
            print(f"  Distance: {distance:.3f} (threshold: {threshold})")
            print(f"  Identified as: {'USER VOICE' if is_user else 'OTHER VOICE'}")
            print(f"  AI should: {'🟢 RESPOND' if should_respond else '🔴 IGNORE'}")
            print(f"  Distance from threshold: {abs(distance - threshold):.3f}")
            
            # Visual representation
            bar_length = 50
            threshold_pos = int(threshold * bar_length / 2.0)  # Assuming max distance is 2.0
            distance_pos = int(distance * bar_length / 2.0)
            
            print("\n  0.0 " + "-" * bar_length + " 2.0")
            print("      " + " " * distance_pos + "D" + " " * (threshold_pos - distance_pos - 1) + "|")
            print("      " + " " * distance_pos + "↑" + " " * (threshold_pos - distance_pos - 1) + "↑")
            print("      " + " " * distance_pos + "You" + " " * (threshold_pos - distance_pos - 3) + "Threshold")
            print()
            
    except KeyboardInterrupt:
        print("\n\nTest stopped.")

if __name__ == "__main__":
    quick_test()