#!/usr/bin/env python
"""Test the application GUI startup"""
import sys
import traceback
from PyQt5 import QtWidgets

try:
    print("Creating QApplication...")
    app = QtWidgets.QApplication(sys.argv)
    print("QApplication created successfully")
    
    print("Importing MainWindow...")
    from main import MainWindow
    print("MainWindow imported successfully")
    
    print("Creating MainWindow instance...")
    window = MainWindow()
    print("MainWindow instance created successfully")
    
    print("Showing window...")
    window.show()
    print("Window shown successfully")
    
    print("\nGUI launched successfully! About to enter event loop...")
    print("Application ready - GUI is running")
    
except Exception as e:
    print(f"\nError occurred: {type(e).__name__}: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
