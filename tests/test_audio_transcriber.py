import os
import sys
import pytest
from unittest.mock import MagicMock

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'app', 'transcribe'))

from app.transcribe.audio_transcriber import WhisperTranscriber


def _basic_config():
    return {
        'General': {
            'clear_transcript_periodically': False,
            'clear_transcript_interval_seconds': 10
        }
    }


def make_mocks():
    mic = MagicMock()
    mic.SAMPLE_RATE = 16000
    mic.SAMPLE_WIDTH = 2
    mic.channels = 1

    speaker = MagicMock()
    speaker.SAMPLE_RATE = 16000
    speaker.SAMPLE_WIDTH = 2
    speaker.channels = 1

    model = MagicMock()
    convo = MagicMock()
    convo.context = MagicMock()

    return mic, speaker, model, convo


# Test Case 1
def test_whisper_transcriber_initializes_sample_rate():
    mic, speaker, model, convo = make_mocks()
    config = _basic_config()

    transcriber = WhisperTranscriber(mic, speaker, model, convo, config, source_name='mic')

    assert transcriber.sample_rate == 16000


# Test Case 2
def test_whisper_transcriber_missing_source_raises():
    _, speaker, model, convo = make_mocks()
    config = _basic_config()

    with pytest.raises(ValueError) as exc:
        WhisperTranscriber(None, speaker, model, convo, config, source_name='dummy')

    assert "Audio source 'dummy' not found" in str(exc.value)

