# -*- coding: utf-8 -*-
"""
Drone Obüs Tespit Sistemi - Basitleştirilmiş Test Sürümü
Bu dosya bağımlılıkları test etmek için kullanılır
"""

import sys
from pathlib import Path

print("=" * 60)
print("🔍 BAĞIMLILIKLARI TEST ETME")
print("=" * 60)

# Test 1: Python versiyonu
print(f"\n✓ Python sürümü: {sys.version}")

# Test 2: Temel paketler
packages = {
    "numpy": "NumPy (sayısal hesaplama)",
    "cv2": "OpenCV (video/resim işleme)",
    "PIL": "Pillow (resim işleme)",
    "pandas": "Pandas (veri analizi)",
    "openpyxl": "Openpyxl (Excel yazma)",
}

print("\n📦 Temel paketler kontrol ediliyor...")
installed = 0
failed = []

for module, name in packages.items():
    try:
        __import__(module)
        print(f"  ✓ {name:30} YÜKLÜ")
        installed += 1
    except ImportError:
        print(f"  ✗ {name:30} EKSIK")
        failed.append(module)

# Test 3: PyQt5
print("\n🎨 GUI Paketleri kontrol ediliyor...")
try:
    from PyQt5.QtWidgets import QApplication
    print(f"  ✓ PyQt5 (GUI çerçevesi)      YÜKLÜ")
    installed += 1
except ImportError:
    print(f"  ✗ PyQt5 (GUI çerçevesi)      EKSIK")
    failed.append("PyQt5")

# Test 4: Torch (isteğe bağlı)
print("\n🤖 YOLOv8 Paketleri kontrol ediliyor...")
try:
    import torch
    print(f"  ✓ Torch (derin öğrenme)      YÜKLÜ")
    installed += 1
except ImportError:
    print(f"  ⚠ Torch (derin öğrenme)      UYARI - YüklenmeyeBİLİR")
    # Bu opsiyonel

try:
    from ultralytics import YOLO
    print(f"  ✓ Ultralytics (YOLOv8)       YÜKLÜ")
    installed += 1
except ImportError:
    print(f"  ✗ Ultralytics (YOLOv8)       EKSIK")
    failed.append("ultralytics")

# Test 5: Diğer paketler
print("\n📄 Diğer paketler kontrol ediliyor...")
try:
    import exifread
    print(f"  ✓ Exifread (EXIF verisi)     YÜKLÜ")
    installed += 1
except ImportError:
    print(f"  ✗ Exifread (EXIF verisi)     EKSIK")
    failed.append("exifread")

# Sonuç
print("\n" + "=" * 60)
print(f"📊 SONUÇ: {installed} paket yüklü")
print("=" * 60)

if not failed:
    print("\n✅ TÜM BAĞIMLILIKLARI YÜKLÜ! Uygulamayı çalıştırabilirsiniz:")
    print("\n  python main.py")
else:
    print(f"\n❌ {len(failed)} PAKET EKSİK:")
    for pkg in failed:
        print(f"  - {pkg}")
    print("\nEksik paketleri yüklemek için çalıştırın:")
    print(f"\n  pip install {' '.join(failed)}")

print("\n" + "=" * 60)
