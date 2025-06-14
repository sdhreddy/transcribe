# Testing Checklist Template

## Pre-Push Testing Requirements

### 1. Code Changes Summary
- [ ] What files were modified?
- [ ] What was the purpose of changes?
- [ ] Any dependencies added/removed?

### 2. Automated Tests Run
- [ ] Unit tests: `python -m pytest tests/`
- [ ] Integration tests: `python test_streaming_tts_automated.py`
- [ ] Sanity check: `python test_tts_sanity.py`
- [ ] Debug check: `python debug_streaming_audio_issue.py`

### 3. Manual Testing (if automated not possible)
- [ ] Basic functionality works?
- [ ] No new errors introduced?
- [ ] Performance acceptable?

### 4. Test Results
```
Test Name: [PASS/FAIL]
- Error messages (if any):
- Expected vs Actual behavior:
- Screenshots/logs (if relevant):
```

### 5. Known Issues
- [ ] Any failing tests?
- [ ] Workarounds needed?
- [ ] Future fixes required?

### 6. Documentation Updates
- [ ] CLAUDE.md updated with results?
- [ ] Code comments added where needed?
- [ ] README updated if interface changed?

### 7. Final Checks
- [ ] All tests passing or failures documented?
- [ ] No sensitive data (API keys, passwords)?
- [ ] Commit message clear and descriptive?

## Example Usage

```bash
# 1. Run tests
python test_tts_sanity.py
python debug_streaming_audio_issue.py

# 2. Document results in CLAUDE.md
## Testing Session - [Date]
- Ran test_tts_sanity.py: PASSED
- Audio chunks returning bytes correctly
- Latency under 300ms

# 3. Commit with results
git add -A
git commit -m "Fix streaming TTS - tests passing, <300ms latency"
git push
```