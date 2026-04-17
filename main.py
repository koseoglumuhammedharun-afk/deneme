# -*- coding: utf-8 -*-
"""
Drone Obus Tespit Sistemi - PyQt5 GUI Uygulamasi
Moduler gorunum ana giris noktasi
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import cv2

# PyTorch DLL hatasini onle
dll_path = r"C:\Users\CASPER\Desktop\drone_detection\venv\lib\site-packages\torch\lib"
if os.path.exists(dll_path):
    os.add_dll_directory(dll_path)

try:
    import torch
except (ImportError, OSError) as e:
    torch = None
    print(f"PyTorch yuklenemedi: {e}")
    print("GUI calisacak, ancak YOLO tespit devre disi olacak")

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QMessageBox,
    QFileDialog,
    QProgressBar,
    QInputDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage

import config
from src import HowitzerDetector, MetadataExtractor, ReportGenerator, ModelTrainer
from src.utils import setup_logging, validate_file, get_file_preview
from gui import (
    create_analysis_ui,
    create_training_ui,
    create_live_analysis_ui,
    CropViewerWindow,
    VideoFrameExtractionDialog,
)
from gui.workers import AnalysisWorker, LiveVideoWorker

logger = setup_logging("GUI")


class MainWindow(QMainWindow):
    """Ana uygulama penceresi"""

    def __init__(self):
        super().__init__()
        self.init_state()
        self.init_ui()
        self.ui_ready = True
        self.load_model()

    def init_state(self):
        """Durum degiskenlerini baslat"""
        self.detector = None
        self.metadata_extractor = MetadataExtractor()
        self.report_generator = ReportGenerator()
        self.model_trainer = ModelTrainer()

        self.selected_files = []
        self.current_file = None
        self.analysis_results = None
        self.analysis_history = []
        self.analysis_thread = None
        self.current_analysis_index = 0
        self.ui_ready = False

        # Canli takip
        self.live_video_path = None
        self.live_video_worker = None
        self.live_total_frames = 0
        self.live_video_fps = 0.0
        self.live_slider_dragging = False
        self.live_start_frame = 0
        self.live_is_paused = False
        self.live_stop_requested = False

    def init_ui(self):
        """Ana UI'yi baslat"""
        self.setWindowTitle("Drone Obus Tespit Sistemi")
        self.setGeometry(50, 50, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        self.tabs = QTabWidget()

        # TAB 1: Analiz
        analysis_widget = QWidget()
        analysis_layout = QVBoxLayout()
        create_analysis_ui(analysis_layout, self)
        analysis_widget.setLayout(analysis_layout)
        self.tabs.addTab(analysis_widget, "Analiz")

        # TAB 2: Canli Takip
        live_widget = QWidget()
        live_layout = QVBoxLayout()
        create_live_analysis_ui(live_layout, self)
        live_widget.setLayout(live_layout)
        self.tabs.addTab(live_widget, "Canli Takip")

        # TAB 3: Model Egitimi
        training_widget = QWidget()
        training_layout = QVBoxLayout()
        create_training_ui(training_layout, self)
        training_widget.setLayout(training_layout)
        self.tabs.addTab(training_widget, "Model Egitimi")

        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(25)
        main_layout.insertWidget(1, self.progress_bar)

    # =========================================================
    # ANALIZ METODLARI
    # =========================================================

    def load_model(self):
        """YOLOv8 modelini yukle"""
        self.log("YOLO modeli yukleniyor...")
        try:
            self.detector = HowitzerDetector()
            if self.detector.model is None:
                self.log("YOLO modeli yuklenemedi")
                QMessageBox.warning(
                    self,
                    "YOLO Uyarisi",
                    "YOLO modeli yuklenemedi.\nUltralytics ve Torch kurulu mu kontrol edin.",
                )
            else:
                self.log("YOLO modeli basariyla yuklendi")
        except Exception as e:
            self.log(f"Model yukleme hatasi: {e}")
            QMessageBox.critical(self, "Model Hatasi", f"Model yuklenemedi: {e}")

    def browse_file(self):
        """Dosya sec"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Resim veya Video Sec (Coklu)",
            "",
            "Desteklenen Dosyalar (*.jpg *.jpeg *.png *.bmp *.mp4 *.avi *.mov *.mkv);;"
            "Resimler (*.jpg *.jpeg *.png *.bmp);;"
            "Videolar (*.mp4 *.avi *.mov *.mkv);;"
            "Tum Dosyalar (*)",
        )

        if not file_paths:
            return

        valid_files = []
        for file_path in file_paths:
            is_valid, error_msg = validate_file(file_path)
            if is_valid:
                valid_files.append(file_path)
            else:
                self.log(f"{Path(file_path).name} - {error_msg}")

        if not valid_files:
            QMessageBox.critical(self, "Hata", "Gecerli dosya yok!")
            return

        self.selected_files = valid_files
        self.current_file = None
        self.analysis_results = None
        self.analysis_history = []

        if len(valid_files) == 1:
            self.file_label.setText(f"Secili: {Path(valid_files[0]).name}")
        else:
            self.file_label.setText(f"Secili: {len(valid_files)} dosya")

        self.analyze_btn.setEnabled(True)
        self.update_results_display()

        preview = get_file_preview(valid_files[0])
        self._show_preview(preview)

        self.log(f"Secili: {len(valid_files)} dosya")

    def _show_preview(self, preview):
        """PIL preview'i QLabel uzerinde goster"""
        try:
            if preview is None or not hasattr(self, "preview_image"):
                return

            img = preview.convert("RGB")
            width, height = img.size
            data = img.tobytes("raw", "RGB")

            qimg = QImage(data, width, height, width * 3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)

            target_w = self.preview_image.width() if self.preview_image.width() > 0 else 250
            target_h = self.preview_image.height() if self.preview_image.height() > 0 else 250

            scaled = pixmap.scaled(
                target_w,
                target_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview_image.setPixmap(scaled)
            self.preview_image.setText("")
        except Exception as e:
            self.log(f"Onizleme gosterme hatasi: {e}")

    def update_threshold(self, *_args):
        """Guven esigini guncelle"""
        value = self.threshold_slider.value() / 100.0
        self.threshold_value_label.setText(f"{value:.0%}")
        if self.detector:
            self.detector.set_confidence_threshold(value)

    def start_analysis(self):
        """Analiz baslat"""
        if not self.selected_files:
            QMessageBox.warning(self, "Dosya Yok", "Lutfen once bir dosya secin")
            return

        if self.detector is None or self.detector.model is None:
            QMessageBox.warning(self, "Model Yok", "YOLO modeli yuklu degil")
            return

        self.analysis_history = []
        self.analysis_results = None
        self.current_analysis_index = 0

        self.log(f"Analiz baslaniyor: {len(self.selected_files)} dosya")
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self._analyze_next_file()

    def _analyze_next_file(self):
        """Dosyalari sira ile analiz et"""
        if self.current_analysis_index >= len(self.selected_files):
            self.log("Tum dosyalarin analizi tamamlandi")
            self.analyze_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            return

        file_path = self.selected_files[self.current_analysis_index]
        self.current_file = file_path

        self.log(
            f"Analiz: {self.current_analysis_index + 1}/{len(self.selected_files)} - "
            f"{Path(file_path).name}"
        )

        analysis_worker = AnalysisWorker(
            self.detector,
            file_path,
            self.metadata_extractor,
            self.report_generator,
        )
        analysis_worker.progress_update.connect(self.log)
        analysis_worker.frame_progress.connect(self.update_frame_progress)
        analysis_worker.analysis_complete.connect(self.on_analysis_complete)
        analysis_worker.error_occurred.connect(self.on_analysis_error)

        self.analysis_thread = analysis_worker
        self.analysis_thread.start()

    def update_frame_progress(self, current, total, confidence):
        """Video analizi sirasinda ilerleme guncelle"""
        if len(self.selected_files) == 1 and total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)

    def on_analysis_complete(self, results):
        """Analiz tamamlandiginda"""
        self.analysis_results = results
        self.analysis_history.append(results)
        self.update_results_display()
        self.log("Analiz tamamlandi")

        if len(self.selected_files) > 1:
            overall = int(((self.current_analysis_index + 1) / len(self.selected_files)) * 100)
            self.progress_bar.setValue(overall)

        self.current_analysis_index += 1
        self._analyze_next_file()

    def on_analysis_error(self, error_msg):
        """Analiz hatasinda"""
        self.log(f"Hata: {error_msg}")
        QMessageBox.critical(self, "Analiz Hatasi", f"Analiz basarisiz:\n{error_msg}")

        if len(self.selected_files) > 1:
            overall = int(((self.current_analysis_index + 1) / len(self.selected_files)) * 100)
            self.progress_bar.setValue(overall)

        self.current_analysis_index += 1
        self._analyze_next_file()

    def update_results_display(self):
        """Sonuc labellerini guncelle"""
        if not self.analysis_results:
            self.status_value.setText("N/A")
            self.conf_value.setText("N/A")
            self.capture_date_value.setText("N/A")
            self.capture_time_value.setText("N/A")
            self.gps_value.setText("N/A")
            self.time_video_value.setText("N/A")
            self.weapon_value.setText("N/A")
            self.crop_btn.setEnabled(False)
            self.export_excel_btn.setEnabled(False)
            self.export_json_btn.setEnabled(False)
            return

        detected = self.analysis_results.get("detected", False)
        self.status_value.setText("EVET" if detected else "HAYIR")
        self.status_value.setStyleSheet("color: green;" if detected else "color: red;")

        confidence = self.analysis_results.get("confidence", 0)
        self.conf_value.setText(f"{confidence:.2%}")

        self.capture_date_value.setText(self.analysis_results.get("capture_date", "N/A"))
        self.capture_time_value.setText(self.analysis_results.get("capture_time", "N/A"))

        gps_lat = self.analysis_results.get("gps_latitude")
        gps_lon = self.analysis_results.get("gps_longitude")
        if gps_lat is not None and gps_lon is not None:
            self.gps_value.setText(f"({gps_lat:.6f}, {gps_lon:.6f})")
        else:
            self.gps_value.setText("Mevcut degil")

        time_video = self.analysis_results.get("time_in_video")
        self.time_video_value.setText(time_video if time_video else "N/A")

        weapon_info = (
            self.analysis_results.get("weapon_type")
            or self.analysis_results.get("class_name")
            or "N/A"
        )
        self.weapon_value.setText(str(weapon_info))

        self.crop_btn.setEnabled(detected and self.analysis_results.get("crop_image") is not None)
        self.export_excel_btn.setEnabled(True)
        self.export_json_btn.setEnabled(True)

    def view_crop(self):
        """Kirpiyi goruntule"""
        if not self.analysis_results or self.analysis_results.get("crop_image") is None:
            QMessageBox.warning(self, "Kirpi Yok", "Tespit kirpisi mevcut degil")
            return

        crop_viewer = CropViewerWindow(
            self.analysis_results["crop_image"],
            self.analysis_results.get("confidence", 0),
            self,
        )
        crop_viewer.exec_()

    def export_excel(self):
        """Excel'e aktar"""
        if not self.analysis_results:
            QMessageBox.warning(self, "Tahmin Yok", "Lutfen once analiz yapin")
            return

        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Excel Dosyasini Kaydet",
                "",
                "Excel Dosyasi (*.xlsx)",
            )
            if not file_path:
                return

            result = self.report_generator.export_to_excel(self.analysis_results, file_path)
            if not result:
                raise RuntimeError("Excel dosyasi olusturulamadi")

            self.log(f"Excel'e kaydedildi: {file_path}")
            QMessageBox.information(self, "Basarili", f"Excel kaydedildi:\n{file_path}")
        except Exception as e:
            self.log(f"Excel aktarma hatasi: {e}")
            QMessageBox.critical(self, "Hata", f"Excel aktarilamadi: {e}")

    def export_json(self):
        """JSON'a aktar"""
        if not self.analysis_results:
            QMessageBox.warning(self, "Tahmin Yok", "Lutfen once analiz yapin")
            return

        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "JSON Dosyasini Kaydet",
                "",
                "JSON Dosyasi (*.json)",
            )
            if not file_path:
                return

            result = self.report_generator.export_to_json(self.analysis_results, file_path)
            if not result:
                raise RuntimeError("JSON dosyasi olusturulamadi")

            self.log(f"JSON'a kaydedildi: {file_path}")
            QMessageBox.information(self, "Basarili", f"JSON kaydedildi:\n{file_path}")
        except Exception as e:
            self.log(f"JSON aktarma hatasi: {e}")
            QMessageBox.critical(self, "Hata", f"JSON aktarilamadi: {e}")

    # =========================================================
    # CANLI TAKIP METODLARI
    # =========================================================

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
        if self.live_video_fps <= 0:
            return "00:00"
        return self._format_time_text(frame_index / self.live_video_fps)

    def reset_live_tracking_ui(self):
        """Canli takip arayuzunu sifirla"""
        if hasattr(self, "live_status_label"):
            self.live_status_label.setText("Hazir")
        if hasattr(self, "live_stats_label"):
            self.live_stats_label.setText("Frame: 0 | Tespit: 0 | FPS: 0.00")
        if hasattr(self, "live_last_detection_label"):
            self.live_last_detection_label.setText("Son tespit: Yok")
        if hasattr(self, "live_log_text"):
            self.live_log_text.clear()
        if hasattr(self, "live_video_label"):
            self.live_video_label.clear()
            self.live_video_label.setText("Canli analiz goruntusu burada gosterilecek")
        if hasattr(self, "live_timeline_slider"):
            self.live_timeline_slider.blockSignals(True)
            self.live_timeline_slider.setRange(0, 0)
            self.live_timeline_slider.setValue(0)
            self.live_timeline_slider.blockSignals(False)
        if hasattr(self, "live_current_time_label"):
            self.live_current_time_label.setText("00:00")
        if hasattr(self, "live_total_time_label"):
            self.live_total_time_label.setText("00:00")

    def _set_live_frame_to_label(self, frame_bgr):
        """OpenCV frame'i QLabel'da goster"""
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimg)

        scaled = pixmap.scaled(
            self.live_video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.live_video_label.setPixmap(scaled)

    def _annotate_preview_frame(self, frame):
        """Onizleme icin tek frame uzerinde mavi kutu ciz"""
        if self.detector is None or self.detector.model is None:
            return frame, None

        try:
            results = self.detector.model(frame, device=self.detector.device, verbose=False)
            annotated = frame.copy()
            last_text = None

            if results and len(results[0].boxes) > 0:
                boxes = results[0].boxes
                confidences = boxes.conf.cpu().numpy()
                class_ids = (
                    boxes.cls.cpu().numpy().astype(int)
                    if hasattr(boxes, "cls")
                    else []
                )

                for i, conf in enumerate(confidences):
                    if conf < self.detector.confidence_threshold:
                        continue

                    box = boxes.xyxy[i].cpu().numpy().astype(int)
                    cls_id = int(class_ids[i]) if len(class_ids) > i else 0
                    class_name = self.detector._resolve_class_name(results[0], cls_id)

                    x1, y1, x2, y2 = box[0], box[1], box[2], box[3]

                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    cv2.putText(
                        annotated,
                        f"{class_name} {conf:.2f}",
                        (x1, max(20, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (255, 0, 0),
                        2,
                    )
                    last_text = f"Son tespit: {class_name} | {conf:.2%}"

            return annotated, last_text
        except Exception as e:
            self.log(f"Canli onizleme annotate hatasi: {e}")
            return frame, None

    def _show_live_preview_frame(self, frame_index: int):
        """Secili frame'i ekranda goster"""
        if not self.live_video_path:
            return

        cap = cv2.VideoCapture(self.live_video_path)
        if not cap.isOpened():
            return

        try:
            if frame_index < 0:
                frame_index = 0

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = cap.read()
            if not ret or frame is None:
                return

            annotated, last_text = self._annotate_preview_frame(frame)
            self._set_live_frame_to_label(annotated)

            if last_text:
                self.live_last_detection_label.setText(last_text)
            else:
                self.live_last_detection_label.setText("Son tespit: Yok")
        finally:
            cap.release()

    def _load_live_video_metadata(self, file_path: str):
        """Video metadata yukle"""
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise RuntimeError("Video metadata okunamadi")

        try:
            self.live_total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.live_video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        finally:
            cap.release()

        if hasattr(self, "live_timeline_slider"):
            self.live_timeline_slider.blockSignals(True)
            self.live_timeline_slider.setRange(0, max(0, self.live_total_frames - 1))
            self.live_timeline_slider.setValue(0)
            self.live_timeline_slider.blockSignals(False)

        if hasattr(self, "live_current_time_label"):
            self.live_current_time_label.setText("00:00")
        if hasattr(self, "live_total_time_label"):
            total_seconds = (
                self.live_total_frames / self.live_video_fps
                if self.live_video_fps > 0
                else 0
            )
            self.live_total_time_label.setText(self._format_time_text(total_seconds))

    def select_live_video(self):
        """Canli takip icin video sec"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Canli Takip Icin Video Sec",
            "",
            "Video Dosyalari (*.mp4 *.avi *.mov *.mkv *.flv);;Tum Dosyalar (*)",
        )

        if not file_path:
            return

        is_valid, error_msg = validate_file(file_path)
        if not is_valid:
            QMessageBox.critical(self, "Gecersiz Dosya", error_msg)
            return

        self.live_video_path = file_path
        self.live_start_frame = 0
        self.live_is_paused = False

        self.reset_live_tracking_ui()
        self.live_video_file_label.setText(Path(file_path).name)
        self.live_play_btn.setEnabled(True)
        self.live_pause_btn.setEnabled(False)
        self.live_stop_btn.setEnabled(False)

        try:
            self._load_live_video_metadata(file_path)
            self._show_live_preview_frame(0)
            self.live_log_text.append(f"Video secildi: {Path(file_path).name}")
            self.live_status_label.setText("Hazir")
        except Exception as e:
            QMessageBox.critical(self, "Video Hatasi", str(e))
            self.live_video_path = None
            self.live_video_file_label.setText("Video secilmedi")

    def start_live_video_tracking(self):
        """Canli video takibini baslat veya devam ettir"""
        if not self.live_video_path:
            QMessageBox.warning(self, "Video Yok", "Lutfen once video secin")
            return

        if self.detector is None or self.detector.model is None:
            QMessageBox.critical(self, "Model Yok", "Yuklu bir model bulunamadi")
            return

        if self.live_video_worker is not None and self.live_video_worker.isRunning():
            if self.live_is_paused:
                self.live_video_worker.resume()
                self.live_is_paused = False
                self.live_status_label.setText("Oynatiliyor")
                self.live_log_text.append("Canli takip devam ettirildi")
                self.live_play_btn.setEnabled(False)
                self.live_pause_btn.setEnabled(True)
                self.live_stop_btn.setEnabled(True)
            return

        self.live_stop_requested = False
        start_frame = self.live_timeline_slider.value() if hasattr(self, "live_timeline_slider") else 0
        self.live_start_frame = start_frame
        self.live_is_paused = False

        self.live_status_label.setText("Oynatiliyor")
        self.live_log_text.append(f"Canli video takibi baslatildi (frame: {start_frame})")

        self.live_play_btn.setEnabled(False)
        self.live_pause_btn.setEnabled(True)
        self.live_stop_btn.setEnabled(True)
        self.live_select_video_btn.setEnabled(False)

        self.live_video_worker = LiveVideoWorker(
            self.detector,
            self.live_video_path,
            start_frame=start_frame,
        )
        self.live_video_worker.frame_ready.connect(self.on_live_frame_ready)
        self.live_video_worker.status_update.connect(self.on_live_status_update)
        self.live_video_worker.stats_update.connect(self.on_live_stats_update)
        self.live_video_worker.log_update.connect(self.on_live_log_update)
        self.live_video_worker.detection_update.connect(self.on_live_detection_update)
        self.live_video_worker.position_update.connect(self.on_live_position_update)
        self.live_video_worker.media_info_loaded.connect(self.on_live_media_info_loaded)
        self.live_video_worker.error_occurred.connect(self.on_live_error)
        self.live_video_worker.finished_signal.connect(self.on_live_finished)
        self.live_video_worker.start()

    def pause_live_video_tracking(self):
        """Canli video takibini duraklat"""
        if self.live_video_worker is None or not self.live_video_worker.isRunning():
            return

        self.live_video_worker.pause()
        self.live_is_paused = True
        self.live_status_label.setText("Duraklatildi")
        self.live_log_text.append("Canli takip duraklatildi")
        self.live_play_btn.setEnabled(True)
        self.live_pause_btn.setEnabled(False)
        self.live_stop_btn.setEnabled(True)

    def stop_live_video_tracking(self):
        """Canli video takibini durdur"""
        if self.live_video_worker is not None and self.live_video_worker.isRunning():
            self.live_stop_requested = True
            self.live_video_worker.stop()
            self.live_status_label.setText("Durduruluyor...")
            self.live_log_text.append("Durdurma komutu verildi...")

    def on_live_slider_pressed(self):
        """Zaman cubugu tutuldu"""
        self.live_slider_dragging = True

    def on_live_slider_moved(self, value):
        """Zaman cubugu tasinirken zaman etiketini guncelle"""
        if hasattr(self, "live_current_time_label"):
            self.live_current_time_label.setText(self._frame_to_time_text(value))

    def on_live_slider_released(self):
        """Zaman cubugu birakildiginda seek yap"""
        self.live_slider_dragging = False

        if not hasattr(self, "live_timeline_slider"):
            return

        target_frame = self.live_timeline_slider.value()
        self.live_start_frame = target_frame

        if hasattr(self, "live_current_time_label"):
            self.live_current_time_label.setText(self._frame_to_time_text(target_frame))

        if self.live_video_worker is not None and self.live_video_worker.isRunning():
            self.live_video_worker.seek_to_frame(target_frame)
            if self.live_is_paused:
                self._show_live_preview_frame(target_frame)
            self.live_log_text.append(f"Seek yapildi: {self._frame_to_time_text(target_frame)}")
        else:
            self._show_live_preview_frame(target_frame)

    def on_live_frame_ready(self, qimage):
        """Yeni canli frame geldiginde"""
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            self.live_video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.live_video_label.setPixmap(scaled)

    def on_live_status_update(self, message: str):
        """Canli durum guncelle"""
        self.live_status_label.setText(message)

    def on_live_stats_update(self, message: str):
        """Canli istatistik guncelle"""
        self.live_stats_label.setText(message)

    def on_live_log_update(self, message: str):
        """Canli log guncelle"""
        self.live_log_text.append(message)

    def on_live_detection_update(self, message: str):
        """Canli tespit logu"""
        self.live_last_detection_label.setText(f"Son tespit: {message}")
        self.live_log_text.append(f"[Tespit] {message}")

    def on_live_media_info_loaded(self, total_frames: int, fps: float, total_time_text: str):
        """Worker medya bilgisini gonderince"""
        self.live_total_frames = total_frames
        self.live_video_fps = fps

        if hasattr(self, "live_timeline_slider"):
            self.live_timeline_slider.blockSignals(True)
            self.live_timeline_slider.setRange(0, max(0, total_frames - 1))
            self.live_timeline_slider.blockSignals(False)

        if hasattr(self, "live_total_time_label"):
            self.live_total_time_label.setText(total_time_text)

    def on_live_position_update(self, current_frame: int, total_frames: int, current_time_text: str, total_time_text: str):
        """Worker pozisyon guncellemesi"""
        self.live_start_frame = current_frame

        if not self.live_slider_dragging and hasattr(self, "live_timeline_slider"):
            self.live_timeline_slider.blockSignals(True)
            self.live_timeline_slider.setValue(current_frame)
            self.live_timeline_slider.blockSignals(False)

        if hasattr(self, "live_current_time_label"):
            self.live_current_time_label.setText(current_time_text)
        if hasattr(self, "live_total_time_label"):
            self.live_total_time_label.setText(total_time_text)

    def on_live_error(self, error_msg: str):
        """Canli takip hatasi"""
        self.live_log_text.append(f"HATA: {error_msg}")
        QMessageBox.critical(self, "Canli Takip Hatasi", error_msg)

    def on_live_finished(self):
        """Canli takip bitince"""
        self.live_select_video_btn.setEnabled(True)
        self.live_play_btn.setEnabled(self.live_video_path is not None)
        self.live_pause_btn.setEnabled(False)
        self.live_stop_btn.setEnabled(False)
        self.live_is_paused = False

        if self.live_stop_requested:
            self.live_status_label.setText("Durduruldu")
            self.live_log_text.append("Canli takip durduruldu")
        else:
            self.live_status_label.setText("Tamamlandi")
            self.live_log_text.append("Canli takip sonlandi")

        self.live_video_worker = None
        self.live_stop_requested = False

    # =========================================================
    # EGITIM METODLARI
    # =========================================================

    def _training_root(self) -> Path:
        return Path(getattr(config, "TRAINING_DATA_DIR", Path(config.PROJECT_ROOT) / "training_data"))

    def _get_available_categories(self):
        """training_data altindaki mevcut kategorileri getir"""
        training_data_dir = self._training_root()
        if not training_data_dir.exists():
            return ["default"]

        categories = []
        for item in training_data_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                if (item / "images").exists() and (item / "labels").exists():
                    categories.append(item.name)

        return categories if categories else ["default"]

    def _refresh_all_category_combos(self):
        """Tum kategori combolarini yenile"""
        categories = self._get_available_categories()

        if hasattr(self, "upload_category_combo"):
            current_text = self.upload_category_combo.currentText()
            self.upload_category_combo.clear()
            self.upload_category_combo.addItems(categories)
            index = self.upload_category_combo.findText(current_text)
            if index >= 0:
                self.upload_category_combo.setCurrentIndex(index)

        if hasattr(self, "training_category_combo"):
            current_text = self.training_category_combo.currentText()
            self.training_category_combo.clear()
            self.training_category_combo.addItems(categories)
            index = self.training_category_combo.findText(current_text)
            if index >= 0:
                self.training_category_combo.setCurrentIndex(index)

        if hasattr(self, "content_category_combo"):
            current_text = self.content_category_combo.currentText()
            self.content_category_combo.clear()
            self.content_category_combo.addItems(categories)
            index = self.content_category_combo.findText(current_text)
            if index >= 0:
                self.content_category_combo.setCurrentIndex(index)

    def refresh_upload_categories(self):
        self._refresh_all_category_combos()
        self.log("Upload kategorileri yenilendi")

    def refresh_training_categories(self):
        self._refresh_all_category_combos()
        self.log("Egitim kategorileri yenilendi")

    def refresh_content_categories(self):
        self._refresh_all_category_combos()
        self.log("Icerik kategorileri yenilendi")

    def browse_training_images(self):
        """Egitim resimlerini yukle"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Egitim Resimlerini Sec",
            "",
            "Resim Dosyalari (*.jpg *.png *.jpeg *.bmp *.tiff);;Tum Dosyalar (*)",
        )
        if not files:
            return

        category = self.upload_category_combo.currentText()
        split = self.upload_split_combo.currentText()

        try:
            copied_count = 0
            for file_path in files:
                if self.model_trainer.copy_image_to_category(
                    file_path,
                    category=category,
                    dataset_split=split,
                ):
                    self.upload_history_list.addItem(
                        f"Resim: {Path(file_path).name} -> {category}/{split}"
                    )
                    copied_count += 1
                else:
                    self.upload_history_list.addItem(f"Hata: {Path(file_path).name}")

            msg = f"{copied_count}/{len(files)} resim '{category}' kategorisine yuklendi."
            QMessageBox.information(self, "Basarili", msg)
            self.train_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Resim yukleme hatasi: {e}")

    def browse_training_labels(self):
        """Egitim label dosyalarini yukle"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Egitim Labellarini Sec",
            "",
            "Label Dosyalari (*.txt);;Tum Dosyalar (*)",
        )
        if not files:
            return

        category = self.upload_category_combo.currentText()
        split = self.upload_split_combo.currentText()

        try:
            copied_count = 0
            for file_path in files:
                if self.model_trainer.copy_label_to_category(
                    file_path,
                    category=category,
                    dataset_split=split,
                ):
                    self.upload_history_list.addItem(
                        f"Label: {Path(file_path).name} -> {category}/{split}"
                    )
                    copied_count += 1
                else:
                    self.upload_history_list.addItem(f"Hata: {Path(file_path).name}")

            msg = f"{copied_count}/{len(files)} label '{category}' kategorisine yuklendi."
            QMessageBox.information(self, "Basarili", msg)
            self.train_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Label yukleme hatasi: {e}")

    def extract_video_frames(self):
        """Video'dan frame cikar"""
        video_path, _ = QFileDialog.getOpenFileName(
            self,
            "Egitim Video'sunu Sec",
            "",
            "Video Dosyalari (*.mp4 *.avi *.mov *.mkv *.flv);;Tum Dosyalar (*)",
        )

        if not video_path:
            return

        dialog = VideoFrameExtractionDialog(self._get_available_categories(), self)
        if dialog.exec_() == VideoFrameExtractionDialog.Accepted:
            values = dialog.get_values()

            self.training_progress.setVisible(True)
            self.training_progress.setValue(0)
            self.train_btn.setEnabled(False)

            try:
                self.training_log.append(f"Video isleniyor: {Path(video_path).name}")
                self.training_log.append(f"  - Kategori: {values['category']}")
                self.training_log.append(f"  - Split: {values['dataset_split']}")

                frame_count, frame_paths = self.model_trainer.extract_frames_from_video(
                    video_path,
                    frame_interval=values["frame_interval"],
                    max_frames=values["max_frames"],
                    dataset_split=values["dataset_split"],
                    category=values["category"],
                    progress_callback=lambda p, m: self.training_log.append(f"[Video] {m}"),
                )

                if frame_count > 0:
                    self.training_log.append(f"{frame_count} frame cikartildi")
                    QMessageBox.information(
                        self,
                        "Basarili",
                        f"{frame_count} frame cikartildi.\n"
                        "Label dosyalarini harici arac ile hazirlayabilirsiniz.",
                    )
                else:
                    self.training_log.append("Video isleme basarisiz")
                    QMessageBox.warning(self, "Hata", "Video islenemedi!")

            except Exception as e:
                self.training_log.append(f"HATA: {e}")
                QMessageBox.critical(self, "Video Isleme Hatasi", str(e))
            finally:
                self.training_progress.setVisible(False)
                self.train_btn.setEnabled(True)

    def refresh_categories_list(self):
        """Kategori listesini yenile"""
        self.categories_list.clear()
        for cat in self._get_available_categories():
            self.categories_list.addItem(cat)

    def refresh_content_display(self):
        """Icerigi yenile"""
        category = self.content_category_combo.currentText()
        split = self.content_split_combo.currentText()

        category_path = self._training_root() / category

        self.content_images_list.clear()
        images_dir = category_path / "images" / split
        if images_dir.exists():
            for img_file in sorted(images_dir.glob("*")):
                self.content_images_list.addItem(img_file.name)

        self.content_labels_list.clear()
        labels_dir = category_path / "labels" / split
        if labels_dir.exists():
            for lbl_file in sorted(labels_dir.glob("*.txt")):
                self.content_labels_list.addItem(lbl_file.name)

        img_count = self.content_images_list.count()
        lbl_count = self.content_labels_list.count()
        self.content_stats_label.setText(f"Resimler: {img_count} | Labellar: {lbl_count}")

    def delete_selected_images(self):
        """Secili resimleri sil"""
        category = self.content_category_combo.currentText()
        split = self.content_split_combo.currentText()

        selected_items = self.content_images_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyari", "Silmek icin resim seciniz!")
            return

        reply = QMessageBox.question(
            self,
            "Onay",
            f"{len(selected_items)} resmi silmek istediginize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            deleted_count = 0
            images_dir = self._training_root() / category / "images" / split

            for item in selected_items:
                file_path = images_dir / item.text()
                if file_path.exists() and file_path.is_file():
                    file_path.unlink()
                    deleted_count += 1

            QMessageBox.information(self, "Basarili", f"{deleted_count} resim silindi!")
            self.refresh_content_display()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatasi: {e}")

    def delete_selected_labels(self):
        """Secili labellari sil"""
        category = self.content_category_combo.currentText()
        split = self.content_split_combo.currentText()

        selected_items = self.content_labels_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyari", "Silmek icin label seciniz!")
            return

        reply = QMessageBox.question(
            self,
            "Onay",
            f"{len(selected_items)} label'i silmek istediginize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            deleted_count = 0
            labels_dir = self._training_root() / category / "labels" / split

            for item in selected_items:
                file_path = labels_dir / item.text()
                if file_path.exists() and file_path.is_file():
                    file_path.unlink()
                    deleted_count += 1

            QMessageBox.information(self, "Basarili", f"{deleted_count} label silindi!")
            self.refresh_content_display()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatasi: {e}")

    def delete_all_content(self):
        """Tum icerigi sil"""
        category = self.content_category_combo.currentText()
        split = self.content_split_combo.currentText()

        img_count = self.content_images_list.count()
        lbl_count = self.content_labels_list.count()

        if img_count + lbl_count == 0:
            QMessageBox.warning(self, "Uyari", "Silinecek dosya yok!")
            return

        reply = QMessageBox.warning(
            self,
            "Dikkat!",
            f"'{category}/{split}' icindeki TUM dosyalari sileceksiniz!\n"
            f"Resimler: {img_count}\nLabellar: {lbl_count}\n\n"
            f"Devam etmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        try:
            deleted_count = 0

            images_dir = self._training_root() / category / "images" / split
            if images_dir.exists():
                for img_file in images_dir.glob("*"):
                    if img_file.is_file():
                        img_file.unlink()
                        deleted_count += 1

            labels_dir = self._training_root() / category / "labels" / split
            if labels_dir.exists():
                for lbl_file in labels_dir.glob("*.txt"):
                    if lbl_file.is_file():
                        lbl_file.unlink()
                        deleted_count += 1

            QMessageBox.information(self, "Basarili", f"Toplam {deleted_count} dosya silindi!")
            self.refresh_content_display()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatasi: {e}")

    def create_new_category(self):
        """Yeni kategori olustur"""
        category_name = self.new_category_input.text().strip()

        if not category_name:
            QMessageBox.warning(self, "Hata", "Kategori adi bos olamaz!")
            return

        if not category_name.replace("_", "").replace("-", "").isalnum():
            QMessageBox.warning(
                self,
                "Hata",
                "Kategori adi sadece alfanumerik ve - _ icerebilir!",
            )
            return

        try:
            base_path = self._training_root() / category_name
            (base_path / "images" / "train").mkdir(parents=True, exist_ok=True)
            (base_path / "images" / "val").mkdir(parents=True, exist_ok=True)
            (base_path / "images" / "test").mkdir(parents=True, exist_ok=True)
            (base_path / "labels" / "train").mkdir(parents=True, exist_ok=True)
            (base_path / "labels" / "val").mkdir(parents=True, exist_ok=True)
            (base_path / "labels" / "test").mkdir(parents=True, exist_ok=True)

            self.new_category_input.clear()
            self.refresh_categories_list()
            self._refresh_all_category_combos()

            QMessageBox.information(self, "Basarili", f"Kategori '{category_name}' olusturuldu!")
            self.log(f"Kategori olusturuldu: {category_name}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kategori olusturulamadi: {e}")

    def rename_category(self):
        """Kategoriyi yeniden adlandir"""
        selected_items = self.categories_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyari", "Once bir kategori seciniz!")
            return

        old_name = selected_items[0].text()
        new_name, ok = QInputDialog.getText(
            self,
            "Kategoriyi Yeniden Adlandir",
            f"Yeni ad (su an: {old_name}):",
        )

        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()

        try:
            old_path = self._training_root() / old_name
            new_path = self._training_root() / new_name
            old_path.rename(new_path)

            self.refresh_categories_list()
            self._refresh_all_category_combos()

            QMessageBox.information(self, "Basarili", f"'{old_name}' -> '{new_name}'")
            self.log(f"Kategori yeniden adlandirildi: {old_name} -> {new_name}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Yeniden adlandirma hatasi: {e}")

    def delete_category(self):
        """Kategoriyi sil"""
        selected_items = self.categories_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyari", "Once bir kategori seciniz!")
            return

        category_name = selected_items[0].text()

        reply = QMessageBox.warning(
            self,
            "Dikkat!",
            f"'{category_name}' kategorisini ve tum icerigini sileceksiniz!\n\n"
            f"Bu islem geri alinamaz!",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        try:
            import shutil

            category_path = self._training_root() / category_name
            shutil.rmtree(category_path)

            self.refresh_categories_list()
            self._refresh_all_category_combos()

            QMessageBox.information(self, "Basarili", f"'{category_name}' silindi!")
            self.log(f"Kategori silindi: {category_name}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatasi: {e}")

    def start_training(self):
        """Model egitimini baslat"""
        category = self.training_category_combo.currentText()

        if category == "default":
            QMessageBox.warning(self, "Hata", "Gecerli bir kategori seciniz!")
            return

        category_path = self._training_root() / category
        train_images = list((category_path / "images" / "train").glob("*")) if (category_path / "images" / "train").exists() else []
        train_labels = list((category_path / "labels" / "train").glob("*.txt")) if (category_path / "labels" / "train").exists() else []

        if len(train_images) == 0 or len(train_labels) == 0:
            QMessageBox.warning(
                self,
                "Hata",
                f"'{category}' kategorisinde yeterli egitim verisi yok!\n"
                f"Images: {len(train_images)}, Labels: {len(train_labels)}",
            )
            return

        self.train_btn.setEnabled(False)
        self.training_progress.setVisible(True)
        self.training_progress.setValue(0)

        try:
            self.training_log.clear()
            self.training_log.append(f"Kategori '{category}' icin model egitimi baslaniyor...")

            class_names = getattr(config, "CLASS_NAMES", ["obus"])
            self.training_log.append(f"Siniflar: {class_names}")
            self.training_log.append("Dataset YAML olusturuluyor...")

            yaml_path = self.model_trainer.create_dataset_yaml(
                category=category,
                class_names=class_names,
            )

            if not yaml_path:
                raise RuntimeError("Dataset YAML olusturulamadi.")

            self.training_log.append(f"YAML hazir: {yaml_path}")
            self.training_log.append("Dataset dogrulaniyor...")

            validation = self.model_trainer.validate_dataset(
                category=category,
                class_names=class_names,
            )

            for split, split_stats in validation.get("stats", {}).items():
                self.training_log.append(
                    f"[{split}] images={split_stats.get('images', 0)}, "
                    f"labels={split_stats.get('labels', 0)}, "
                    f"invalid_lines={split_stats.get('invalid_label_lines', 0)}"
                )

            if not validation.get("ok", False):
                first_errors = validation.get("errors", [])[:10]
                error_text = "\n".join(first_errors) if first_errors else "Bilinmeyen dataset hatasi"
                self.training_log.append("Dataset dogrulama basarisiz:")
                self.training_log.append(error_text)
                raise RuntimeError(error_text)

            self.training_log.append("Model egitimi baslaniyor...")

            trained_model_path = self.model_trainer.train_model(
                category=category,
                epochs=self.epoch_spinbox.value(),
                batch_size=self.batch_spinbox.value(),
                imgsz=self.imgsz_spinbox.value(),
                progress_callback=lambda e, m: self.training_log.append(f"[Epoch {e}] {m}"),
                class_names=class_names,
            )

            if trained_model_path:
                self.training_log.append(f"Egitim tamamlandi! Model: {trained_model_path}")
                self.training_progress.setValue(100)
                QMessageBox.information(self, "Basarili", "Model egitimi tamamlandi!")
                self.log(f"Model egitimi tamamlandi: {category}")
            else:
                raise RuntimeError("Egitim tamamlanamadi veya model kaydedilemedi.")

        except Exception as e:
            self.training_log.append(f"HATA: {e}")
            QMessageBox.critical(self, "Egitim Hatasi", f"Egitim basarisiz: {e}")
            self.log(f"Egitim hatasi: {e}")
        finally:
            self.train_btn.setEnabled(True)
            self.training_progress.setVisible(False)

    def log(self, message: str):
        """Gunluge mesaj ekle"""
        if not self.ui_ready or not hasattr(self, "log_text") or self.log_text is None:
            print(f"[LOG] {message}")
            return

        try:
            current_text = self.log_text.toPlainText()
            timestamp = datetime.now().strftime("%H:%M:%S")
            new_message = f"[{timestamp}] {message}"

            if current_text.strip():
                self.log_text.setText(f"{current_text}\n{new_message}")
            else:
                self.log_text.setText(new_message)

            scrollbar = self.log_text.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())
        except Exception:
            pass


def main():
    """Ana giris noktasi"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()