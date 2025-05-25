"""Database package initialization with path adjustments."""
from __future__ import annotations

import os
import sys

PARENT_DIR = os.path.dirname(os.path.dirname(__file__))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from db.app_db import AppDB


DB_CONTEXT = AppDB()
