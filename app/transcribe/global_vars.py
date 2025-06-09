"""Global context for the application
"""
import sys
import os
import queue
import datetime
from audio_transcriber import AudioTranscriber
import audio_player
sys.path.append('../..')
import conversation  # noqa: E402 pylint: disable=C0413
from sdk import audio_recorder as ar  # noqa: E402 pylint: disable=C0413
from tsutils import Singleton, task_queue, utilities, app_logging  # noqa: E402 pylint: disable=C0413
logger = app_logging.get_logger()


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
    # Speak streaming text as it arrives
    real_time_read: bool = False
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
        self.real_time_read = False
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
        data_dir = utilities.get_data_path(app_name='Transcribe')
        
        # Improved microphone initialization with device validation
        if not config['General']['disable_mic']:
            print('[INFO] Initializing microphone...')
            
            # Get available input devices for validation
            try:
                inputs, _ = ar.list_audio_devices()
                available_input_indices = [device[0] for device in inputs]
                print(f'[INFO] Available input devices: {inputs}')
            except Exception as e:
                logger.warning(f"Could not list audio devices: {e}")
                available_input_indices = []
            
            # Check if specified mic device exists
            mic_index = config['General']['mic_device_index']
            if mic_index != -1 and mic_index not in available_input_indices:
                print(f'[WARNING] Specified mic device index {mic_index} not found.')
                if available_input_indices:
                    mic_index = available_input_indices[0]
                    print(f'[INFO] Falling back to device index {mic_index}')
                else:
                    print('[WARNING] No input devices available, mic will be disabled')
                    config['General']['disable_mic'] = True
            
            if not config['General']['disable_mic']:
                try:
                    self.user_audio_recorder = ar.MicRecorder(audio_file_name=f'{data_dir}/logs/mic.wav')
                    if mic_index != -1:
                        print(f'[INFO] Setting microphone to device index {mic_index}')
                        self.user_audio_recorder.set_device(index=int(mic_index))
                    else:
                        print('[INFO] Using default microphone')
                except Exception as e:
                    logger.warning(f"Could not initialize user mic recorder: {e}")
                    self.user_audio_recorder = None
        else:
            print('[INFO] Microphone disabled in configuration')
            self.user_audio_recorder = None

        # Handle speaker if it is not disabled in arguments or yaml file
        if not config['General']['disable_speaker']:
            print('[INFO] Initializing speaker recorder...')
            try:
                self.speaker_audio_recorder = ar.SpeakerRecorder(
                    audio_file_name=f'{data_dir}/logs/speaker.wav'
                )
                if config['General']['speaker_device_index'] != -1:
                    print(f'[INFO] Setting speaker to device index {config["General"]["speaker_device_index"]}')
                    self.speaker_audio_recorder.set_device(index=int(config['General']['speaker_device_index']))
                else:
                    print('[INFO] Using default speaker device')
            except Exception as e:
                logger.warning(f"Could not initialize speaker recorder: {e}")
                self.speaker_audio_recorder = None
        else:
            print('[INFO] Speaker recording disabled in configuration')
            self.speaker_audio_recorder = None

    def set_read_response(self, value: bool):
        """Signal that the response will be read aloud
        """
        self.read_response = value
        self.audio_player_var.read_response = value

    def set_continuous_read(self, value: bool):
        """Toggle continuous read aloud of responses"""
        self.continuous_read = value

    def set_real_time_read(self, value: bool):
        """Toggle real-time read aloud of streaming responses"""
        self.real_time_read = value


# Instantiate a single copy of globals here itself
T_GLOBALS = TranscriptionGlobals()
