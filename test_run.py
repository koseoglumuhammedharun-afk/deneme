#!/usr/bin/env python
"""Test the application startup and capture errors"""
import sys
import traceback

try:
    print("Python version:", sys.version)
    print("Starting main application...")
    
    # Try importing main
    import main
    
    print("Main module imported successfully")
    
except Exception as e:
    print(f"Error occurred: {type(e).__name__}: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
