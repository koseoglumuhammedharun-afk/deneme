# -*- coding: utf-8 -*-
"""
Dosya işleme, doğrulama ve günlük kaydı için yardımcı işlevler
"""

import sys
import logging
from pathlib import Path
from typing import Tuple, Optional

import cv2
import numpy as np
from PIL import Image

import config

RESAMPLE_FILTER = Image.Resampling.LANCZOS


def setup_logging(name: str = "HowitzerDetector") -> logging.Logger:
    """Günlük kaydı yapılandırmasını ayarla"""
    logger = logging.getLogger(name)
    logger.setLevel(config.LOG_LEVEL)
    logger.propagate = False

    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(config.LOG_LEVEL)
        formatter = logging.Formatter(config.LOG_FORMAT)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


logger = setup_logging()


def validate_file(file_path: str) -> Tuple[bool, str]:
    """
    Dosyanın var olup olmadığını ve desteklenip desteklenmediğini doğrula

    Args:
        file_path: Dosyanın yolu

    Returns:
        Tuple[bool, str]: (geçerli_mi, hata_mesajı)
    """
    path = Path(file_path)

    if not path.exists():
        return False, f"Dosya bulunamadı: {file_path}"

    if not path.is_file():
        return False, f"Yol bir dosya değil: {file_path}"

    if path.suffix.lower() not in config.SUPPORTED_FORMATS:
        supported = ", ".join(config.SUPPORTED_FORMATS)
        return False, f"Desteklenmeyen dosya formatı. Desteklenenler: {supported}"

    file_size_mb = path.stat().st_size / (1024 * 1024)

    if path.suffix.lower() in config.SUPPORTED_IMAGE_FORMATS:
        max_size = config.MAX_IMAGE_SIZE_MB
    else:
        max_size = config.MAX_VIDEO_SIZE_MB

    if file_size_mb > max_size:
        return False, f"Dosya çok büyük: {file_size_mb:.1f}MB (maksimum {max_size}MB)"

    return True, ""


def get_image_preview(
    image_path: str,
    size: Optional[Tuple[int, int]] = None
) -> Optional[Image.Image]:
    """
    Resim küçük resmini almak için ön izleme

    Args:
        image_path: Resim dosyasının yolu
        size: Küçük resim boyutu (genişlik, yükseklik)

    Returns:
        PIL Image veya başarısız olursa None
    """
    try:
        if size is None:
            size = config.THUMBNAIL_SIZE

        img = Image.open(image_path)
        img.thumbnail(size, RESAMPLE_FILTER)
        return img

    except Exception as e:
        logger.error(f"Resim ön izlemesi oluşturma hatası: {e}")
        return None


def get_video_first_frame(
    video_path: str,
    size: Optional[Tuple[int, int]] = None
) -> Optional[Image.Image]:
    """
    Videodan ilk frame çıkar

    Args:
        video_path: Video dosyasının yolu
        size: Küçük resim boyutu (genişlik, yükseklik)

    Returns:
        PIL Image veya başarısız olursa None
    """
    cap = None

    try:
        if size is None:
            size = config.THUMBNAIL_SIZE

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Video açılamadı: {video_path}")
            return None

        ret, frame = cap.read()
        if not ret or frame is None:
            logger.error(f"Videodan ilk frame okunamadı: {video_path}")
            return None

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img.thumbnail(size, RESAMPLE_FILTER)
        return img

    except Exception as e:
        logger.error(f"Video ön izlemesi oluşturma hatası: {e}")
        return None

    finally:
        if cap is not None:
            cap.release()


def get_file_preview(
    file_path: str,
    size: Optional[Tuple[int, int]] = None
) -> Optional[Image.Image]:
    """
    Desteklenen herhangi bir dosya için ön izleme (küçük resim veya ilk frame) al

    Args:
        file_path: Dosyanın yolu
        size: Ön izleme boyutu

    Returns:
        PIL Image veya None
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in config.SUPPORTED_IMAGE_FORMATS:
        return get_image_preview(file_path, size)

    if suffix in config.SUPPORTED_VIDEO_FORMATS:
        return get_video_first_frame(file_path, size)

    return None


def save_image(image, file_path: str) -> bool:
    """
    PIL görüntüsünü veya numpy dizisini dosyaya kaydet

    Args:
        image: PIL Image veya np.ndarray
        file_path: Çıktı yolu

    Returns:
        bool: Başarı durumu
    """
    try:
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(image, Image.Image):
            image.save(str(output_path))
        elif isinstance(image, np.ndarray):
            success = cv2.imwrite(str(output_path), image)
            if not success:
                raise ValueError("cv2.imwrite başarısız oldu")
        else:
            raise TypeError(f"Desteklenmeyen görüntü tipi: {type(image)}")

        logger.info(f"Resim kaydedildi: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Resim kaydetme hatası: {e}")
        return False


def format_timestamp(timestamp_str: str) -> str:
    """Zaman damgası dizesini biçimlendir"""
    return timestamp_str if timestamp_str else "N/A"


def seconds_to_mmss(seconds: float) -> str:
    """
    Saniyeleri DD:SS formatına dönüştür

    Args:
        seconds: Saniye değeri

    Returns:
        str: Biçimlendirilmiş DD:SS dizesi
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def frames_to_mmss(frame_number: int, fps: float) -> str:
    """
    Frame numarasını DD:SS formatına dönüştür

    Args:
        frame_number: Frame indeksi
        fps: Saniye başına frame sayısı

    Returns:
        str: Biçimlendirilmiş DD:SS dizesi
    """
    if fps == 0:
        return "00:00"

    seconds = frame_number / fps
    return seconds_to_mmss(seconds)


def ensure_output_directory() -> Path:
    """Çıktı dizininin var olduğundan emin ol ve yolunu döndür"""
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    return config.OUTPUTS_DIR