#!/usr/bin/env python3
"""
Comprehensive debugging tool for voice filter issues.
This combines insights from both WSL and Windows implementations.
"""

import os
import sys
import numpy as np
from pathlib import Path
import yaml
import json
from datetime import datetime

sys.path.append(str(Path(__file__).parent))
from app.transcribe.voice_filter import VoiceFilter

def debug_voice_filter():
    print("="*60)
    print("VOICE FILTER DIAGNOSTIC TOOL")
    print("="*60)
    
    # Load configuration
    with open('app/transcribe/parameters.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    general = config.get('General', {})
    
    # Check configuration
    print("\n1. CONFIGURATION CHECK:")
    print("-" * 40)
    
    settings = {
        'voice_filter_enabled': general.get('voice_filter_enabled'),
        'voice_filter_profile': general.get('voice_filter_profile'),
        'voice_filter_threshold': general.get('voice_filter_threshold'),
        'inverted_voice_response': general.get('inverted_voice_response'),
        'voice_identification_enabled': general.get('voice_identification_enabled')
    }
    
    for key, value in settings.items():
        status = "✅" if value is not None else "❌"
        print(f"{status} {key}: {value}")
    
    # Check critical settings
    issues = []
    
    if settings['voice_filter_enabled'] != 'Yes':
        issues.append("voice_filter_enabled should be 'Yes'")
    
    if settings['voice_identification_enabled'] not in [None, 'No', False]:
        issues.append("voice_identification_enabled should be 'No' or not set")
    
    if not isinstance(settings['voice_filter_threshold'], (int, float)):
        issues.append(f"voice_filter_threshold should be a number, got: {type(settings['voice_filter_threshold'])}")
    
    # Check voice profile
    print("\n2. VOICE PROFILE CHECK:")
    print("-" * 40)
    
    profile_path = settings['voice_filter_profile']
    if not Path(profile_path).is_absolute():
        profile_path = Path.cwd() / profile_path
    
    if Path(profile_path).exists():
        print(f"✅ Voice profile found: {profile_path}")
        profile_data = np.load(profile_path)
        print(f"   Shape: {profile_data.shape}")
        print(f"   Data type: {profile_data.dtype}")
        if profile_data.shape == (512,):
            print("   ✅ Correct embedding size")
        else:
            issues.append(f"Voice profile has wrong shape: {profile_data.shape}, expected (512,)")
    else:
        print(f"❌ Voice profile NOT found: {profile_path}")
        issues.append(f"Voice profile missing at: {profile_path}")
    
    # Check dependencies
    print("\n3. DEPENDENCY CHECK:")
    print("-" * 40)
    
    try:
        import torch
        print(f"✅ PyTorch installed: {torch.__version__}")
    except ImportError:
        print("❌ PyTorch NOT installed")
        issues.append("PyTorch not installed")
    
    try:
        import pyannote.audio
        print("✅ Pyannote.audio installed")
    except ImportError:
        print("❌ Pyannote.audio NOT installed")
        issues.append("Pyannote.audio not installed")
    
    # Check HuggingFace token
    print("\n4. HUGGINGFACE TOKEN CHECK:")
    print("-" * 40)
    
    hf_token = None
    token_sources = []
    
    if os.environ.get("HF_TOKEN"):
        hf_token = "Found"
        token_sources.append("environment variable")
    
    hf_file = Path.home() / ".huggingface_token"
    if hf_file.exists():
        hf_token = "Found"
        token_sources.append(f"file: {hf_file}")
    
    win_file = Path.home() / "huggingface_token.txt"
    if win_file.exists():
        hf_token = "Found"
        token_sources.append(f"file: {win_file}")
    
    if hf_token:
        print(f"✅ HuggingFace token found in: {', '.join(token_sources)}")
    else:
        print("❌ HuggingFace token NOT found")
        issues.append("HuggingFace token not found")
    
    # Initialize voice filter
    print("\n5. VOICE FILTER INITIALIZATION:")
    print("-" * 40)
    
    try:
        threshold = float(settings['voice_filter_threshold'])
        vf = VoiceFilter(profile_path, threshold)
        
        if vf.inference:
            print("✅ Pyannote model loaded successfully")
        else:
            print("❌ Pyannote model failed to load")
            issues.append("Pyannote model initialization failed")
        
        if vf.user_embedding is not None:
            print("✅ User voice profile loaded")
        else:
            print("❌ User voice profile NOT loaded")
            issues.append("Voice profile loading failed")
            
    except Exception as e:
        print(f"❌ Voice filter initialization failed: {e}")
        issues.append(f"Voice filter error: {e}")
        vf = None
    
    # Test with voice recordings if available
    print("\n6. VOICE RECORDING TEST:")
    print("-" * 40)
    
    voice_dirs = [
        "voice recordings",
        "voice recording for test",
        "voice_recordings"
    ]
    
    test_results = []
    found_recordings = False
    
    for dir_name in voice_dirs:
        if Path(dir_name).exists():
            print(f"\nTesting recordings in: {dir_name}/")
            found_recordings = True
            
            for audio_file in Path(dir_name).glob("*.wav"):
                if vf and vf.inference:
                    try:
                        # Load audio file
                        import librosa
                        audio, sr = librosa.load(audio_file, sr=16000)
                        
                        # Test voice
                        is_user, confidence = vf.is_user_voice(audio, sr)
                        distance = 1.0 - confidence
                        
                        result = {
                            'file': audio_file.name,
                            'distance': float(distance),  # Convert numpy float to Python float
                            'is_user': bool(is_user),    # Convert numpy bool to Python bool
                            'should_respond': bool(vf.should_respond(is_user, settings['inverted_voice_response'] == 'Yes' or settings['inverted_voice_response'] == True))
                        }
                        test_results.append(result)
                        
                        status = "🟢" if result['should_respond'] else "🔴"
                        print(f"{status} {audio_file.name}: distance={distance:.3f}, user={is_user}, respond={result['should_respond']}")
                        
                    except Exception as e:
                        print(f"❌ Error testing {audio_file.name}: {e}")
    
    if not found_recordings:
        print("No voice recordings found for testing")
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    if issues:
        print("\n❌ ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ All checks passed!")
    
    # Save diagnostic report
    report = {
        'timestamp': datetime.now().isoformat(),
        'configuration': settings,
        'issues': issues,
        'test_results': test_results,
        'profile_exists': Path(profile_path).exists() if 'profile_path' in locals() else False,
        'hf_token_found': hf_token is not None,
        'model_loaded': vf.inference is not None if 'vf' in locals() and vf else False
    }
    
    report_file = f"voice_filter_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDiagnostic report saved to: {report_file}")
    
    # Recommendations
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    if test_results:
        user_distances = [r['distance'] for r in test_results if 'Primary' in r['file'] or 'User' in r['file']]
        other_distances = [r['distance'] for r in test_results if 'Colleague' in r['file']]
        
        if user_distances and other_distances:
            user_max = max(user_distances)
            other_min = min(other_distances)
            current_threshold = float(settings['voice_filter_threshold'])
            
            print(f"\nBased on test results:")
            print(f"  Your voice distances: {min(user_distances):.3f} - {max(user_distances):.3f}")
            print(f"  Colleague distances: {min(other_distances):.3f} - {max(other_distances):.3f}")
            print(f"  Current threshold: {current_threshold}")
            
            if other_min > user_max:
                optimal = (user_max + other_min) / 2
                print(f"\n  Recommended threshold: {optimal:.3f}")
                print(f"  (midpoint between {user_max:.3f} and {other_min:.3f})")
            else:
                print("\n  ⚠️  Voice ranges overlap - discrimination may be unreliable")
    
    print("\nNext steps:")
    print("1. Fix any issues listed above")
    print("2. Run './scripts/tune_voice_threshold.py' to calibrate threshold")
    print("3. Test with './test_voice_filter_live.py'")
    print("4. Update threshold in parameters.yaml if needed")

if __name__ == "__main__":
    debug_voice_filter()