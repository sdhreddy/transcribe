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
SPEAKER_REENABLE_DELAY_SECONDS = 0.5
# Window after playback during which identical or similar speaker input is ignored
PLAYBACK_IGNORE_WINDOW_SECONDS = 2.0
# Similarity ratio above which speaker transcript is treated as echo
IGNORE_SIMILARITY_THRESHOLD = 0.85
# Default speech rate for TTS output (1.0 is normal speed)
DEFAULT_TTS_SPEECH_RATE = 1.3
# Default volume for TTS playback (1.0 is 100%)
DEFAULT_TTS_VOLUME = 0.5
