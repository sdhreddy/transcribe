"""Globally used constants
"""

PERSONA_YOU = 'You'
PERSONA_ASSISTANT = 'assistant'
PERSONA_SYSTEM = 'system'
PERSONA_SPEAKER = 'Speaker'

LOG_NAME = 'Transcribe'
MAX_TRANSCRIPTION_PHRASES_FOR_LLM = 100
TRANSCRIPT_UI_UPDATE_DELAY_DURATION_MS = 500

# Delay before re-enabling speaker capture after TTS playback stops
SPEAKER_REENABLE_DELAY_SECONDS = 0.3
# Window after playback during which identical speaker input is ignored
PLAYBACK_IGNORE_WINDOW_SECONDS = 1.0
