import subprocess
import sys
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[:400]


def test_start_package_and_direct():
    run([sys.executable, '-m', 'app.transcribe.main', '--help'])
    run([sys.executable, str(REPO / 'app' / 'transcribe' / 'main.py'), '--help'])
