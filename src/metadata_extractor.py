# -*- coding: utf-8 -*-
"""
Resim ve videodan meta veri çıkarma
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

import cv2

try:
    import exifread
except ImportError:
    exifread = None

import config

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Resim ve videodan meta veriler çıkar"""

    @staticmethod
    def extract_image_metadata(image_path: str) -> Dict:
        """
        Resimden meta veri çıkar (EXIF verileri)

        Returns:
            {
                'capture_date': str | None,
                'capture_time': str | None,
                'gps_latitude': float | None,
                'gps_longitude': float | None,
                'camera_make': str | None,
                'camera_model': str | None,
                'image_width': int | None,
                'image_height': int | None,
                'source': str
            }
        """
        metadata = {
            "capture_date": None,
            "capture_time": None,
            "gps_latitude": None,
            "gps_longitude": None,
            "camera_make": None,
            "camera_model": None,
            "image_width": None,
            "image_height": None,
            "source": "exif",
        }

        try:
            img = cv2.imread(image_path)
            if img is not None:
                h, w = img.shape[:2]
                metadata["image_width"] = w
                metadata["image_height"] = h

            if exifread is None:
                logger.warning("exifread yüklenmedi, dosya zamanı kullanılacak")
                return MetadataExtractor._fallback_metadata(image_path, metadata)

            with open(image_path, "rb") as f:
                tags = exifread.process_file(f, details=False)

            if "EXIF DateTimeOriginal" in tags:
                dt_str = str(tags["EXIF DateTimeOriginal"])
                metadata.update(MetadataExtractor._parse_datetime(dt_str))
            elif "Image DateTime" in tags:
                dt_str = str(tags["Image DateTime"])
                metadata.update(MetadataExtractor._parse_datetime(dt_str))

            gps_lat = MetadataExtractor._extract_gps_latitude(tags)
            gps_lon = MetadataExtractor._extract_gps_longitude(tags)

            if gps_lat is not None:
                metadata["gps_latitude"] = gps_lat
            if gps_lon is not None:
                metadata["gps_longitude"] = gps_lon

            if "Image Make" in tags:
                metadata["camera_make"] = str(tags["Image Make"])
            if "Image Model" in tags:
                metadata["camera_model"] = str(tags["Image Model"])

            if metadata["capture_date"] is None:
                return MetadataExtractor._fallback_metadata(image_path, metadata)

            logger.info(
                f"Resim meta verisi çıkarıldı: {metadata['capture_date']} {metadata['capture_time']}"
            )
            return metadata

        except Exception as e:
            logger.warning(f"EXIF çıkarma hatası: {e}, dosya zamanı kullanılacak")
            return MetadataExtractor._fallback_metadata(image_path, metadata)

    @staticmethod
    def extract_video_metadata(video_path: str) -> Dict:
        """
        Video dosyasından meta veri çıkar

        Returns:
            {
                'capture_date': str | None,
                'capture_time': str | None,
                'gps_latitude': None,
                'gps_longitude': None,
                'fps': float,
                'total_frames': int,
                'duration_seconds': float,
                'video_width': int,
                'video_height': int,
                'source': str
            }
        """
        metadata = {
            "capture_date": None,
            "capture_time": None,
            "gps_latitude": None,
            "gps_longitude": None,
            "fps": 30.0,
            "total_frames": 0,
            "duration_seconds": 0.0,
            "video_width": 0,
            "video_height": 0,
            "source": "file",
        }

        cap = None
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.warning(f"Video açılamadı: {video_path}")
                return MetadataExtractor._fallback_metadata(video_path, metadata)

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

            metadata["fps"] = fps
            metadata["total_frames"] = total_frames
            metadata["video_width"] = width
            metadata["video_height"] = height
            metadata["duration_seconds"] = total_frames / fps if fps > 0 else 0.0

            return MetadataExtractor._fallback_metadata(video_path, metadata)

        except Exception as e:
            logger.error(f"Video meta verisi çıkarma hatası: {e}")
            return MetadataExtractor._fallback_metadata(video_path, metadata)

        finally:
            if cap is not None:
                cap.release()

    @staticmethod
    def _fallback_metadata(file_path: str, metadata: Dict) -> Dict:
        """Dosya değiştirme zamanını yedek olarak kullan"""
        try:
            mtime = Path(file_path).stat().st_mtime
            dt = datetime.fromtimestamp(mtime)

            metadata["capture_date"] = dt.strftime(config.REPORT_DATE_FORMAT)
            metadata["capture_time"] = dt.strftime(config.REPORT_TIME_FORMAT)
            metadata["source"] = "file_time"

            logger.info(
                f"Dosya zamanı kullanılıyor: {metadata['capture_date']} {metadata['capture_time']}"
            )
        except Exception as e:
            logger.error(f"Dosya zamanı alma hatası: {e}")
            dt = datetime.now()
            metadata["capture_date"] = dt.strftime(config.REPORT_DATE_FORMAT)
            metadata["capture_time"] = dt.strftime(config.REPORT_TIME_FORMAT)
            metadata["source"] = "system_time"

        return metadata

    @staticmethod
    def _parse_datetime(dt_string: str) -> Dict[str, Optional[str]]:
        """EXIF tarih saat dizesini ayrıştır"""
        result: Dict[str, Optional[str]] = {
            "capture_date": None,
            "capture_time": None,
        }

        try:
            # EXIF örneği: 2024:01:15 14:30:45
            dt_obj = datetime.strptime(dt_string.strip(), "%Y:%m:%d %H:%M:%S")
            result["capture_date"] = dt_obj.strftime(config.REPORT_DATE_FORMAT)
            result["capture_time"] = dt_obj.strftime(config.REPORT_TIME_FORMAT)
        except Exception:
            pass

        return result

    @staticmethod
    def _extract_gps_latitude(tags: Dict) -> Optional[float]:
        """EXIF etiketlerinden GPS enlemini çıkar (DMS -> Decimal Degrees)"""
        try:
            if "GPS GPSLatitude" not in tags:
                return None

            lat = tags["GPS GPSLatitude"].values
            lat_ref = str(tags.get("GPS GPSLatitudeRef", "N")).strip()

            degree = float(lat[0].num) / float(lat[0].den) if lat[0].den != 0 else 0.0
            minute = float(lat[1].num) / float(lat[1].den) if lat[1].den != 0 else 0.0
            second = float(lat[2].num) / float(lat[2].den) if lat[2].den != 0 else 0.0

            decimal = degree + minute / 60.0 + second / 3600.0
            if lat_ref == "S":
                decimal = -decimal

            return decimal

        except Exception as e:
            logger.debug(f"GPS enlemi çıkarma hatası: {e}")
            return None

    @staticmethod
    def _extract_gps_longitude(tags: Dict) -> Optional[float]:
        """EXIF etiketlerinden GPS boylamını çıkar (DMS -> Decimal Degrees)"""
        try:
            if "GPS GPSLongitude" not in tags:
                return None

            lon = tags["GPS GPSLongitude"].values
            lon_ref = str(tags.get("GPS GPSLongitudeRef", "E")).strip()

            degree = float(lon[0].num) / float(lon[0].den) if lon[0].den != 0 else 0.0
            minute = float(lon[1].num) / float(lon[1].den) if lon[1].den != 0 else 0.0
            second = float(lon[2].num) / float(lon[2].den) if lon[2].den != 0 else 0.0

            decimal = degree + minute / 60.0 + second / 3600.0
            if lon_ref == "W":
                decimal = -decimal

            return decimal

        except Exception as e:
            logger.debug(f"GPS boylamı çıkarma hatası: {e}")
            return None