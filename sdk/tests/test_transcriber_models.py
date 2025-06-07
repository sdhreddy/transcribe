import unittest
from unittest.mock import patch, mock_open, MagicMock

from sdk.transcriber_models import WhisperSTTModel

class TestDownloadModel(unittest.TestCase):
    def _base_config(self):
        return {
            'local_transcription_model_file': 'tiny',
            'audio_lang': 'en',
            'api_key': 'dummy'
        }

    @patch('sdk.transcriber_models.whisper.load_model')
    @patch('sdk.transcriber_models.platform.system', return_value='Windows')
    @patch('sdk.transcriber_models.utilities.download_using_bits')
    @patch('os.path.exists', return_value=False)
    @patch('sdk.transcriber_models.utilities.ensure_directory_exists')
    def test_windows_uses_bits(self, mock_ensure, mock_exists, mock_bits, mock_system, mock_whisper):
        WhisperSTTModel(self._base_config())
        mock_bits.assert_called()
        mock_whisper.assert_called()

    def test_non_windows_uses_requests(self):
        response = MagicMock()
        response.iter_content.return_value = [b'data']
        response.raise_for_status = MagicMock()
        with patch('os.path.exists', return_value=False), \
             patch('sdk.transcriber_models.utilities.ensure_directory_exists'), \
             patch('sdk.transcriber_models.platform.system', return_value='Linux'), \
             patch('requests.get', return_value=response) as mock_get, \
             patch('builtins.open', new_callable=mock_open) as mock_open_fn, \
             patch('sdk.transcriber_models.whisper.load_model') as mock_whisper:
            WhisperSTTModel(self._base_config())
            mock_get.assert_called()
            mock_open_fn.assert_called()
            mock_whisper.assert_called()

    @patch('sdk.transcriber_models.whisper.load_model')
    @patch('os.path.exists', return_value=True)
    def test_existing_file_skips_download(self, mock_exists, mock_whisper):
        WhisperSTTModel(self._base_config())
        mock_whisper.assert_called()

if __name__ == '__main__':
    unittest.main()
