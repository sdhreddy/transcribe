import os
import sys
from unittest.mock import MagicMock

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'app', 'transcribe'))

from app.transcribe import audio_transcriber


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


def test_source_name_fallback(monkeypatch):
    mic, speaker, model, convo = make_mocks()
    config = _basic_config()
    monkeypatch.setattr(audio_transcriber, 'available_sources', ['FirstMic', 'SecondMic'])
    transcriber = audio_transcriber.WhisperTranscriber(
        mic, speaker, model, convo, config, source_name='NonexistentMic'
    )
    assert transcriber.source == 'FirstMic'
