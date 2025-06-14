#!/usr/bin/env python3
"""Analyze the streaming TTS flow by examining the code structure without running it."""

import os
import re
import ast

def analyze_file(filepath):
    """Analyze a Python file for streaming TTS patterns."""
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    analysis = {
        'file': filepath,
        'has_streaming': False,
        'sentence_detection': [],
        'tts_calls': [],
        'token_handling': [],
        'issues': []
    }
    
    # Check for streaming indicators
    if 'streaming' in content.lower():
        analysis['has_streaming'] = True
    
    # Find sentence detection patterns
    sentence_patterns = [
        r'sentence_end|end_sentence',
        r'detect.*sentence|sentence.*detect',
        r'\.put\s*\(\s*.*sentence',
        r'sent_q\.put'
    ]
    
    for pattern in sentence_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            analysis['sentence_detection'].append({
                'line': line_num,
                'text': match.group(),
                'context': content[max(0, match.start()-50):match.end()+50].strip()
            })
    
    # Find TTS calls
    tts_patterns = [
        r'tts\.generate|generate_tts',
        r'process_tts|tts_processing',
        r'audio.*chunk|chunk.*audio',
        r'StreamingAudioPlayer'
    ]
    
    for pattern in tts_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            analysis['tts_calls'].append({
                'line': line_num,
                'text': match.group(),
                'context': content[max(0, match.start()-50):match.end()+50].strip()
            })
    
    # Find token handling
    token_patterns = [
        r'on_token|token.*received',
        r'for.*token.*in',
        r'process.*token|token.*process'
    ]
    
    for pattern in token_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            analysis['token_handling'].append({
                'line': line_num,
                'text': match.group(),
                'context': content[max(0, match.start()-50):match.end()+50].strip()
            })
    
    # Check for potential issues
    if 'streaming_complete' in content and 'wait' in content:
        analysis['issues'].append("Might be waiting for complete response before TTS")
    
    if 'join()' in content and 'tts' in content.lower():
        analysis['issues'].append("Possible blocking on TTS completion")
    
    return analysis

def main():
    """Analyze the streaming TTS implementation."""
    print("=== STREAMING TTS FLOW ANALYSIS ===")
    print("Analyzing code structure to understand streaming flow\n")
    
    # Files to analyze
    files_to_check = [
        'app/transcribe/gpt_responder.py',
        'app/transcribe/audio_player_streaming.py',
        'app/transcribe/streaming_tts.py',
        'app/transcribe/audio_player.py'
    ]
    
    results = {}
    
    for filepath in files_to_check:
        print(f"Analyzing {filepath}...")
        analysis = analyze_file(filepath)
        if analysis:
            results[filepath] = analysis
            
            # Show findings
            if analysis['sentence_detection']:
                print(f"  ✓ Found {len(analysis['sentence_detection'])} sentence detection points")
                for item in analysis['sentence_detection'][:2]:
                    print(f"    Line {item['line']}: {item['text']}")
            
            if analysis['tts_calls']:
                print(f"  ✓ Found {len(analysis['tts_calls'])} TTS-related calls")
                for item in analysis['tts_calls'][:2]:
                    print(f"    Line {item['line']}: {item['text']}")
            
            if analysis['token_handling']:
                print(f"  ✓ Found {len(analysis['token_handling'])} token handling points")
                for item in analysis['token_handling'][:2]:
                    print(f"    Line {item['line']}: {item['text']}")
            
            if analysis['issues']:
                print(f"  ⚠️  Potential issues:")
                for issue in analysis['issues']:
                    print(f"    - {issue}")
        else:
            print(f"  ❌ File not found")
        print()
    
    # Check GPT responder in detail
    print("\n=== DETAILED GPT_RESPONDER ANALYSIS ===")
    gpt_file = 'app/transcribe/gpt_responder.py'
    if os.path.exists(gpt_file):
        with open(gpt_file, 'r') as f:
            content = f.read()
        
        # Look for the streaming implementation
        print("Checking for streaming implementation patterns...")
        
        # Check if sentences are processed during streaming
        if 'sent_q' in content and 'put' in content:
            print("✓ Found sentence queue implementation")
            
            # Check if it's in the token processing loop
            token_loop_match = re.search(r'for.*token.*in.*:.*?sent_q\.put', content, re.DOTALL)
            if token_loop_match:
                print("✓ Sentences are queued during token processing")
            else:
                print("❌ Sentences might not be queued during streaming")
        
        # Check for TTS thread
        if 'tts_stream_processor' in content or 'process_tts_stream' in content:
            print("✓ Found TTS stream processor")
        else:
            print("⚠️  No explicit TTS stream processor found")
        
        # Check configuration
        if 'tts_streaming_enabled' in content:
            print("✓ Streaming TTS configuration check found")
        
        # Look for the actual streaming flow
        streaming_flow = []
        
        # Find where tokens are received
        token_matches = re.finditer(r'(on_token|for.*token.*in)', content)
        for match in token_matches:
            line_num = content[:match.start()].count('\n') + 1
            streaming_flow.append(f"Line {line_num}: Token received - {match.group()}")
        
        # Find where sentences are detected
        sentence_matches = re.finditer(r'(sentence_end|sent_q\.put|complete_sentence)', content)
        for match in sentence_matches:
            line_num = content[:match.start()].count('\n') + 1
            streaming_flow.append(f"Line {line_num}: Sentence processing - {match.group()}")
        
        if streaming_flow:
            print("\nStreaming flow found:")
            for item in sorted(streaming_flow)[:10]:
                print(f"  {item}")
    
    # Summary
    print("\n=== SUMMARY ===")
    
    streaming_works = False
    
    # Check if we found the key components
    for filepath, analysis in results.items():
        if 'gpt_responder' in filepath:
            if analysis['sentence_detection'] and analysis['token_handling']:
                print("✓ GPT responder has sentence detection during token processing")
                streaming_works = True
            else:
                print("❌ GPT responder missing streaming sentence detection")
    
    if 'app/transcribe/audio_player_streaming.py' in results:
        print("✓ Streaming audio player exists")
    else:
        print("❌ Streaming audio player not found")
    
    if streaming_works:
        print("\n✅ CONCLUSION: Streaming TTS flow appears to be implemented")
        print("   - Tokens are processed as they arrive")
        print("   - Sentences are detected during streaming")
        print("   - TTS can process sentences before response completes")
    else:
        print("\n❌ CONCLUSION: Streaming TTS flow may have issues")
        print("   - Check if sentences are detected during token processing")
        print("   - Verify TTS is called for each sentence during streaming")

if __name__ == "__main__":
    main()