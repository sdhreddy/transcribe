# Backup Restore Information

## Backup Created: January 13, 2025

### Backup Details:
- **Commit Hash**: `91a8891a6c079162cf36e5b6c563d39dc4a26332`
- **Commit Message**: "Add comprehensive tests for sentence splitting and TTS delay fixes"
- **Branch**: `disc-clean`
- **Backup Branch**: `backup-before-streaming-tts`

### To Restore This Backup:

```bash
# Option 1: Reset current branch to backup state
git reset --hard 91a8891a6c079162cf36e5b6c563d39dc4a26332

# Option 2: Switch to backup branch
git checkout backup-before-streaming-tts

# Option 3: Create new branch from backup
git checkout -b restored-from-backup 91a8891a6c079162cf36e5b6c563d39dc4a26332
```

### Current State Before Streaming TTS Implementation:
- Voice filter: 99% accurate
- TTS delay: 2-4 seconds (reduced from original by 400ms)
- All tests passing
- Configuration:
  - Voice filter threshold: 0.625
  - Inverted voice response: True
  - Phrase timeout: 5.0 seconds
  - UI update interval: 100ms

### Files That Will Be Modified:
- `/app/transcribe/audio_player.py`
- `/app/transcribe/gpt_responder.py`
- `/app/transcribe/appui.py`
- `/app/transcribe/parameters.yaml`
- New file: `/app/transcribe/streaming_tts.py`