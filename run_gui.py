#!/usr/bin/env python3
"""
Launcher script for the Attendance Report GUI.
This script provides a simple way to start the PyQt6 desktop application.
"""

import sys
import os


def main():
    """Launch the attendance report GUI application."""
    try:
        # Add current directory to Python path if needed
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)

        # Import and run the GUI
        from gui_pyqt6 import main as gui_main

        gui_main()

    except ImportError as e:
        print(f"❌ Error importing GUI components: {e}")
        print("Make sure PyQt6 is installed: pip install PyQt6")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting GUI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
