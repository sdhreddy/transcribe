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
import pygame
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
        self.current_process = None
        self.play_lock = threading.Lock()
        self.speech_rate = constants.DEFAULT_TTS_SPEECH_RATE
        
        # Initialize pygame mixer for cleaner audio playback
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
            pygame.mixer.init()
            self.use_pygame = True
            logger.info("Using pygame for audio playback")
        except Exception as e:
            self.use_pygame = False
            logger.warning(f"Pygame initialization failed, falling back to ffplay: {e}")

    def stop_current_playback(self):
        """Stop any current audio playback"""
        if self.use_pygame:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        elif self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=1)
            except Exception:
                try:
                    self.current_process.kill()
                except Exception:
                    pass
        self.current_process = None

    def play_audio(self, speech: str, lang: str, rate: float | None = None):
        """Play text as audio.
        This is a blocking method and will return when audio playback is complete.
        For large audio text, this could take several minutes.
        """
        logger.info(f'{self.__class__.__name__} - Playing audio')  # pylint: disable=W1203
        
        # Note: Speaker recording disabling is handled by the calling method (play_audio_loop)
        # to prevent feedback loops while keeping microphone active
        
        try:
            audio_obj = gtts.gTTS(speech, lang=lang, slow=False)
            temp_audio_file = tempfile.mkstemp(dir=self.temp_dir, suffix='.mp3')
            os.close(temp_audio_file[0])

            audio_obj.save(temp_audio_file[1])
            with self.play_lock:
                self.stop_current_playback()
                
                if self.use_pygame and (not rate or rate == 1.0):
                    # Use pygame for cleaner audio playback (only for normal speed)
                    try:
                        pygame.mixer.music.load(temp_audio_file[1])
                        pygame.mixer.music.set_volume(0.7)  # Reduce volume to prevent distortion
                        pygame.mixer.music.play()
                        
                        # Wait for playback to complete
                        while pygame.mixer.music.get_busy():
                            if not self.conversation.context.audio_queue.empty():
                                pygame.mixer.music.stop()
                                break
                            time.sleep(0.02)
                    except Exception as e:
                        logger.warning(f"Pygame playback failed, falling back to ffplay: {e}")
                        self.use_pygame = False
                elif rate and rate != 1.0:
                    # Use ffplay for speed adjustment
                    self.use_pygame = False
                
                if not self.use_pygame:
                    # Fallback to ffplay
                    cmd = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet']
                    # Apply audio filters to reduce static
                    if rate and rate != 1.0:
                        cmd += ['-af', f'atempo={rate},volume=0.7,highpass=f=80,lowpass=f=8000']
                    else:
                        cmd += ['-af', 'volume=0.7,highpass=f=80,lowpass=f=8000']
                    cmd.append(temp_audio_file[1])
                    self.current_process = subprocess.Popen(
                        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    while self.current_process.poll() is None:
                        if not self.conversation.context.audio_queue.empty():
                            self.stop_current_playback()
                            break
                        time.sleep(0.1)
                
            # Minimal delay for streaming - reduced for faster response
            time.sleep(0.02)
            
        except Exception as play_ex:
            logger.error('Error when attempting to play audio.', exc_info=True)
            logger.info(play_ex)
        finally:
            os.remove(temp_audio_file[1])
            with self.play_lock:
                self.stop_current_playback()
            
            # Speaker recording re-enabling is handled by the calling method

    def play_audio_loop(self, config: dict):
        """Continuously play text as audio based on event signaling.
        """
        lang = 'english'
        lang_code = self._get_language_code(lang)
        rate = config.get('General', {}).get('tts_speech_rate', self.speech_rate)
        self.speech_rate = rate

        while self.stop_loop is False:
            gv = self.conversation.context

            if self.speech_text_available.is_set() and self.read_response:
                self.speech_text_available.clear()
                speech = self._get_speech_text()
                final_speech = self._process_speech_text(speech)

                new_lang = config.get('OpenAI', {}).get('response_lang', lang)
                if new_lang != lang:
                    lang_code = self._get_language_code(new_lang)
                    lang = new_lang

                self.read_response = False
                # Disable audio capture to avoid echo
                sp_rec = gv.speaker_audio_recorder
                # Only disable speaker capture so user mic remains active and
                # playback can be interrupted by new speech.
                prev_sp_state = sp_rec.enabled if sp_rec else False
                if sp_rec:
                    sp_rec.enabled = False
                gv = self.conversation.context
                try:
                    self.play_audio(speech=final_speech, lang=lang_code, rate=rate)
                finally:
                    time.sleep(constants.SPEAKER_REENABLE_DELAY_SECONDS)
                    if sp_rec:
                        sp_rec.enabled = prev_sp_state
                    gv.last_playback_end = datetime.datetime.utcnow()

                    # Reset last_spoken_response so any queued text is cleared
                    # after playback completes. update_response_ui will
                    # populate this again when a new response arrives.

                    # Keep last_spoken_response so update_response_ui
                    # can detect when a new response is generated and
                    # avoid replaying the same audio multiple times.

            time.sleep(0.02)  # Small delay to prevent high CPU usage

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
