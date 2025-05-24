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

import sys
sys.modules['simpleaudio'] = MagicMock()
import simpleaudio

import playsound
import sys
from types import ModuleType

# sys.path.append('app/transcribe')
from app.transcribe.audio_player import AudioPlayer
import app.transcribe.conversation as c
import app.transcribe.constants as const


class TestAudioPlayer(unittest.TestCase):
    """Unit tests for the AudioPlayer class."""

    def setUp(self):
        """Set up the test environment."""
        self.convo = MagicMock(spec=c.Conversation)
        self.audio_player = AudioPlayer(convo=self.convo)
        self.config = {'OpenAI': {'response_lang': 'english'}, 'english': 'en'}
        # Provide a dummy global_vars module expected by AudioPlayer
        mock_module = ModuleType('global_vars')
        mock_globals = MagicMock()
        mock_globals.audio_player_var = None
        mock_globals.speaker_audio_recorder = MagicMock(enabled=True)
        mock_module.T_GLOBALS = mock_globals
        sys.modules['global_vars'] = mock_module

    def tearDown(self):
        if 'global_vars' in sys.modules:
            del sys.modules['global_vars']

    @patch('gtts.gTTS')

    @patch('subprocess.Popen')
    def test_play_audio_exception(self, mock_popen, mock_gtts):

    @patch('subprocess.call')
    @patch('simpleaudio.WaveObject.from_wave_file')
    def test_play_audio_exception(self, mock_wave, mock_call, mock_gtts):

        """
        Test the play_audio method when an exception occurs.

        Verifies that the method handles the playback exception correctly and logs the error.
        """
        speech = "Hello, this is a test."
        lang = 'en'
        mock_gtts.return_value = MagicMock(spec=gTTS)

        process_mock = MagicMock()
        process_mock.wait.side_effect = playsound.PlaysoundException
        mock_popen.return_value = process_mock

        mock_wave.side_effect = Exception('fail')
        mock_call.return_value = 0

        with self.assertLogs(level='ERROR') as log:
            self.audio_player._play_audio(speech, lang)
            self.assertIn('Error when attempting to play audio.', log.output[0])

    @patch.object(AudioPlayer, 'start_playback')
    def test_play_audio_loop(self, mock_start_playback):
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

        mock_start_playback.side_effect = side_effect
        self.audio_player.speech_text_available.set()
        self.audio_player.read_response = True

        thread = threading.Thread(target=self.audio_player.play_audio_loop, args=(self.config,))
        thread.start()

        time.sleep(0.5)

        self.assertFalse(self.audio_player.speech_text_available.is_set(), 'Threading Event was not cleared.')
        self.assertFalse(self.audio_player.read_response, 'Read response boolean was not cleared.')
        # mock_play_audio.assert_called_once_with("Hello, this is a test.", 'en')
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
