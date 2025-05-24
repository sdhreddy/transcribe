import unittest
import datetime
import sys
import os
from types import ModuleType
from unittest.mock import MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.modules['pyaudiowpatch'] = ModuleType('pyaudiowpatch')

from app.transcribe.audio_transcriber import AudioTranscriber
import app.transcribe.constants as const

class DummyTranscriber(AudioTranscriber):
    def check_for_latency(self, results):
        return False, 0, 0

    def prune_for_latency(self, who_spoke, original_data_size, results, prune_id, file_path, prune_percent):
        return '', ''

class TestAudioTranscriber(unittest.TestCase):
    def setUp(self):
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
        config = {
            'General': {
                'clear_transcript_periodically': False,
                'clear_transcript_interval_seconds': 10
            }
        }
        self.transcriber = DummyTranscriber(mic, speaker, model, convo, config)

    def test_should_ignore_recent_tts(self):
        gv = self.transcriber.conversation.context
        gv.last_tts_response = 'hello world'
        gv.last_playback_end = datetime.datetime.utcnow()
        self.assertTrue(self.transcriber._should_ignore_speaker_transcript('hello world'))

    def test_ignore_partial_match(self):
        gv = self.transcriber.conversation.context
        gv.last_tts_response = 'hello world'
        gv.last_playback_end = datetime.datetime.utcnow()
        self.assertTrue(self.transcriber._should_ignore_speaker_transcript('world'))

    def test_not_ignore_when_old(self):
        gv = self.transcriber.conversation.context
        gv.last_tts_response = 'hello world'
        gv.last_playback_end = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
        self.assertFalse(self.transcriber._should_ignore_speaker_transcript('hello world'))

if __name__ == '__main__':
    unittest.main()
