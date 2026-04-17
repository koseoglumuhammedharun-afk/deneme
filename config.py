# -*- coding: utf-8 -*-
"""
Drone Obus Tespit Sistemi - Yapilandirma ve Sabitler
"""

from pathlib import Path

# Proje yolları
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "src"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
TRAINING_DATA_DIR = PROJECT_ROOT / "training_data"

# Klasorlerin var oldugundan emin ol
MODELS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)

# YOLOv8 Model yapilandirmasi
MODEL_PATH = str(MODELS_DIR / "howitzer_detector.pt")  # Egitimden sonra best model buraya kopyalanir
CONFIDENCE_THRESHOLD = 0.25
DEFAULT_CONFIDENCE_MIN = 0.05
DEFAULT_CONFIDENCE_MAX = 0.95

# =========================================
# COK SINIFLI EGITIM AYARLARI
# Label id karsiliklari:
# 0 -> obus
# 1 -> nora_b52
# 2 -> zuzana
# =========================================
CLASS_NAMES = [
    "obus",
    "nora_b52",
    "zuzana",
]
NUM_CLASSES = len(CLASS_NAMES)

# Desteklenen dosya formatları
SUPPORTED_IMAGE_FORMATS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
SUPPORTED_VIDEO_FORMATS = (".mp4", ".avi", ".mov", ".mkv")
SUPPORTED_FORMATS = SUPPORTED_IMAGE_FORMATS + SUPPORTED_VIDEO_FORMATS

# Dosya boyutu limitleri
MAX_IMAGE_SIZE_MB = 100
MAX_VIDEO_SIZE_MB = 500

# Video isleme
VIDEO_SKIP_FRAMES = 1  # 1 = her frame, 2 = her 2. frame, vb.
VIDEO_PROGRESS_UPDATE_INTERVAL = 10  # Her N frame'de ilerleme guncelle

# Varsayilan drone / kamera ozellikleri
DEFAULT_DRONE_ALTITUDE_M = 50
DEFAULT_CAMERA_FOV_EQUIV = 35
DEFAULT_SENSOR_WIDTH_MM = 6.3

# GUI Sabitleri
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900
THUMBNAIL_SIZE = (200, 150)
CROP_PADDING = 50  # Tespit etrafinda piksel padding

# Gunluk
LOG_LEVEL = "INFO"
LOG_FORMAT = "[%(asctime)s] %(levelname)s - %(message)s"

# Rapor olusturma
REPORT_DATE_FORMAT = "%Y-%m-%d"
REPORT_TIME_FORMAT = "%H:%M:%S"
ANALYSIS_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# Excel / JSON
EXCEL_SHEET_NAME = "Analiz Sonuclari"
JSON_INDENT = 2

# GPU Ayarlari
USE_GPU = True
GPU_DEVICE = 0  # Birincil GPU cihazı

print(f"Model yolu yapılandırıldı: {MODEL_PATH}")
print(f"Çıktı dizini: {OUTPUTS_DIR}")
print(f"Egitim veri dizini: {TRAINING_DATA_DIR}")
print(f"Siniflar: {CLASS_NAMES}")
print(f"Sinif sayisi: {NUM_CLASSES}")