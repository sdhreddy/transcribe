"""
Unit tests for the AudioPlayer class.
These tests cover the functionality of the AudioPlayer class, including text-to-speech conversion,
audio playback, and configuration handling.
"""

import unittest
from unittest.mock import patch, MagicMock
import time
import threading
from gtts import gTTS
import subprocess
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.transcribe.audio_player import AudioPlayer
import app.transcribe.conversation as c
import app.transcribe.constants as const


class TestAudioPlayer(unittest.TestCase):
    """Unit tests for the AudioPlayer class."""

    def setUp(self):
        """Set up the test environment."""
        self.convo = MagicMock(spec=c.Conversation)
        self.convo.context = MagicMock()
        self.convo.context.last_spoken_response = "initial"
        self.audio_player = AudioPlayer(convo=self.convo)
        self.config = {
            'OpenAI': {'response_lang': 'english'},
            'General': {'tts_speech_rate': 1.5, 'tts_playback_volume': 0.5},
            'english': 'en'
        }

    @patch('gtts.gTTS')
    @patch('subprocess.Popen')
    def test_play_audio_exception(self, mock_popen, mock_gtts):
        """
        Test the play_audio method when an exception occurs.

        Verifies that the method handles the playsound exception correctly and logs the error.
        """
        speech = "Hello, this is a test."
        lang = 'en'
        mock_gtts.return_value = MagicMock(spec=gTTS)
        mock_popen.side_effect = Exception('ffplay missing')

        with self.assertLogs(level='ERROR') as log:
            self.audio_player.play_audio(speech, lang, response_id='id1')
            self.assertIn('Error when attempting to play audio.', log.output[0])

    @patch.object(AudioPlayer, 'play_audio')
    def test_play_audio_loop(self, mock_play_audio):
        """
        Test the play_audio_loop method.

        Verifies that the method correctly processes speech text and plays audio based on event signaling.
        """
        self.audio_player.read_response = True
        self.audio_player.speech_text_available.set()
        self.convo.get_conversation.return_value = f"{const.PERSONA_ASSISTANT}: [Hello, this is a test.]"

        def side_effect(*args, **kwargs):
            self.audio_player.read_response = False
            self.audio_player.speech_text_available.clear()

        mock_play_audio.side_effect = side_effect
        self.audio_player.speech_text_available.set()
        self.audio_player.read_response = True

        thread = threading.Thread(target=self.audio_player.play_audio_loop, args=(self.config,))
        thread.start()

        time.sleep(0.5)

        self.assertFalse(self.audio_player.speech_text_available.is_set(), 'Threading Event was not cleared.')
        self.assertFalse(self.audio_player.read_response, 'Read response boolean was not cleared.')
        self.assertEqual(self.convo.context.last_spoken_response, 'initial',
                         'Last spoken response should remain unchanged after playback.')

        mock_play_audio.assert_called_once_with(speech="Hello, this is a test.", lang='en', rate=1.5, volume=0.5, response_id='Hello, this is a test.')


        mock_play_audio.assert_called_once_with(speech="Hello, this is a test.", lang='en', rate=1.5, volume=0.5, response_id='Hello, this is a test.')


        mock_play_audio.assert_called_once_with(speech="Hello, this is a test.", lang='en', rate=1.5, volume=0.5, response_id='Hello, this is a test.')


        mock_play_audio.assert_called_once_with(speech="Hello, this is a test.", lang='en', rate=1.5, volume=0.5, response_id='Hello, this is a test.')


        mock_play_audio.assert_called_once_with(speech="Hello, this is a test.", lang='en', rate=1.5, volume=0.5, response_id='Hello, this is a test.')

        mock_play_audio.assert_called_once_with(speech="Hello, this is a test.", lang='en', rate=1.5, volume=0.5)



        self.audio_player.stop_loop = True

    def test_get_language_code(self):
        """
        Test the _get_language_code method.

        Verifies that the method correctly returns the language code from the configuration.
        """
        lang_code = self.audio_player._get_language_code('english')  # pylint: disable=W0212
        self.assertEqual(lang_code, 'en')

        lang_code = self.audio_player._get_language_code('chinese')  # pylint: disable=W0212
        self.assertEqual(lang_code, 'zh')

        lang_code = self.audio_player._get_language_code('bulgarian')  # pylint: disable=W0212
        self.assertEqual(lang_code, 'bg')

    def test_process_speech_text(self):
        """
        Test the _process_speech_text method.

        Verifies that the method correctly processes the speech text to remove persona
        and formatting.
        """
        speech = f"{const.PERSONA_ASSISTANT}: [Hello, this is a test.]"
        processed_speech = self.audio_player._process_speech_text(speech)  # pylint: disable=W0212
        self.assertEqual(processed_speech, "Hello, this is a test.")


if __name__ == '__main__':
    unittest.main()
