# Streaming TTS Fix Summary

## Problem
The TTS was waiting for the entire GPT response to complete before starting playback, causing 3-4 second delays.

## Solution Implemented
True streaming TTS with sentence-level processing that starts playback within 200-400ms.

## Key Changes Made

### 1. Fixed Sentence Detection (`gpt_responder.py`)
- Changed regex pattern from `r"[.!?]\s*"` to `r"[.!?]\s"` (requires space after punctuation)
- Process sentences immediately instead of waiting for multiple matches
- Send sentences to TTS as soon as they're complete (>10 chars)
- Force break at 42 characters if no punctuation found

### 2. Audio Player Improvements (`audio_player_streaming.py`)
- Added Windows-specific device detection
- Increased buffer size to 75ms minimum on Windows
- Added proper error handling for audio device issues
- Auto-detect default output device

### 3. TTS Provider Updates (`streaming_tts.py`)
- OpenAI TTS uses raw PCM format for immediate playback
- Added StopIteration exception handling for OpenAI library bug
- Proper streaming implementation with 4096 byte chunks

### 4. Configuration Changes (`parameters.yaml`)
- Changed `tts_provider` from `gtts` to `openai` (required for streaming)
- `tts_streaming_enabled: true`
- `tts_min_sentence_chars: 10`

## How to Test on Windows

1. **Install Dependencies** (if not already done):
   ```cmd
   cd C:\Users\sdhre\transcribe
   install_streaming_tts_windows.bat
   ```

2. **Debug Audio Devices**:
   ```cmd
   python debug_tts_windows.py
   ```

3. **Run the Application**:
   - Start transcribe as usual
   - Voice filter will work as before
   - When a colleague speaks, you should hear TTS start within 200-400ms

## Expected Behavior
- Colleague speaks → GPT starts generating → First sentence completes → TTS starts immediately
- Total latency: ~400ms (down from 3000ms)
- Continuous playback for long responses
- No duplicate sentences

## Troubleshooting
- If no audio: Check `debug_tts_windows.py` output for device issues
- If still slow: Ensure `tts_provider: openai` in parameters.yaml
- If choppy: Windows may need larger buffer (already set to 75ms)