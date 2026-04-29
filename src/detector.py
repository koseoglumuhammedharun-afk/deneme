# -*- coding: utf-8 -*-
"""
Drone Obus Tespit Motoru - YOLOv8 Tabanli

Bu revizyonda analiz mantigi parca odaklidir:
- Model dusuk confidence degerlerinde de calistirilabilir.
- Tek en yuksek kutu yerine esigin ustundeki tum kutular saklanir.
- Namlu / piston / govde tespiti ana arac/silah kararina cevrilir.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Callable, Any, List, Tuple
from collections import Counter

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
    YOLOv8 kullanan cok sinifli tespit motoru.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: Optional[float] = None
    ):
        self.model_path = str(Path(model_path or config.MODEL_PATH).absolute())
        if confidence_threshold is None:
            confidence_threshold = config.CONFIDENCE_THRESHOLD
        self.confidence_threshold = config.normalize_confidence_threshold(confidence_threshold)
        self.model: Optional[Any] = None
        self.device: str = "cpu"
        self._load_model()

    def _load_model(self):
        """YOLOv8 modelini yukle ve uygun cihaza tasi."""
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
        """YOLO sonucundan sinif adini guvenli sekilde al."""
        names = getattr(result_obj, "names", {})

        if isinstance(names, dict):
            return str(names.get(cls_id, f"class_{cls_id}"))

        if isinstance(names, list) and 0 <= cls_id < len(names):
            return str(names[cls_id])

        class_names = getattr(config, "CLASS_NAMES", None)
        if isinstance(class_names, list) and 0 <= cls_id < len(class_names):
            return str(class_names[cls_id])

        return f"class_{cls_id}"

    def _model_confidence_value(self) -> float:
        """
        Ultralytics model cagrisi icin kullanilacak guven esigi.

        Kritik nokta: model() icine conf parametresi verilmezse Ultralytics
        kendi varsayilanini kullanabilir. Bu da GUI slider'i %0/%5 yapsa bile
        dusuk guvenli parcaların gelmemesine sebep olur.
        """
        return config.normalize_confidence_threshold(self.confidence_threshold)

    def _run_model(self, image: np.ndarray):
        """Modeli aktif confidence esigiyle calistir."""
        return self.model(
            image,
            device=self.device,
            conf=self._model_confidence_value(),
            verbose=False,
        )

    def _empty_detection_result(self, image=None) -> Dict:
        return {
            "detected": False,
            "confidence": 0.0,
            "bbox": None,
            "image": image,
            "annotated_image": image.copy() if image is not None else None,
            "annotated_frame": None,
            "detection_frame": None,
            "crop": None,
            "crop_items": [],
            "crop_count": 0,
            "class_id": None,
            "class_name": None,
            "weapon_type": None,
            "weapon_display": None,
            "part_type": None,
            "part_display": None,
            "detection_level": None,
            "evidence_summary": None,
            "detections": [],
            "detection_count": 0,
            "class_counts": {},
        }

    def _make_detection_item(self, result_obj, cls_id: int, conf: float, box) -> Dict:
        """Tek kutuyu standart sozluk yapisina cevir."""
        class_name = self._resolve_class_name(result_obj, cls_id)
        weapon_type = config.get_weapon_from_class(class_name)
        weapon_display = config.get_weapon_display_name(weapon_type)
        part_type = config.get_part_from_class(class_name)
        part_display = config.get_part_display_name(part_type) if part_type else ""
        display_name = config.get_class_display_name(class_name)
        decision = config.get_weapon_decision(class_name, conf)
        level = config.get_detection_level(conf)

        x1, y1, x2, y2 = map(int, box[:4])

        return {
            "class_id": int(cls_id),
            "class_name": class_name,
            "display_name": display_name,
            "weapon_type": weapon_type,
            "weapon_display": weapon_display,
            "part_type": part_type,
            "part_display": part_display,
            "decision": decision,
            "detection_level": level,
            "confidence": float(conf),
            "bbox": (x1, y1, x2, y2),
        }

    def _collect_detections_from_result(self, result_obj) -> List[Dict]:
        """YOLO result objesinden aktif esigin ustundeki tum tespitleri al."""
        boxes = getattr(result_obj, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return []

        confidences = boxes.conf.cpu().numpy()
        class_ids = (
            boxes.cls.cpu().numpy().astype(int)
            if hasattr(boxes, "cls")
            else np.zeros(len(confidences), dtype=int)
        )

        detections: List[Dict] = []
        threshold = self.confidence_threshold

        for i, conf in enumerate(confidences):
            conf = float(conf)
            if conf < threshold:
                continue

            cls_id = int(class_ids[i]) if len(class_ids) > i else 0
            box = boxes.xyxy[i].cpu().numpy().astype(int)
            detections.append(self._make_detection_item(result_obj, cls_id, conf, box))

        detections.sort(key=lambda item: item["confidence"], reverse=True)
        return detections

    def _summarize_detections(self, detections: List[Dict]) -> Dict:
        """Tespit listesinden ana sonuc metinlerini uret."""
        if not detections:
            return {
                "detected": False,
                "confidence": 0.0,
                "class_counts": {},
                "evidence_summary": None,
                "weapon_display": None,
                "weapon_type": None,
                "class_name": None,
                "part_type": None,
                "part_display": None,
                "detection_level": None,
            }

        best = detections[0]
        class_counts = Counter(item["class_name"] for item in detections)

        # En guclu ilk 5 tespiti ozetle
        evidence_items = []
        for item in detections[:5]:
            evidence_items.append(
                f"{item['decision']} - {item['confidence']:.1%}"
            )

        return {
            "detected": True,
            "confidence": best["confidence"],
            "class_counts": dict(class_counts),
            "evidence_summary": " | ".join(evidence_items),
            "weapon_display": best["decision"],
            "weapon_type": best["weapon_type"],
            "class_name": best["class_name"],
            "part_type": best["part_type"],
            "part_display": best["part_display"],
            "detection_level": best["detection_level"],
        }

    @staticmethod
    def _color_for_level(level: Optional[str]) -> Tuple[int, int, int]:
        """OpenCV BGR renk secimi."""
        if level == "Güçlü":
            return (0, 200, 0)
        if level == "Şüpheli":
            return (0, 210, 255)
        return (0, 0, 255)

    def _draw_single_detection(self, image: np.ndarray, item: Dict, origin: Tuple[int, int] = (0, 0)) -> None:
        """Bir tespiti verilen goruntu uzerine isaretle."""
        ox, oy = origin
        x1, y1, x2, y2 = item["bbox"]
        x1 -= ox
        x2 -= ox
        y1 -= oy
        y2 -= oy

        h, w = image.shape[:2]
        x1 = max(0, min(w - 1, int(x1)))
        x2 = max(0, min(w - 1, int(x2)))
        y1 = max(0, min(h - 1, int(y1)))
        y2 = max(0, min(h - 1, int(y2)))

        if x2 <= x1 or y2 <= y1:
            return

        color = self._color_for_level(item.get("detection_level"))
        thickness = 2 if item.get("confidence", 0) >= 0.05 else 1
        label = f"{item.get('display_name', item.get('class_name', 'tespit'))} {item.get('confidence', 0):.2f}"

        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)

        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        cv2.circle(image, (cx, cy), 5, color, -1, cv2.LINE_AA)
        cv2.drawMarker(image, (cx, cy), color, markerType=cv2.MARKER_CROSS, markerSize=18, thickness=2)

        text_y = max(18, y1 - 8)
        cv2.putText(
            image,
            label,
            (x1, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

    def _draw_detections(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """Tum tespitleri goruntu uzerine ciz."""
        annotated = image.copy()
        for item in detections:
            self._draw_single_detection(annotated, item)
        return annotated

    def _crop_detection_with_bounds(
        self,
        image: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
    ) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
        """Tespit alanini orijinal piksel kalitesinde kirp ve kirpma sinirlarini dondur."""
        padding = config.CROP_PADDING
        h, w = image.shape[:2]

        c_x1 = max(0, int(x1) - padding)
        c_y1 = max(0, int(y1) - padding)
        c_x2 = min(w, int(x2) + padding)
        c_y2 = min(h, int(y2) + padding)

        return image[c_y1:c_y2, c_x1:c_x2].copy(), (c_x1, c_y1, c_x2, c_y2)

    def _make_crop_items(self, image: np.ndarray, detections: List[Dict]) -> List[Dict]:
        """Her tespit icin ayri kirpinti ve isaretlenmis kirpinti olustur."""
        crop_items: List[Dict] = []

        for index, item in enumerate(detections, start=1):
            x1, y1, x2, y2 = item["bbox"]
            raw_crop, bounds = self._crop_detection_with_bounds(image, x1, y1, x2, y2)
            marked_crop = raw_crop.copy()
            self._draw_single_detection(marked_crop, item, origin=(bounds[0], bounds[1]))

            crop_items.append({
                "index": index,
                "class_id": item.get("class_id"),
                "class_name": item.get("class_name"),
                "display_name": item.get("display_name"),
                "decision": item.get("decision"),
                "weapon_type": item.get("weapon_type"),
                "weapon_display": item.get("weapon_display"),
                "part_type": item.get("part_type"),
                "part_display": item.get("part_display"),
                "detection_level": item.get("detection_level"),
                "confidence": item.get("confidence", 0.0),
                "bbox": item.get("bbox"),
                "crop_bounds": bounds,
                "crop_image": raw_crop,
                "marked_crop_image": marked_crop,
                "original_size": tuple(image.shape[:2][::-1]),
                "crop_size": tuple(raw_crop.shape[:2][::-1]) if raw_crop is not None else None,
            })

        return crop_items

    def detect_in_image(self, image_path: str) -> Dict:
        """Tekli resimde tespit yap."""
        try:
            if self.model is None:
                raise RuntimeError("YOLO modeli yuklenemedigi icin islem yapilamiyor.")

            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Resim dosyasi okunamadi veya yol hatali: {image_path}")

            detection_result = self._empty_detection_result(image)

            results = self._run_model(image)
            if not results:
                return detection_result

            detections = self._collect_detections_from_result(results[0])
            if not detections:
                return detection_result

            summary = self._summarize_detections(detections)
            detection_result.update(summary)

            best = detections[0]
            x1, y1, x2, y2 = best["bbox"]

            detection_result["bbox"] = best["bbox"]
            detection_result["class_id"] = best["class_id"]
            crop_items = self._make_crop_items(image, detections)

            detection_result["detections"] = detections
            detection_result["detection_count"] = len(detections)
            detection_result["crop_items"] = crop_items
            detection_result["crop_count"] = len(crop_items)
            detection_result["annotated_image"] = self._draw_detections(image, detections)
            detection_result["crop"] = (
                crop_items[0].get("marked_crop_image") if crop_items else self._crop_detection(image, x1, y1, x2, y2)
            )

            logger.info(
                f"Tespit basarili: {best['class_name']} ({best['confidence']:.3f}), "
                f"toplam kutu={len(detections)}"
            )
            return detection_result

        except Exception as e:
            logger.error(f"Goruntu isleme hatasi: {e}")
            raise

    def detect_in_video(
        self,
        video_path: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """Video framelerinde tespit yap."""
        cap = None
        try:
            if self.model is None:
                raise RuntimeError("YOLO modeli yuklenmedi.")

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Video dosyasi acilamadi: {video_path}")

            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            detection_result = self._empty_detection_result()
            detection_result.update({
                "frame_index": 0,
                "timestamp_mmss": "00:00",
            })

            frame_count = 0
            max_confidence = 0.0
            best_detection = None
            class_counts = Counter()
            total_detection_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % config.VIDEO_SKIP_FRAMES != 0:
                    frame_count += 1
                    continue

                results = self._run_model(frame)

                if results:
                    detections = self._collect_detections_from_result(results[0])
                    if detections:
                        total_detection_count += len(detections)
                        class_counts.update(item["class_name"] for item in detections)

                        frame_best = detections[0]
                        if frame_best["confidence"] > max_confidence:
                            max_confidence = frame_best["confidence"]
                            best_detection = {
                                "frame_index": frame_count,
                                "frame": frame.copy(),
                                "detections": detections,
                                "best": frame_best,
                            }

                if progress_callback and frame_count % config.VIDEO_PROGRESS_UPDATE_INTERVAL == 0:
                    progress_callback(frame_count, total_frames, max_confidence)

                frame_count += 1

            if best_detection:
                best = best_detection["best"]
                detections = best_detection["detections"]

                summary = self._summarize_detections(detections)
                detection_result.update(summary)

                detection_result["frame_index"] = best_detection["frame_index"]
                detection_result["timestamp_mmss"] = self._frames_to_mmss(
                    best_detection["frame_index"], fps
                )
                detection_result["bbox"] = best["bbox"]
                detection_result["class_id"] = best["class_id"]
                frame = best_detection["frame"]
                x1, y1, x2, y2 = best["bbox"]
                crop_items = self._make_crop_items(frame, detections)

                detection_result["detections"] = detections
                detection_result["detection_count"] = total_detection_count
                detection_result["frame_detection_count"] = len(detections)
                detection_result["class_counts"] = dict(class_counts)
                detection_result["crop_items"] = crop_items
                detection_result["crop_count"] = len(crop_items)

                detection_result["annotated_frame"] = self._draw_detections(frame, detections)
                detection_result["detection_frame"] = frame
                detection_result["crop"] = (
                    crop_items[0].get("marked_crop_image") if crop_items else self._crop_detection(frame, x1, y1, x2, y2)
                )

            return detection_result

        except Exception as e:
            logger.error(f"Video isleme hatasi: {e}")
            raise

        finally:
            if cap is not None:
                cap.release()

    def _crop_detection(
        self,
        image: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int
    ) -> np.ndarray:
        """Tespit edilen alanin etrafina padding ekleyerek kirp."""
        padding = config.CROP_PADDING
        h, w = image.shape[:2]

        c_x1 = max(0, x1 - padding)
        c_y1 = max(0, y1 - padding)
        c_x2 = min(w, x2 + padding)
        c_y2 = min(h, y2 + padding)

        return image[c_y1:c_y2, c_x1:c_x2]

    @staticmethod
    def _frames_to_mmss(frame_number: int, fps: float) -> str:
        """Frame numarasini DD:SS formatina cevir."""
        seconds = frame_number / (fps if fps > 0 else 30)
        return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"

    def set_confidence_threshold(self, threshold: float):
        """Confidence threshold guncelle."""
        self.confidence_threshold = config.normalize_confidence_threshold(threshold)
