#!/usr/bin/env python3
"""
Main entry point for GUI interface
"""

import sys
import os

# Add the parent directory to Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.gui.app import ZenodoUploaderApp
from PyQt6.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)
    window = ZenodoUploaderApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()