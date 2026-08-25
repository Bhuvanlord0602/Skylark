"""Root Streamlit entrypoint for Streamlit Community Cloud."""

import os
import sys
from pathlib import Path

# Ensure root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Execute main UI application
from ui.streamlit_app import *
