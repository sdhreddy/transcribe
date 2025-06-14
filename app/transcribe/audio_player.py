"""
Plays the responses received from LLM as Audio.
This class handles text-to-speech functionality.
"""

import os
import time
import tempfile
import threading
import subprocess
import datetime
import gtts
from .conversation import Conversation
from . import constants
from tsutils import app_logging as al
from tsutils.language import LANGUAGES_DICT
from typing import Optional

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
        self.current_process = None
        self.play_lock = threading.Lock()
        self.playing = False
        self.speech_rate = constants.DEFAULT_TTS_SPEECH_RATE
        self.tts_volume = constants.DEFAULT_TTS_VOLUME

        self.played_responses: set[str] = set()
        self.last_playback_end: float = 0.0

    def reset_played_responses(self) -> None:
        """Clear memory of played responses."""
        with self.play_lock:
            self.played_responses.clear()

    def stop_current_playback(self):
        """Stop any current audio playback"""
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=1)
            except Exception:
                try:
                    self.current_process.kill()
                except Exception:
                    pass
        self.current_process = None


    def play_audio(
        self,
        speech: str,
        lang: str,
        rate: Optional[float] = None,
        volume: Optional[float] = None,
        response_id: Optional[str] = None,
    ) -> None:
        """Play text as audio.
        This is a blocking method and will return when audio playback is complete.
        For large audio text, this could take several minutes.
        """
        logger.info(f'{self.__class__.__name__} - play_audio called')  # pylint: disable=W1203
        try:
            audio_obj = gtts.gTTS(speech, lang=lang)
            temp_audio_file = tempfile.mkstemp(dir=self.temp_dir, suffix='.mp3')
            os.close(temp_audio_file[0])

            audio_obj.save(temp_audio_file[1])
            now = time.time()
            with self.play_lock:

                if now - self.last_playback_end < 1.0:
                    logger.info("Skipping potential duplicate within 1s window")
                    return
                if response_id and response_id in self.played_responses:
                    logger.info(f"Skipping duplicate playback for {response_id}")
                    return
                if response_id:
                    self.played_responses.add(response_id)
                if self.playing:
                    logger.warning("Audio already playing, skipping redundant call.")
                    return
                logger.info("Audio playback starting")
                self.playing = True
                self.stop_current_playback()
                cmd = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet']
                filters = []
                if rate and rate != 1.0:
                    filters.append(f'atempo={rate}')
                if volume is not None and volume != 1.0:
                    filters.append(f'volume={volume}')
                if filters:
                    cmd += ['-af', ','.join(filters)]
                cmd.append(temp_audio_file[1])
                self.current_process = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            while self.current_process.poll() is None:
                if not self.conversation.context.audio_queue.empty():
                    self.stop_current_playback()
                    break
                time.sleep(0.1)
        except Exception as play_ex:
            logger.error('Error when attempting to play audio.', exc_info=True)
            logger.info(play_ex)
        finally:
            os.remove(temp_audio_file[1])
            with self.play_lock:
                self.stop_current_playback()
                self.playing = False
                self.last_playback_end = time.time()



    def play_audio_loop(self, config: dict):
        """Continuously play text as audio based on event signaling.
        """
        lang = 'english'
        lang_code = self._get_language_code(lang)
        rate = config.get('General', {}).get('tts_speech_rate', self.speech_rate)
        self.speech_rate = rate
        volume = config.get('General', {}).get('tts_playback_volume', self.tts_volume)
        self.tts_volume = volume

        while self.stop_loop is False:
            if self.speech_text_available.is_set() and self.read_response:
                logger.info("play_audio_loop triggered by speech_text_available")
                self.speech_text_available.clear()
                speech = self._get_speech_text()
                final_speech = self._process_speech_text(speech)

                new_lang = config.get('OpenAI', {}).get('response_lang', lang)
                if new_lang != lang:
                    lang_code = self._get_language_code(new_lang)
                    lang = new_lang

                self.read_response = False
                # Disable audio capture to avoid echo
                sp_rec = self.conversation.context.speaker_audio_recorder
                # Only disable speaker capture so user mic remains active and
                # playback can be interrupted by new speech.
                prev_sp_state = sp_rec.enabled
                sp_rec.enabled = False
                try:
                    current_volume = self.tts_volume
                    logger.info("Playing audio response once")
                    
                    self.play_audio(
                        speech=final_speech,
                        lang=lang_code,
                        rate=rate,
                        volume=current_volume,
                        response_id=final_speech,
                    )





                finally:
                    time.sleep(constants.SPEAKER_REENABLE_DELAY_SECONDS)
                    sp_rec.enabled = prev_sp_state
                    gv = self.conversation.context
                    gv.last_playback_end = datetime.datetime.utcnow()
                    logger.info("Audio playback finished")

                    # Reset last_spoken_response so any queued text is cleared
                    # after playback completes. update_response_ui will
                    # populate this again when a new response arrives.

                    # Keep last_spoken_response so update_response_ui
                    # can detect when a new response is generated and
                    # avoid replaying the same audio multiple times.

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
