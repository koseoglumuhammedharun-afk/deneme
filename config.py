# -*- coding: utf-8 -*-
"""
Drone Obus Tespit Sistemi - Yapilandirma ve Sabitler

Yeni sinif mantigi:
Model artik sadece "obus / nora_b52 / zuzana" seklinde 3 ana sinifla calismaz.

Yeni sistemde model parcalari tespit eder:
- govde
- namlu
- piston
- ayak

Ancak her parca hangi silaha ait oldugunu da tasir:
- nora_b52_govde
- zuzana_namlu
- obus_piston

Boylece model parcayi yakaladiginda sistem ana silah tipini de anlayabilir.
"""

from pathlib import Path

# Proje yollari
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "src"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
TRAINING_DATA_DIR = PROJECT_ROOT / "training_data"

# Klasorlerin var oldugundan emin ol
MODELS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Kullanici feedback / aktif ogrenme klasorleri
FEEDBACK_LOG_PATH = TRAINING_DATA_DIR / "feedback_actions.jsonl"
FEEDBACK_REVIEW_DIR = TRAINING_DATA_DIR / "feedback_review"
FEEDBACK_REJECTED_DIR = TRAINING_DATA_DIR / "feedback_rejected"
FEEDBACK_REFERENCE_DIR = TRAINING_DATA_DIR / "feedback_reference"
FEEDBACK_MANUAL_LABEL_DIR = TRAINING_DATA_DIR / "feedback_manual_label_required"
FEEDBACK_DUPLICATE_DIR = TRAINING_DATA_DIR / "feedback_duplicate_or_unnecessary"

for _feedback_dir in [
    FEEDBACK_REVIEW_DIR,
    FEEDBACK_REJECTED_DIR,
    FEEDBACK_REFERENCE_DIR,
    FEEDBACK_MANUAL_LABEL_DIR,
    FEEDBACK_DUPLICATE_DIR,
]:
    _feedback_dir.mkdir(parents=True, exist_ok=True)


# YOLOv8 model yapilandirmasi
MODEL_PATH = str(MODELS_DIR / "howitzer_detector.pt")  # Egitimden sonra best model buraya kopyalanir
# Varsayilan analiz esigi. Testlerde parca yakalamayi kacirmamak icin dusuk tutuldu.
# Arayuz slider'i %0'a kadar iner; %0 secilirse YOLO'ya MIN_MODEL_CONFIDENCE gider.
CONFIDENCE_THRESHOLD = 0.05
DEFAULT_CONFIDENCE_MIN = 0.0
DEFAULT_CONFIDENCE_MAX = 0.95
MIN_MODEL_CONFIDENCE = 0.001

# Parca tabanli karar esikleri
SUSPICIOUS_CONFIDENCE_THRESHOLD = 0.05
STRONG_CONFIDENCE_THRESHOLD = 0.45

# =========================================
# SILAH + PARCA TABANLI COK SINIFLI EGITIM
# =========================================
#
# Label id karsiliklari:
#
# 0  -> nora_b52_govde
# 1  -> nora_b52_namlu
# 2  -> nora_b52_piston
# 3  -> nora_b52_ayak
#
# 4  -> zuzana_govde
# 5  -> zuzana_namlu
# 6  -> zuzana_piston
# 7  -> zuzana_ayak
#
# 8  -> obus_govde
# 9  -> obus_namlu
# 10 -> obus_piston
# 11 -> obus_ayak
#
# ONEMLI:
# Etiketleme uygulamasindaki sinif sirasi ile bu liste birebir ayni olmalidir.
# Aksi halde model yanlis siniflari ogrenir.
# =========================================

WEAPON_TYPES = [
    "nora_b52",
    "zuzana",
    "obus",
]

PART_TYPES = [
    "govde",
    "namlu",
    "piston",
    "ayak",
]

CLASS_NAMES = [
    "nora_b52_govde",
    "nora_b52_namlu",
    "nora_b52_piston",
    "nora_b52_ayak",

    "zuzana_govde",
    "zuzana_namlu",
    "zuzana_piston",
    "zuzana_ayak",

    "obus_govde",
    "obus_namlu",
    "obus_piston",
    "obus_ayak",
]

NUM_CLASSES = len(CLASS_NAMES)

# Ekranda daha okunabilir isim gostermek icin
WEAPON_DISPLAY_NAMES = {
    "nora_b52": "Nora B-52",
    "zuzana": "Zuzana",
    "obus": "Obus",
}

PART_DISPLAY_NAMES = {
    "govde": "Gövde",
    "namlu": "Namlu",
    "piston": "Piston",
    "ayak": "Ayak",
}

CLASS_DISPLAY_NAMES = {
    "nora_b52_govde": "Nora B-52 Gövde",
    "nora_b52_namlu": "Nora B-52 Namlu",
    "nora_b52_piston": "Nora B-52 Piston",
    "nora_b52_ayak": "Nora B-52 Ayak",

    "zuzana_govde": "Zuzana Gövde",
    "zuzana_namlu": "Zuzana Namlu",
    "zuzana_piston": "Zuzana Piston",
    "zuzana_ayak": "Zuzana Ayak",

    "obus_govde": "Obus Gövde",
    "obus_namlu": "Obus Namlu",
    "obus_piston": "Obus Piston",
    "obus_ayak": "Obus Ayak",
}

# Tespit edilen parca sinifindan ana silah tipini bulmak icin
CLASS_TO_WEAPON = {
    "nora_b52_govde": "nora_b52",
    "nora_b52_namlu": "nora_b52",
    "nora_b52_piston": "nora_b52",
    "nora_b52_ayak": "nora_b52",

    "zuzana_govde": "zuzana",
    "zuzana_namlu": "zuzana",
    "zuzana_piston": "zuzana",
    "zuzana_ayak": "zuzana",

    "obus_govde": "obus",
    "obus_namlu": "obus",
    "obus_piston": "obus",
    "obus_ayak": "obus",
}

# Tespit edilen parca sinifindan parca tipini bulmak icin
CLASS_TO_PART = {
    "nora_b52_govde": "govde",
    "nora_b52_namlu": "namlu",
    "nora_b52_piston": "piston",
    "nora_b52_ayak": "ayak",

    "zuzana_govde": "govde",
    "zuzana_namlu": "namlu",
    "zuzana_piston": "piston",
    "zuzana_ayak": "ayak",

    "obus_govde": "govde",
    "obus_namlu": "namlu",
    "obus_piston": "piston",
    "obus_ayak": "ayak",
}


def get_class_display_name(class_name: str) -> str:
    """
    Teknik sinif adini ekranda okunabilir hale getirir.
    """
    return CLASS_DISPLAY_NAMES.get(class_name, class_name)


def get_weapon_from_class(class_name: str) -> str:
    """
    Parca sinifindan ana silah tipini dondurur.

    Ornek:
        zuzana_govde -> zuzana
        nora_b52_namlu -> nora_b52
    """
    return CLASS_TO_WEAPON.get(class_name, class_name)


def get_weapon_display_name(weapon_name: str) -> str:
    """
    Teknik silah adini ekranda okunabilir hale getirir.
    """
    return WEAPON_DISPLAY_NAMES.get(weapon_name, weapon_name)


def get_part_from_class(class_name: str) -> str:
    """
    Parca sinifindan parca adini dondurur.

    Ornek:
        zuzana_govde -> govde
    """
    return CLASS_TO_PART.get(class_name, "")


def get_part_display_name(part_name: str) -> str:
    """
    Teknik parca adini ekranda okunabilir hale getirir.
    """
    return PART_DISPLAY_NAMES.get(part_name, part_name)


def normalize_confidence_threshold(value: float) -> float:
    """
    GUI'den gelen guven esigini model icin guvenli hale getirir.

    Kullanici slider'da %0 secerse ekranda %0 gorunur; fakat YOLO'ya 0.0
    vermek yerine 0.001 gonderilir. Boylece modelin uretebildigi en dusuk
    guvenli kutular da gorunur.
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = CONFIDENCE_THRESHOLD

    if value <= 0:
        return MIN_MODEL_CONFIDENCE

    return max(MIN_MODEL_CONFIDENCE, min(1.0, value))


def get_detection_level(confidence: float) -> str:
    """
    Guven oranindan kullaniciya gosterilecek seviye metnini uretir.
    """
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    if confidence >= STRONG_CONFIDENCE_THRESHOLD:
        return "Güçlü"
    if confidence >= SUSPICIOUS_CONFIDENCE_THRESHOLD:
        return "Şüpheli"
    return "Düşük"


def get_weapon_decision(class_name: str, confidence: float = 0.0) -> str:
    """
    Parca sinifindan analiz karar metni uretir.

    Ornek:
        zuzana_namlu  -> Zuzana şüphesi
        zuzana_govde  -> Zuzana tespiti
        nora_b52_piston -> Nora B-52 şüphesi
    """
    weapon_name = get_weapon_from_class(class_name)
    weapon_display = get_weapon_display_name(weapon_name)
    part_name = get_part_from_class(class_name)
    level = get_detection_level(confidence)

    if part_name == "govde":
        return f"{weapon_display} tespiti ({level})"

    if part_name:
        part_display = get_part_display_name(part_name)
        return f"{weapon_display} şüphesi ({part_display}, {level})"

    return f"{weapon_display} şüphesi ({level})"


def get_class_id(class_name: str) -> int:
    """
    Sinif adindan class id dondurur.
    """
    if class_name not in CLASS_NAMES:
        raise ValueError(f"Tanimlanmamis sinif adi: {class_name}")
    return CLASS_NAMES.index(class_name)


# Desteklenen dosya formatlari
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

# GUI sabitleri
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

# GPU ayarlari
USE_GPU = True
GPU_DEVICE = 0  # Birincil GPU cihazi

print(f"Model yolu yapılandırıldı: {MODEL_PATH}")
print(f"Çıktı dizini: {OUTPUTS_DIR}")
print(f"Egitim veri dizini: {TRAINING_DATA_DIR}")
print(f"Siniflar: {CLASS_NAMES}")
print(f"Sinif sayisi: {NUM_CLASSES}")