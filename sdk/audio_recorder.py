import sys
import os
import queue
import time
import wave
from datetime import datetime
from abc import abstractmethod

import logging
import pyaudio
import custom_speech_recognition as sr
from tsutils import app_logging as al
from tsutils import configuration  # noqa: E402 pylint: disable=C0413

sys.path.append('../..')

ENERGY_THRESHOLD = 1000
DYNAMIC_ENERGY_THRESHOLD = False

logger = al.get_module_logger(al.AUDIO_RECORDER_LOGGER)

# Mapping of driver types
# https://people.csail.mit.edu/hubert/pyaudio/docs/#id6
DRIVER_TYPE = {
    -1: 'Not actually an audio device',
    0: 'Still in development',
    1: 'DirectSound (Windows only)',
    2: 'Multimedia Extension (Windows only)',
    3: 'Steinberg Audio Stream Input/Output',
    4: 'SoundManager (OSX only)',
    5: 'CoreAudio (OSX only)',
    7: 'Open Sound System (Linux only)',
    8: 'Advanced Linux Sound Architecture (Linux only)',
    9: 'Open Audio Library',
    10: 'BeOS Sound System',
    11: 'Windows Driver Model (Windows only)',
    12: 'JACK Audio Connection Kit',
    13: 'Windows Vista Audio stack architecture'
}


def list_audio_devices():
    """Return lists of available input and output audio devices."""
    pa = pyaudio.PyAudio()
    input_devices = []
    output_devices = []
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        name = info.get('name')
        if info.get('maxInputChannels', 0) > 0:
            input_devices.append((i, name))
        if info.get('maxOutputChannels', 0) > 0:
            output_devices.append((i, name))
    logging.info("Available input devices: %s", input_devices)
    logging.info("Available output devices: %s", output_devices)
    pa.terminate()
    return input_devices, output_devices


def print_detailed_audio_info(print_func=print):
    """
    Print information about Host APIs and devices using the provided print function.

    :param print_func: Print function or wrapper
    :type print_func: function
    :rtype: None
    """
    print_func("\n|", "~ Audio Drivers on this machine ~".center(20), "|\n")
    header = f" ^ #{'INDEX'.center(7)}#{'DRIVER TYPE'.center(13)}#{'DEVICE COUNT'.center(15)}#{'NAME'.center(5)}"
    print_func(header)
    print_func("-"*len(header))
    py_audio = pyaudio.PyAudio()

    for host_api in py_audio.get_host_api_info_generator():
        print_func(
            (
                f" » "
                f"{('['+str(host_api['index'])+']').center(8)}|"
                f"{str(host_api['type']).center(13)}|"
                f"{str(host_api['deviceCount']).center(15)}|"
                f"  {host_api['name']}"
            )
        )

    print_func("\n\n\n|", "~ Audio Devices on this machine ~".center(20), "|\n")
    header = f" ^ #{'INDEX'.center(7)}# HOST API INDEX #{'LOOPBACK'.center(10)}#{'NAME'.center(5)}"
    print_func(header)
    print_func("-"*len(header))

    for device in py_audio.get_device_info_generator():
        print_func(
            (
                f" » "
                f"{('['+str(device['index'])+']').center(8)}"
                f"{str(device['hostApi']).center(16)}"
                f"  {str(device['isLoopbackDevice']).center(10)}"
                f"  {device['name']}"
            )
        )

    # Below statements are useful to view all available fields in the
    # driver and device list
    # Do not remove these statements from here
    # print('Windows Audio Drivers')
    # for host_api_info_gen in py_audio.get_host_api_info_generator():
    #    print(host_api_info_gen)

    # print('Windows Audio Devices')
    # for device_info_gen in py_audio.get_device_info_generator():
    #    print(device_info_gen)


class BaseRecorder:
    """Base class for Speaker, Microphone classes
    """

    def __init__(self, source, source_name, audio_file_name: str = None):
        logger.info(BaseRecorder.__name__)
        self.recorder = sr.Recognizer()
        self.recorder.energy_threshold = ENERGY_THRESHOLD
        self.recorder.dynamic_energy_threshold = DYNAMIC_ENERGY_THRESHOLD
        # Determines if this device is being used for transcription
        self.enabled: bool = True

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source
        self.source_name: str = source_name
        self.config = configuration.Config().data
        self.stop_record_func = None
        self.audio_file_name = audio_file_name
        self._remove_existing_audio_files()

    def _remove_existing_audio_files(self):
        """Remove existing audio files if they exist"""
        if self.audio_file_name and os.path.exists(self.audio_file_name):
            os.remove(self.audio_file_name)
        if self.audio_file_name and os.path.exists(self.audio_file_name + '.bak'):
            os.remove(self.audio_file_name + '.bak')

    @abstractmethod
    def get_name(self):
        """Get the name of this device
        """

    def enable(self):
        """Enable transcription from this device
        """
        self.enabled = True

    def disable(self):
        """Disable transcription from this device
        """
        self.enabled = False

    def adjust_for_noise(self, device_name, msg):
        """Adjust based on noise from surroundings.
        """
        logger.info(BaseRecorder.adjust_for_noise.__name__)
        logger.info(f"Adjusting for ambient noise from {device_name}. {msg}")
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)
        logger.info(f"Completed ambient noise adjustment for {device_name}.")

    def record_audio(self, audio_queue: queue.Queue):
        """Start recording audion from the stream and add data to queue
        """
        def record_callback(_, audio: sr.AudioData) -> None:
            if self.enabled:
                data = audio.get_raw_data()
                audio_queue.put((self.source_name, data, datetime.utcnow()))
                if self.audio_file_name:
                    with open(file=self.audio_file_name+'.bak', mode='ab') as file_handle:
                        file_handle.write(data)

        stop_func = self.recorder.listen_in_background(source=self.source,
                                                       source_name=self.source_name,
                                                       callback=record_callback,
                                                       phrase_time_limit=self.config['General']['transcript_audio_duration_seconds'])
        return stop_func

    def write_wav_data_to_file(self) -> str:
        """Write the raw input data into a wave file
        """
        if self.audio_file_name is None:
            return

        if not os.path.exists(self.audio_file_name+'.bak'):
            return

        frame_rate = self.source.SAMPLE_RATE
        sample_width = self.source.SAMPLE_WIDTH
        channels = self.source.channels

        with open(file=self.audio_file_name+'.bak', mode='rb') as input_file_handle:
            data = input_file_handle.read()

        with wave.open(self.audio_file_name, 'wb') as wf:
            # print(f'{datetime.datetime.now()} - Writing speaker data into file: {file_path}')
            wf.setnchannels(channels)    # pylint: disable=E1101
            wf.setsampwidth(sample_width)    # pylint: disable=E1101
            wf.setframerate(frame_rate)    # pylint: disable=E1101
            wf.writeframes(data)    # pylint: disable=E1101
            # print(f'datasize: {len(data)}')
        # print(f'filesize: {os.path.getsize(self.audio_file_name)}')


class MicRecorder(BaseRecorder):
    """Encapsultes the Microphone device audio input
    """
    def __init__(self, source_name='You', audio_file_name: str = None):
        logger.info(MicRecorder.__name__)
        pa = pyaudio.PyAudio()
        try:
            info = pa.get_default_input_device_info()
        except IOError:
            inputs, _ = list_audio_devices()
            if inputs:
                info = pa.get_device_info_by_index(inputs[0][0])
                logging.warning(
                    "No default input device. Falling back to: %s", info["name"]
                )
            else:
                pa.terminate()
                raise RuntimeError("No input audio devices found.")
        self.device_index = info["index"]
        self.device_info = info
        pa.terminate()
        self.source = sr.Microphone(
            device_index=self.device_index,
            sample_rate=int(info["defaultSampleRate"]),
            channels=1,
        )
        super().__init__(
            source=self.source, source_name=source_name, audio_file_name=audio_file_name
        )
        self.adjust_for_noise(
            "Default Mic", "Please make some noise from the Default Mic..."
        )

#    def __init__(self):
#        logger.info(MicRecorder.__name__)
#        with pyaudio.PyAudio() as py_audio:
#             WASAPI is windows specific
#            wasapi_info = py_audio.get_host_api_info_by_type(pyaudio.paWASAPI)
#            self.device_index = wasapi_info["defaultInputDevice"]
#            default_mic = py_audio.get_device_info_by_index(self.device_index)

#        self.device_info = default_mic
#        print(f'default_mic: {default_mic}')

#        source = sr.Microphone(device_index=default_mic["index"],
#                               sample_rate=int(default_mic["defaultSampleRate"]),
#                               channels=1
#                               )
#        self.source = source
#        super().__init__(source=source, source_name="You")
#        logger.info(f'Listening to sound from Microphone: {self.get_name()}')
        # This line is commented because in case of non default microphone it can occasionally take
        # several minutes to execute, thus delaying the start of the application.
#        self.adjust_for_noise("Default Mic", "Please make some noise from the Default Mic...")

    def get_name(self):
        return f'#{self.device_index} - {self.device_info["name"]}'

    def set_device(self, index: int):
        """Set active device based on index.
        """
        logger.info(MicRecorder.set_device.__name__)
        pa = pyaudio.PyAudio()
        self.device_index = index
        mic = pa.get_device_info_by_index(self.device_index)
        pa.terminate()

        # Stop the current stream
        if self.stop_record_func is not None:
            self.stop_record_func(wait_for_stop=False)
            time.sleep(2)
        self.device_info = mic
        self.source = sr.Microphone(device_index=mic["index"],
                                    sample_rate=int(mic["defaultSampleRate"]),
                                    channels=1
                                    )

        logger.info(f'Listening to sound from Microphone: {self.get_name()}')
        self.adjust_for_noise("Mic", "Please make some noise from the chosen Mic...")


class SpeakerRecorder(BaseRecorder):
    """Encapsultes the Speaer device audio input
    """
    def __init__(self, source_name='Speaker', audio_file_name: str = None):
        logger.info(SpeakerRecorder.__name__)
        pa = pyaudio.PyAudio()
        
        # Check if we're on Windows (WASAPI available) or Linux/WSL
        try:
            wasapi_inf = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            self.device_index = wasapi_inf["defaultOutputDevice"]
            default_speakers = pa.get_device_info_by_index(self.device_index)
            is_windows = True
        except Exception:
            # On Linux/WSL, try to find a suitable loopback device
            is_windows = False
            default_speakers = None
            
            # Look for PulseAudio monitor devices (Linux loopback equivalent)
            for i in range(pa.get_device_count()):
                device_info = pa.get_device_info_by_index(i)
                device_name = device_info.get('name', '').lower()
                
                # Look for monitor devices which are Linux equivalent of loopback
                if ('monitor' in device_name or 'loopback' in device_name) and \
                   device_info.get('maxInputChannels', 0) > 0:
                    default_speakers = device_info
                    self.device_index = i
                    logger.info(f"Found monitor device for speaker recording: {device_info['name']}")
                    break
            
            if default_speakers is None:
                # Fallback to any output device with input capabilities
                _, outputs = list_audio_devices()
                if outputs:
                    self.device_index = outputs[0][0]
                    default_speakers = pa.get_device_info_by_index(self.device_index)
                    logging.warning(
                        "No monitor device found. Using fallback speaker device: %s. "
                        "Speaker recording may not work properly on WSL/Linux without PulseAudio monitor.",
                        default_speakers["name"],
                    )
                else:
                    pa.terminate()
                    raise RuntimeError("No suitable audio devices found for speaker recording.")

        # Only try Windows-specific loopback if on Windows
        if is_windows and not default_speakers.get("isLoopbackDevice"):
            try:
                for loopback in pa.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        default_speakers = loopback
                        break
                else:
                    logger.error("No loopback device found.")
            except AttributeError:
                # get_loopback_device_info_generator doesn't exist on this platform
                logger.warning("Loopback device enumeration not available on this platform.")
                
        self.device_info = default_speakers
        pa.terminate()

        # Set up appropriate parameters based on device capabilities
        max_input_channels = default_speakers.get("maxInputChannels", 1)
        if max_input_channels == 0:
            max_input_channels = 1  # Fallback for devices reporting 0 input channels
            
        source = sr.Microphone(
            speaker=True,
            device_index=default_speakers["index"],
            sample_rate=int(default_speakers["defaultSampleRate"]),
            chunk_size=pyaudio.get_sample_size(pyaudio.paInt16),
            channels=min(max_input_channels, 2),  # Limit to stereo max
        )

        super().__init__(source=source, source_name=source_name, audio_file_name=audio_file_name)
        logger.info(f'Listening to sound from Speaker: {self.get_name()}')
        # On some devices, speaker adjustment is very slow unless some noise is
        # made from the speakers, though capturing of speaker output is very
        # good in almost all instances I have seen thus far.
        # self.adjust_for_noise("Default Speaker",
        #                       "Please play sound from Default Speaker...")

    def get_name(self):
        return f'#{self.device_index} - {self.device_info["name"]}'

    def set_device(self, index: int):
        """Set active device based on index.
        """
        logger.info(SpeakerRecorder.set_device.__name__)
        pa = pyaudio.PyAudio()
        self.device_index = index
        speakers = pa.get_device_info_by_index(self.device_index)

        # Check for Windows loopback only if on Windows
        try:
            # Test if we have WASAPI (Windows)
            pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            is_windows = True
        except Exception:
            is_windows = False

        if is_windows and not speakers.get("isLoopbackDevice"):
            try:
                for loopback in pa.get_loopback_device_info_generator():
                    if speakers["name"] in loopback["name"]:
                        speakers = loopback
                        break
                else:
                    logger.error("No loopback device found.")
            except AttributeError:
                logger.warning("Loopback device enumeration not available on this platform.")
        pa.terminate()

        # Stop the current stream
        if self.stop_record_func is not None:
            self.stop_record_func(wait_for_stop=False)
            time.sleep(2)

        self.device_info = speakers
        max_input_channels = speakers.get("maxInputChannels", 1)
        if max_input_channels == 0:
            max_input_channels = 1
            
        self.source = sr.Microphone(speaker=True,
                                    device_index=speakers["index"],
                                    sample_rate=int(speakers["defaultSampleRate"]),
                                    chunk_size=pyaudio.get_sample_size(pyaudio.paInt16),
                                    channels=min(max_input_channels, 2))

        logger.info(f'Listening to sound from Speaker: {self.get_name()}')
        # self.adjust_for_noise("Speaker",
        #                       f"Please play sound from selected Speakers {self.get_name()}...")


if __name__ == "__main__":
    print_detailed_audio_info()
    pa = pyaudio.PyAudio()
    wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
    print(wasapi_info)
    default_mic = pa.get_device_info_by_index(wasapi_info["defaultInputDevice"])
    print(default_mic)
    pa.terminate()
