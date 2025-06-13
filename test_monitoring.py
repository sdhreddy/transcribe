#!/usr/bin/env python
"""Test script to verify monitoring system functionality."""

import time
import json
import requests
import numpy as np
from datetime import datetime

def test_monitoring_server(server_url="http://localhost:8888"):
    """Test monitoring server endpoints and functionality."""
    
    print("Testing Monitoring System")
    print("=" * 50)
    
    # Test 1: Server Status
    print("\n1. Testing server status...")
    try:
        response = requests.get(f"{server_url}/api/status")
        if response.status_code == 200:
            status = response.json()
            print(f"   ✓ Server is running")
            print(f"   - Uptime: {status.get('uptime', 0):.1f} seconds")
            print(f"   - Connected clients: {status.get('connected_clients', 0)}")
        else:
            print(f"   ✗ Server returned status {response.status_code}")
    except Exception as e:
        print(f"   ✗ Failed to connect: {e}")
        return False
    
    # Test 2: Send Configuration Event
    print("\n2. Testing configuration event...")
    try:
        config_event = {
            "type": "config",
            "data": {
                "voice_filter_enabled": True,
                "voice_filter_threshold": 0.7,
                "inverted_voice_response": False,
                "voice_filter_profile": "my_voice.npy"
            }
        }
        response = requests.post(f"{server_url}/api/event", json=config_event)
        if response.status_code == 200:
            print("   ✓ Configuration sent successfully")
        else:
            print(f"   ✗ Failed to send config: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 3: Send Voice Decision Events
    print("\n3. Testing voice decision events...")
    test_decisions = [
        {"is_user": True, "confidence": 0.85, "respond": True, "text": "Hello, can you help me?"},
        {"is_user": False, "confidence": 0.92, "respond": False, "text": "Background conversation"},
        {"is_user": True, "confidence": 0.65, "respond": True, "text": "What's the weather today?"},
        {"is_user": False, "confidence": 0.78, "respond": False, "text": "TV audio in background"},
        {"is_user": True, "confidence": 0.91, "respond": True, "text": "Thank you for your help"},
    ]
    
    for i, decision in enumerate(test_decisions):
        try:
            voice_event = {
                "type": "voice_decision",
                "data": {
                    "is_user_voice": decision["is_user"],
                    "confidence": decision["confidence"],
                    "should_respond": decision["respond"],
                    "transcript": decision["text"],
                    "audio_length": 2.5,
                    "sample_rate": 16000
                }
            }
            response = requests.post(f"{server_url}/api/event", json=voice_event)
            if response.status_code == 200:
                print(f"   ✓ Decision {i+1}: {decision['text'][:30]}...")
            time.sleep(0.5)  # Simulate real-time events
        except Exception as e:
            print(f"   ✗ Error sending decision {i+1}: {e}")
    
    # Test 4: Send Latency Events
    print("\n4. Testing latency events...")
    latency_stages = [
        ("audio", 15.3),
        ("transcription", 125.8),
        ("tts", 85.2),
        ("audio", 12.1),
        ("transcription", 98.5),
        ("tts", 92.7)
    ]
    
    for stage, duration in latency_stages:
        try:
            latency_event = {
                "type": "latency",
                "data": {
                    "stage": stage,
                    "duration_ms": duration
                }
            }
            response = requests.post(f"{server_url}/api/event", json=latency_event)
            if response.status_code == 200:
                print(f"   ✓ {stage}: {duration}ms")
            time.sleep(0.2)
        except Exception as e:
            print(f"   ✗ Error sending latency: {e}")
    
    # Test 5: Check Statistics
    print("\n5. Checking accumulated statistics...")
    try:
        response = requests.get(f"{server_url}/api/stats")
        if response.status_code == 200:
            stats = response.json()
            print("   ✓ Statistics retrieved:")
            print(f"   - Total transcriptions: {stats.get('stats', {}).get('total_transcriptions', 0)}")
            print(f"   - User voice detected: {stats.get('stats', {}).get('user_voice_detected', 0)}")
            print(f"   - Responses triggered: {stats.get('stats', {}).get('responses_triggered', 0)}")
        else:
            print(f"   ✗ Failed to get stats: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 6: Send Error Event
    print("\n6. Testing error event...")
    try:
        error_event = {
            "type": "error",
            "data": {
                "type": "test_error",
                "message": "This is a test error message"
            }
        }
        response = requests.post(f"{server_url}/api/event", json=error_event)
        if response.status_code == 200:
            print("   ✓ Error event sent")
        else:
            print(f"   ✗ Failed to send error: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n" + "=" * 50)
    print("Testing complete!")
    print(f"Open http://localhost:8888 in your browser to see the dashboard")
    return True


def simulate_monitoring_session():
    """Simulate a longer monitoring session with varied events."""
    
    print("\nStarting simulated monitoring session...")
    print("This will generate events for 30 seconds")
    print("Press Ctrl+C to stop early")
    
    server_url = "http://localhost:8888"
    start_time = time.time()
    event_count = 0
    
    try:
        # Send initial config
        config_event = {
            "type": "config",
            "data": {
                "voice_filter_enabled": True,
                "voice_filter_threshold": 0.7,
                "inverted_voice_response": False,
                "voice_filter_profile": "my_voice.npy"
            }
        }
        requests.post(f"{server_url}/api/event", json=config_event)
        
        while time.time() - start_time < 30:
            # Simulate voice decision
            is_user = np.random.random() > 0.4  # 60% user voice
            confidence = np.random.uniform(0.3, 0.95)
            should_respond = is_user and confidence > 0.6
            
            texts = [
                "Can you tell me about the weather?",
                "What time is it?",
                "Background noise and chatter",
                "TV playing in the background",
                "How do I get to the station?",
                "Thank you for your help",
                "Random conversation nearby",
                "Could you repeat that please?",
                "Music playing softly",
                "I need some assistance"
            ]
            
            voice_event = {
                "type": "voice_decision",
                "data": {
                    "is_user_voice": bool(is_user),
                    "confidence": float(confidence),
                    "should_respond": bool(should_respond),
                    "transcript": np.random.choice(texts),
                    "audio_length": np.random.uniform(1, 4),
                    "sample_rate": 16000
                }
            }
            
            requests.post(f"{server_url}/api/event", json=voice_event)
            event_count += 1
            
            # Simulate latencies
            if np.random.random() > 0.5:
                latency_event = {
                    "type": "latency",
                    "data": {
                        "stage": np.random.choice(["audio", "transcription", "tts"]),
                        "duration_ms": float(np.random.uniform(10, 200))
                    }
                }
                requests.post(f"{server_url}/api/event", json=latency_event)
                event_count += 1
            
            # Occasional error
            if np.random.random() > 0.95:
                error_event = {
                    "type": "error",
                    "data": {
                        "type": "simulation_error",
                        "message": "Simulated error for testing"
                    }
                }
                requests.post(f"{server_url}/api/event", json=error_event)
                event_count += 1
            
            time.sleep(np.random.uniform(0.5, 2))
            
            # Progress indicator
            elapsed = time.time() - start_time
            print(f"\rEvents sent: {event_count} | Elapsed: {elapsed:.1f}s", end="")
    
    except KeyboardInterrupt:
        print("\nSimulation stopped by user")
    except Exception as e:
        print(f"\nError during simulation: {e}")
    
    print(f"\n\nSimulation complete!")
    print(f"Total events sent: {event_count}")
    print(f"Check the dashboard for results: http://localhost:8888")


def main():
    """Main test function."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "simulate":
        simulate_monitoring_session()
    else:
        if test_monitoring_server():
            print("\n\nRun with 'simulate' argument to generate more test data:")
            print("  python test_monitoring.py simulate")


if __name__ == "__main__":
    main()