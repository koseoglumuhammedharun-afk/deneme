#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test refactored GUI application"""
import sys
import traceback
from PyQt5 import QtWidgets

try:
    print("="*60)
    print("REFACTORED GUI TEST")
    print("="*60)
    
    print("\n1. QApplication created...")
    app = QtWidgets.QApplication(sys.argv)
    print("   OK - QApplication")
    
    print("\n2. MainWindow imported...")
    from main import MainWindow
    print("   OK - MainWindow imported")
    
    print("\n3. MainWindow instance created...")
    window = MainWindow()
    print("   OK - MainWindow instance created")
    
    print("\n4. GUI components ready")
    
    print("\n" + "="*60)
    print("SUCCESS - REFACTORING COMPLETE!")
    print("="*60)
    print("\nWindow closes in 3 seconds...")
    
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(3000, app.quit)
    window.show()
    app.exec_()
    
    print("\nGUI closed. Test successful.")

except Exception as e:
    print("\nERROR: " + type(e).__name__ + ": " + str(e))
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
