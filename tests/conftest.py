import sys
from pathlib import Path

# Ensure project root and app/transcribe are on path
ROOT = Path(__file__).resolve().parents[1]
APP_TRANSCRIBE = ROOT / 'app' / 'transcribe'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(APP_TRANSCRIBE) not in sys.path:
    sys.path.insert(0, str(APP_TRANSCRIBE))

