import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_TRANSCRIBE = ROOT / 'app' / 'transcribe'
APP_DB = APP_TRANSCRIBE / 'db'

for p in [ROOT, APP_TRANSCRIBE, APP_DB]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


