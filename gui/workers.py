# -*- coding: utf-8 -*-
"""
Arka plan calisanlari (workers) - Thread-based islemler
"""

import logging
import time
from pathlib import Path
from datetime import datetime

import cv2
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

import config

logger = logging.getLogger(__name__)


class AnalysisWorker(QThread):
    """Arka planda analiz yapan worker thread"""

    progress_update = pyqtSignal(str)
    frame_progress = pyqtSignal(int, int, float)
    analysis_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, detector, file_path, metadata_extractor, report_generator):
        super().__init__()
        self.detector = detector
        self.file_path = file_path
        self.metadata_extractor = metadata_extractor
        self.report_generator = report_generator
        self.results = {}

    def run(self):
        """Arka planda analiz islemi calistir"""
        try:
            file_path = Path(self.file_path)
            file_suffix = file_path.suffix.lower()

            self.progress_update.emit(f"Analiz baslaniyor: {file_path.name}")

            if file_suffix in config.SUPPORTED_IMAGE_FORMATS:
                self._analyze_image()
            elif file_suffix in config.SUPPORTED_VIDEO_FORMATS:
                self._analyze_video()
            else:
                raise ValueError(f"Desteklenmeyen dosya formati: {file_suffix}")

            self.analysis_complete.emit(self.results)

        except Exception as e:
            logger.error(f"Analiz hatasi: {e}")
            self.error_occurred.emit(str(e))

    def _base_result_payload(self, detection: dict, metadata: dict, file_type: str) -> dict:
        """Ortak analiz sonuc alanlarini olustur."""
        return {
            "filename": Path(self.file_path).name,
            "file_type": file_type,
            "detected": detection.get("detected", False),
            "confidence": detection.get("confidence", 0.0),
            "capture_date": metadata["capture_date"],
            "capture_time": metadata["capture_time"],
            "analysis_date": datetime.now().strftime(config.REPORT_DATE_FORMAT),
            "analysis_time": datetime.now().strftime(config.REPORT_TIME_FORMAT),
            "analysis_datetime": datetime.now().isoformat(),
            "gps_latitude": metadata.get("gps_latitude"),
            "gps_longitude": metadata.get("gps_longitude"),
            "distance_m": None,
            "crop_image": detection.get("crop"),
            "crop_items": detection.get("crop_items", []),
            "crop_count": detection.get("crop_count", 0),
            "frame_detection_count": detection.get("frame_detection_count", 0),
            "camera_make": metadata.get("camera_make"),
            "camera_model": metadata.get("camera_model"),
            "weapon_type": detection.get("weapon_type"),
            "weapon_display": detection.get("weapon_display"),
            "class_name": detection.get("class_name"),
            "part_type": detection.get("part_type"),
            "part_display": detection.get("part_display"),
            "detection_level": detection.get("detection_level"),
            "evidence_summary": detection.get("evidence_summary"),
            "detections": detection.get("detections", []),
            "detection_count": detection.get("detection_count", 0),
            "class_counts": detection.get("class_counts", {}),
        }

    def _analyze_image(self):
        """Tek bir resim analiz et"""
        try:
            self.progress_update.emit("Resim analiz ediliyor...")

            detection = self.detector.detect_in_image(self.file_path)
            metadata = self.metadata_extractor.extract_image_metadata(self.file_path)

            self.results = self._base_result_payload(detection, metadata, "image")
            self.results.update({
                "time_in_video": None,
                "annotated_image": detection.get("annotated_image"),
                "original_image": detection.get("image"),
            })

            if detection.get("detected"):
                msg = (
                    f"Tespit bulundu! Guven: {detection.get('confidence', 0):.2%} | "
                    f"{detection.get('evidence_summary') or detection.get('class_name')}"
                )
                self.progress_update.emit(msg)
            else:
                self.progress_update.emit("Tespit bulunamadi")

        except Exception as e:
            logger.error(f"Resim analiz hatasi: {e}")
            raise

    def _analyze_video(self):
        """Video dosyasini analiz et"""
        try:
            self.progress_update.emit("Video analiz ediliyor...")

            def progress_callback(current_frame, total_frames, confidence):
                self.frame_progress.emit(current_frame, total_frames, confidence)
                self.progress_update.emit(
                    f"Frame {current_frame}/{total_frames} - En yuksek guven: {confidence:.2%}"
                )

            detection = self.detector.detect_in_video(self.file_path, progress_callback)
            metadata = self.metadata_extractor.extract_video_metadata(self.file_path)

            self.results = self._base_result_payload(detection, metadata, "video")
            self.results.update({
                "time_in_video": detection.get("timestamp_mmss"),
                "annotated_image": detection.get("annotated_frame"),
                "original_image": detection.get("detection_frame"),
                "fps": metadata.get("fps"),
                "total_frames": metadata.get("total_frames"),
            })

            if detection.get("detected"):
                msg = (
                    f"Tespit: {detection.get('timestamp_mmss')} | "
                    f"Guven: {detection.get('confidence', 0):.2%} | "
                    f"{detection.get('evidence_summary') or detection.get('class_name')}"
                )
                self.progress_update.emit(msg)
            else:
                self.progress_update.emit("Videoda tespit bulunamadi")

        except Exception as e:
            logger.error(f"Video analiz hatasi: {e}")
            raise


class LiveVideoWorker(QThread):
    """Canli video takip worker'i"""

    frame_ready = pyqtSignal(QImage)
    status_update = pyqtSignal(str)
    stats_update = pyqtSignal(str)
    log_update = pyqtSignal(str)
    detection_update = pyqtSignal(str)
    position_update = pyqtSignal(int, int, str, str)
    media_info_loaded = pyqtSignal(int, float, str)
    error_occurred = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, detector, video_path: str, start_frame: int = 0):
        super().__init__()
        self.detector = detector
        self.video_path = video_path
        self.start_frame = max(0, int(start_frame))
        self._running = True
        self._paused = False
        self._seek_frame = None
        self.frame_counter = 0
        self.detection_counter = 0
        self.total_frames = 0
        self.fps = 25.0

    def stop(self):
        """Worker'i durdur"""
        self._running = False

    def pause(self):
        """Duraklat"""
        self._paused = True

    def resume(self):
        """Devam ettir"""
        self._paused = False

    def seek_to_frame(self, frame_index: int):
        """Belirli frame'e git"""
        self._seek_frame = max(0, int(frame_index))

    def _format_time_text(self, seconds: float) -> str:
        """Saniyeyi zaman metnine cevir"""
        total_seconds = max(0, int(seconds))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _frame_to_time_text(self, frame_index: int) -> str:
        """Frame no -> zaman"""
        if self.fps <= 0:
            return "00:00"
        return self._format_time_text(frame_index / self.fps)

    def _to_qimage(self, frame_bgr):
        """OpenCV BGR frame -> QImage"""
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return image.copy()

    def _annotate_frame(self, frame):
        """Frame uzerine kutu ve etiket ciz"""
        results = self.detector.model(
            frame,
            device=self.detector.device,
            conf=self.detector._model_confidence_value(),
            verbose=False,
        )
        annotated = frame.copy()
        detections_for_log = []

        if results and len(results[0].boxes) > 0:
            boxes = results[0].boxes
            confidences = boxes.conf.cpu().numpy()
            class_ids = (
                boxes.cls.cpu().numpy().astype(int)
                if hasattr(boxes, "cls")
                else []
            )

            current_time_text = self._frame_to_time_text(self.frame_counter)

            for i, conf in enumerate(confidences):
                conf = float(conf)
                if conf < self.detector.confidence_threshold:
                    continue

                self.detection_counter += 1

                box = boxes.xyxy[i].cpu().numpy().astype(int)
                cls_id = int(class_ids[i]) if len(class_ids) > i else 0
                class_name = self.detector._resolve_class_name(results[0], cls_id)
                display_name = config.get_class_display_name(class_name)
                decision = config.get_weapon_decision(class_name, conf)

                x1, y1, x2, y2 = box[0], box[1], box[2], box[3]

                cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(
                    annotated,
                    f"{display_name} {conf:.2f}",
                    (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 0, 0),
                    2,
                )

                detections_for_log.append(
                    f"{current_time_text} | {decision} | {conf:.2%}"
                )

        return annotated, detections_for_log

    def run(self):
        """Canli video takibini baslat"""
        cap = None
        try:
            if self.detector is None or self.detector.model is None:
                raise RuntimeError("Yuklu bir model bulunamadi.")

            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                raise RuntimeError(f"Video acilamadi: {self.video_path}")

            self.fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            total_time_text = self._format_time_text(
                self.total_frames / self.fps if self.fps > 0 else 0
            )

            self.media_info_loaded.emit(self.total_frames, self.fps, total_time_text)

            if self.start_frame > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)

            self.status_update.emit("Oynatiliyor")
            self.log_update.emit(f"Video acildi: {Path(self.video_path).name}")
            self.log_update.emit(
                f"Toplam frame: {self.total_frames}, FPS: {self.fps:.2f}"
            )

            while self._running:
                loop_start = time.time()

                if self._seek_frame is not None:
                    target = max(0, min(self._seek_frame, max(0, self.total_frames - 1)))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target)
                    self.frame_counter = target
                    self._seek_frame = None

                if self._paused:
                    self.msleep(50)
                    continue

                ret, frame = cap.read()
                if not ret:
                    break

                current_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                self.frame_counter = max(0, current_pos)

                annotated, detections_for_log = self._annotate_frame(frame)

                for det_msg in detections_for_log:
                    self.detection_update.emit(det_msg)
                    self.log_update.emit(f"Tespit: {det_msg}")

                current_time_text = self._frame_to_time_text(self.frame_counter)
                total_time_text = self._format_time_text(
                    self.total_frames / self.fps if self.fps > 0 else 0
                )

                elapsed = time.time() - loop_start
                processing_fps = (1.0 / elapsed) if elapsed > 0 else 0.0

                self.stats_update.emit(
                    f"Frame: {self.frame_counter + 1}/{self.total_frames} | "
                    f"Tespit: {self.detection_counter} | FPS: {processing_fps:.2f}"
                )
                self.position_update.emit(
                    self.frame_counter,
                    self.total_frames,
                    current_time_text,
                    total_time_text,
                )
                self.frame_ready.emit(self._to_qimage(annotated))

                desired_frame_time = 1.0 / self.fps if self.fps > 0 else 0.04
                sleep_time = desired_frame_time - (time.time() - loop_start)
                if sleep_time > 0:
                    self.msleep(int(sleep_time * 1000))

            self.status_update.emit("Tamamlandi")
            self.log_update.emit("Video sonuna ulasildi")
            self.finished_signal.emit()

        except Exception as e:
            logger.error(f"Canli video takip hatasi: {e}")
            self.error_occurred.emit(str(e))
            self.finished_signal.emit()

        finally:
            if cap is not None:
                cap.release()
