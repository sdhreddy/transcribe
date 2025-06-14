#!/usr/bin/env python3
"""Real-time monitoring dashboard for streaming TTS debugging."""

import os
import sys
import time
import threading
import queue
from datetime import datetime
from flask import Flask, render_template, jsonify
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global state for monitoring
monitor_data = {
    'tokens': [],
    'sentences': [],
    'tts_calls': [],
    'audio_chunks': [],
    'errors': [],
    'stats': {
        'tokens_received': 0,
        'sentences_detected': 0,
        'tts_generated': 0,
        'audio_played': 0,
        'avg_sentence_delay': 0,
        'avg_tts_delay': 0,
        'avg_audio_delay': 0
    }
}

class TTSMonitor:
    """Monitor for TTS streaming events."""
    
    def __init__(self):
        self.start_time = time.time()
        
    def log_token(self, token, buffer_size):
        """Log token received from GPT."""
        event = {
            'time': time.time() - self.start_time,
            'token': token,
            'buffer_size': buffer_size,
            'timestamp': datetime.now().isoformat()
        }
        monitor_data['tokens'].append(event)
        monitor_data['stats']['tokens_received'] += 1
        
    def log_sentence(self, sentence, detection_time):
        """Log sentence detection."""
        event = {
            'time': time.time() - self.start_time,
            'sentence': sentence,
            'detection_time': detection_time,
            'timestamp': datetime.now().isoformat()
        }
        monitor_data['sentences'].append(event)
        monitor_data['stats']['sentences_detected'] += 1
        
        # Update average delay
        if len(monitor_data['sentences']) > 1:
            delays = [s['detection_time'] for s in monitor_data['sentences']]
            monitor_data['stats']['avg_sentence_delay'] = sum(delays) / len(delays)
    
    def log_tts_call(self, text, provider, start_time):
        """Log TTS API call."""
        event = {
            'time': time.time() - self.start_time,
            'text': text,
            'provider': provider,
            'start_time': start_time,
            'timestamp': datetime.now().isoformat()
        }
        monitor_data['tts_calls'].append(event)
        monitor_data['stats']['tts_generated'] += 1
        
    def log_audio_chunk(self, chunk_size, chunk_number):
        """Log audio chunk playback."""
        event = {
            'time': time.time() - self.start_time,
            'chunk_size': chunk_size,
            'chunk_number': chunk_number,
            'timestamp': datetime.now().isoformat()
        }
        monitor_data['audio_chunks'].append(event)
        monitor_data['stats']['audio_played'] += 1
        
    def log_error(self, error_type, error_msg):
        """Log error event."""
        event = {
            'time': time.time() - self.start_time,
            'type': error_type,
            'message': error_msg,
            'timestamp': datetime.now().isoformat()
        }
        monitor_data['errors'].append(event)

# Global monitor instance
tts_monitor = TTSMonitor()

@app.route('/')
def index():
    """Serve monitoring dashboard."""
    return render_template('monitor.html')

@app.route('/api/data')
def get_data():
    """Get current monitoring data."""
    return jsonify(monitor_data)

@app.route('/api/reset')
def reset_data():
    """Reset monitoring data."""
    global monitor_data
    monitor_data = {
        'tokens': [],
        'sentences': [],
        'tts_calls': [],
        'audio_chunks': [],
        'errors': [],
        'stats': {
            'tokens_received': 0,
            'sentences_detected': 0,
            'tts_generated': 0,
            'audio_played': 0,
            'avg_sentence_delay': 0,
            'avg_tts_delay': 0,
            'avg_audio_delay': 0
        }
    }
    tts_monitor.start_time = time.time()
    return jsonify({'status': 'reset'})

def create_monitor_template():
    """Create HTML template for monitoring dashboard."""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Streaming TTS Monitor</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
        .container { max-width: 1400px; margin: 0 auto; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }
        .stat-box { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 32px; font-weight: bold; color: #2196F3; }
        .stat-label { color: #666; margin-top: 5px; }
        .timeline { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .event { padding: 8px; margin: 4px 0; border-left: 4px solid #2196F3; background: #f5f5f5; }
        .event.sentence { border-color: #4CAF50; }
        .event.tts { border-color: #FF9800; }
        .event.audio { border-color: #9C27B0; }
        .event.error { border-color: #F44336; background: #ffebee; }
        .time { font-weight: bold; color: #666; }
        .controls { margin-bottom: 20px; }
        button { padding: 10px 20px; font-size: 16px; cursor: pointer; }
        .refresh { background: #2196F3; color: white; border: none; border-radius: 4px; }
        .reset { background: #F44336; color: white; border: none; border-radius: 4px; margin-left: 10px; }
        h2 { color: #333; }
        .waterfall { height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; background: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Streaming TTS Monitor</h1>
        
        <div class="controls">
            <button class="refresh" onclick="refreshData()">Refresh</button>
            <button class="reset" onclick="resetData()">Reset</button>
            <span style="margin-left: 20px;">Auto-refresh: <input type="checkbox" id="autoRefresh" checked></span>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-value" id="tokensReceived">0</div>
                <div class="stat-label">Tokens Received</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="sentencesDetected">0</div>
                <div class="stat-label">Sentences Detected</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="ttsGenerated">0</div>
                <div class="stat-label">TTS Generated</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="audioPlayed">0</div>
                <div class="stat-label">Audio Chunks Played</div>
            </div>
        </div>
        
        <div class="timeline">
            <h2>Event Timeline</h2>
            <div class="waterfall" id="timeline"></div>
        </div>
        
        <div class="timeline">
            <h2>Errors</h2>
            <div id="errors"></div>
        </div>
    </div>
    
    <script>
        let autoRefresh = true;
        
        document.getElementById('autoRefresh').addEventListener('change', (e) => {
            autoRefresh = e.target.checked;
        });
        
        function refreshData() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    // Update stats
                    document.getElementById('tokensReceived').textContent = data.stats.tokens_received;
                    document.getElementById('sentencesDetected').textContent = data.stats.sentences_detected;
                    document.getElementById('ttsGenerated').textContent = data.stats.tts_generated;
                    document.getElementById('audioPlayed').textContent = data.stats.audio_played;
                    
                    // Update timeline
                    const timeline = document.getElementById('timeline');
                    timeline.innerHTML = '';
                    
                    // Combine all events
                    const allEvents = [];
                    
                    data.tokens.forEach(e => {
                        allEvents.push({...e, type: 'token', label: `Token: "${e.token}"`});
                    });
                    
                    data.sentences.forEach(e => {
                        allEvents.push({...e, type: 'sentence', label: `Sentence: "${e.sentence.substring(0, 50)}..."`});
                    });
                    
                    data.tts_calls.forEach(e => {
                        allEvents.push({...e, type: 'tts', label: `TTS: "${e.text.substring(0, 50)}..." (${e.provider})`});
                    });
                    
                    data.audio_chunks.forEach(e => {
                        allEvents.push({...e, type: 'audio', label: `Audio Chunk #${e.chunk_number} (${e.chunk_size} bytes)`});
                    });
                    
                    // Sort by time
                    allEvents.sort((a, b) => a.time - b.time);
                    
                    // Display events
                    allEvents.forEach(event => {
                        const div = document.createElement('div');
                        div.className = `event ${event.type}`;
                        div.innerHTML = `<span class="time">${event.time.toFixed(3)}s</span> - ${event.label}`;
                        timeline.appendChild(div);
                    });
                    
                    // Update errors
                    const errors = document.getElementById('errors');
                    errors.innerHTML = '';
                    data.errors.forEach(error => {
                        const div = document.createElement('div');
                        div.className = 'event error';
                        div.innerHTML = `<span class="time">${error.time.toFixed(3)}s</span> - ${error.type}: ${error.message}`;
                        errors.appendChild(div);
                    });
                    
                    // Auto-scroll timeline
                    timeline.scrollTop = timeline.scrollHeight;
                });
        }
        
        function resetData() {
            if (confirm('Reset all monitoring data?')) {
                fetch('/api/reset')
                    .then(() => refreshData());
            }
        }
        
        // Initial load
        refreshData();
        
        // Auto-refresh every second
        setInterval(() => {
            if (autoRefresh) {
                refreshData();
            }
        }, 1000);
    </script>
</body>
</html>'''
    
    with open(os.path.join(template_dir, 'monitor.html'), 'w') as f:
        f.write(html_content)

def run_monitor():
    """Run the monitoring dashboard."""
    create_monitor_template()
    print("Starting TTS Monitor Dashboard...")
    print("Open http://localhost:5555 in your browser")
    app.run(host='0.0.0.0', port=5555, debug=False)

if __name__ == '__main__':
    run_monitor()