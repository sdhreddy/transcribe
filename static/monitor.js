// Monitor Dashboard JavaScript
class TranscribeMonitor {
    constructor() {
        this.eventSource = null;
        this.events = [];
        this.maxEvents = 50;
        this.stats = {
            total_transcriptions: 0,
            user_voice_detected: 0,
            other_voice_detected: 0,
            responses_triggered: 0,
            responses_ignored: 0,
            errors: 0
        };
        this.latencyData = {
            labels: [],
            audio: [],
            transcription: [],
            tts: []
        };
        this.latencyChart = null;
        
        this.init();
    }

    init() {
        this.connectToServer();
        this.setupEventHandlers();
        this.initializeChart();
        this.startPolling();
    }

    connectToServer() {
        const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
        const host = window.location.hostname;
        const port = window.location.port || '8888';
        const baseUrl = `${protocol}//${host}:${port}`;

        // Setup EventSource for real-time updates
        this.eventSource = new EventSource(`${baseUrl}/api/events`);
        
        this.eventSource.onopen = () => {
            this.updateStatus('Connected', true);
        };

        this.eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            this.updateStatus('Disconnected', false);
        };

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleServerEvent(data);
            } catch (e) {
                console.error('Failed to parse event:', e);
            }
        };
    }

    handleServerEvent(event) {
        switch (event.type) {
            case 'stats':
                this.updateStats(event.data);
                break;
            case 'voice_decision':
                this.handleVoiceDecision(event.data);
                break;
            case 'latency':
                this.handleLatency(event.data);
                break;
            case 'config':
                this.updateConfig(event.data);
                break;
            case 'error':
                this.handleError(event.data);
                break;
            default:
                this.addEvent(event);
        }
    }

    updateStats(data) {
        if (data.stats) {
            this.stats = data.stats;
            this.updateStatsDisplay();
        }
        
        if (data.config) {
            this.updateConfig(data.config);
        }

        if (data.recent_events) {
            data.recent_events.forEach(event => {
                this.addEventToList(event);
            });
        }
    }

    updateStatsDisplay() {
        // Update metric cards
        document.getElementById('totalTranscriptions').textContent = this.stats.total_transcriptions;
        document.getElementById('userVoice').textContent = this.stats.user_voice_detected;
        document.getElementById('otherVoice').textContent = this.stats.other_voice_detected;
        document.getElementById('responsesTriggered').textContent = this.stats.responses_triggered;
        document.getElementById('responsesIgnored').textContent = this.stats.responses_ignored;

        // Calculate response rate
        const total = this.stats.responses_triggered + this.stats.responses_ignored;
        const rate = total > 0 ? (this.stats.responses_triggered / total * 100).toFixed(1) : 0;
        document.getElementById('responseRate').textContent = `${rate}%`;
    }

    updateConfig(config) {
        const configContent = document.getElementById('configContent');
        configContent.innerHTML = '';
        
        const configItems = [
            { label: 'Voice Filter Enabled', value: config.voice_filter_enabled ? 'Yes' : 'No' },
            { label: 'Voice Filter Threshold', value: config.voice_filter_threshold || 'N/A' },
            { label: 'Inverted Response', value: config.inverted_voice_response ? 'Yes' : 'No' },
            { label: 'Voice Profile', value: config.voice_filter_profile || 'Default' }
        ];

        configItems.forEach(item => {
            const div = document.createElement('div');
            div.className = 'config-item';
            div.innerHTML = `
                <span class="config-label">${item.label}:</span>
                <span class="config-value">${item.value}</span>
            `;
            configContent.appendChild(div);
        });
    }

    handleVoiceDecision(data) {
        this.addEventToList({
            timestamp: new Date().toISOString(),
            text: data.transcript || '',
            is_user: data.is_user_voice,
            confidence: data.confidence,
            responded: data.should_respond
        });

        // Update stats
        this.stats.total_transcriptions++;
        if (data.is_user_voice) {
            this.stats.user_voice_detected++;
        } else {
            this.stats.other_voice_detected++;
        }
        if (data.should_respond) {
            this.stats.responses_triggered++;
        } else {
            this.stats.responses_ignored++;
        }
        
        this.updateStatsDisplay();
    }

    handleLatency(data) {
        const now = new Date();
        const label = `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
        
        // Add to appropriate array
        if (this.latencyData.labels.length > 20) {
            this.latencyData.labels.shift();
            this.latencyData.audio.shift();
            this.latencyData.transcription.shift();
            this.latencyData.tts.shift();
        }
        
        this.latencyData.labels.push(label);
        
        // Add data based on stage
        if (data.stage === 'audio') {
            this.latencyData.audio.push(data.duration_ms);
            this.latencyData.transcription.push(null);
            this.latencyData.tts.push(null);
        } else if (data.stage === 'transcription') {
            this.latencyData.audio.push(null);
            this.latencyData.transcription.push(data.duration_ms);
            this.latencyData.tts.push(null);
        } else if (data.stage === 'tts') {
            this.latencyData.audio.push(null);
            this.latencyData.transcription.push(null);
            this.latencyData.tts.push(data.duration_ms);
        }
        
        this.updateLatencyChart();
        
        // Update average latency
        const allLatencies = [...this.latencyData.audio, ...this.latencyData.transcription, ...this.latencyData.tts]
            .filter(v => v !== null);
        if (allLatencies.length > 0) {
            const avg = allLatencies.reduce((a, b) => a + b, 0) / allLatencies.length;
            document.getElementById('avgLatency').textContent = `${avg.toFixed(1)}ms`;
        }
    }

    handleError(data) {
        this.stats.errors++;
        this.addEvent({
            type: 'error',
            data: data,
            timestamp: new Date().toISOString()
        });
    }

    addEventToList(event) {
        const eventList = document.getElementById('eventList');
        
        // Clear loading message if present
        if (eventList.querySelector('.loading')) {
            eventList.innerHTML = '';
        }
        
        // Create event element
        const eventDiv = document.createElement('div');
        eventDiv.className = 'event-item';
        
        // Determine icon and styling
        let iconClass = 'other';
        let iconText = 'O';
        if (event.is_user) {
            iconClass = 'user';
            iconText = 'U';
        }
        if (event.responded) {
            iconClass = 'respond';
            iconText = '✓';
        }
        
        // Determine confidence badge
        let confidenceClass = 'confidence-low';
        if (event.confidence > 0.7) confidenceClass = 'confidence-high';
        else if (event.confidence > 0.4) confidenceClass = 'confidence-medium';
        
        const time = new Date(event.timestamp).toLocaleTimeString();
        
        eventDiv.innerHTML = `
            <div class="event-icon ${iconClass}">${iconText}</div>
            <div class="event-content">
                <div class="event-text">${this.escapeHtml(event.text || 'No transcript')}</div>
                <div class="event-meta">
                    ${time} - 
                    <span class="confidence-badge ${confidenceClass}">
                        ${(event.confidence * 100).toFixed(0)}% confidence
                    </span>
                    ${event.responded ? ' - Response triggered' : ' - Ignored'}
                </div>
            </div>
        `;
        
        // Add to top of list
        eventList.insertBefore(eventDiv, eventList.firstChild);
        
        // Limit number of events
        while (eventList.children.length > this.maxEvents) {
            eventList.removeChild(eventList.lastChild);
        }
    }

    addEvent(event) {
        this.events.push(event);
        if (this.events.length > this.maxEvents) {
            this.events.shift();
        }
        
        // Add to event list if it's a general event
        if (event.type !== 'stats' && event.type !== 'config') {
            this.addEventToList({
                timestamp: event.timestamp,
                text: JSON.stringify(event.data),
                is_user: false,
                confidence: 0,
                responded: false
            });
        }
    }

    initializeChart() {
        const canvas = document.getElementById('latencyChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        // Simple line chart implementation
        this.latencyChart = {
            ctx: ctx,
            canvas: canvas,
            draw: () => {
                const width = canvas.width = canvas.offsetWidth;
                const height = canvas.height = 100;
                
                ctx.clearRect(0, 0, width, height);
                
                if (this.latencyData.labels.length < 2) return;
                
                // Find max value
                const allValues = [...this.latencyData.audio, ...this.latencyData.transcription, ...this.latencyData.tts]
                    .filter(v => v !== null);
                const maxValue = Math.max(...allValues, 100);
                
                // Draw lines for each data series
                const drawLine = (data, color) => {
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    
                    let started = false;
                    data.forEach((value, index) => {
                        if (value === null) return;
                        
                        const x = (index / (data.length - 1)) * width;
                        const y = height - (value / maxValue) * height;
                        
                        if (!started) {
                            ctx.moveTo(x, y);
                            started = true;
                        } else {
                            ctx.lineTo(x, y);
                        }
                    });
                    
                    ctx.stroke();
                };
                
                drawLine(this.latencyData.audio, '#3b82f6');
                drawLine(this.latencyData.transcription, '#f59e0b');
                drawLine(this.latencyData.tts, '#10b981');
                
                // Draw legend
                ctx.font = '10px sans-serif';
                ctx.fillStyle = '#8b92b9';
                ctx.fillText('Audio', 10, 15);
                ctx.fillText('Transcription', 50, 15);
                ctx.fillText('TTS', 130, 15);
            }
        };
    }

    updateLatencyChart() {
        if (this.latencyChart) {
            this.latencyChart.draw();
        }
    }

    setupEventHandlers() {
        document.getElementById('clearEvents').addEventListener('click', () => {
            document.getElementById('eventList').innerHTML = '<div class="loading">Waiting for events...</div>';
            this.events = [];
        });
        
        // Resize handler for chart
        window.addEventListener('resize', () => {
            this.updateLatencyChart();
        });
    }

    updateStatus(text, connected) {
        document.getElementById('statusText').textContent = text;
        const dot = document.getElementById('statusDot');
        dot.style.background = connected ? 'var(--accent-green)' : 'var(--accent-red)';
    }

    startPolling() {
        // Poll for stats every 5 seconds as backup
        setInterval(async () => {
            try {
                const response = await fetch('/api/stats');
                if (response.ok) {
                    const data = await response.json();
                    this.updateStats(data);
                }
            } catch (e) {
                console.error('Polling error:', e);
            }
        }, 5000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize monitor when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.monitor = new TranscribeMonitor();
});