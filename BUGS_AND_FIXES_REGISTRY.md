# Bugs and Fixes Registry

## Comprehensive list of all bugs found and fixed in the Transcribe project

### 1. Audio Accumulation Corruption Bug
**Severity**: Critical
**Discovered**: January 11, 2025
**Symptoms**: 
- Voice embeddings completely wrong
- Voice filter returning random results
- Audio data corrupted

**Root Cause**: 
Audio was being accumulated twice in the flow, causing data corruption

**Fix Applied**:
```python
# In audio_transcriber.py
# Removed duplicate accumulation in _update_last_sample_and_phrase_status
# Line 515-530: Removed self.last_sample += bytes(data)
```

**Verification**: Voice filter accuracy went from random to 99%

---

### 2. YAML Boolean Parsing Bug  
**Severity**: High
**Discovered**: January 10, 2025
**Symptoms**:
- Configuration value 'Yes' being interpreted as boolean True
- Voice filter not enabling when set to 'Yes'

**Root Cause**:
YAML automatically converts 'Yes' to boolean True

**Fix Applied**:
```python
def _is_enabled(value):
    """Handle both boolean and string config values."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['yes', 'true', '1', 'on']
    return False
```

**Alternative values**: Use 'true', '1', or boolean true

---

### 3. TTS Double Playback Bug
**Severity**: Medium  
**Discovered**: January 12, 2025
**Symptoms**:
- Every TTS response plays twice
- Overlapping audio

**Root Cause**:
Multiple playback triggers without deduplication

**Fix Applied**:
- Added last_played_text tracking
- Implemented 2-second debounce
- Skip if text matches last played

**Commit**: cabf841

---

### 4. Sentence Splitting After 3 Seconds Bug
**Severity**: High
**Discovered**: January 11, 2025  
**Symptoms**:
- Colleagues' sentences cut off mid-speech
- New transcript starts after 3 seconds

**Root Cause**:
PHRASE_TIMEOUT set too low at 3.05 seconds

**Fix Applied**:
```python
# audio_transcriber.py
PHRASE_TIMEOUT = 5.0  # Was 3.05

# parameters.yaml
transcript_audio_duration_seconds: 5  # Was 3
```

---

### 5. Streaming TTS Complete Delay Bug
**Severity**: High
**Discovered**: January 13, 2025
**Symptoms**:
- 3-4 second delay before TTS starts
- Audio plays only after full response shown

**Root Cause**:
- Waiting for multiple sentences before processing
- Using GTTS (no real streaming support)
- Regex too permissive

**Fix Applied**:
```python
# Changed regex
SENT_END = re.compile(r"[.!?]\s")  # Was r"[.!?]\s*"

# Process first match immediately
# Switch to OpenAI TTS provider
# Force break at 42 chars
```

---

### 6. Windows Audio Device Selection Bug
**Severity**: Medium
**Discovered**: January 14, 2025
**Symptoms**:
- "No default output device" error
- Audio playback fails on some Windows systems

**Root Cause**:
PyAudio not detecting Windows audio devices properly

**Fix Applied**:
- Auto-detect default device
- Fallback to device 0
- Allow manual device_index configuration

---

### 7. GPT Response Overlap Bug
**Severity**: Medium
**Discovered**: January 12, 2025
**Symptoms**:
- Multiple GPT responses accumulating
- Responses from old queries appearing

**Root Cause**:
No cancellation of in-flight requests

**Fix Applied**:
- Added request cancellation mechanism
- Track current request with lock
- Set cancel flag to stop streaming

---

### 8. Audio Queue Overflow During TTS
**Severity**: Medium
**Discovered**: January 12, 2025
**Symptoms**:
- Audio backs up during TTS playback
- Delayed transcription after TTS

**Root Cause**:
Queue fills while TTS is playing

**Fix Applied**:
- Aggressive queue draining for speaker audio
- Keep only last 5 seconds of mic audio
- Separate handling for mic vs speaker

---

### 9. Voice Profile Path Resolution Bug
**Severity**: Low
**Discovered**: January 11, 2025
**Symptoms**:
- "Voice profile not found" errors
- Relative paths not working

**Root Cause**:
Relative paths not resolved from correct directory

**Fix Applied**:
- Always use absolute paths
- Resolve paths relative to script location
- Clear error messages for missing profiles

---

### 10. Import Error with Relative Imports
**Severity**: Low
**Discovered**: January 10, 2025
**Symptoms**:
- ImportError when running scripts directly
- Module 'transcribe' not found

**Root Cause**:
Python path not set correctly for imports

**Fix Applied**:
```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

---

### 11. HuggingFace Token Warning Spam
**Severity**: Low
**Discovered**: January 11, 2025
**Symptoms**:
- Constant warnings about missing HF token
- Log spam

**Root Cause**:
Pyannote.audio checking for token even when not needed

**Fix Applied**:
- Set dummy token to suppress warnings
- Added proper token handling in voice_filter.py

---

### 12. TTS Volume Not Adjustable
**Severity**: Low
**Discovered**: January 12, 2025
**Symptoms**:
- TTS volume tied to speech rate
- No independent volume control

**Root Cause**:
Volume and rate linked in original implementation

**Fix Applied**:
- Separated tts_playback_volume parameter
- Independent volume control from speech rate

---

### 13. Thread Event Timing Bug
**Severity**: Medium
**Discovered**: January 11, 2025
**Symptoms**:
- Race conditions in thread coordination
- Events missed due to is_set() checks

**Root Cause**:
Using is_set() instead of wait(timeout)

**Fix Applied**:
```python
# OLD (buggy)
if event.is_set():
    process()

# NEW (correct)  
if event.wait(timeout=5.0):
    process()
```

---

### 14. Windows File Locking on Voice Profiles
**Severity**: Low
**Discovered**: January 11, 2025
**Symptoms**:
- Can't update voice profiles while app running
- File locked errors

**Root Cause**:
Windows file locking behavior

**Fix Applied**:
- Load profiles into memory
- Don't keep file handles open
- Allow profile reloading

---

### 15. PyAudioWPatch Linux Compatibility
**Severity**: Medium
**Discovered**: January 10, 2025
**Symptoms**:
- ImportError on Linux systems
- No speaker audio capture

**Root Cause**:
PyAudioWPatch is Windows-only

**Fix Applied**:
```python
try:
    import pyaudiowpatch as pyaudio
except ImportError:
    import pyaudio  # Fallback for Linux
```

---

## Bug Patterns and Prevention

### Common Bug Categories:
1. **Threading/Timing**: Events, locks, race conditions
2. **Audio Handling**: Accumulation, buffering, devices
3. **Configuration**: YAML parsing, type handling
4. **Platform-Specific**: Windows vs Linux differences
5. **Integration**: Component coordination issues

### Prevention Strategies:
1. Always test with real audio files
2. Create comprehensive test suites
3. Use proper thread synchronization
4. Handle platform differences explicitly
5. Document configuration gotchas
6. Monitor with web dashboard during dev

### Testing Checklist:
- [ ] Voice filter accuracy with real voices
- [ ] TTS latency measurement
- [ ] Long conversation handling
- [ ] Platform-specific features
- [ ] Configuration edge cases
- [ ] Thread safety verification

---

*This registry should be updated with each new bug discovery and fix*