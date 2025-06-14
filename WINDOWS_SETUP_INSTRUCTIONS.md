# Windows Setup Instructions for Streaming TTS

## IMPORTANT: Follow these steps IN ORDER

### Step 1: Pull Latest Changes
```cmd
cd C:\Users\sdhre\transcribe
git pull
```

### Step 2: Activate Virtual Environment
```cmd
venv\Scripts\activate
```

### Step 3: Install Required Dependencies (if not already installed)
```cmd
pip install pyaudio openai gtts
```
**Note**: If pyaudio fails, use the provided script:
```cmd
install_pyaudio_windows.bat
```

### Step 4: Verify API Key
Make sure your `app\transcribe\override.yaml` contains your OpenAI API key:
```yaml
OpenAI:
  api_key: YOUR_ACTUAL_API_KEY_HERE
```

### Step 5: Run Monitoring Dashboard (OPTIONAL - in separate terminal)
```cmd
# Open new terminal
cd C:\Users\sdhre\transcribe
venv\Scripts\activate
python monitor_streaming_tts.py
```
Then open http://localhost:5555 in your browser to see real-time streaming metrics.

### Step 6: Launch Application
```cmd
# In main terminal
run_windows_launch.bat
```

**OR manually:**
```cmd
cd app\transcribe
python main.py
```

## What to Look For:

### In Console:
1. **[INIT DEBUG]** messages showing TTS initialization
2. **[TTS Debug]** messages showing:
   - Token received
   - Sentence detected
   - Audio chunk generation
   - First audio chunk timing

### Expected Behavior:
1. Colleague speaks → Voice filter detects (non-user)
2. GPT response starts → Text appears in UI
3. **STREAMING**: Audio should start playing WHILE text is still appearing
4. Each sentence plays as it completes (not waiting for full response)

### If Streaming is NOT Working:
Look for these issues:
- No [TTS Debug] messages = TTS not initialized
- "OpenAI TTS complete: 71 chunks" before ANY audio = Not streaming
- Old response playing = Response duplication issue

### Debugging Commands:

1. **Test basic audio**:
```cmd
python test_windows_audio_direct.py
```

2. **Debug streaming flow**:
```cmd
python debug_streaming_realtime.py --test
```

3. **Check configuration**:
```cmd
python verify_streaming_tts_setup.py
```

## Monitor Dashboard Features:

The web dashboard at http://localhost:5555 shows:
- **Token Flow**: Tokens arriving from GPT
- **Sentence Detection**: When sentences are detected
- **TTS Generation**: When audio is generated
- **Audio Playback**: When audio chunks play
- **Timing Analysis**: Latency between stages

## Key Indicators of Success:

✅ **Streaming Working**:
- First audio plays within 1 second of response starting
- Audio plays progressively as text appears
- Smooth, continuous playback

❌ **Streaming NOT Working**:
- Long delay (3-6 seconds) before any audio
- All audio plays at once after text completes
- Audio stops after a few words

## Troubleshooting:

1. **No audio at all**:
   - Check API key in override.yaml
   - Run `python test_windows_audio_direct.py`

2. **Audio plays but not streaming**:
   - Check [TTS Debug] messages in console
   - Verify `tts_streaming_enabled: true` in parameters.yaml

3. **Old responses playing**:
   - Response duplication issue
   - Restart application

4. **Terminal shows errors as commands**:
   - Use `run_windows_launch.bat` instead of running directly
   - Or redirect output: `python main.py 2>&1`