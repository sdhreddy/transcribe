#!/usr/bin/env python3
"""Test different threshold values with existing voice recordings."""

import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent))
from app.transcribe.voice_filter import VoiceFilter

def test_threshold_with_files(threshold):
    """Test a threshold value with existing voice files."""
    print(f"\n{'='*60}")
    print(f"Testing threshold: {threshold}")
    print(f"{'='*60}")
    
    vf = VoiceFilter("my_voice.npy", threshold)
    
    if not vf.inference or vf.user_embedding is None:
        print("ERROR: Voice filter not initialized!")
        return
    
    # Test files
    test_files = [
        ("voice_recordings/Primary_User.wav", "User", True),  # Should be blocked
        ("voice_recordings/Colleague A.wav", "Colleague A", False),  # Should respond
        ("voice_recordings/Colleague B.wav", "Colleague B", False),  # Should respond
        ("voice_recordings/Colleague C.wav", "Colleague C", False),  # Should respond
    ]
    
    results = []
    all_correct = True
    
    for file_path, label, expected_is_user in test_files:
        if not Path(file_path).exists():
            print(f"❌ File not found: {file_path}")
            continue
            
        try:
            import librosa
            audio, sr = librosa.load(file_path, sr=16000)
            
            # Test voice
            is_user, confidence = vf.is_user_voice(audio, sr)
            distance = 1.0 - confidence
            should_respond = vf.should_respond(is_user, inverted=True)
            
            # Check if correct
            correct_detection = (is_user == expected_is_user)
            correct_response = should_respond == (not expected_is_user)
            is_correct = correct_detection and correct_response
            
            if not is_correct:
                all_correct = False
            
            status = "✅" if is_correct else "❌"
            print(f"{status} {label:12} - Distance: {distance:.3f}, User: {is_user}, Respond: {should_respond}")
            
            results.append({
                'file': label,
                'distance': distance,
                'is_user': is_user,
                'should_respond': should_respond,
                'correct': is_correct
            })
            
        except Exception as e:
            print(f"❌ Error testing {label}: {e}")
            all_correct = False
    
    # Summary
    print(f"\n{'='*60}")
    if all_correct:
        print(f"✅ THRESHOLD {threshold} WORKS PERFECTLY!")
        print("All voices correctly identified and response logic correct.")
    else:
        print(f"❌ THRESHOLD {threshold} HAS ISSUES!")
        failed = [r for r in results if not r['correct']]
        for f in failed:
            print(f"  - {f['file']}: distance={f['distance']:.3f}")
    
    # Show distance ranges
    if results:
        user_distances = [r['distance'] for r in results if 'User' in r['file']]
        other_distances = [r['distance'] for r in results if 'Colleague' in r['file']]
        
        if user_distances and other_distances:
            print(f"\nDistance ranges:")
            print(f"  User: {min(user_distances):.3f} - {max(user_distances):.3f}")
            print(f"  Others: {min(other_distances):.3f} - {max(other_distances):.3f}")
            
            separation = min(other_distances) - max(user_distances)
            print(f"  Separation: {separation:.3f}")
            
            if separation > 0:
                optimal = max(user_distances) + separation / 2
                print(f"  Optimal threshold: {optimal:.3f}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--threshold', type=float, default=0.425, help='Threshold to test')
    parser.add_argument('--all', action='store_true', help='Test multiple thresholds')
    args = parser.parse_args()
    
    if args.all:
        # Test multiple thresholds
        thresholds = [0.3, 0.35, 0.4, 0.425, 0.45, 0.5, 0.55, 0.6, 0.625, 0.65, 0.7]
        for t in thresholds:
            test_threshold_with_files(t)
    else:
        test_threshold_with_files(args.threshold)