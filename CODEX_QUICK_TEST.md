# Quick Setup & Test Guide for Transcribe App (disc-clean branch)

## What This App Does
Real-time transcription app that:
- Captures microphone & speaker audio
- Uses voice discrimination (only responds to colleagues, not primary user)
- Provides GPT-4 responses with streaming Text-to-Speech

## Recent Fixes to Test
1. **6-second delay fixed**: `llm_response_interval` reduced from 10s to 1s
2. **Streaming TTS**: Audio should play AS text appears, not after
3. **Voice filter**: 99% accuracy with threshold=0.625

## Minimal Setup Commands

```bash
# 1. Install Python dependencies
pip install numpy==1.26.4 openai==1.66.3 pyaudiowpatch wave==0.0.2
pip install customtkinter==5.2.2 pyperclip PyYAML soundfile gtts
pip install openai-whisper==20240930 flask
pip install pyannote.audio torch torchvision torchaudio

# 2. Install system dependencies
# Windows: choco install ffmpeg
# Linux: apt-get install ffmpeg

# 3. Create API key file
echo "OpenAI:" > app/transcribe/override.yaml
echo "  api_key: YOUR_API_KEY_HERE" >> app/transcribe/override.yaml

# 4. Set HuggingFace token for voice discrimination
export HF_TOKEN=your_huggingface_token
```

## Quick Test Commands

```bash
# Test 1: Comprehensive component test (no audio needed)
python run_comprehensive_tests.py

# Test 2: Check configuration is correct
python -c "from tsutils import configuration; c=configuration.Config().data; print(f\"LLM interval: {c['General']['llm_response_interval']}s (should be 1)\")"

# Test 3: Test audio directly
python test_windows_audio_direct.py

# Test 4: Run the app
cd app/transcribe && python main.py
```

## What to Look For

### Success Indicators:
- ✅ App starts without IndentationError
- ✅ Console shows: `llm_response_interval: 1` (not 10)
- ✅ Voice input → Response appears in ~1 second (not 6)
- ✅ Audio plays while text is still appearing
- ✅ Only responds to non-user voices

### Key Log Messages:
```
[Response Debug] Transcript changed at...  # Voice detected
[TTS Debug] First GPT token received at... # Response starting
[TTS Debug] Sentence detected: ...         # Ready to speak
[TTS Debug] Playing chunk immediately...   # Audio playing
```

## Automated Test Script

```python
# save as quick_test.py
import subprocess
import json

tests = [
    ("Config Check", "python -c \"from tsutils import configuration; c=configuration.Config().data; assert c['General']['llm_response_interval']==1\""),
    ("Import Check", "python -c \"import app.transcribe.gpt_responder; print('Imports OK')\""),
    ("Component Test", "python run_comprehensive_tests.py"),
]

for name, cmd in tests:
    print(f"\n=== {name} ===")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ {name} passed")
    else:
        print(f"❌ {name} failed: {result.stderr}")
```

## If Tests Fail

1. **ModuleNotFoundError**: Install missing package with pip
2. **No API key**: Add to app/transcribe/override.yaml
3. **Audio device error**: Check Windows audio settings
4. **Import errors**: Ensure you're in venv (Windows: `venv\Scripts\activate`)

The main thing to verify: **Voice → Response in 1 second with streaming audio**