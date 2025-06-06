import os
import subprocess
import unittest
import platform


def in_wsl():
    return 'microsoft' in platform.uname().release.lower() or 'WSL_DISTRO_NAME' in os.environ


@unittest.skipUnless(in_wsl(), 'WSL environment required')
class TestWSLAudioSetup(unittest.TestCase):
    """Tests for WSL audio configuration."""

    def test_loopback_available(self):
        """Check that the loopback device is present."""
        if os.environ.get('CI'):  # Simplified check for CI environment
            result = subprocess.run(['lsmod'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn('snd_aloop', result.stdout)
        else:
            result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn('Loopback', result.stdout)

    def test_record_and_play_silence(self):
        """Record and play a short silence on the loopback device."""
        if os.environ.get('CI'):
            self.skipTest('Skip recording test in CI')
        subprocess.run(['arecord', '-d', '1', 'test.wav', '-D', 'hw:Loopback,0,0'], check=True)
        subprocess.run(['aplay', '-D', 'hw:Loopback,1,0', 'test.wav'], check=True)
        os.remove('test.wav')


if __name__ == '__main__':
    unittest.main()
