#!/usr/bin/env python3
"""
Tune voice filter threshold by testing with actual voice samples.
This tool helps find the optimal threshold for your specific system.
"""

import os
import sys
import numpy as np
import sounddevice as sd
import time
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from app.transcribe.voice_filter import VoiceFilter

def test_threshold(profile_path, test_threshold):
    """Test a specific threshold value"""
    print(f"\n{'='*60}")
    print(f"Testing threshold: {test_threshold}")
    print(f"{'='*60}")
    
    vf = VoiceFilter(profile_path, threshold=test_threshold)
    
    if not vf.inference or vf.user_embedding is None:
        print("ERROR: Voice filter not properly initialized!")
        return None
    
    results = {
        'threshold': test_threshold,
        'timestamp': datetime.now().isoformat(),
        'user_tests': [],
        'other_tests': []
    }
    
    # Test user voice 3 times
    print("\nTesting USER voice (3 samples):")
    print("Speak naturally when prompted.\n")
    
    for i in range(3):
        input(f"Press Enter when ready to record YOUR voice (test {i+1}/3)...")
        print("🎙️  Recording for 5 seconds... Speak now!")
        
        audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1, dtype='float32')
        sd.wait()
        
        # Convert to proper format
        audio = audio.flatten()
        
        # Test voice
        is_user, confidence = vf.is_user_voice(audio, 16000)
        distance = 1.0 - confidence  # Convert back to distance
        
        results['user_tests'].append(distance)
        
        if is_user:
            print(f"✅ Test {i+1}: Distance = {distance:.3f} → CORRECTLY IDENTIFIED as user")
        else:
            print(f"❌ Test {i+1}: Distance = {distance:.3f} → INCORRECTLY identified as other")
        
        time.sleep(1)
    
    # Test other voices 3 times
    print("\n\nTesting OTHER voices (3 different people):")
    print("Have colleagues speak when prompted.\n")
    
    for i in range(3):
        input(f"Press Enter when colleague {i+1} is ready to speak...")
        print("🎙️  Recording for 5 seconds... Colleague should speak now!")
        
        audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1, dtype='float32')
        sd.wait()
        
        audio = audio.flatten()
        is_user, confidence = vf.is_user_voice(audio, 16000)
        distance = 1.0 - confidence
        
        results['other_tests'].append(distance)
        
        if not is_user:
            print(f"✅ Colleague {i+1}: Distance = {distance:.3f} → CORRECTLY identified as other")
        else:
            print(f"❌ Colleague {i+1}: Distance = {distance:.3f} → INCORRECTLY identified as user")
        
        time.sleep(1)
    
    # Analyze results
    user_max = max(results['user_tests'])
    other_min = min(results['other_tests'])
    margin = other_min - user_max
    
    print(f"\n{'='*60}")
    print(f"Results for threshold {test_threshold}")
    print(f"{'='*60}")
    print(f"User voice distances: {min(results['user_tests']):.3f} to {max(results['user_tests']):.3f}")
    print(f"Other voice distances: {min(results['other_tests']):.3f} to {max(results['other_tests']):.3f}")
    print(f"Separation margin: {margin:.3f}")
    
    # Check if threshold works
    all_user_correct = all(d < test_threshold for d in results['user_tests'])
    all_others_correct = all(d >= test_threshold for d in results['other_tests'])
    
    if all_user_correct and all_others_correct:
        print(f"\n✅ THRESHOLD {test_threshold} WORKS PERFECTLY!")
        print("All voices correctly identified.")
    else:
        print(f"\n❌ THRESHOLD {test_threshold} FAILS!")
        if not all_user_correct:
            failed_count = sum(1 for d in results['user_tests'] if d >= test_threshold)
            print(f"   - {failed_count}/3 user voice samples not recognized")
        if not all_others_correct:
            failed_count = sum(1 for d in results['other_tests'] if d < test_threshold)
            print(f"   - {failed_count}/3 colleague voices incorrectly blocked")
    
    return results

def find_optimal_threshold(profile_path):
    """Find the optimal threshold through testing"""
    print("="*60)
    print("VOICE FILTER THRESHOLD CALIBRATION")
    print("="*60)
    print("\nThis tool will help find the perfect threshold for your system.")
    print("\nYou'll need:")
    print("- Your voice (3 recordings)")
    print("- 3 different colleagues to speak")
    print("\nIMPORTANT: Use the same microphone and environment as normal usage.")
    
    input("\nPress Enter to begin calibration...")
    
    # First, get baseline measurements
    vf = VoiceFilter(profile_path, threshold=0.5)  # Use middle threshold for testing
    
    if not vf.inference or vf.user_embedding is None:
        print("\nERROR: Voice filter not properly initialized!")
        print("Check that:")
        print("1. HuggingFace token is set")
        print("2. Voice profile exists at:", profile_path)
        print("3. PyTorch and Pyannote are installed")
        return None
    
    print("\n" + "="*60)
    print("STEP 1: Baseline Measurements")
    print("="*60)
    
    user_distances = []
    other_distances = []
    
    # Measure user voice
    print("\nFirst, let's measure YOUR voice...")
    for i in range(3):
        input(f"\nPress Enter to record YOUR voice (sample {i+1}/3)...")
        print("🎙️  Recording 5 seconds... Speak naturally!")
        
        audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1, dtype='float32')
        sd.wait()
        
        is_user, confidence = vf.is_user_voice(audio.flatten(), 16000)
        distance = 1.0 - confidence
        user_distances.append(distance)
        print(f"Your voice distance: {distance:.3f}")
    
    # Measure other voices
    print("\n\nNow, let's measure COLLEAGUE voices...")
    for i in range(3):
        input(f"\nPress Enter when colleague {i+1} is ready...")
        print("🎙️  Recording 5 seconds... Colleague should speak!")
        
        audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1, dtype='float32')
        sd.wait()
        
        is_user, confidence = vf.is_user_voice(audio.flatten(), 16000)
        distance = 1.0 - confidence
        other_distances.append(distance)
        print(f"Colleague {i+1} distance: {distance:.3f}")
    
    # Calculate optimal threshold
    user_max = max(user_distances)
    other_min = min(other_distances)
    
    print("\n" + "="*60)
    print("ANALYSIS")
    print("="*60)
    print(f"Your voice range: {min(user_distances):.3f} to {max(user_distances):.3f}")
    print(f"Other voices range: {min(other_distances):.3f} to {max(other_distances):.3f}")
    
    if other_min <= user_max:
        print("\n⚠️  WARNING: Voice ranges overlap!")
        print("Voice discrimination may not work reliably.")
        print("Consider re-creating your voice profile with better quality recordings.")
        optimal = (user_max + other_min) / 2
    else:
        # Calculate optimal threshold with safety margin
        separation = other_min - user_max
        print(f"\nSeparation: {separation:.3f} (good!)")
        
        # Use 20% safety margins
        margin = separation * 0.2
        optimal = user_max + margin
        
        print(f"Recommended threshold: {optimal:.3f}")
        print(f"(This gives {margin:.3f} safety margin on each side)")
    
    # Save detailed results
    results = {
        'timestamp': datetime.now().isoformat(),
        'user_distances': user_distances,
        'other_distances': other_distances,
        'user_range': {'min': min(user_distances), 'max': max(user_distances)},
        'other_range': {'min': min(other_distances), 'max': max(other_distances)},
        'separation': other_min - user_max,
        'recommended_threshold': optimal
    }
    
    results_file = f'threshold_calibration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nCalibration results saved to: {results_file}")
    
    # Test recommended threshold
    input(f"\nPress Enter to test threshold {optimal:.3f}...")
    test_results = test_threshold(profile_path, optimal)
    
    return optimal

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tune voice filter threshold")
    parser.add_argument('--profile', default='my_voice.npy', help='Voice profile path')
    parser.add_argument('--test', type=float, help='Test specific threshold')
    args = parser.parse_args()
    
    profile_path = args.profile
    if not Path(profile_path).is_absolute():
        profile_path = str(Path.cwd() / profile_path)
    
    if args.test:
        test_threshold(profile_path, args.test)
    else:
        optimal = find_optimal_threshold(profile_path)
        if optimal:
            print(f"\n" + "="*60)
            print("FINAL RECOMMENDATION")
            print("="*60)
            print(f"Update parameters.yaml with:")
            print(f"  voice_filter_threshold: {optimal:.3f}")
            print("\nThen test with the full application to verify.")