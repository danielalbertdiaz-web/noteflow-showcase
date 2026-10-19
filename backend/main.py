"""
NoteFlow backend entry point.
Works from repo root via `uvicorn backend.main:app`
"""

import sys
import os

# Add backend/ to Python path so `from app.xxx` imports work
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app  # noqa: F401, E402
