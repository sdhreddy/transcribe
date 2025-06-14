# Claude Assistant Best Practices for Technical Projects

## How to Be an Effective AI Development Partner

This document outlines the practices that have made our Claude-human collaboration highly successful, achieving 99% accuracy voice discrimination and <400ms latency in our transcribe project.

## 1. Context Management and Memory

### The CLAUDE.md Master Document
**Purpose**: Persistent memory across sessions

**Structure**:
```markdown
# Master Context for [Project Name]

## Current Status
- Brief project overview
- Latest working state
- Key metrics achieved

## Session History
### [Date] - Session Title
- Problems addressed
- Solutions implemented  
- Files modified
- Test results
- Important learnings

## Important Files
- List of critical files with descriptions
- Configuration files and their purposes
- Test files and what they validate

## Known Issues
- Current bugs
- Workarounds in place
- Future improvements needed
```

**Best Practice**: Update CLAUDE.md after EVERY significant change or discovery

### Pre-Task Context Check
Always start sessions by:
1. Reading CLAUDE.md for project state
2. Checking recent git commits
3. Understanding current goals
4. Reviewing any instruction documents

```python
# Example session start
I'll check the master context and claude.md file for history and instructions.
[Reads CLAUDE.md]
Based on the CLAUDE.md file, I can see:
- Current status: Voice filter at 99% accuracy
- Latest work: Streaming TTS implementation
- Key issue: TTS delay of 3 seconds
```

## 2. Task Management with Todo Lists

### Proactive Task Planning
Use TodoWrite immediately when receiving complex requests:

```
# Good practice - break down the request
User: "Fix the streaming TTS delay issue"
Assistant: I'll create a todo list to track this task systematically.

[Creates todos]:
1. Analyze current TTS implementation
2. Identify bottlenecks causing delay  
3. Implement streaming solution
4. Test latency improvements
5. Document changes
```

### Real-Time Status Updates
Mark todos as in_progress/completed immediately:
```
- Mark as in_progress when starting
- Mark as completed immediately when done
- Don't batch completions
- Add new todos if discovering additional work
```

## 3. Bug Tracking and Documentation

### Bug Discovery Protocol
When finding a bug:

1. **Document Immediately**
```markdown
### [Bug Name] - [Date]
**Symptoms**: What user experiences
**Root Cause**: Technical explanation
**Discovery Method**: How we found it
**Fix Applied**: Code changes made
**Verification**: How we confirmed the fix
```

2. **Create Test Case**
```python
# Always create a test to prevent regression
def test_voice_filter_yaml_boolean():
    """Test that YAML 'Yes' is handled correctly."""
    assert _is_enabled('Yes') == True
    assert _is_enabled('No') == False
```

3. **Update Master Context**
Add to CLAUDE.md under "Important Learnings" or "Bug Fixes"

### Maintaining Bug Registry
Create BUGS_AND_FIXES_REGISTRY.md with:
- Severity levels (Critical/High/Medium/Low)
- Discovery dates
- Symptoms and root causes
- Code snippets of fixes
- Verification methods

## 4. Code Change Best Practices

### Before Making Changes
1. **Read relevant files first**
```python
# Always read before editing
[Reads app/transcribe/gpt_responder.py]
# Understand the current implementation
# Identify the specific area to change
```

2. **Check for existing patterns**
```python
# Look for similar implementations
[Grep for "streaming" or "tts"]
# Follow existing code style
```

3. **Backup critical files**
```bash
# For major changes
cp important_file.py important_file.py.backup
```

### Making Changes

1. **Incremental modifications**
```python
# Change one thing at a time
# Test after each change
# Commit working states
```

2. **Preserve working code**
```python
# Comment rather than delete when uncertain
# if old_approach:  # Keeping for reference
#     old_code()
if new_approach:
    new_code()
```

3. **Add helpful comments**
```python
# Windows fix: Minimum 75ms buffer for stability
if platform.system() == "Windows":
    buf_ms = max(75, buf_ms)
```

## 5. Testing and Verification

### Test-First Approach
1. **Create test before fixing**
```python
# Write test that fails
# Fix the code
# Verify test passes
```

2. **Multiple test types**
```python
- Unit tests (test_voice_filter.py)
- Integration tests (test_audio_flow.py)
- Live tests (test_voice_filter_live.py)
- Performance tests (test_tts_latency.py)
```

3. **Real-world testing**
```
Always test with:
- Real voice recordings
- Actual hardware (not just mocks)
- Production-like conditions
- Multiple platforms
```

## 6. Communication Patterns

### Status Updates
Keep user informed without overwhelming:
```
Good: "Found the issue - audio being accumulated twice"
Bad: [20 lines explaining audio processing theory]
```

### Error Handling
Be specific and actionable:
```
Good: "PyAudio not found. Run: pip install pyaudiowpatch"
Bad: "Audio error occurred"
```

### Progress Indicators
```
"Analyzing current implementation..." [Does analysis]
"Found 3 issues. Fixing them now..."
"Testing fixes..."
"✓ All tests passing. Latency reduced to 400ms"
```

## 7. Cross-Platform Considerations

### Document Platform Differences
```python
# Windows-specific
if platform.system() == "Windows":
    # Document why this is needed
    buffer_size = 75  # Windows audio stability

# Linux-specific  
else:
    buffer_size = 50  # Linux handles smaller buffers
```

### Create Platform-Specific Guides
- install_windows.bat
- install_linux.sh
- debug_windows.py
- Platform-specific READMEs

## 8. Knowledge Transfer

### Create Comprehensive Guides
When sharing with other teams:

1. **Implementation Guide**
   - Architecture overview
   - Key components
   - Configuration details
   - Performance metrics

2. **Bug Registry**
   - All bugs found
   - Root causes
   - Fixes applied
   - Prevention strategies

3. **Best Practices**
   - What worked well
   - What to avoid
   - Testing strategies
   - Monitoring setup

### Include Working Examples
```python
# Don't just explain - show working code
# Include full context
# Add expected output
# Explain why it works
```

## 9. Session Continuity

### End of Session Protocol
1. **Update CLAUDE.md**
2. **Commit all changes**
3. **Create summary document**
4. **Note any pending work**

### Session Handoff
```markdown
## Session Summary - [Date]
### Completed
- Fixed streaming TTS (latency 3s → 400ms)
- Added Windows audio fixes
- Created test suite

### Pending
- Test on ARM64 platform
- Optimize for slower systems

### Key Files Changed
- gpt_responder.py: Added sentence streaming
- audio_player.py: Windows buffer fixes
```

## 10. Performance Tracking

### Maintain Metrics
Track key performance indicators:
```markdown
## Performance History
- January 10: Voice filter accuracy 60%
- January 11: Fixed audio accumulation → 99%
- January 13: TTS latency 3000ms
- January 14: Streaming fix → 400ms
```

### Create Benchmarks
```python
# Always measure before/after
start_time = time.time()
# ... code ...
latency = time.time() - start_time
print(f"Latency: {latency*1000:.0f}ms")
```

## 11. Git Best Practices

### Meaningful Commits
```bash
# Good commit message
git commit -m "Fix streaming TTS sentence detection

- Changed regex to require space after punctuation
- Process first match immediately instead of last
- Reduces latency from 3000ms to 400ms"

# Bad commit message  
git commit -m "Fix TTS"
```

### Branch Strategy
```
main → stable release
dev → active development  
feature/xyz → specific features
fix/abc → bug fixes
```

## 12. Debugging Methodology

### Systematic Approach
1. **Reproduce the issue**
2. **Isolate the component**
3. **Add logging/monitoring**
4. **Test hypothesis**
5. **Verify fix**
6. **Add regression test**

### Debug Tools Creation
Create specific debug tools:
```python
# debug_tts_windows.py
# monitor_realtime.py
# test_voice_filter_live.py
# calibrate_threshold.py
```

## Example Success Story

### Voice Filter Implementation
1. **Started at 60% accuracy**
2. **Discovered audio accumulation bug**
3. **Fixed → 99% accuracy**
4. **Created comprehensive tests**
5. **Documented in CLAUDE.md**
6. **Shared with ARM64 team**

This systematic approach led to production-ready code with exceptional performance.

## Key Principles

1. **Document Everything** - Future you will thank you
2. **Test First** - Catch bugs before users do
3. **Incremental Progress** - Small steps, frequent verification
4. **Real-World Testing** - Mocks aren't enough
5. **Knowledge Sharing** - Help other teams succeed
6. **Continuous Improvement** - Always refine the process

---

*These practices have enabled our team to achieve 99% voice discrimination accuracy and <400ms TTS latency. Following these guidelines will help any Claude-human team achieve similar success.*