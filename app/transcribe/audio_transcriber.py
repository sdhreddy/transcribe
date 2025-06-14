"""Encapsulates all Speech to Text functionality
"""
import sys
import os
import subprocess  # nosec
import queue
import time
import threading
import io
import datetime
from abc import abstractmethod
# import pprint
import wave
import tempfile
import pyaudio
from difflib import SequenceMatcher
import logging
from pathlib import Path
import numpy as np
# from db import AppDB as appdb
import conversation  # noqa: E402 pylint: disable=C0413
import constants  # noqa: E402 pylint: disable=C0413
sys.path.append('../..')
import custom_speech_recognition as sr  # noqa: E402 pylint: disable=C0413
from tsutils import app_logging as al  # noqa: E402 pylint: disable=C0413
from tsutils import duration, utilities  # noqa: E402 pylint: disable=C0413
from sdk.transcriber_models import WhisperCPPSTTModel

# Define logger before using it
logger = al.get_module_logger(al.TRANSCRIBER_LOGGER)

try:
    from transcribe.voice_filter import VoiceFilter  # Production voice filter
    logger.info("Using production VoiceFilter")
except ImportError:
    try:
        from voice_filter import VoiceFilter  # Try local import
        logger.info("Using local VoiceFilter")
    except ImportError:
        from transcribe.voice_filter_mock import VoiceFilter  # Mock for testing
        logger.warning("WARNING: Using MockVoiceFilter for testing")


# There can be prompts for speech to text aspects as well, that have not been considered as yet.
# See the prompting section here https://platform.openai.com/docs/guides/speech-to-text/prompting

# pylint: disable=logging-fstring-interpolation
PHRASE_TIMEOUT = 1.5  # Reduced from 3.05 to improve responsiveness
# List available microphone sources for lookups
available_sources = sr.Microphone.list_microphone_names()
# Attempt to prune after these number of segments in transcription
WHISPER_SEGMENT_PRUNE_THRESHOLD = 6
# Duration of audio (seconds) after which force pruning
AUDIO_LENGTH_PRUNE_THRESHOLD_SECONDS = 45


class AudioTranscriber:   # pylint: disable=C0115, R0902

    def __init__(self, mic_source, speaker_source, model,
                 convo: conversation.Conversation,
                 config: dict):
        logger.info(self.__class__.__name__)
        # Transcript_data should be replaced with the conversation object.
        # We do not need to store transcription in 2 different places.
        # self.transcript_data = {"You": [], "Speaker": []}
        self.transcript_changed_event = threading.Event()
        self.last_transcript_update_time = None  # Track when transcript was last updated
        
        # Get voice filter configuration
        voice_filter_config = config.get('General', {}).get('voice_filter_enabled', 'No')
        # Handle both string and boolean values
        if isinstance(voice_filter_config, bool):
            self.voice_filter_enabled = voice_filter_config
        else:
            self.voice_filter_enabled = voice_filter_config == 'Yes'
        
        # Initialize VoiceFilter for speaker-aware filtering
        self.voice_filter = None
        if self.voice_filter_enabled:
            try:
                # Get absolute path for voice profile
                profile_path = config.get('General', {}).get('voice_filter_profile', 'my_voice.npy')
                if not Path(profile_path).is_absolute():
                    # Convert to absolute path relative to project root
                    profile_path = str(Path('/home/sdhre/transcribe') / profile_path)
                
                self.voice_filter = VoiceFilter(
                    profile_path=profile_path,
                    similarity_threshold=float(config.get('General', {}).get('voice_filter_threshold', 0.75))
                )
                logger.info(f"VoiceFilter initialized with profile: {profile_path}")
                logger.info("VoiceFilter initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize VoiceFilter: {e}")
                self.voice_filter = None
        self.stt_model = model
        # Same mutex is used for all audio sources. In case locking becomes an issue, can consider
        # using separate mutex for each audio source
        self.mutex = threading.Lock()
        self.config = config
        self.clear_transcript_periodically: bool = \
            self.config['General']['clear_transcript_periodically']
        self.clear_transcript_interval_seconds: int = \
            self.config['General']['clear_transcript_interval_seconds']
        # Determines if transcription is enabled for the application. By default it is enabled.
        self.transcribe = True
        self.audio_sources_properties = {
            "You": {
                # int
                "sample_rate": mic_source.SAMPLE_RATE,
                # int
                "sample_width": mic_source.SAMPLE_WIDTH,
                # int
                "channels": mic_source.channels,
                "last_sample": bytes(),  # Raw bytes for wav format data
                # Timestamp (UTC) for when the last transcribed audio record was put in queue
                "last_spoken": None,
                # bool
                "new_phrase": True,
                # function pointer
                "process_data_func": self.process_mic_data,
                # mutex
                "mutex": self.mutex
            },
            "Speaker": {
                # int
                "sample_rate": mic_source.SAMPLE_RATE if speaker_source is None else speaker_source.SAMPLE_RATE,
                # int
                "sample_width": mic_source.SAMPLE_WIDTH if speaker_source is None else speaker_source.SAMPLE_WIDTH,
                # int
                "channels": mic_source.channels if speaker_source is None else speaker_source.channels,
                "last_sample": bytes(),  # Raw bytes for wav format data
                # Timestamp (UTC) for when the last transcribed audio record was put in queue
                "last_spoken": None,
                # bool
                "new_phrase": True,
                # function pointer
                "process_data_func": self.process_speaker_data,
                # mutex
                "mutex": self.mutex
            }
        }
        self.conversation = convo
        self.voice_identifier = None  # Will be set by app_utils if enabled
        self.last_speaker_id = 'unknown'
        self.last_speaker_confidence = 0.0

    def identify_speaker(self, audio_data: bytes, who_spoke: str) -> tuple[str, float]:
        """Identify the speaker using voice identification if enabled.
        
        Returns:
            tuple: (speaker_id, confidence) where speaker_id is 'primary_user' or 'unknown'
        """
        if self.voice_identifier is None:
            # Voice identification not enabled, return default
            return ('unknown', 0.0)
        
        try:
            # Save audio to temporary file for processing
            import tempfile
            fd, temp_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            
            # Write audio data to file
            self.write_wav_data_to_file(
                audio_data,
                channels=self.audio_sources_properties[who_spoke]["channels"],
                sample_width=self.audio_sources_properties[who_spoke]["sample_width"],
                frame_rate=self.audio_sources_properties[who_spoke]["sample_rate"],
                file_path=temp_path
            )
            
            # Identify speaker
            is_known, speaker_id, confidence = self.voice_identifier.identify_speaker(temp_path)
            
            # Clean up
            os.unlink(temp_path)
            
            # Map to our expected format
            # Use the speaker_id regardless of confidence level
            # This allows inverted logic to work correctly even with low confidence
            if speaker_id:
                result_id = speaker_id
            else:
                # No speaker identified at all
                result_id = 'unknown'
            
            # Enhanced logging for debugging
            logger.info(f"Voice identification: is_known={is_known}, speaker_id={speaker_id}, "
                       f"confidence={confidence:.2f}, threshold={self.voice_identifier.similarity_threshold:.2f}, "
                       f"result={result_id}")
            
            # Store last identification results for UI display
            self.last_speaker_id = result_id
            self.last_speaker_confidence = confidence
            
            return (result_id, confidence)
            
        except Exception as e:
            logger.error(f"Error in voice identification: {e}")
            return ('unknown', 0.0)
    
    def set_source_properties(self, mic_source=None, speaker_source=None):
        """Resets the audio source properties stored in internal data structures.
        """
        if mic_source is not None:
            self.audio_sources_properties['You']['sample_rate'] = mic_source.SAMPLE_RATE
            self.audio_sources_properties['You']['sample_width'] = mic_source.SAMPLE_WIDTH
            self.audio_sources_properties['You']['channels'] = mic_source.channels

        if speaker_source is not None:
            self.audio_sources_properties['Speaker']['sample_rate'] = speaker_source.SAMPLE_RATE
            self.audio_sources_properties['Speaker']['sample_width'] = speaker_source.SAMPLE_WIDTH
            self.audio_sources_properties['Speaker']['channels'] = speaker_source.channels

    def transcribe_audio_queue(self, audio_queue: queue.Queue):
        """Transcribe data from audio sources. In this case we have 2 sources, microphone, speaker.
        Args:
          audio_queue: queue object with reference to audio files
        """
        logger.info(self.__class__.__name__)
        while True:
            who_spoke, data, time_spoken = audio_queue.get()
            
            # Skip speaker audio during/after TTS playback to prevent queue backup
            if who_spoke == "Speaker":
                import global_vars as gv
                if hasattr(gv, 'last_playback_end') and gv.last_playback_end:
                    time_since_playback = (datetime.datetime.utcnow() - gv.last_playback_end).total_seconds()
                    if time_since_playback < 2.0:  # Skip for 2 seconds after TTS
                        logger.info(f"Skipping speaker audio - TTS recently played ({time_since_playback:.1f}s ago)")
                        continue
            
            # If queue has backlog and current input is from microphone, drain old speaker audio
            # Enhanced queue monitoring
            queue_size = audio_queue.qsize()
            
            # Check if TTS is playing to determine queue limits
            is_tts_playing = False
            gv = self.conversation.context
            if hasattr(gv, 'is_tts_playing'):
                is_tts_playing = gv.is_tts_playing
            
            # Extend queue size and time window during TTS playback
            max_queue_size = 30 if is_tts_playing else 5
            max_age = 30.0 if is_tts_playing else 5.0
            
            if queue_size > max_queue_size:
                logger.warning(f"Audio queue severely backed up: {queue_size} items (TTS playing: {is_tts_playing})")
                # Aggressively drain old speaker audio
                items_to_check = []
                for _ in range(min(queue_size - 1, 20)):
                    try:
                        item = audio_queue.get_nowait()
                        items_to_check.append(item)
                    except queue.Empty:
                        break
                
                # Re-add only recent microphone audio
                mic_items = []
                speaker_items_dropped = 0
                for who, data, ts in items_to_check:
                    if who == "You":
                        # Keep only recent mic audio (extended during TTS)
                        age = (datetime.datetime.utcnow() - ts).total_seconds()
                        if age < max_age:
                            mic_items.append((who, data, ts))
                    else:
                        speaker_items_dropped += 1
                
                # Re-add mic items
                for item in mic_items:
                    try:
                        audio_queue.put_nowait(item)
                    except:
                        pass
                
                if speaker_items_dropped > 0:
                    logger.info(f"Dropped {speaker_items_dropped} speaker items, kept {len(mic_items)} recent mic items")
            if who_spoke == "You" and audio_queue.qsize() > 2:
                drained = 0
                while audio_queue.qsize() > 1:
                    try:
                        peek_who, _, _ = audio_queue.get_nowait()
                        if peek_who == "Speaker":
                            drained += 1
                        else:
                            # Put it back if it's not speaker audio
                            audio_queue.put((peek_who, _, _))
                            break
                    except queue.Empty:
                        break
                if drained > 0:
                    logger.info(f"Drained {drained} speaker audio chunks from queue")
            logger.info(f'Transcribe Audio Queue. Current time: {datetime.datetime.utcnow()} '
                        f'- Time Spoken: {time_spoken} by : {who_spoke}, queue_backlog - '
                        f'{audio_queue.qsize()}')
            self._update_last_sample_and_phrase_status(who_spoke, data, time_spoken)
            
            # Apply voice filtering if enabled
            if self.voice_filter and who_spoke == "You":
                # Use accumulated audio for better voice matching
                raw_bytes = self.audio_sources_properties[who_spoke]["last_sample"]
                
                if raw_bytes:
                    # Convert audio and check duration
                    sample_rate = self.audio_sources_properties[who_spoke]["sample_rate"]
                    audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                    audio_duration = len(audio_np) / sample_rate
                    
                    # Log detailed debug info
                    logger.info(f"[VOICE_FILTER] Processing audio - Duration: {audio_duration:.2f}s, "
                              f"Samples: {len(audio_np)}, Sample rate: {sample_rate}, "
                              f"Accumulated bytes: {len(raw_bytes)}")
                    
                    # Process all audio, but weight by duration for better accuracy
                    # Shorter clips might have lower confidence
                    if audio_duration >= 0.1:  # Process even short clips
                        try:
                            is_user, similarity = self.voice_filter.is_user(audio_np, sample_rate)
                            logger.info(f"[VOICE_FILTER] Similarity: {similarity:.3f}, threshold: {self.voice_filter.similarity_threshold:.2f}")
                        except Exception as e:
                            logger.error(f"[VOICE_FILTER] Error: {e}")
                            is_user, similarity = False, 0.0
                    else:
                        # Not enough audio, allow through but log
                        logger.info(f"[VOICE_FILTER] Audio too short ({audio_duration:.2f}s), allowing through")
                        is_user, similarity = False, 0.0
                else:
                    # No audio data
                    is_user, similarity = False, 0.0
                
                if is_user:
                    logger.info(f"[VOICE_FILTER] Skipping primary user voice (similarity: {similarity:.3f})")
                    continue  # Skip processing this audio
                else:
                    logger.info(f"[VOICE_FILTER] Processing non-user voice (similarity: {similarity:.3f})")

            source_info = self.audio_sources_properties[who_spoke]

            text = ''
            try:
                file_descritor, path = tempfile.mkstemp(suffix=".wav")
                os.close(file_descritor)
                source_info["process_data_func"](source_info["last_sample"], path)
                if self.transcribe:
                    with duration.Duration('Transcription (Speech to Text)', screen=False):
                        logger.info(f'{datetime.datetime.now()} - Begin transcription')
                        response = self.stt_model.get_transcription(path)
                        text = self.stt_model.process_response(response)
                        if text != '':
                            self._prune_audio_file(response, who_spoke, time_spoken, path)

                        logger.info(f'{datetime.datetime.utcnow()} = Transcribed text: {text}')
                        logger.info(f'{datetime.datetime.utcnow()} - End transcription')

            except Exception as exception:
                print(exception)
            finally:
                # print(f'transcribe_audio_queue: file: {path} filesize: {os.path.getsize(path)}')
                os.unlink(path)

            if text != '' and text.lower() != 'you':
                if not (who_spoke == 'Speaker' and self._should_ignore_speaker_transcript(text)):
                    # Identify speaker if voice identification is enabled
                    speaker_id, confidence = self.identify_speaker(
                        self.audio_sources_properties[who_spoke]["last_sample"], 
                        who_spoke
                    )
                    
                    # Update transcript with speaker identity
                    self.update_transcript(who_spoke, text, time_spoken, speaker_id, confidence)
                    self.last_transcript_update_time = datetime.datetime.utcnow()  # Track update time
                    
                    # Set transcript changed event with speaker info
                    self.last_speaker_id = speaker_id
                    self.last_speaker_confidence = confidence
                    self.transcript_changed_event.set()

    def _prune_audio_file(self, results, who_spoke, time_spoken, path):
        """Checks if pruning of Audio Source is required based on transcriber
        parameters, and prunes appropriately."""
        source_info = self.audio_sources_properties[who_spoke]
        with source_info["mutex"]:
            original_data_size = len(source_info["last_sample"])

        prune, prune_id, prune_percent = self.check_for_latency(results)
        # print(f'Prune: {prune}. prune_id: {prune_id}. prune_percent: {prune_percent}')
        if prune:
            logger.info(f'{datetime.datetime.utcnow()} - Attempted to prune.')
            first, second = self.prune_for_latency(who_spoke=who_spoke,
                                                   original_data_size=original_data_size,
                                                   prune_percent=prune_percent,
                                                   results=results,
                                                   prune_id=prune_id,
                                                   file_path=path)
            # For pruned audio, we don't re-identify speaker, use last known values
            self.update_transcript(who_spoke, first, time_spoken, 
                                 self.last_speaker_id, self.last_speaker_confidence)
            self.update_transcript(who_spoke, second, time_spoken,
                                 self.last_speaker_id, self.last_speaker_confidence)

    def _should_ignore_speaker_transcript(self, text: str) -> bool:
        """Determine if speaker transcript matches recent TTS output."""
        gv = self.conversation.context
        if gv.last_playback_end is None:
            return False
        delta = (datetime.datetime.utcnow() - gv.last_playback_end).total_seconds()
        if delta > constants.PLAYBACK_IGNORE_WINDOW_SECONDS:
            return False
        last_tts = gv.last_tts_response.strip().lower()
        candidate = text.strip().lower()
        if candidate == last_tts or candidate in last_tts or last_tts in candidate:
            return True
        ratio = SequenceMatcher(None, candidate, last_tts).ratio()
        return ratio >= constants.IGNORE_SIMILARITY_THRESHOLD

    @abstractmethod
    def check_for_latency(self, results: dict) -> tuple[bool, int, float]:
        """Very long audio clips can result in latency of transcription.
        Prune long audio clips based on number of segments, audio duration.
        Latency check is specific to each transcriber because of the difference
        in format of results. It is implemented in each transcriber specific class.
        Return values are
          prune: bool: Whether to prune or not
          prune_segment_id: int: Prune everything before this segment / paragraph
          prune_percent: float: % of audio clip (by size) to be pruned
        """

    @abstractmethod
    def prune_for_latency(self, who_spoke: str, original_data_size: int,
                          results: dict, prune_id: int,
                          file_path: str, prune_percent: int) -> tuple[str, str]:
        """Very long audio clips can result in latency of transcription.
        Prune long audio clips based on number of segments, audio duration.
        Latency check is specific to each transcriber because of the difference
        in format of results. It is implemented in each transcriber specific class.
        """

    def write_wav_data_to_file(self, data, channels,
                               sample_width, frame_rate, file_path='', ) -> str:
        """Write the data as a wave file
        """
        if file_path == '':
            file_descritor, file_path = tempfile.mkstemp(suffix=".wav")
            os.close(file_descritor)

        with wave.open(file_path, 'wb') as wf:
            # print(f'{datetime.datetime.now()} - Writing speaker data into file: {file_path}')
            wf.setnchannels(channels)    # pylint: disable=E1101
            wf.setsampwidth(sample_width)    # pylint: disable=E1101
            wf.setframerate(frame_rate)    # pylint: disable=E1101
            wf.writeframes(data)    # pylint: disable=E1101
            # print(f'datasize: {len(data)}')
        # print(f'filesize: {os.path.getsize(file_path)}')
        return file_path

    # Once these 2 PR's are resolved, we might be able to get rid of this method
    # and use whisper.cpp for conversion to 16khz format
    # https://github.com/ggerganov/whisper.cpp/pull/1549
    # https://github.com/ggerganov/whisper.cpp/pull/1524
    def convert_wav_to_16khz_format(self, file_path: str) -> str:
        """Convert input wav file to 16 khz format, since this is the only format accepted by
        whisper.cpp at the moment.
        """
        try:
            # Convert input file to 16khz. That is a requirement for using whisper.cpp
            # ffmpeg -i <input audio filename> -ar 16000 -ac 1 -c:a pcm_s16le -y <output audio file>

            file_descritor, mod_file_path = tempfile.mkstemp(suffix=".wav")
            os.close(file_descritor)
            # print(f'Convert file {file_path} to 16khz file {mod_file_path}')
            log_file = f"{utilities.get_data_path(app_name='Transcribe')}/logs/ffmpeg.txt"
            subprocess.call(["ffmpeg", '-i', file_path, '-ar', '16000', '-ac',  # nosec
                             '1', '-c:a', 'pcm_s16le', '-y', mod_file_path],
                            stdout=open(file=log_file, mode='a', encoding='utf-8'),
                            stderr=subprocess.STDOUT)
            return mod_file_path
        except Exception as ex:
            print(f'ERROR: converting wav file {file_path} to 16khz.')
            print(ex)
            return ''

    def get_wav_file_data(self, file_path):
        """Return just the data from wav file. Does not include wav format headers and such.
        """
        data = None
        try:
            with wave.open(file_path, 'rb') as file_handle:
                data = file_handle.readframes(file_handle.getnframes())
        except Exception as ex:
            print(f'ERROR: reading from wav file {file_path} to 16khz.')
            print(ex)
        return data

    def _update_last_sample_and_phrase_status(self, who_spoke, data, time_spoken):
        logger.info(AudioTranscriber._update_last_sample_and_phrase_status.__name__)
        if not self.transcribe:
            return
        source_info = self.audio_sources_properties[who_spoke]

        with source_info["mutex"]:
            # time_spoken - when current audio record was put into the queue (utc)
            if source_info["last_spoken"] and time_spoken - source_info["last_spoken"] \
                    > datetime.timedelta(seconds=PHRASE_TIMEOUT):
                # New phrase detected - reset the accumulated audio
                source_info["last_sample"] = data  # Start fresh with current data
                source_info["new_phrase"] = True
            else:
                # Continue the same phrase - accumulate audio
                source_info["last_sample"] += data  # Accumulate the audio
                source_info["new_phrase"] = False

            if isinstance(self.stt_model, WhisperCPPSTTModel):
                # Target sample_rate: For Whisper CPP target sample rate is 16000 khz
                # if source and target sample rates are not the same, conver to target sample rate
                # Write wav data to file
                # Convert to desired sample rate using ffmpeg
                channels = int(source_info["channels"])
                p = pyaudio.PyAudio()
                sample_width = p.get_sample_size(pyaudio.paInt16)
                frame_rate = int(source_info["sample_rate"])
                file_descritor, file_path = tempfile.mkstemp(suffix=".wav")
                os.close(file_descritor)

                # Distinguish audio from speaker, microphone.
                # Microphone audio requires a little bit of extra processing.
                if who_spoke == 'Speaker':
                    file_path = self.write_wav_data_to_file(data,
                                                            channels=channels,
                                                            sample_width=sample_width,
                                                            frame_rate=frame_rate,
                                                            file_path=file_path)
                if who_spoke == 'You':
                    audio_data = sr.AudioData(data, frame_rate, sample_width)
                    with open(file_path, 'w+b') as file_handle:
                        file_handle.write(audio_data.get_wav_data())
                mod_file_path = self.convert_wav_to_16khz_format(file_path)
                data = self.get_wav_file_data(mod_file_path)

                os.unlink(file_path)
                os.unlink(mod_file_path)

            source_info["last_spoken"] = time_spoken

    def process_mic_data(self, data, temp_file_name):
        """Processes audio data received from the microphone
        Args:
            temp_file_name: Name of .wav file to store the data
        """
        logger.info(AudioTranscriber.process_mic_data.__name__)
        if not self.transcribe:
            return

        p = pyaudio.PyAudio()
        sample_width = p.get_sample_size(pyaudio.paInt16)
        frame_rate = int(self.audio_sources_properties["You"]["sample_rate"])
        audio_data = sr.AudioData(data, frame_rate, sample_width)
        with open(temp_file_name, 'w+b') as file_handle:
            file_handle.write(audio_data.get_wav_data())
        # print(f'filesize: {os.path.getsize(temp_file_name)}')

    def process_speaker_data(self, data, temp_file_name):
        """Processes audio data received from the speaker
        Args:
            temp_file_name: Name of .wav file to store the data
        """
        logger.info(AudioTranscriber.process_speaker_data.__name__)
        if not self.transcribe:
            return
        channels = int(self.audio_sources_properties["Speaker"]["channels"])
        p = pyaudio.PyAudio()
        sample_width = p.get_sample_size(pyaudio.paInt16)
        frame_rate = self.audio_sources_properties["Speaker"]["sample_rate"]
        self.write_wav_data_to_file(data,
                                    channels=channels,
                                    sample_width=sample_width,
                                    frame_rate=frame_rate,
                                    file_path=temp_file_name)

    def update_transcript(self, who_spoke, text, time_spoken, speaker_id='unknown', confidence=0.0):
        """Update transcript with new data
        Args:
        who_spoke: Person this audio is attributed to
        text: Actual spoken words
        time_spoken: Time at which audio was taken, relative to start time
        speaker_id: Identified speaker ('primary_user' or 'unknown')
        confidence: Voice identification confidence score
        """
        source_info = self.audio_sources_properties[who_spoke]
        
        # Store speaker identity for use by responder
        self.last_speaker_id = speaker_id
        self.last_speaker_confidence = confidence

        # if source_info["new_phrase"] or len(transcript) == 0:
        if source_info["new_phrase"]:
            self.conversation.update_conversation(persona=who_spoke,
                                                  time_spoken=time_spoken,
                                                  text=text)
        else:
            self.conversation.update_conversation(persona=who_spoke,
                                                  time_spoken=time_spoken,
                                                  text=text,
                                                  update_previous=True)

    def get_transcript(self, length: int = 0):
        """Get the audio transcript
        Args:
        length: Get the last length elements from the audio transcript.
                Default value = 0, gives the complete transcript
        """
        sources = [
            constants.PERSONA_YOU,
            constants.PERSONA_SPEAKER
            ]
        convo_object_return_value = self.conversation.get_conversation(
            sources=sources, length=length)
        return convo_object_return_value

    def clear_transcript_data_loop(self, audio_queue: queue.Queue):
        """Clear transcript data at a specified interval if needed.
        Args:
          audio_queue: queue object with reference to audio files
        """
        while True:
            if self.clear_transcript_periodically:
                self.clear_transcriber_context(audio_queue=audio_queue)
            time.sleep(self.clear_transcript_interval_seconds)

    def clear_transcriber_context(self, audio_queue: queue.Queue):
        """Reset the transcriber
        Args:
          textbox: textbox to be updated
          text: updated text
    """
        with self.mutex:
            # This method can be invoked from 2 different contexts.
            # Mutex ensures integrity of data for race conditions.
            logger.info(AudioTranscriber.clear_transcriber_context.__name__)
            self.clear_transcript_data()
            with audio_queue.mutex:
                audio_queue.queue.clear()

    def clear_transcript_data(self):
        """Clears all internal data associated with the transcript
        """
        self.audio_sources_properties["You"]["last_sample"] = bytes()
        self.audio_sources_properties["Speaker"]["last_sample"] = bytes()

        self.audio_sources_properties["You"]["new_phrase"] = True
        self.audio_sources_properties["Speaker"]["new_phrase"] = True

        self.conversation.clear_conversation_data()


class WhisperTranscriber(AudioTranscriber):
    """Does local application specific processing related to WhisperTranscriber.
    Also processes the local application state as it relates to Whisper.
    Does not interact with the Whisper API or Local Whisper SDK.
    """
    def __init__(self, mic_source, speaker_source, model,
                 convo: conversation.Conversation, config: dict,
                 source_name: str):
        try:
            _ = available_sources.index(source_name)
            selected_source = source_name
        except ValueError:
            selected_source = available_sources[0] if available_sources else source_name
            logging.warning(
                "Audio source '%s' not found. Falling back to '%s'.",
                source_name,
                selected_source,
            )

        if mic_source is None:
            raise ValueError(
                f"Audio source '{selected_source}' not found. Please configure a valid microphone source."  # noqa: E501
            )
        self.source = selected_source
        self.sample_rate = mic_source.SAMPLE_RATE
        super().__init__(mic_source, speaker_source, model, convo, config)

    def check_for_latency(self, results: dict) -> tuple[bool, int, float]:
        """Very long audio clips can result in latency of transcription.
        Prune long audio clips based on number of segments, audio duration.
        Return values are
          prune: bool: Whether to prune or not
          prune_segment_id: int: Prune everything before this segment
          prune_percent: float: % of audio clip (by size) to be pruned
        """

        # We get a few different type of response objects. We will have to adjust how we prune
        # based on the type of response object. See the file
        # venv\Lib\site-packages\openai\util.py
        # def convert_to_openai_object(
        # For types of responses
        # Look into this a little bit further.

        logger.info(WhisperTranscriber.check_for_latency)
        logger.info('Check for latency')
        try:
            len_segments = len(results["segments"])
        except KeyError:
            # print(f'Key error in check for latency. {ke}')
            # print(f'Type of results: {type(results)}')
            # pprint.pprint(results)
            return (False, 0, 0)
        except TypeError:
            # For the case of API Whisper we run into this exception
            # Transcription' object is not subscriptable
            return (False, 0, 0)

        if len_segments == 0:
            # print('0 segments in the response.')
            # pprint.pprint(results)
            return (False, 0, 0)

        len_speech = float(results['segments'][len_segments-1]['end'])
        logger.info(f'Segments: {len_segments}. Speech length: {len_speech} seconds.')
        # print(f'Segments: {len_segments}. Speech length: {len_speech} seconds.')

        if len_segments > WHISPER_SEGMENT_PRUNE_THRESHOLD:
            log_msg = f'Attempt Prune segments: {len_segments - WHISPER_SEGMENT_PRUNE_THRESHOLD}.'
            # print(log_msg)
            logger.info(log_msg)
        else:
            # print(f'Segments: {len_segments}. Skip pruning.')
            return (False, 0, 0)

        prune_percent = 0
        original_duration = results['segments'][len_segments-1]['end']

        # Determine how many segments to keep based on sentence ending.
        # Start with len - max segments and determine which one is the last one that
        # can be kept based on end of sentence.
        for rev_segment in reversed(results['segments']):
            if int(rev_segment['id']) > len_segments - 3:
                continue
            text = rev_segment['text'].strip()
            if text.endswith('.') or text.endswith('!') or text.endswith('?'):
                prune_segment_id = int(rev_segment['id'])
                prune_seconds = float(rev_segment['end'])
                prune_percent = prune_seconds / original_duration
                logger.info(f'Prune till segment id : {prune_segment_id}.'
                                 f' Prune duration: {prune_seconds}.')
                logger.info(f'Prune {prune_percent}% of data.')
                break

        # for segment in results['segments']:
        #     print(f'id: {segment['id']} start: {segment['start']} end: {segment['end']} ' +
        #           f'text: {segment['text'].strip()}')

        if prune_percent == 0:
            logger.info(f'Total segments ({len_segments}) is more than prune threshold'
                             f' ({WHISPER_SEGMENT_PRUNE_THRESHOLD}), but could not find'
                             f' segment endings.')

            # Attempt to determine prune percent based on audio duration
            if original_duration > AUDIO_LENGTH_PRUNE_THRESHOLD_SECONDS:
                # Prune the first prunes_seconds of audio.
                prune_seconds = original_duration - AUDIO_LENGTH_PRUNE_THRESHOLD_SECONDS + 5
                # Find the segment that corresponds to prune_seconds
                for segment in results['segments']:
                    if float(segment['end']) > prune_seconds:
                        prune_segment_id = int(segment['id'])
                        prune_percent = prune_seconds / original_duration
                        logger.info(f'Prune till segment id : {prune_segment_id}.'
                                         f' Prune duration: {prune_seconds}.')
                        logger.info(f'Prune {prune_percent}% of data.')
                        break

        if prune_percent == 0:
            return (False, 0, 0)

        return True, prune_segment_id, prune_percent

    def prune_for_latency(self, who_spoke: str, original_data_size: int,
                          results: dict, prune_id: int,
                          file_path: str, prune_percent: int):
        """Prune Audio clip to a smaller size based on size.
        Adjusts the application context based on pruning to reflect pruning.
        """
        # If original_data_size and current size of data do not match, do nothing
        # print('Prune for latency')
        logger.info(WhisperTranscriber.prune_for_latency.__name__)
        segments = results['segments']
        logger.info(f'prune_for_latency: Prune source data by {prune_percent}%. ')
        source_info = self.audio_sources_properties[who_spoke]

        with source_info["mutex"]:
            # Concurrency check
            if len(source_info["last_sample"]) != original_data_size:
                logger.info(f'Aborting pruning. Data Size has changed from '
                                 f'{original_data_size} to '
                                 f'{len(source_info["last_sample"])}')
                return

            # Open the wav file
            with wave.open(file_path, 'rb') as wavfile:

                # Get the number of frames
                num_frames = wavfile.getnframes()
                save_frames = int(num_frames * prune_percent)
                logger.info(f'File {file_path} has {num_frames} frames.'
                                 f' We will save the last {save_frames} frames.')
                new_data = b""

                with io.BytesIO() as temp_wav_file:
                    with wave.open(temp_wav_file, "wb") as wav_writer:
                        wav_writer.setnchannels(wavfile.getnchannels())  # pylint: disable=E1101
                        wav_writer.setsampwidth(wavfile.getsampwidth())  # pylint: disable=E1101
                        wav_writer.setframerate(wavfile.getframerate())  # pylint: disable=E1101
                        wavfile.setpos(save_frames)
                        data = wavfile.readframes(num_frames - int(save_frames))
                        new_data = new_data + data
                        wav_writer.writeframes(data)  # pylint: disable=E1101

            source_info["last_sample"] = new_data

        logger.info(f'Prune convo object until prune id: {prune_id}')
        try:
            first_string = ''
            second_string = ''
            for segment in segments:
                if int(segment["id"]) <= prune_id:
                    first_string += segment["text"]
                else:
                    second_string += segment["text"]
        except Exception as ex:
            print(f'Exception while pruning: {ex}')

        logger.info(f'First string: {first_string}')
        logger.info(f'Second string: {second_string}')

        return first_string, second_string


WHISPERCPP_SEGMENT_PRUNE_THRESHOLD = 6


class WhisperCPPTranscriber(AudioTranscriber):
    """Does local application specific processing related to WhisperCPPTranscriber.
    Also processes the local application state as it relates to WhisperCPP.
    """

    def __init__(self, mic_source, speaker_source, model,
                 convo: conversation.Conversation, config: dict):
        super().__init__(mic_source, speaker_source, model, convo, config)
        # Whisper CPP transcriber requires all files to be mono and have a
        # sample rate of 16khz
        self.audio_sources_properties["You"]["target_sample_rate"] = 16000
        self.audio_sources_properties["You"]["target_channels"] = 1
        self.audio_sources_properties["Speaker"]["target_sample_rate"] = 16000
        self.audio_sources_properties["Speaker"]["target_channels"] = 1

    def process_speaker_data(self, data, temp_file_name):
        """Processes audio data received from the speaker.
        Args:
            temp_file_name: Name of .wav file to store the data
        """
        logger.info(AudioTranscriber.process_speaker_data.__name__)
        if not self.transcribe:
            return
        # print(f'filesize: {os.path.getsize(temp_file_name)}')
        with wave.open(temp_file_name, 'wb') as wf:
            # print(f'{datetime.datetime.now()} - Writing speaker data into file: {temp_file_name}')
            wf.setnchannels(self.audio_sources_properties["Speaker"]["target_channels"])    # pylint: disable=E1101
            p = pyaudio.PyAudio()
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))    # pylint: disable=E1101
            wf.setframerate(self.audio_sources_properties["Speaker"]["target_sample_rate"])    # pylint: disable=E1101
            wf.writeframes(data)    # pylint: disable=E1101
            # print(f'datasize: {len(data)}')
        # print(f'filesize: {os.path.getsize(temp_file_name)}')

    def process_mic_data(self, data, temp_file_name):
        """Processes audio data received from the microphone
        Args:
            temp_file_name: Name of .wav file to store the data
        """
        logger.info(AudioTranscriber.process_mic_data.__name__)
        if not self.transcribe:
            return

        audio_data = sr.AudioData(data, self.audio_sources_properties["You"]["target_sample_rate"],
                                  self.audio_sources_properties["You"]["sample_width"])
        with open(temp_file_name, 'w+b') as file_handle:
            file_handle.write(audio_data.get_wav_data())
        # print(f'filesize: {os.path.getsize(temp_file_name)}')

    def check_for_latency(self, results: dict) -> tuple[bool, int, float]:
        """Very long audio clips can result in latency of transcription.
        Prune long audio clips based on number of segments, audio duration.
        Return values are
          prune: bool: Whether to prune or not
          prune_segment_id: int: Prune everything before this segment
          prune_percent: float: % of audio clip (by size) to be pruned
        """
        logger.info(WhisperCPPTranscriber.check_for_latency)
        logger.info('Check for latency')
        try:
            len_segments = len(results["transcription"])
        except KeyError:
            # print(f'Key error in check for latency. {ke}')
            # print(f'Type of results: {type(results)}')
            # pprint.pprint(results)
            return (False, 0, 0)

        len_speech_ms = int(results['transcription'][-1]['offsets']['to'])
        logger.info(f'Segments: {len_segments}. Speech length: {len_speech_ms} milliseconds.')
        # print(f'Segments: {len_segments}. Speech length: {len_speech_ms} milliseconds.')

        if len_segments > WHISPERCPP_SEGMENT_PRUNE_THRESHOLD:
            log_msg = f'Attempt Prune segments: {len_segments-WHISPERCPP_SEGMENT_PRUNE_THRESHOLD}.'
            # print(log_msg)
            logger.info(log_msg)
        else:
            # print(f'Segments: {len_segments}. Skip pruning.')
            return (False, 0, 0)

        prune_percent = 0
        original_duration = float(len_speech_ms / 1000)

        # Determine how many segments to keep based on sentence ending.
        # Start with len - max segments and determine which one is the last one that
        # can be kept based on end of sentence.
        # Keep at least the last 3 segments
        segment_id = len_segments - 3
        for rev_segment in reversed(results['transcription'][:-3]):
            segment_id -= 1
            text = rev_segment['text'].strip()
            if text.endswith('.') or text.endswith('!') or text.endswith('?'):
                prune_segment_id = segment_id
                prune_seconds = float(rev_segment['offsets']['to']/1000)
                prune_percent = prune_seconds / original_duration
                logger.info(f'Prune till segment id : {prune_segment_id}.'
                                 f' Prune duration: {prune_seconds}.')
                logger.info(f'Prune {prune_percent}% of data.')
                break

        if prune_percent == 0:
            logger.info(f'Total segments ({len_segments}) is more than prune threshold'
                             f' ({WHISPERCPP_SEGMENT_PRUNE_THRESHOLD}), but could not find'
                             f' segment endings.')

            segment_id = 0
            # Attempt to determine prune percent based on audio duration
            if original_duration > AUDIO_LENGTH_PRUNE_THRESHOLD_SECONDS:
                # Prune the first prune_seconds of audio.
                prune_seconds = original_duration - AUDIO_LENGTH_PRUNE_THRESHOLD_SECONDS + 5
                # Find the segment that corresponds to prune_seconds
                for segment in results['transcription']:
                    if float(segment['offsets']['to']/1000) > prune_seconds:
                        prune_segment_id = segment_id
                        prune_percent = prune_seconds / original_duration
                        logger.info(f'Prune till segment id : {prune_segment_id}.'
                                         f' Prune duration: {prune_seconds}.')
                        # print(f'Prune till segment id : {prune_segment_id}.'
                        #       f' Prune duration: {prune_seconds}.')
                        logger.info(f'Prune {prune_percent}% of data.')
                        # print(f'Prune {prune_percent}% of data.')
                        break
                    segment_id += 1

        if prune_percent == 0:
            return (False, 0, 0)

        return True, prune_segment_id, prune_percent

    def prune_for_latency(self, who_spoke: str, original_data_size: int,
                          results: dict, prune_id: int,
                          file_path: str, prune_percent: int) -> tuple[str, str]:
        """Prune Audio clip to a smaller size based on size.
        Adjusts the application context based on pruning to reflect pruning.
        """

        # If original_data_size and current size of data do not match, do nothing
        # print('Prune for latency')
        logger.info(WhisperCPPTranscriber.prune_for_latency.__name__)
        segments = results['transcription']
        logger.info(f'prune_for_latency: Prune source data by {prune_percent}%. ')
        source_info = self.audio_sources_properties[who_spoke]

        with source_info['mutex']:
            # Concurrency check
            if len(source_info['last_sample']) != original_data_size:
                logger.info(f'Aborting pruning. Data Size has changed from '
                                 f'{original_data_size} to '
                                 f'{len(source_info["last_sample"])}')
                return

            # Open the wav file
            with wave.open(file_path, 'rb') as wavfile:
                # Get the number of frames
                num_frames = wavfile.getnframes()
                save_frames = int(num_frames * prune_percent)
                logger.info(f'File {file_path} has {num_frames} frames.'
                                 f' We will save the last {save_frames} frames.')
                new_data = b""

                with io.BytesIO() as temp_wav_file:
                    with wave.open(temp_wav_file, "wb") as wav_writer:
                        wav_writer.setnchannels(wavfile.getnchannels())  # pylint: disable=E1101
                        wav_writer.setsampwidth(wavfile.getsampwidth())  # pylint: disable=E1101
                        wav_writer.setframerate(wavfile.getframerate())  # pylint: disable=E1101
                        wavfile.setpos(save_frames)
                        data = wavfile.readframes(num_frames - int(save_frames))
                        new_data = new_data + data
                        wav_writer.writeframes(data)  # pylint: disable=E1101

            source_info['last_sample'] = new_data

        logger.info(f'Prune convo object until prune id: {prune_id}')
        try:
            first_string = ''
            second_string = ''
            current_id = 0
            for segment in segments:
                if current_id <= prune_id:
                    first_string += segment['text']
                else:
                    second_string += segment['text']
                current_id += 1
        except Exception as ex:
            print(f'Exception while pruning: {ex}')

        logger.info(f'First string: {first_string}')
        logger.info(f'Second string: {second_string}')

        return first_string, second_string


DEEPGRAM_PARAGRAPH_PRUNE_THRESHOLD = 2  # Prune anything more than 2 paragraphs


class DeepgramTranscriber(AudioTranscriber):
    """Does local application specific processing related to Deepgram.
    Also processes the local application state as it relates to Deepgram.
    Does not interact with the Deepgram API.
    """

    def check_for_latency(self, results: dict) -> tuple[bool, int, float]:
        """Determine if the response can be pruned to optimize STT processing
        Prune when
            - More than 2 paragraphs
            - Keep atleast 4 sentences
        Return values are
            prune: bool: Whether or not to prune
            num_paragraphs_to_keep: Prune everything up to this paragraph
            prune_percent: float: % of audio clip (by size) to be pruned
        """
        # check for existence of paragraphs
        logger.info(DeepgramTranscriber.check_for_latency)
        try:
            outer_paragraphs = results.results.channels[0].alternatives[0].paragraphs
        except KeyError as ke:
            print('Error when attempting to get paragraphs from Deepgram response.')
            print(f'Key Error: {ke}')
            return [False, 0, 0]

        speech_duration = float(results.metadata.duration)
        # print(f'Total speech length: {speech_duration}')

        para_list = outer_paragraphs.paragraphs
        num_paragraphs = len(para_list)
        # print(f'There are {num_paragraphs} paragraphs')
        # i = 1
        # for para in para_list:
        #    len_sentences = len(para["sentences"])
        #    # print(f'Paragraph: {i}, {len_sentences} sentences.')
        #    i += 1

        if num_paragraphs > DEEPGRAM_PARAGRAPH_PRUNE_THRESHOLD:
            # Keep the last 2 paragraphs. Prune everything else
            num_paragraphs_to_keep = DEEPGRAM_PARAGRAPH_PRUNE_THRESHOLD
        else:
            # print(f'Number of paras {num_paragraphs} less than or equal to threshold '\
            # '{DEEPGRAM_PARAGRAPH_PRUNE_THRESHOLD}. Skip pruning.')
            return [False, 0, 0]

        # determine prune percent based on how much speech we need to keep
        # First paragraph we will keep is
        beginning_para = para_list[-DEEPGRAM_PARAGRAPH_PRUNE_THRESHOLD]
        start_time = float(beginning_para.sentences[0].start)
        # print(f"First para to keep, start time: {start_time}.")
        # print(f"Para text: {beginning_para['sentences'][0]['text']}.")
        prune_percent = start_time / speech_duration

        # Incorporate AUDIO_LENGTH_PRUNE_THRESHOLD_SECONDS into pruning calculations

        return [True, num_paragraphs_to_keep, prune_percent]

    def prune_for_latency(self, who_spoke: str, original_data_size: int,
                          results: dict, prune_id: int,
                          file_path: str, prune_percent: int):
        """Prune Audio clip to a smaller size based on size.
        Adjusts the application context based on pruning to reflect pruning.
        """
        # If original_data_size and current size of data do not match, do nothing
        logger.info(DeepgramTranscriber.prune_for_latency)
        logger.info(f'prune_for_latency: Prune source data by {prune_percent}%. ')
        source_info = self.audio_sources_properties[who_spoke]

        with source_info['mutex']:
            # Concurrency check
            if len(source_info['last_sample']) != original_data_size:
                logger.info(f'Aborting pruning. Data Size has changed from '
                                 f'{original_data_size} to '
                                 f'{len(source_info["last_sample"])}')
                return

            # Open the wav file
            with wave.open(file_path, 'rb') as wavfile:

                # Get the number of frames
                num_frames = wavfile.getnframes()
                save_frames = int(num_frames * prune_percent)
                logger.info(f'File {file_path} has {num_frames} frames.'
                                 f' We will save the last {save_frames} frames.')
                new_data = b""

                with io.BytesIO() as temp_wav_file:
                    with wave.open(temp_wav_file, "wb") as wav_writer:
                        wav_writer.setnchannels(wavfile.getnchannels())  # pylint: disable=E1101
                        wav_writer.setsampwidth(wavfile.getsampwidth())  # pylint: disable=E1101
                        wav_writer.setframerate(wavfile.getframerate())  # pylint: disable=E1101
                        wavfile.setpos(save_frames)
                        data = wavfile.readframes(num_frames - int(save_frames))
                        new_data = new_data + data
                        wav_writer.writeframes(data)  # pylint: disable=E1101

            source_info['last_sample'] = new_data

        try:
            logger.info(f'Prune convo object until prune id: {prune_id}')
            first_string = ''
            second_string = ''
            para_list = results.results.channels[0].alternatives[0].paragraphs.paragraphs
            for para in para_list[0:-prune_id]:
                for sentence in para.sentences:
                    first_string += sentence.text
            for para in para_list[-prune_id:]:
                for sentence in para.sentences:
                    second_string += sentence.text
        except Exception as ex:
            print(f'Exception while pruning: {ex}')

        return first_string, second_string
