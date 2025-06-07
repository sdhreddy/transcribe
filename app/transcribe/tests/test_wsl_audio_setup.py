import subprocess
import pytest
import platform

@pytest.mark.skipif("microsoft-standard" not in platform.uname().release, reason="Only on WSLg")
def test_pulseaudio_running_under_wslg():
    # Verify the PulseAudio daemon is active
    result = subprocess.run(["pulseaudio", "--check"], capture_output=True)
    assert result.returncode == 0

    # List sources and sinks
    sources = subprocess.run(["pactl", "list", "sources"], capture_output=True, text=True)
    assert "Name:" in sources.stdout
    sinks = subprocess.run(["pactl", "list", "sinks"], capture_output=True, text=True)
    assert "Name:" in sinks.stdout
