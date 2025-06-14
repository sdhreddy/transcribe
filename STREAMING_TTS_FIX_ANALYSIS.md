# Streaming TTS Fix Analysis

## Root Cause Identified

The streaming TTS feature stopped working because:

1. **Invalid API Parameter**: The OpenAI TTS API does **NOT** support a `stream=True` parameter
2. **Silent Thread Death**: When the TTS worker thread tried to call OpenAI with this invalid parameter, it threw an exception and died silently
3. **No Error Recovery**: The error handling didn't properly log the full traceback or recover from the error

## What Was Happening

### First colleague voice test:
- ✓ Voice captured correctly
- ✓ Visual response shown (LLM streaming worked)
- ✗ NO audio (TTS worker thread crashed on first sentence)

### Second colleague voice test:
- ✓ Voice captured correctly
- ✗ NO visual response (possibly due to system state after first error)
- ✗ NO audio (TTS worker thread already dead)

## Fixes Applied

### 1. Fixed OpenAI TTS API Call (`streaming_tts.py`)

**Before:**
```python
resp = self.client.audio.speech.create(
    model="tts-1",
    voice=self.cfg.voice,
    input=text,
    response_format="pcm",
    stream=True  # ← THIS PARAMETER DOESN'T EXIST!
)
```

**After:**
```python
resp = self.client.audio.speech.create(
    model="tts-1",
    voice=self.cfg.voice,
    input=text,
    response_format="pcm"  # No stream parameter
)

# Use iter_bytes() to get chunks
for chunk in resp.iter_bytes(chunk_size=4096):
    yield chunk
```

### 2. Improved Error Handling (`gpt_responder.py`)

Added better error logging in the TTS worker thread:
- Full traceback logging on exceptions
- Proper task_done() handling even on errors
- Thread continues processing after errors instead of dying

### 3. Enhanced Audio Player Logging (`audio_player_streaming.py`)

Added more detailed initialization logging:
- Device selection logging
- Buffer size calculations
- Full error tracebacks on initialization failures

## Why This Happened

The confusion likely arose because:
1. OpenAI's response object supports iteration via `iter_bytes()` which gives a streaming-like experience
2. Someone may have assumed this required a `stream=True` parameter (like the chat completions API has)
3. The OpenAI TTS API documentation doesn't explicitly mention streaming, leading to assumptions

## Testing the Fix

The user should now test again:
1. Start the application with streaming TTS enabled
2. Speak with the first colleague's voice
3. Check if audio plays correctly
4. Test with second colleague's voice
5. Monitor logs for any errors

## Expected Behavior After Fix

- Visual responses should appear as text streams in
- Audio should start playing shortly after the first sentence is detected
- No exceptions in the logs
- Both visual and audio responses for all voices

## Additional Notes

The OpenAI TTS API does support "streaming" in the sense that:
- The response can be consumed in chunks via `iter_bytes()`
- This allows starting playback before the entire audio is generated
- But it doesn't require (or support) a `stream=True` parameter