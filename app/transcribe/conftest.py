import os
import sys

TEST_DIR = os.path.dirname(__file__)
# Add transcribe package and project root for imports
sys.path.insert(0, os.path.abspath(TEST_DIR))
sys.path.insert(0, os.path.abspath(os.path.join(TEST_DIR, '..')))
sys.path.insert(0, os.path.abspath(os.path.join(TEST_DIR, '..', '..')))
