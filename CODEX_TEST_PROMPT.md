# OpenAI Codex Test Environment Setup and Comprehensive Testing

## Project Overview
You need to set up and test the "transcribe" application - a real-time transcription system with AI-powered responses. The application captures both microphone and speaker audio, uses voice discrimination to respond only to colleagues (not the primary user), and features streaming Text-to-Speech (TTS) for immediate audio feedback.

## Current Testing Goals
1. Verify the 6-second GPT response delay has been fixed (was 10s polling interval, now 1s)
2. Confirm streaming TTS works - audio should play AS text appears, not after
3. Test voice discrimination (99% accuracy achieved, threshold=0.625)
4. Ensure no response duplication issues

## Environment Setup Requirements

### Python Version
- Python 3.11.0 or higher (3.12 compatible)

### Core Dependencies to Install
```bash
# Core packages
pip install numpy==1.26.4
pip install openai==1.66.3
pip install pyaudio  # Or pyaudiowpatch on Windows
pip install wave==0.0.2
pip install customtkinter==5.2.2
pip install tkinter-tooltip
pip install pyperclip
pip install PyYAML
pip install soundfile
pip install gtts
pip install playsound==1.2.2

# Voice discrimination
pip install pyannote.audio
pip install torch --extra-index-url https://download.pytorch.org/whl/cu121

# Optional monitoring
pip install flask  # For web-based monitoring dashboard

# Windows-specific
pip install pyaudiowpatch  # Instead of pyaudio on Windows

# Whisper for STT
pip install openai-whisper==20240930
```

### System Requirements
1. **FFmpeg** - Required for audio processing
   - Windows: `choco install ffmpeg` or download from ffmpeg.org
   - Linux: `apt-get install ffmpeg`

2. **Audio devices** - Microphone and speaker loopback

3. **Whisper.cpp binaries** (already in bin/ directory):
   - bin/main.exe
   - bin/whisper.dll

### Configuration Files Needed

1. **app/transcribe/override.yaml** - Create with:
```yaml
OpenAI:
  api_key: YOUR_OPENAI_API_KEY_HERE
```

2. **Voice profile** - my_voice.npy (for voice discrimination)

3. **HuggingFace token** - For pyannote.audio (set as environment variable)
```bash
export HUGGINGFACE_TOKEN=your_token_here
```

## Test Execution Steps

### 1. Run Comprehensive Test Suite
```bash
cd transcribe
python run_comprehensive_tests.py
```

This tests:
- Configuration (llm_response_interval = 1s)
- Module imports
- GPT responder timing
- Audio flow simulation
- Sentence detection
- TTS provider creation
- Audio player creation
- Response timing logs

### 2. Run E2E Streaming Test
```bash
python test_e2e_streaming_full.py
```

### 3. Run Monitoring (Optional)
```bash
# Terminal 1
python monitor_streaming_tts.py
# Open http://localhost:5555 in browser

# Terminal 2
cd app/transcribe
python main.py
```

### 4. Test Voice Discrimination
```bash
python test_voice_filter_e2e.py
```

## Expected Test Results

### Configuration Tests Should Show:
- llm_response_interval: 1 (not 10)
- tts_streaming_enabled: true
- tts_provider: openai
- continuous_response: true
- voice_filter_enabled: true
- voice_filter_threshold: 0.625

### Timing Tests Should Show:
- Voice input → GPT response: ~1 second (was 6 seconds)
- First token → First audio: <1 second
- Sentences play progressively, not all at once

### Voice Filter Tests Should Show:
- User voice ignored (distance ~0.32)
- Colleague voices processed (distance 0.93-1.03)
- Threshold: 0.625 with inverted logic

## Debugging Commands

### Check Audio Devices
```python
import pyaudio
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(f"{i}: {info['name']} - {info['maxInputChannels']} in, {info['maxOutputChannels']} out")
```

### Test TTS Directly
```bash
python test_windows_audio_direct.py
```

### Debug Streaming Flow
```bash
python debug_streaming_realtime.py --test
```

## Key Files to Monitor

### Log Messages to Watch For:
- `[Response Debug] Transcript changed at...` - Shows GPT trigger timing
- `[TTS Debug] First GPT token received at...` - Response start time
- `[TTS Debug] Sentence detected:...` - Sentence boundary detection
- `[TTS Debug] Playing chunk immediately:...` - Audio playback confirmation
- `[INFO] Voice filter: is_user=...` - Voice discrimination results

### Critical Code Sections:
1. **app/transcribe/parameters.yaml** - Check llm_response_interval: 1
2. **app/transcribe/gpt_responder.py** - Streaming token handler
3. **app/transcribe/audio_transcriber.py** - Transcript change event
4. **app/transcribe/streaming_tts.py** - OpenAI TTS implementation
5. **app/transcribe/voice_filter.py** - Voice discrimination logic

## Success Criteria

1. **No Errors on Startup** - Application launches without IndentationError
2. **Fast Response** - GPT responds within 1-2 seconds of voice input
3. **Streaming Audio** - Audio plays while text is still appearing
4. **Voice Discrimination** - Only responds to non-user voices
5. **No Duplicates** - Each response plays only once

## Automated Test Script

Create and run this comprehensive test:

```python
#!/usr/bin/env python3
import subprocess
import time
import sys

def run_test(name, command):
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print(f"{'='*60}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode == 0

# Run all tests
tests = [
    ("Configuration Test", "python run_comprehensive_tests.py"),
    ("E2E Streaming Test", "python test_e2e_streaming_full.py"),
    ("Direct Audio Test", "python test_windows_audio_direct.py"),
    ("Streaming Debug", "python debug_streaming_realtime.py --test"),
]

results = []
for name, cmd in tests:
    success = run_test(name, cmd)
    results.append((name, success))
    time.sleep(1)

# Summary
print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
for name, success in results:
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {name}")
```

## Notes for Codex

- The application uses disc-clean branch
- Voice filter uses inverted logic (responds to colleagues, not user)
- Streaming TTS should play audio progressively, not wait for complete response
- The 6-second delay was caused by llm_response_interval=10, now fixed to 1
- Monitor dashboard helps visualize the streaming flow in real-time
- All fixes have been applied, just need to verify they work correctly