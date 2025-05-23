"""
Plays the responses received from LLM as Audio.
This class handles text-to-speech functionality.
"""

import os
import time
import tempfile
import threading
import gtts
import simpleaudio
import subprocess
from conversation import Conversation
import constants
from tsutils import app_logging as al
from tsutils.language import LANGUAGES_DICT

logger = al.get_module_logger(al.AUDIO_PLAYER_LOGGER)


class AudioPlayer:
    """Play text to audio.
    """

    def __init__(self, convo: Conversation):
        logger.info(self.__class__.__name__)
        self.speech_text_available = threading.Event()
        self.conversation = convo
        self.temp_dir = tempfile.gettempdir()
        self.read_response = False
        self.stop_loop = False
        self.is_playing = False
        self._play_obj = None
        self.play_thread = None

    def _play_audio(self, speech: str, lang: str):
        """Internal method to play text as audio."""
        logger.info(f'{self.__class__.__name__} - Playing audio')
        mp3_file = tempfile.mkstemp(dir=self.temp_dir, suffix='.mp3')
        wav_file = tempfile.mkstemp(dir=self.temp_dir, suffix='.wav')
        os.close(mp3_file[0])
        os.close(wav_file[0])
        try:
            audio_obj = gtts.gTTS(speech, lang=lang)
            audio_obj.save(mp3_file[1])
            subprocess.call([
                'ffmpeg', '-y', '-i', mp3_file[1], wav_file[1]
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            wave_obj = simpleaudio.WaveObject.from_wave_file(wav_file[1])
            self.is_playing = True
            self._play_obj = wave_obj.play()
            self._play_obj.wait_done()
        except Exception as play_ex:  # pylint: disable=broad-except
            logger.error('Error when attempting to play audio.', exc_info=True)
            logger.info(play_ex)
        finally:
            self.is_playing = False
            self._play_obj = None
            try:
                os.remove(mp3_file[1])
                os.remove(wav_file[1])
            except OSError:
                pass

    def start_playback(self, speech: str, lang: str):
        """Start audio playback asynchronously."""
        self.play_thread = threading.Thread(target=self._play_audio, args=(speech, lang))
        self.play_thread.start()

    def stop_playback(self):
        """Stop current playback if any."""
        if self._play_obj is not None:
            try:
                self._play_obj.stop()
            except Exception:  # pylint: disable=broad-except
                pass
        self.is_playing = False
        self.read_response = False

    def play_audio_loop(self, config: dict):
        """Continuously play text as audio based on event signaling.
        """
        lang = 'english'
        lang_code = self._get_language_code(lang)

        while self.stop_loop is False:
            if self.speech_text_available.is_set() and self.read_response:
                self.speech_text_available.clear()
                speech = self._get_speech_text()
                final_speech = self._process_speech_text(speech)

                new_lang = config.get('OpenAI', {}).get('response_lang', lang)
                if new_lang != lang:
                    lang_code = self._get_language_code(new_lang)
                    lang = new_lang

                self.read_response = False
                self.start_playback(speech=final_speech, lang=lang_code)
                while self.is_playing and self.stop_loop is False:
                    time.sleep(0.1)
            time.sleep(0.1)

    def _get_language_code(self, lang: str) -> str:
        """Get the language code from the configuration.
        """
        try:
            return next(key for key, value in LANGUAGES_DICT.items() if value == lang)
        except StopIteration:
            # Return dafault lang if nothing else is found
            return 'en'

    def _get_speech_text(self) -> str:
        """Get the speech text from the conversation.
        """
        return self.conversation.get_conversation(sources=[constants.PERSONA_ASSISTANT], length=1)

    def _process_speech_text(self, speech: str) -> str:
        """Process the speech text to remove persona and formatting.
        """
        persona_length = len(constants.PERSONA_ASSISTANT) + 2
        final_speech = speech[persona_length:].strip()
        return final_speech[1:-1]  # Remove square brackets
