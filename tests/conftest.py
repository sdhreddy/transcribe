
import os
import sys

# Add the repository root and the app/transcribe directory to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
APP_DIR = os.path.join(ROOT_DIR, 'app', 'transcribe')
for p in (ROOT_DIR, APP_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import sys
from pathlib import Path

# Ensure project root and app/transcribe are on path
ROOT = Path(__file__).resolve().parents[1]
APP_TRANSCRIBE = ROOT / 'app' / 'transcribe'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(APP_TRANSCRIBE) not in sys.path:
    sys.path.insert(0, str(APP_TRANSCRIBE))


