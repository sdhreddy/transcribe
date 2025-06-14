"""Global context for the application
"""
import sys
import os
import queue
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from .audio_transcriber import AudioTranscriber
from . import audio_player
from . import conversation  # noqa: E402 pylint: disable=C0413

from sdk import audio_recorder as ar  # noqa: E402 pylint: disable=C0413
from tsutils import Singleton, task_queue, utilities  # noqa: E402 pylint: disable=C0413


class TranscriptionGlobals(Singleton.Singleton):
    """Global constants for audio processing. It is implemented as a Singleton class.
    """

    audio_queue: queue.Queue = None
    user_audio_recorder: ar.MicRecorder = None
    speaker_audio_recorder: ar.SpeakerRecorder = None
    audio_player_var: audio_player.AudioPlayer = None
    # Global for transcription from speaker, microphone
    transcriber: AudioTranscriber = None
    # Global for responses from openAI API
    responder = None
    # Update_response_now is true when we are waiting for a one time immediate response to query
    update_response_now: bool = False
    # Read response in voice
    read_response: bool = False
    # Read every AI response aloud when enabled
    continuous_read: bool = False
    # Last response that was read aloud
    last_tts_response: str = ""
    # Last response actually spoken out loud
    last_spoken_response: str = ""
    # Timestamp when the last TTS playback finished
    last_playback_end: datetime.datetime = None
    # LLM Response to an earlier conversation
    # This is populated when user clicks on text in transcript textbox
    previous_response: str = None
    start: datetime.datetime = None
    task_worker = None
    main_window = None
    data_dir = None
    db_file_path: str = None
    # Current working directory
    current_working_dir: str = None
    db_context: dict = None

    convo: conversation.Conversation = None
    _initialized: bool = None

    def __init__(self):
        if self._initialized:
            return
        if self.audio_queue is None:
            self.audio_queue = queue.Queue()
        self.convo = conversation.Conversation(self)
        self.start = datetime.datetime.now()
        self.task_worker = task_queue.TaskQueue()
        self.data_dir = utilities.get_data_path(app_name='Transcribe')
        zip_file_name = utilities.incrementing_filename(filename=f'{self.data_dir}/logs/transcript', extension='zip')
        zip_params = {
            'task_type': task_queue.TaskQueueEnum.ZIP_TASK,
            'folder_path': f'{self.data_dir}/logs',
            'zip_file_name': zip_file_name,
            'skip_zip_files': True
        }
        self.task_worker.add(**zip_params)
        self.current_working_dir = os.path.dirname(os.path.realpath(__file__))
        # print(f'Current folder is : {self.current_working_dir}')
        # Ensure that vscode.env file is being read correctly
        # print(f'Env var is: {os.getenv("test_environment_variable")}')
        # Ensure log folder exists
        utilities.ensure_directory_exists(f'{self.data_dir}/logs')
        db_log_file = utilities.incrementing_filename(filename=f'{self.data_dir}logs/db',
                                                      extension='log')
        self.db_file_path = self.data_dir + 'logs/app.db'
        self.db_context = {}
        self.db_context['db_file_path'] = self.db_file_path
        self.db_context['current_working_dir'] = self.current_working_dir
        self.db_context['db_log_file'] = db_log_file
        self.continuous_read = False
        self.last_tts_response = ""
        self.last_spoken_response = ""
        self.last_playback_end = None
        self._initialized = True

    def set_transcriber(self, transcriber):
        """Set Transcriber to be used across the application.
        """
        self.transcriber = transcriber

    def initiate_audio_devices(self, config: dict):
        """Initialize the necessary audio devices
        """
        # Handle mic if it is not disabled in arguments or yaml file
        print('[INFO] Using default microphone.')
        data_dir = utilities.get_data_path(app_name='Transcribe')
        self.user_audio_recorder = ar.MicRecorder(audio_file_name=f'{data_dir}/logs/mic.wav')
        if not config['General']['disable_mic'] and config['General']['mic_device_index'] != -1:
            print('[INFO] Override default microphone with device specified in parameters file.')
            self.user_audio_recorder.set_device(index=int(config['General']['mic_device_index']))

        # Handle speaker if it is not disabled in arguments or yaml file
        print('[INFO] Using default speaker.')
        self.speaker_audio_recorder = ar.SpeakerRecorder(audio_file_name=f'{data_dir}/logs/speaker.wav')
        if not config['General']['disable_speaker'] and config['General']['speaker_device_index'] != -1:
            print('[INFO] Override default speaker with device specified in parameters file.')
            self.speaker_audio_recorder.set_device(index=int(
                config['General']['speaker_device_index']))

    def set_read_response(self, value: bool):
        """Signal that the response will be read aloud
        """
        self.read_response = value
        self.audio_player_var.read_response = value

    def set_continuous_read(self, value: bool):
        """Toggle continuous read aloud of responses"""
        self.continuous_read = value


# Instantiate a single copy of globals here itself
T_GLOBALS = TranscriptionGlobals()
