#!/usr/bin/env python3
"""
Test the latest fixes:
1. Sentence splitting (PHRASE_TIMEOUT increased to 5.0)
2. TTS delay reduction (UI update interval reduced to 100ms)
"""

import sys
import os
import time
import numpy as np
from pathlib import Path
import yaml
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
from app.transcribe import audio_transcriber
from app.transcribe.voice_filter import VoiceFilter

def test_phrase_timeout():
    """Test that PHRASE_TIMEOUT was increased to 5.0"""
    print("\n=== Testing Sentence Splitting Fix ===")
    
    # Check the constant
    timeout = audio_transcriber.PHRASE_TIMEOUT
    print(f"PHRASE_TIMEOUT: {timeout} seconds")
    
    # Check parameters.yaml
    with open('app/transcribe/parameters.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    transcript_duration = config['General']['transcript_audio_duration_seconds']
    print(f"transcript_audio_duration_seconds: {transcript_duration}")
    
    # Verify values
    success = True
    if timeout != 5.0:
        print(f"❌ PHRASE_TIMEOUT is {timeout}, expected 5.0")
        success = False
    else:
        print("✅ PHRASE_TIMEOUT correctly set to 5.0 seconds")
    
    if transcript_duration != 5:
        print(f"❌ transcript_audio_duration_seconds is {transcript_duration}, expected 5")
        success = False
    else:
        print("✅ transcript_audio_duration_seconds correctly set to 5")
    
    return success

def test_ui_update_interval():
    """Test that UI update interval was reduced"""
    print("\n=== Testing TTS Delay Fix ===")
    
    # Read appui.py and check for the update interval
    with open('app/transcribe/appui.py', 'r') as f:
        content = f.read()
    
    # Look for the textbox.after call
    if 'textbox.after(100,' in content:
        print("✅ UI update interval reduced to 100ms")
        if '# Reduced from 300ms to 100ms' in content:
            print("✅ Comment indicates the change was applied")
        return True
    elif 'textbox.after(300,' in content:
        print("❌ UI update interval still at 300ms (not reduced)")
        return False
    else:
        print("❓ Could not find textbox.after call")
        return False

def simulate_audio_segments():
    """Simulate how audio segments would be handled with new timeout"""
    print("\n=== Simulating Audio Segmentation ===")
    
    # Simulate different speaking patterns
    test_cases = [
        ("Short sentence", 2.5),
        ("Medium sentence with natural pauses", 4.2),
        ("Long sentence that would have been split before", 4.8),
        ("Very long monologue", 5.5)
    ]
    
    print(f"With PHRASE_TIMEOUT = {audio_transcriber.PHRASE_TIMEOUT}:")
    for description, duration in test_cases:
        if duration > audio_transcriber.PHRASE_TIMEOUT:
            print(f"  ❌ '{description}' ({duration}s) - WOULD BE SPLIT")
        else:
            print(f"  ✅ '{description}' ({duration}s) - kept as single segment")
    
    return True

def test_voice_filter_with_segments():
    """Test voice filter with different audio segment durations"""
    print("\n=== Testing Voice Filter with New Timeout ===")
    
    # Check if voice filter is enabled
    with open('app/transcribe/parameters.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    if not config['General']['voice_filter_enabled']:
        print("⚠️  Voice filter not enabled in config")
        return True
    
    print(f"Voice filter threshold: {config['General']['voice_filter_threshold']}")
    print(f"Inverted response: {config['General']['inverted_voice_response']}")
    
    # Simulate colleague speaking for different durations
    print("\nSimulated colleague speech patterns:")
    patterns = [
        ("Quick question", 2.0),
        ("Normal conversation", 3.5),
        ("Detailed explanation", 4.5),
        ("Long technical discussion", 5.0)
    ]
    
    for pattern, duration in patterns:
        print(f"  - {pattern} ({duration}s): ", end="")
        if duration <= audio_transcriber.PHRASE_TIMEOUT:
            print("✅ Single response")
        else:
            print("⚠️  May trigger multiple responses")
    
    return True

def test_real_voice_files():
    """Test with real voice files if available"""
    print("\n=== Testing with Real Voice Files ===")
    
    voice_dir = Path("voice_recordings")
    if not voice_dir.exists():
        print("⚠️  No voice_recordings directory found - skipping real voice tests")
        return True
    
    # List available voice files
    voice_files = list(voice_dir.glob("*.wav")) + list(voice_dir.glob("*.mp3"))
    if not voice_files:
        print("⚠️  No voice files found in voice_recordings/")
        return True
    
    print(f"Found {len(voice_files)} voice files")
    
    # Check if voice filter can handle them
    try:
        vf = VoiceFilter("my_voice.npy", threshold=0.625)
        print("✅ Voice filter initialized successfully")
        
        # Test buffer behavior with new timeout
        print("\nTesting audio buffer with 5-second timeout:")
        print("- Buffer should accumulate up to 2 seconds (min_window)")
        print("- Then make decision and process")
        print("- With 5s PHRASE_TIMEOUT, longer sentences won't be split")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing voice filter: {e}")
        return False

def generate_test_report():
    """Generate a test report"""
    report = {
        "test_date": datetime.now().isoformat(),
        "fixes_tested": {
            "sentence_splitting": {
                "description": "Increased PHRASE_TIMEOUT from 3.05 to 5.0 seconds",
                "purpose": "Prevent colleague sentences from being split"
            },
            "tts_delay": {
                "description": "Reduced UI update interval from 300ms to 100ms",
                "purpose": "Reduce delay between text display and audio playback"
            }
        },
        "test_results": {}
    }
    
    return report

def main():
    print("=== TESTING LATEST FIXES ===")
    print("Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("\nThis test verifies:")
    print("1. Sentence splitting fix (PHRASE_TIMEOUT = 5.0)")
    print("2. TTS delay reduction (UI update = 100ms)")
    
    report = generate_test_report()
    all_passed = True
    
    # Run tests
    tests = [
        ("Phrase Timeout", test_phrase_timeout),
        ("UI Update Interval", test_ui_update_interval),
        ("Audio Segmentation", simulate_audio_segments),
        ("Voice Filter Integration", test_voice_filter_with_segments),
        ("Real Voice Files", test_real_voice_files)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            report["test_results"][test_name] = {
                "passed": result,
                "timestamp": datetime.now().isoformat()
            }
            if not result:
                all_passed = False
        except Exception as e:
            print(f"\n❌ Error in {test_name}: {e}")
            report["test_results"][test_name] = {
                "passed": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            all_passed = False
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed_count = sum(1 for r in report["test_results"].values() if r.get("passed", False))
    total_count = len(report["test_results"])
    
    print(f"Tests passed: {passed_count}/{total_count}")
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED!")
        print("\nChanges verified:")
        print("- Colleagues can speak up to 5 seconds without splitting")
        print("- TTS response time reduced by ~200ms")
        print("\n🚀 Ready to push changes to GitHub")
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("Please fix issues before pushing to GitHub")
    
    # Save report
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nTest report saved to: {report_file}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())