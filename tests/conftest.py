import os
import sys

# Add the repository root and the app/transcribe directory to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
APP_DIR = os.path.join(ROOT_DIR, 'app', 'transcribe')
for p in (ROOT_DIR, APP_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)
