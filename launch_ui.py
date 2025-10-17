#!/usr/bin/env python3
"""
Convenient launcher for the Gradio UI.
Usage: python launch_ui.py [--share] [--port PORT] [--host HOST]
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gradio_app import main

if __name__ == "__main__":
    main()
