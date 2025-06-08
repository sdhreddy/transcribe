import unittest
import yaml
import tempfile
import os


class TestTTSVolumeConfig(unittest.TestCase):
    def test_tts_volume_setting(self):
        with open('app/transcribe/parameters.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.assertIn('tts_playback_volume', config['General'])
        self.assertGreaterEqual(config['General']['tts_playback_volume'], 0)
        self.assertLessEqual(config['General']['tts_playback_volume'], 1)

        fd, temp_name = tempfile.mkstemp()
        os.close(fd)
        try:
            yaml.dump(config, open(temp_name, 'w', encoding='utf-8'))
            config['General']['tts_playback_volume'] = 0.3
            yaml.dump(config, open(temp_name, 'w', encoding='utf-8'))
            with open(temp_name, 'r', encoding='utf-8') as f:
                updated = yaml.safe_load(f)
            self.assertEqual(updated['General']['tts_playback_volume'], 0.3)
        finally:
            os.remove(temp_name)


if __name__ == '__main__':
    unittest.main()
