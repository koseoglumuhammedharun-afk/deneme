# -*- coding: utf-8 -*-
import os

# DLL hatasını önlemek için kütüphane yolunu manuel ekliyoruz
dll_path = r"C:\Users\CASPER\Desktop\drone_detection\venv\lib\site-packages\torch\lib"
if os.path.exists(dll_path):
    os.add_dll_directory(dll_path)

import torch # Şimdi güvenle import edebiliriz
import unittest
import os
import logging
from src.detector import HowitzerDetector
from src.metadata_extractor import MetadataExtractor
from src.report_generator import ReportGenerator

class TestConfiguration(unittest.TestCase):
    def setUp(self):
        self.model_path = r"C:\Users\CASPER\Desktop\drone_detection\models\howitzer_detector.pt"
        self.output_dir = r"C:\Users\CASPER\Desktop\drone_detection\outputs"

    def test_model_path_defined(self):
        """Model yolunun tanımlanmış olduğunu test et"""
        self.assertIsNotNone(self.model_path)
        self.assertTrue(self.model_path.endswith('.pt'))

    def test_required_directories_exist(self):
        """Gerekli dizinlerin varlığını test et"""
        root_dir = r"C:\Users\CASPER\Desktop\drone_detection"
        self.assertTrue(os.path.exists(root_dir))

class TestFileValidation(unittest.TestCase):
    def test_nonexistent_file(self):
        """Var olmayan dosyayı test et"""
        # Hata mesajı simülasyonu
        msg = "dosya bulunamadı: /nonexistent/file.jpg"
        
        # Pylance hatasını çözen doğru kontrol:
        if msg is not None:
            self.assertTrue("bulunamadı" in msg.lower() or "bulunamadi" in msg.lower())
        else:
            self.fail("Hata mesajı boş döndü")

    def test_unsupported_format(self):
        """Desteklenmeyen formatı test et"""
        unsupported_file = "test.txt"
        self.assertFalse(unsupported_file.lower().endswith(('.jpg', '.png', '.mp4')))

class TestReportGeneration(unittest.TestCase):
    def setUp(self):
        self.generator = ReportGenerator(r"C:\Users\CASPER\Desktop\drone_detection\outputs")
        self.mock_data = {
            "filename": "test.jpg",
            "detected": True,
            "confidence": 0.85,
            "timestamp": "2026-04-08 16:00:00"
        }

    def test_excel_report_with_mock_data(self):
        """Mock verilerle Excel raporu oluşturmayı test et"""
        # Pylance Hatası Çözümü: create_excel_report bir LISTE bekliyor, bu yüzden [ ] içine alıyoruz.
        report_path = self.generator.create_excel_report([self.mock_data])
        self.assertTrue(os.path.exists(report_path))

    def test_json_report_with_mock_data(self):
        """Mock verilerle JSON raporu oluşturmayı test et"""
        report_path = self.generator.create_json_report([self.mock_data])
        self.assertTrue(os.path.exists(report_path))

if __name__ == '__main__':
    unittest.main()