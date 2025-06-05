import os
import time
import tempfile
import threading
import subprocess
import datetime
import gtts

from conversation import Conversation
import constants
from tsutils import app_logging as al
from tsutils.language import LANGUAGES_DICT

logger = al.get_module_logger(al.AUDIO_PLAYER_LOGGER)


class AudioPlayer:    """Play text to audio."""

    """High‑level helper that converts text into speech (gTTS ➜ ffplay) and
    plays it either once (\"Suggest Response and Read\") or incrementally in
    real time (\"Read Responses Continuously\").
    """

    def __init__(self, convo: Conversation):
        logger.info(self.__class__.__name__)
        self.conversation = convo
        self.temp_dir = tempfile.gettempdir()
        self.speech_text_available = threading.Event()
        self.read_response = False  # toggled by UI handler
        self.stop_loop = False      # set to True on application shutdown
        self.current_process: subprocess.Popen | None = None
        self.play_lock = threading.Lock()
        self.speech_rate = constants.DEFAULT_TTS_SPEECH_RATE

    # ---------------------------------------------------------------------
    #  Low‑level helpers
    # ---------------------------------------------------------------------
    def stop_current_playback(self) -> None:
        """Terminate the ffplay process if one is running."""
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


    def play_audio(self, speech: str, lang: str, rate: float | None = None):
        """Play text as audio.

        This is a blocking method and will return when audio playback is complete.
        For long passages, this could take several seconds or minutes.
        """
        logger.info(
            f"{self.__class__.__name__} - Playing audio"
        )  # pylint: disable=W1203
        try:
            audio_obj = gtts.gTTS(speech, lang=lang)
            temp_audio_file = tempfile.mkstemp(dir=self.temp_dir, suffix=".mp3")
            os.close(temp_audio_file[0])

    def _get_language_code(self, lang: str) -> str:
        """Return the ISO language code used by gTTS/ffplay (default: "en")."""
        try:
            return next(code for code, value in LANGUAGES_DICT.items() if value == lang)
        except StopIteration:
            return "en"

    def _get_speech_text(self) -> str:
        """Return the raw assistant text (latest chunk) from the conversation."""
        return self.conversation.get_conversation(
            sources=[constants.PERSONA_ASSISTANT], length=1
        )

    def _process_speech_text(self, speech: str) -> str:
        """Strip persona labels and square brackets so TTS speaks cleanly."""
        persona_offset = len(constants.PERSONA_ASSISTANT) + 2  # "XX: "
        clean = speech[persona_offset:].strip()
        if clean.startswith("[") and clean.endswith("]"):
            clean = clean[1:-1].strip()
        return clean

    # ---------------------------------------------------------------------
    #  Core playback utilities
    # ---------------------------------------------------------------------
    def play_audio(self, speech: str, lang: str, rate: float | None = None) -> bool:
        """Convert *speech* to mp3 and play it synchronously.

        Returns **True** if playback finished uninterrupted, **False** if it was
        cancelled (e.g. new text arrived during streaming).
        """
        logger.info(f"{self.__class__.__name__} – Playing audio")
        interrupted = False
        completed = True
        mp3_path: str | None = None

        try:
            tts_obj = gtts.gTTS(speech, lang=lang)
            fd, mp3_path = tempfile.mkstemp(dir=self.temp_dir, suffix=".mp3")
            os.close(fd)
            tts_obj.save(mp3_path)


            with self.play_lock:
                self.stop_current_playback()

                cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
                if rate and rate != 1.0:
                    cmd += ["-af", f"atempo={rate}"]
                cmd.append(temp_audio_file[1])

                cmd = [
                    "ffplay",
                    "-nodisp",
                    "-autoexit",
                    "-loglevel",
                    "quiet",
                ]
                if rate and rate != 1.0:
                    cmd += ["-af", f"atempo={rate}"]
                cmd.append(mp3_path)

                self.current_process = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

            while self.current_process.poll() is None:
                gv = self.conversation.context
                if (
                    self.speech_text_available.is_set()
                    or (not gv.audio_queue.empty())
                    or (gv.real_time_read and self.speech_text_available.is_set())
                ):
                    interrupted = True
                    completed = False
                    self.stop_current_playback()
                    break
                time.sleep(0.1)

        except Exception as play_ex:
            logger.error("Error when attempting to play audio.", exc_info=True)
            logger.info(play_ex)


        except Exception:
            logger.error("Error when attempting to play audio.", exc_info=True)
            interrupted = True
            completed = False

        finally:
            if mp3_path and os.path.exists(mp3_path):
                try:
                    os.remove(mp3_path)
                except Exception:
                    pass
            with self.play_lock:
                self.stop_current_playback()


    def play_audio_loop(self, config: dict):
        """Continuously play text as audio based on event signaling."""
        lang = "english"
        lang_code = self._get_language_code(lang)
        rate = config.get("General", {}).get("tts_speech_rate", self.speech_rate)
        self.speech_rate = rate

        return completed and not interrupted

    # ---------------------------------------------------------------------
    #  Main loop (runs in dedicated thread)
    # ---------------------------------------------------------------------
    def play_audio_loop(self, config: dict) -> None:
        """Main loop that reacts to UI events and streams TTS accordingly."""
        lang_name = config.get("OpenAI", {}).get("response_lang", "english")
        lang_code = self._get_language_code(lang_name)
        self.speech_rate = config.get("General", {}).get(
            "tts_speech_rate", self.speech_rate
        )


        while not self.stop_loop:
            gv = self.conversation.context

            # --------------------------------------------------------------
            # Real‑time, incremental playback
            # --------------------------------------------------------------
            if gv.real_time_read and self.read_response:
                speech = self._process_speech_text(self._get_speech_text())
                start = len(gv.last_spoken_response)
                new_text = speech[start:]

                if new_text:
                    self.speech_text_available.clear()
                    sp_rec = gv.speaker_audio_recorder
                    prev_state = sp_rec.enabled
                    sp_rec.enabled = False  # avoid echo
                    try:
                        self.play_audio(speech=new_text, lang=lang_code, rate=rate)
                        gv.last_spoken_response += new_text

                        if self.play_audio(new_text, lang_code, self.speech_rate):
                            gv.last_spoken_response += new_text

                    finally:
                        time.sleep(constants.SPEAKER_REENABLE_DELAY_SECONDS)
                        sp_rec.enabled = prev_state
                        gv.last_playback_end = datetime.datetime.utcnow()

                if gv.responder.streaming_complete.is_set():
                    self.read_response = False

            # --------------------------------------------------------------
            # Single‑shot playback when streaming completes
            # --------------------------------------------------------------
            elif self.speech_text_available.is_set() and self.read_response:
                self.speech_text_available.clear()
                speech = self._process_speech_text(self._get_speech_text())


                new_lang = config.get("OpenAI", {}).get("response_lang", lang)
                if new_lang != lang:
                    lang_code = self._get_language_code(new_lang)
                    lang = new_lang

                # Update language dynamically in case settings changed
                new_lang_name = config.get("OpenAI", {}).get("response_lang", lang_name)
                if new_lang_name != lang_name:
                    lang_name = new_lang_name
                    lang_code = self._get_language_code(lang_name)


                sp_rec = gv.speaker_audio_recorder
                prev_state = sp_rec.enabled
                sp_rec.enabled = False
                try:

                    if gv.real_time_read:
                        start = 0
                        if final_speech.startswith(gv.last_spoken_response):
                            start = len(gv.last_spoken_response)
                        new_text = final_speech[start:]
                        if new_text:
                            self.speech_text_available.clear()
                            self.play_audio(speech=new_text, lang=lang_code, rate=rate)
                            gv.last_spoken_response += new_text
                    else:
                        self.speech_text_available.clear()
                        self.play_audio(speech=final_speech, lang=lang_code, rate=rate)
                        gv.last_spoken_response = final_speech

                    if self.play_audio(speech, lang_code, self.speech_rate):
                        gv.last_spoken_response = speech

                finally:
                    time.sleep(constants.SPEAKER_REENABLE_DELAY_SECONDS)
                    sp_rec.enabled = prev_state
                    gv.last_playback_end = datetime.datetime.utcnow()
                    self.read_response = False

            # --------------------------------------------------------------
            time.sleep(0.1)


    def _get_language_code(self, lang: str) -> str:
        """Get the language code from the configuration."""
        try:
            return next(key for key, value in LANGUAGES_DICT.items() if value == lang)
        except StopIteration:
            # Return dafault lang if nothing else is found
            return "en"

    def _get_speech_text(self) -> str:
        """Get the speech text from the conversation."""
        return self.conversation.get_conversation(
            sources=[constants.PERSONA_ASSISTANT], length=1
        )

    def _process_speech_text(self, speech: str) -> str:
        """Process the speech text to remove persona and formatting."""
        persona_length = len(constants.PERSONA_ASSISTANT) + 2
        final_speech = speech[persona_length:].strip()
        return final_speech[1:-1]  # Remove square brackets

