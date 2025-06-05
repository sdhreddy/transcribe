import unittest
from unittest.mock import patch
import yaml
from tsutils.utilities import (
    merge, incrementing_filename, naturalsize,
    download_using_bits, ensure_directory_exists,
    parse_yaml_bool
)


class TestFunctions(unittest.TestCase):

    def test_merge(self):
        first = {'a': 1, 'b': {'c': 3}}
        second = {'b': {'d': 4}, 'e': 5}
        result = merge(first, second)
        self.assertEqual(result, {'a': 1, 'b': {'c': 3, 'd': 4}, 'e': 5})

    @patch('os.path.exists', side_effect=[True, True, False])
    def test_incrementing_filename(self, mock_exists):
        result = incrementing_filename('file', 'txt')
        self.assertEqual(result, 'file-2.txt')

    def test_naturalsize(self):
        result = naturalsize(3000000)
        self.assertEqual(result, '3.0 MB')
        result = naturalsize(300, False, True)
        self.assertEqual(result, '300.0B', f'Expected 300.0B got {result}')

    @patch('subprocess.check_output')
    def test_download_using_bits(self, mock_subproc):
        download_using_bits('https://github.com/vivekuppal/transcribe/archive/refs/heads/main.zip', 'transcribe.zip')
        mock_subproc.assert_called_once_with(['powershell',
                                              '-NoProfile',
                                              '-ExecutionPolicy',
                                              'Bypass',
                                              '-Command',
                                              'Start-BitsTransfer',
                                              '-Source',
                                              'https://github.com/vivekuppal/transcribe/archive/refs/heads/main.zip',
                                              '-Destination',
                                              'transcribe.zip'])

    @patch('os.makedirs')
    @patch('os.path.exists', return_value=False)
    def test_ensure_directory_exists(self, mock_exists, mock_makedirs):
        ensure_directory_exists('.')
        mock_makedirs.assert_called_once_with('.')

    def test_parse_yaml_bool(self):
        self.assertTrue(parse_yaml_bool('Yes'))
        self.assertTrue(parse_yaml_bool('true'))
        self.assertFalse(parse_yaml_bool('No'))
        self.assertFalse(parse_yaml_bool('false'))
        self.assertTrue(parse_yaml_bool(True))
        self.assertFalse(parse_yaml_bool(False))

    def test_yaml_boolean_types(self):
        yaml_content = """
        General:
          continuous_read: true
          real_time_read: true
          llm_response_interval: 0.5
        """
        data = yaml.safe_load(yaml_content)
        self.assertIsInstance(data['General']['continuous_read'], bool)
        self.assertIsInstance(data['General']['real_time_read'], bool)
        self.assertEqual(data['General']['llm_response_interval'], 0.5)


if __name__ == '__main__':
    unittest.main()
