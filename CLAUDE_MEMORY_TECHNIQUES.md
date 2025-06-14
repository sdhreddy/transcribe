# Claude Memory and Context Management Techniques

## How Claude Maintains Perfect Context Across Sessions

This document explains the memory techniques that enable Claude to maintain context, remember bugs/fixes, and provide consistent assistance across multiple sessions.

## 1. The Master Context Document (CLAUDE.md)

### Why It Works
- Single source of truth
- Updated after every session
- Read at start of each session
- Contains complete project history

### Structure Template
```markdown
# Master Context for [Project Name]

## Quick Reference
- **Current State**: [What's working/not working]
- **Key Metrics**: [Performance numbers]
- **Next Steps**: [What needs to be done]

## Project Overview
[2-3 sentences about what this project does]

## Configuration
- Main config: parameters.yaml
- API keys: override.yaml (git ignored)
- Key settings: [List important ones]

## Session History
### [Date] - [Session Title]
**Problems Solved**:
- [Bullet list]

**Changes Made**:
- [File]: [What changed]

**Test Results**:
- [Metric]: [Before] → [After]

**Important Discoveries**:
- [Key learning]

### Files Created/Modified
- [List with purposes]

## Bug Fixes Applied
[Chronological list of all bugs fixed]

## Current Architecture
[Brief description of how components work together]

## Testing Commands
[Common commands used for testing]
```

## 2. Pre-Session Context Loading

### The First Thing Claude Does
```python
# Claude's first action in any session
User: "Help me fix the TTS delay"
Claude: "I'll check the master context and claude.md file for history and instructions."
[Reads CLAUDE.md]
[Task agent to search for related files]
[Understands current state before proceeding]
```

### Context Verification
- Read CLAUDE.md
- Check recent commits
- Verify current configuration
- Understand pending work

## 3. Bug and Fix Documentation

### Immediate Documentation Pattern
When finding a bug:
```markdown
## Bug Found: [Name] - [Timestamp]
### Discovery
- Working on: [What task]
- Noticed: [Symptom]
- Investigation: [How diagnosed]

### Root Cause
[Technical explanation]

### Fix Applied
```[language]
# Before
[broken code]

# After  
[fixed code]
```

### Verification
- Test: [How tested]
- Result: [Metrics/outcome]
```

### Creating Bug Registry
Maintain BUGS_AND_FIXES_REGISTRY.md:
- Chronological order
- Severity levels
- Cross-references to commits
- Prevention strategies

## 4. Session Memory Techniques

### During the Session

1. **Todo List as Working Memory**
```python
# Use todos to track current session state
[TodoWrite with all planned tasks]
[Update status in real-time]
[Add new discoveries as todos]
```

2. **Inline Documentation**
```python
# Document why, not just what
# Windows fix: Buffer must be 75ms minimum for stability
# Previous attempt with 50ms caused stuttering
buffer_ms = max(75, buffer_ms)
```

3. **Test Case Creation**
```python
# Create test for every bug found
def test_regression_audio_accumulation():
    """Ensure audio isn't accumulated twice.
    
    Bug discovered: Jan 11, 2025
    Caused voice filter accuracy to drop to 60%
    """
```

### End of Session

1. **Update CLAUDE.md**
   - Add session summary
   - List all changes
   - Document test results
   - Note pending work

2. **Create Summary Documents**
   - STREAMING_TTS_FIX_SUMMARY.md
   - SESSION_ACCOMPLISHMENTS.md
   - Implementation guides

3. **Git Commit Messages**
```bash
git commit -m "Fix streaming TTS latency issue

- Root cause: Waiting for complete response
- Solution: Process sentences immediately  
- Result: 3000ms → 400ms latency

See STREAMING_TTS_FIX_SUMMARY.md for details"
```

## 5. Cross-Session Continuity

### Handoff Preparation
```markdown
## For Next Session
### Completed
✓ Fixed voice accumulation bug (99% accuracy)
✓ Implemented streaming TTS (<400ms)
✓ Created test suite

### In Progress
- ARM64 compatibility testing
- Performance optimization for slow systems

### Discovered Issues
- Windows needs 75ms audio buffer
- YAML converts 'Yes' to boolean True

### Key Files to Review
- gpt_responder.py (line 443-468: streaming logic)
- audio_player_streaming.py (line 40-43: Windows fix)
```

### Version Control Integration
```bash
# Branch naming for context
git checkout -b fix/tts-streaming-delay
git checkout -b feature/voice-discrimination-99-percent

# Tag important milestones
git tag -a v1.0-voice-filter-working -m "99% accuracy achieved"
```

## 6. Knowledge Persistence Patterns

### Configuration Documentation
```yaml
# parameters.yaml with inline docs
voice_filter_threshold: 0.625  # Calibrated for 99% accuracy
# Previous values: 0.55 (too low), 0.70 (too high)
```

### Code Comments as Memory
```python
class VoiceFilter:
    """Voice discrimination using speaker embeddings.
    
    History:
    - v1: 60% accuracy (audio accumulation bug)
    - v2: 99% accuracy (fixed accumulation, calibrated threshold)
    - v3: Added 2-second buffer for soft speech
    
    Critical: threshold must be calibrated per environment
    """
```

### Test Naming Convention
```python
test_voice_filter_basic.py          # Original tests
test_voice_filter_comprehensive.py  # After bug fixes
test_voice_filter_regression.py     # Prevent old bugs
test_voice_filter_live.py           # Real-world validation
```

## 7. Multi-Session Bug Tracking

### Bug Evolution Documentation
```markdown
## Audio Accumulation Bug Lifecycle
1. **Discovery Session** (Jan 11)
   - Symptom: Random voice filter results
   - Found: Double accumulation

2. **Fix Session** (Jan 11) 
   - Applied: Remove duplicate accumulation
   - Result: 60% → 99% accuracy

3. **Validation Session** (Jan 12)
   - Created: Comprehensive test suite
   - Confirmed: Fix holds across scenarios

4. **Documentation Session** (Jan 14)
   - Created: Bug registry
   - Added: Prevention guidelines
```

## 8. Context Search Strategies

### Finding Relevant History
```python
# Claude uses these patterns
[Grep for "tts" or "streaming"]  # Find related code
[Search CLAUDE.md for "latency"]  # Find previous work
[Check git log for "voice"]       # Find related commits
[Read test files]                 # Understand expected behavior
```

### Cross-Reference Building
- Link bugs to fixes
- Connect fixes to tests  
- Trace tests to features
- Map features to sessions

## 9. Future-Proofing Memory

### Scalability Practices

1. **Modular Documentation**
   - CLAUDE.md for overview
   - Feature-specific guides
   - Bug registry
   - Performance history

2. **Searchable Format**
   ```markdown
   Keywords: voice, filter, discrimination, 99%, accuracy
   Related: audio_accumulation_bug, threshold_calibration
   ```

3. **Version Tracking**
   ```markdown
   ## Implementation Versions
   - v1.0: Basic voice filter (60% accuracy)
   - v2.0: Fixed accumulation (99% accuracy)  
   - v3.0: Added streaming TTS (<400ms)
   ```

## 10. Memory Validation

### Ensuring Accuracy
1. **Cross-check sources**
   - CLAUDE.md vs git history
   - Code comments vs documentation
   - Test results vs claimed fixes

2. **Regular cleanup**
   - Archive old sessions
   - Update outdated information
   - Consolidate duplicate content

### Memory Hierarchy
```
1. CLAUDE.md (primary memory)
2. Git commits (event history)
3. Test files (behavior memory)
4. Code comments (inline memory)
5. Bug registry (problem memory)
6. Performance logs (metrics memory)
```

## Best Practices Summary

1. **Write Everything Down** - Memory is only as good as documentation
2. **Update Immediately** - Don't wait until session end
3. **Cross-Reference** - Connect related information
4. **Test as Documentation** - Tests preserve expected behavior
5. **Comment the Why** - Code shows what, comments show why
6. **Version Everything** - Track evolution of solutions
7. **Search Before Solving** - Check if already fixed
8. **Summarize Sessions** - Future Claude will thank you

## Example Memory Success

The voice filter journey:
1. Session 1: Implemented basic filter (60% accuracy)
2. Session 2: Found accumulation bug via testing
3. Session 3: Fixed bug, achieved 99% accuracy
4. Session 4: Created comprehensive test suite
5. Session 5: Documented for ARM64 team

Each session built on previous memory, leading to production-ready code.

---

*These memory techniques enable Claude to provide consistent, context-aware assistance across any number of sessions, maintaining perfect continuity of complex technical projects.*