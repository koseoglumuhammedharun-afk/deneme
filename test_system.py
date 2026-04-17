# -*- coding: utf-8 -*-
"""
DRONE OBUS TESPIT SISTEMI - SİSTEM KONTROL TESTLERI
Bağımlılık ve sistem durumunu kontrol et
"""

import sys
import os
from pathlib import Path

print("=" * 70)
print("DRONE OBUS TESPIT SISTEMI - SİSTEM KONTROL")
print("=" * 70)

# Test 1: Python versiyonu
print("\n[1] Python Versiyonu Kontrolü")
print(f"    Python: {sys.version.split()[0]}")
if sys.version_info >= (3, 8):
    print("    ✓ BAŞARILI - Python 3.8+")
else:
    print("    ✗ BAŞARISIZ - Python 3.8+ gerekli")
    sys.exit(1)

# Test 2: Temel kütüphaneler
print("\n[2] Temel Kütüphaneler")
test_imports = {
    "numpy": "NumPy",
    "cv2": "OpenCV",
    "torch": "PyTorch",
    "PyQt5": "PyQt5",
    "pandas": "Pandas",
    "openpyxl": "OpenPyXL",
    "exifread": "ExifRead",
    "ultralytics": "YOLOv8"
}

import_success = True
for module_name, display_name in test_imports.items():
    try:
        if module_name == "PyQt5":
            from PyQt5 import QtWidgets
            print(f"    ✓ {display_name}: OK")
        else:
            __import__(module_name)
            print(f"    ✓ {display_name}: OK")
    except ImportError as e:
        print(f"    ✗ {display_name}: BAŞARISIZ ({str(e)[:50]})")
        import_success = False

if not import_success:
    print("\n    ⚠ Bazı kütüphaneler yüklenmemiş!")
    sys.exit(1)

# Test 3: Versiyon Uyumluluğu
print("\n[3] Versiyon Uyumluluğu")
import numpy
import cv2
import torch

print(f"    NumPy: {numpy.__version__}")
if numpy.__version__.startswith("1."):
    print("    ✓ NumPy 1.x (uyumlu)")
else:
    print("    ⚠ NumPy 2.x (kontrol et)")

print(f"    OpenCV: {cv2.__version__}")
if cv2.__version__ >= "4.10":
    print("    ✓ OpenCV 4.10+ (uyumlu)")
else:
    print("    ⚠ OpenCV eski versiyon")

print(f"    PyTorch: {torch.__version__}")
print(f"    ✓ PyTorch yüklü")

# Test 4: Proje Yapısı
print("\n[4] Proje Yapısı Kontrolü")
project_root = Path(__file__).parent
required_files = [
    "main.py",
    "config.py",
    "requirements.txt",
    "src/__init__.py",
    "src/detector.py",
    "src/metadata_extractor.py",
    "src/report_generator.py",
    "src/utils.py",
]

files_ok = True
for file_path in required_files:
    full_path = project_root / file_path
    if full_path.exists():
        print(f"    ✓ {file_path}")
    else:
        print(f"    ✗ {file_path} - BULUNAMADI")
        files_ok = False

if not files_ok:
    print("\n    ✗ Bazı dosyalar eksik!")
    sys.exit(1)

# Test 5: Modül Importunları
print("\n[5] Kaynak Modülleri")
try:
    from src import HowitzerDetector, MetadataExtractor, ReportGenerator, ModelTrainer
    print(f"    ✓ HowitzerDetector: OK")
    print(f"    ✓ MetadataExtractor: OK")
    print(f"    ✓ ReportGenerator: OK")
    print(f"    ✓ ModelTrainer: OK")
except ImportError as e:
    print(f"    ✗ Modül import hatası: {e}")
    sys.exit(1)

# Test 6: Konfigürasyon
print("\n[6] Konfigürasyon Kontrolü")
import config
print(f"    Project Root: {config.PROJECT_ROOT}")
print(f"    Model Path: {config.MODEL_PATH}")
print(f"    Output Dir: {config.OUTPUTS_DIR}")
print(f"    ✓ Konfigürasyon yüklü")

# Test 7: Dizin Varlığı
print("\n[7] Gerekli Dizinler")
required_dirs = [
    config.PROJECT_ROOT / "models",
    config.PROJECT_ROOT / "outputs",
    config.PROJECT_ROOT / "src",
]

for dir_path in required_dirs:
    if dir_path.exists():
        print(f"    ✓ {dir_path.name}/")
    else:
        print(f"    ✗ {dir_path.name}/ - BULUNAMADI")

# Test 8: Syntax Kontrolü
print("\n[8] Python Syntax Kontrolü")
try:
    import py_compile
    py_compile.compile(str(project_root / "main.py"), doraise=True)
    print(f"    ✓ main.py syntax: OK")
except py_compile.PyCompileError as e:
    print(f"    ✗ main.py syntax hatası: {e}")
    sys.exit(1)

# Sonuç
print("\n" + "=" * 70)
print("✓ SİSTEM KONTROL BAŞARILI - UYGULAMA ÇALIŞMAYA HAZIR")
print("=" * 70)
print("\nUygulamayı başlatmak için:")
print("  python main.py")
print("=" * 70)
