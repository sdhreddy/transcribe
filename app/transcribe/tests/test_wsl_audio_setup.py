import os
import subprocess
import unittest
import platform


def in_wsl():
    return 'microsoft' in platform.uname().release.lower() or 'WSL_DISTRO_NAME' in os.environ


@unittest.skipUnless(in_wsl(), 'WSL environment required')
class TestWSLAudioSetup(unittest.TestCase):
    """Tests for WSL audio configuration without snd_aloop."""

    def test_pulseaudio_running(self):
        """Ensure PulseAudio daemon is running."""
        if os.environ.get('CI'):
            self.skipTest('Skip PulseAudio check in CI')
        result = subprocess.run(['pulseaudio', '--check'])
        self.assertEqual(result.returncode, 0)

    def test_sources_and_sinks_present(self):
        """PulseAudio should list at least one source and sink."""
        if os.environ.get('CI'):
            self.skipTest('Skip PulseAudio check in CI')
        sources = subprocess.check_output(['pactl', 'list', 'sources']).decode()
        sinks = subprocess.check_output(['pactl', 'list', 'sinks']).decode()
        self.assertTrue(len(sources.strip()) > 0)
        self.assertTrue(len(sinks.strip()) > 0)


if __name__ == '__main__':
    unittest.main()
