# -*- coding: utf-8 -*-
"""
Drone Obus Tespit Motoru - YOLOv8 Tabanli
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Callable, Any

import cv2
import numpy as np

try:
    import torch
except (ImportError, OSError) as e:
    torch = None
    logging.warning(f"PyTorch yuklenemedi: {e}")

try:
    from ultralytics import YOLO
except (ImportError, OSError) as e:
    YOLO = None
    logging.error(f"YOLOv8 kutuphanesi baslatilamadi: {e}")

import config

logger = logging.getLogger(__name__)


class HowitzerDetector:
    """
    YOLOv8 kullanan cok sinifli tespit motoru
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: Optional[float] = None
    ):
        self.model_path = str(Path(model_path or config.MODEL_PATH).absolute())
        self.confidence_threshold = confidence_threshold or config.CONFIDENCE_THRESHOLD
        self.model: Optional[Any] = None
        self.device: str = "cpu"
        self._load_model()

    def _load_model(self):
        """YOLOv8 modelini yukle ve uygun cihaza tasi"""
        try:
            if YOLO is None:
                raise ImportError("Ultralytics/Torch kutuphaneleri bulunamadi.")

            if config.USE_GPU and torch and torch.cuda.is_available():
                self.device = f"cuda:{config.GPU_DEVICE}"
                gpu_name = torch.cuda.get_device_name(config.GPU_DEVICE)
                logger.info(f"GPU tespit edildi: {gpu_name}")
                logger.info(f"Kullanilan cihaz: {self.device}")
            else:
                self.device = "cpu"
                logger.info("CPU modu kullaniliyor")

            if not os.path.exists(self.model_path):
                logger.warning(
                    f"Ozel model bulunamadi, varsayilan model yukleniyor: {self.model_path}"
                )
                self.model = YOLO("yolov8n.pt")
            else:
                logger.info(f"Model yukleniyor: {self.model_path}")
                self.model = YOLO(self.model_path)

            self.model.to(self.device)
            logger.info(f"Model {self.device.upper()} cihazinda baslatildi")

        except Exception as e:
            logger.error(f"Model yukleme hatasi: {str(e)}")
            self.model = None
            self.device = "cpu"

    @staticmethod
    def _resolve_class_name(result_obj, cls_id: int) -> str:
        """YOLO sonucundan sinif adini guvenli sekilde al"""
        names = getattr(result_obj, "names", {})

        if isinstance(names, dict):
            return str(names.get(cls_id, f"class_{cls_id}"))

        if isinstance(names, list) and 0 <= cls_id < len(names):
            return str(names[cls_id])

        class_names = getattr(config, "CLASS_NAMES", None)
        if isinstance(class_names, list) and 0 <= cls_id < len(class_names):
            return str(class_names[cls_id])

        return f"class_{cls_id}"

    def detect_in_image(self, image_path: str) -> Dict:
        """Tekli resimde tespit yap"""
        try:
            if self.model is None:
                raise RuntimeError("YOLO modeli yuklenemedigi icin islem yapilamiyor.")

            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Resim dosyasi okunamadi veya yol hatali: {image_path}")

            results = self.model(image, device=self.device, verbose=False)

            detection_result = {
                "detected": False,
                "confidence": 0.0,
                "bbox": None,
                "image": image,
                "annotated_image": image.copy(),
                "crop": None,
                "class_id": None,
                "class_name": None,
                "weapon_type": None,
            }

            if not results:
                return detection_result

            result = results[0]
            boxes = getattr(result, "boxes", None)

            if boxes is None or len(boxes) == 0:
                return detection_result

            confidences = boxes.conf.cpu().numpy()
            class_ids = (
                boxes.cls.cpu().numpy().astype(int)
                if hasattr(boxes, "cls")
                else np.zeros(len(confidences), dtype=int)
            )

            valid_detections = [
                (i, conf)
                for i, conf in enumerate(confidences)
                if conf >= self.confidence_threshold
            ]

            if not valid_detections:
                return detection_result

            idx, max_conf = max(valid_detections, key=lambda x: x[1])
            box = boxes.xyxy[idx].cpu().numpy().astype(int)
            cls_id = int(class_ids[idx]) if len(class_ids) > idx else 0
            class_name = self._resolve_class_name(result, cls_id)

            x1, y1, x2, y2 = map(int, box[:4])

            detection_result["detected"] = True
            detection_result["confidence"] = float(max_conf)
            detection_result["bbox"] = (x1, y1, x2, y2)
            detection_result["class_id"] = cls_id
            detection_result["class_name"] = class_name
            detection_result["weapon_type"] = class_name

            annotated = image.copy()
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                annotated,
                f"{class_name} - Guven: {max_conf:.2f}",
                (x1, max(20, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

            detection_result["annotated_image"] = annotated
            detection_result["crop"] = self._crop_detection(image, x1, y1, x2, y2)

            logger.info(f"Tespit basarili: {class_name} ({max_conf:.3f})")
            return detection_result

        except Exception as e:
            logger.error(f"Goruntu isleme hatasi: {e}")
            raise

    def detect_in_video(
        self,
        video_path: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """Video framelerinde tespit yap"""
        try:
            if self.model is None:
                raise RuntimeError("YOLO modeli yuklenmedi.")

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Video dosyasi acilamadi: {video_path}")

            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            detection_result = {
                "detected": False,
                "confidence": 0.0,
                "frame_index": 0,
                "timestamp_mmss": "00:00",
                "bbox": None,
                "annotated_frame": None,
                "detection_frame": None,
                "crop": None,
                "class_id": None,
                "class_name": None,
                "weapon_type": None,
            }

            frame_count = 0
            max_confidence = 0.0
            best_detection = None

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % config.VIDEO_SKIP_FRAMES != 0:
                    frame_count += 1
                    continue

                results = self.model(frame, device=self.device, verbose=False)

                if progress_callback and frame_count % config.VIDEO_PROGRESS_UPDATE_INTERVAL == 0:
                    progress_callback(frame_count, total_frames, max_confidence)

                if results:
                    result = results[0]
                    boxes = getattr(result, "boxes", None)

                    if boxes is not None and len(boxes) > 0:
                        confidences = boxes.conf.cpu().numpy()
                        class_ids = (
                            boxes.cls.cpu().numpy().astype(int)
                            if hasattr(boxes, "cls")
                            else np.zeros(len(confidences), dtype=int)
                        )

                        for i, conf in enumerate(confidences):
                            if conf >= self.confidence_threshold and conf > max_confidence:
                                max_confidence = float(conf)
                                box = boxes.xyxy[i].cpu().numpy().astype(int)
                                cls_id = int(class_ids[i]) if len(class_ids) > i else 0
                                class_name = self._resolve_class_name(result, cls_id)

                                best_detection = {
                                    "frame_index": frame_count,
                                    "frame": frame.copy(),
                                    "bbox": (int(box[0]), int(box[1]), int(box[2]), int(box[3])),
                                    "confidence": max_confidence,
                                    "class_id": cls_id,
                                    "class_name": class_name,
                                }

                frame_count += 1

            cap.release()

            if best_detection:
                detection_result["detected"] = True
                detection_result["confidence"] = best_detection["confidence"]
                detection_result["frame_index"] = best_detection["frame_index"]
                detection_result["timestamp_mmss"] = self._frames_to_mmss(
                    best_detection["frame_index"], fps
                )
                detection_result["bbox"] = best_detection["bbox"]
                detection_result["class_id"] = best_detection["class_id"]
                detection_result["class_name"] = best_detection["class_name"]
                detection_result["weapon_type"] = best_detection["class_name"]

                frame = best_detection["frame"]
                x1, y1, x2, y2 = best_detection["bbox"]
                class_name = best_detection["class_name"]

                annotated = frame.copy()
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    annotated,
                    f"{class_name} - Guven: {best_detection['confidence']:.2f}",
                    (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

                detection_result["annotated_frame"] = annotated
                detection_result["detection_frame"] = frame
                detection_result["crop"] = self._crop_detection(frame, x1, y1, x2, y2)

            return detection_result

        except Exception as e:
            logger.error(f"Video isleme hatasi: {e}")
            raise

    def _crop_detection(
        self,
        image: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int
    ) -> np.ndarray:
        """Tespit edilen alanin etrafina padding ekleyerek kirp"""
        padding = config.CROP_PADDING
        h, w = image.shape[:2]

        c_x1 = max(0, x1 - padding)
        c_y1 = max(0, y1 - padding)
        c_x2 = min(w, x2 + padding)
        c_y2 = min(h, y2 + padding)

        return image[c_y1:c_y2, c_x1:c_x2]

    @staticmethod
    def _frames_to_mmss(frame_number: int, fps: float) -> str:
        """Frame numarasini DD:SS formatina cevir"""
        seconds = frame_number / (fps if fps > 0 else 30)
        return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"

    def set_confidence_threshold(self, threshold: float):
        """Confidence threshold guncelle"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))