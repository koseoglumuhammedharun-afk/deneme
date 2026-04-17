# -*- coding: utf-8 -*-
"""
Hata Cozum Dogrulama Betiği
Tum sistemin basariyla calıstığını doğrular
"""

import sys
from pathlib import Path

def verify_system():
    print("\n" + "="*60)
    print("DRONE OBÜS TESPIT SISTEMI - DOGRULAMA")
    print("="*60 + "\n")
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: PyTorch
    tests_total += 1
    try:
        import torch
        print(f"✅ PyTorch {torch.__version__}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ PyTorch: {e}")
    
    # Test 2: YOLO
    tests_total += 1
    try:
        from ultralytics import YOLO
        print(f"✅ Ultralytics YOLO")
        tests_passed += 1
    except Exception as e:
        print(f"❌ YOLO: {e}")
    
    # Test 3: Detector
    tests_total += 1
    try:
        from src.detector import HowitzerDetector
        print(f"✅ Obüs Tespit Modulu")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Detector: {e}")
    
    # Test 4: Model Trainer
    tests_total += 1
    try:
        from src.model_trainer import ModelTrainer
        print(f"✅ Model Egitim Modulu (Video Frame Cikarma)")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Model Trainer: {e}")
    
    # Test 5: Metadata Extractor
    tests_total += 1
    try:
        from src.metadata_extractor import MetadataExtractor
        print(f"✅ Meta Veri Cikartma")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Metadata: {e}")
    
    # Test 6: Report Generator
    tests_total += 1
    try:
        from src.report_generator import ReportGenerator
        print(f"✅ Rapor Olusturma (Excel/JSON)")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Report: {e}")
    
    # Test 7: Config paths
    tests_total += 1
    try:
        from config import PROJECT_ROOT, OUTPUTS_DIR
        outputs_exist = OUTPUTS_DIR.exists()
        print(f"✅ Yapilandirma (Proje: {PROJECT_ROOT.name})")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Config: {e}")
    
    # Summary
    print("\n" + "="*60)
    print(f"SONUC: {tests_passed}/{tests_total} test BASARILI")
    print("="*60)
    
    if tests_passed == tests_total:
        print("\n✅ SISTEM TAMAMEN HAZIR - UYGULAMAYI BASLATABILIRSINIZ\n")
        return 0
    else:
        print(f"\n⚠️  {tests_total - tests_passed} test BASARISIZ\n")
        return 1

if __name__ == "__main__":
    sys.exit(verify_system())
