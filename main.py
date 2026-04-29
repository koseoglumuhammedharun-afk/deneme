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
    QHBoxLayout,
    QGridLayout,
    QTabWidget,
    QMessageBox,
    QFileDialog,
    QProgressBar,
    QInputDialog,
    QDialog,
    QScrollArea,
    QLabel,
    QPushButton,
    QComboBox,
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread
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


class TrainingTaskWorker(QObject):
    """
    Egitim islemlerini GUI'yi dondurmadan calistiran worker.

    Desteklenen modlar:
    - category_train: Secili kategoriyi egitir.
    - prepare_combined: Kategorileri birlestirip weapon_dataset olusturur.
    - combined_train: Kategorileri birlestirir ve final modeli egitir.
    """

    progress_update = pyqtSignal(int, str)
    log_update = pyqtSignal(str)
    task_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, model_trainer: ModelTrainer, mode: str, payload: dict):
        super().__init__()
        self.model_trainer = model_trainer
        self.mode = mode
        self.payload = payload or {}

    def run(self):
        try:
            if self.mode == "category_train":
                self._run_category_training()
            elif self.mode == "prepare_combined":
                self._run_prepare_combined_dataset()
            elif self.mode == "combined_train":
                self._run_combined_training()
            else:
                raise RuntimeError(f"Bilinmeyen egitim gorevi: {self.mode}")
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()

    def _emit_progress(self, percent: int, message: str):
        try:
            percent = int(percent)
        except Exception:
            percent = 0

        self.progress_update.emit(percent, str(message))

    def _progress_callback(self, percent: int, message: str):
        self._emit_progress(percent, message)

    def _log_validation(self, validation: dict):
        for split, split_stats in validation.get("stats", {}).items():
            self.log_update.emit(
                f"[{split}] images={split_stats.get('images', 0)}, "
                f"labels={split_stats.get('labels', 0)}, "
                f"invalid_lines={split_stats.get('invalid_label_lines', 0)}"
            )

    def _run_category_training(self):
        category = self.payload.get("category", "default")
        epochs = self.payload.get("epochs", 50)
        batch_size = self.payload.get("batch_size", 16)
        imgsz = self.payload.get("imgsz", 640)
        class_names = self.payload.get("class_names") or list(getattr(config, "CLASS_NAMES", ["obus"]))

        self._emit_progress(0, f"Kategori '{category}' icin egitim hazirlaniyor...")
        self.log_update.emit(f"Kategori '{category}' icin model egitimi baslaniyor...")
        self.log_update.emit(f"Siniflar: {class_names}")
        self.log_update.emit("Dataset YAML olusturuluyor...")

        yaml_path = self.model_trainer.create_dataset_yaml(
            category=category,
            class_names=class_names,
        )

        if not yaml_path:
            raise RuntimeError("Dataset YAML olusturulamadi.")

        self.log_update.emit(f"YAML hazir: {yaml_path}")
        self.log_update.emit("Dataset dogrulaniyor...")

        validation = self.model_trainer.validate_dataset(
            category=category,
            class_names=class_names,
        )

        self._log_validation(validation)

        if not validation.get("ok", False):
            first_errors = validation.get("errors", [])[:10]
            error_text = "\n".join(first_errors) if first_errors else "Bilinmeyen dataset hatasi"
            self.log_update.emit("Dataset dogrulama basarisiz:")
            self.log_update.emit(error_text)
            raise RuntimeError(error_text)

        self.log_update.emit("Model egitimi baslaniyor...")

        trained_model_path = self.model_trainer.train_model(
            category=category,
            epochs=epochs,
            batch_size=batch_size,
            imgsz=imgsz,
            progress_callback=self._progress_callback,
            class_names=class_names,
            clear_cache=True,
        )

        if not trained_model_path:
            raise RuntimeError("Egitim tamamlanamadi veya model kaydedilemedi.")

        self._emit_progress(100, "Egitim tamamlandi!")
        self.task_complete.emit(f"Egitim tamamlandi! Model: {trained_model_path}")

    def _run_prepare_combined_dataset(self):
        source_categories = self.payload.get("source_categories") or []
        target_category = self.payload.get("target_category", "weapon_dataset")
        class_names = self.payload.get("class_names") or list(getattr(config, "CLASS_NAMES", ["obus"]))

        self._emit_progress(0, "Birlesik dataset hazirlaniyor...")
        self.log_update.emit("Birlesik dataset hazirlama basladi...")
        self.log_update.emit(f"Kaynak kategoriler: {source_categories}")
        self.log_update.emit(f"Hedef dataset: {target_category}")

        summary = self.model_trainer.prepare_combined_dataset(
            source_categories=source_categories,
            target_category=target_category,
            overwrite=True,
            class_names=class_names,
            progress_callback=self._progress_callback,
        )

        validation = summary.get("validation", {})

        self.log_update.emit("")
        self.log_update.emit("Birlesik dataset ozeti:")
        self.log_update.emit(f"Hedef klasor: {summary.get('target_dir')}")
        self.log_update.emit(f"Kopyalanan resim: {summary.get('copied_images', 0)}")
        self.log_update.emit(f"Kopyalanan label: {summary.get('copied_labels', 0)}")
        self.log_update.emit(f"Eksik label: {summary.get('missing_labels', 0)}")
        self.log_update.emit(f"Atlanan dosya: {summary.get('skipped_files', 0)}")

        for split, split_stats in summary.get("split_stats", {}).items():
            self.log_update.emit(
                f"[{split}] images={split_stats.get('images', 0)}, "
                f"labels={split_stats.get('labels', 0)}"
            )

        if validation:
            self.log_update.emit("")
            self.log_update.emit("Birlesik dataset dogrulama:")
            self._log_validation(validation)

        if not validation.get("ok", False):
            first_errors = validation.get("errors", [])[:10]
            error_text = "\n".join(first_errors) if first_errors else "Bilinmeyen dataset hatasi"
            raise RuntimeError(error_text)

        self._emit_progress(100, "Birlesik dataset hazirlandi.")
        self.task_complete.emit(
            f"Birlesik dataset hazirlandi: {target_category}\n"
            f"Kopyalanan resim: {summary.get('copied_images', 0)}\n"
            f"Kopyalanan label: {summary.get('copied_labels', 0)}"
        )

    def _run_combined_training(self):
        source_categories = self.payload.get("source_categories") or []
        target_category = self.payload.get("target_category", "weapon_dataset")
        epochs = self.payload.get("epochs", 50)
        batch_size = self.payload.get("batch_size", 16)
        imgsz = self.payload.get("imgsz", 640)
        class_names = self.payload.get("class_names") or list(getattr(config, "CLASS_NAMES", ["obus"]))

        self._emit_progress(0, "Birlesik final model egitimi hazirlaniyor...")
        self.log_update.emit("Birlesik final model egitimi baslaniyor...")
        self.log_update.emit(f"Kaynak kategoriler: {source_categories}")
        self.log_update.emit(f"Hedef dataset: {target_category}")
        self.log_update.emit(f"Siniflar: {class_names}")

        summary = self.model_trainer.prepare_combined_dataset(
            source_categories=source_categories,
            target_category=target_category,
            overwrite=True,
            class_names=class_names,
            progress_callback=self._progress_callback,
        )

        validation = summary.get("validation", {})

        self.log_update.emit("")
        self.log_update.emit("Birlesik dataset ozeti:")
        self.log_update.emit(f"Kopyalanan resim: {summary.get('copied_images', 0)}")
        self.log_update.emit(f"Kopyalanan label: {summary.get('copied_labels', 0)}")
        self.log_update.emit(f"Eksik label: {summary.get('missing_labels', 0)}")
        self.log_update.emit(f"Atlanan dosya: {summary.get('skipped_files', 0)}")

        self._log_validation(validation)

        if not validation.get("ok", False):
            first_errors = validation.get("errors", [])[:10]
            error_text = "\n".join(first_errors) if first_errors else "Bilinmeyen dataset hatasi"
            raise RuntimeError(error_text)

        self.log_update.emit("")
        self.log_update.emit("Birlesik dataset hazir. Final model egitimi basliyor...")

        def mapped_progress_callback(percent: int, message: str):
            try:
                percent = int(percent)
            except Exception:
                percent = 0

            if percent < 0:
                mapped_percent = percent
            else:
                mapped_percent = 20 + int((max(0, min(100, percent)) / 100.0) * 80)
                mapped_percent = max(20, min(100, mapped_percent))

            self._emit_progress(mapped_percent, message)

        trained_model_path = self.model_trainer.train_model(
            category=target_category,
            epochs=epochs,
            batch_size=batch_size,
            imgsz=imgsz,
            progress_callback=mapped_progress_callback,
            class_names=class_names,
            clear_cache=True,
        )

        if not trained_model_path:
            raise RuntimeError("Birlesik final model egitimi tamamlanamadi veya model kaydedilemedi.")

        self._emit_progress(100, "Birlesik final model egitimi tamamlandi!")
        self.task_complete.emit(f"Birlesik final model egitimi tamamlandi! Model: {trained_model_path}")


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

        self.training_thread = None
        self.training_worker = None
        self.training_task_running = False

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

        analysis_widget = QWidget()
        analysis_layout = QVBoxLayout()
        create_analysis_ui(analysis_layout, self)
        analysis_widget.setLayout(analysis_layout)
        self.tabs.addTab(analysis_widget, "Analiz")

        live_widget = QWidget()
        live_layout = QVBoxLayout()
        create_live_analysis_ui(live_layout, self)
        live_widget.setLayout(live_layout)
        self.tabs.addTab(live_widget, "Canli Takip")

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
        model_value = config.normalize_confidence_threshold(value)

        if value <= 0:
            self.threshold_value_label.setText("%0")
        else:
            self.threshold_value_label.setText(f"{value:.0%}")

        if self.detector:
            self.detector.set_confidence_threshold(model_value)

        if value <= 0:
            self.log("Guven esigi %0 test modunda: model esigi 0.001 olarak uygulandi.")

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
        detection_count = self.analysis_results.get("detection_count", 0)
        crop_count = self.analysis_results.get("crop_count", 0)
        frame_detection_count = self.analysis_results.get("frame_detection_count", 0)
        class_counts = self.analysis_results.get("class_counts") or {}

        conf_lines = [f"{confidence:.2%}"]
        if detection_count:
            conf_lines.append(f"Toplam tespit sayisi: {detection_count}")
        if frame_detection_count:
            conf_lines.append(f"Gosterilecek karedeki unsur: {frame_detection_count}")
        if crop_count:
            conf_lines.append(f"Kirpinti sayisi: {crop_count}")
        if class_counts:
            top_classes = sorted(class_counts.items(), key=lambda item: item[1], reverse=True)[:4]
            class_text = ", ".join(f"{config.get_class_display_name(k)}: {v}" for k, v in top_classes)
            conf_lines.append(class_text)
        self.conf_value.setText("\n".join(conf_lines))

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
            self.analysis_results.get("evidence_summary")
            or self.analysis_results.get("weapon_display")
            or self.analysis_results.get("weapon_type")
            or self.analysis_results.get("class_name")
            or "N/A"
        )
        self.weapon_value.setText(str(weapon_info))

        crop_items = self.analysis_results.get("crop_items") or []
        self.crop_btn.setEnabled(detected and (bool(crop_items) or self.analysis_results.get("crop_image") is not None))
        self.export_excel_btn.setEnabled(True)
        self.export_json_btn.setEnabled(True)

    def _cv_bgr_to_pixmap(self, image_bgr):
        """OpenCV BGR/Numpy goruntuyu QPixmap'e cevir. Kaynak goruntu degistirilmez."""
        if image_bgr is None:
            return None

        frame_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        return QPixmap.fromImage(qimg)


    def _feedback_timestamp(self) -> str:
        """Feedback dosyalari icin benzersiz zaman etiketi uret."""
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    def _safe_name(self, value: str) -> str:
        """Dosya adi icin guvenli metin uret."""
        value = str(value or "item").strip().lower()
        cleaned = []
        for ch in value:
            if ch.isalnum() or ch in ("_", "-", "."):
                cleaned.append(ch)
            else:
                cleaned.append("_")
        text = "".join(cleaned).strip("_")
        while "__" in text:
            text = text.replace("__", "_")
        return text or "item"

    def _ensure_dir(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _write_image_lossless(self, path: Path, image) -> bool:
        """
        Goruntuyu kaynak kaliteyi bozmadan kaydetmeye calisir.
        PNG kayit lossless oldugu icin egitim feedbacklerinde varsayilan olarak kullanilir.
        """
        if image is None:
            return False
        self._ensure_dir(path.parent)
        return bool(cv2.imwrite(str(path), image))

    def _append_feedback_log(self, record: dict):
        """Kullanici feedback aksiyonlarini JSONL olarak kaydet."""
        try:
            log_path = Path(getattr(config, "FEEDBACK_LOG_PATH", Path(config.TRAINING_DATA_DIR) / "feedback_actions.jsonl"))
            self._ensure_dir(log_path.parent)
            safe_record = {}
            for key, value in (record or {}).items():
                if key in {"image", "crop_image", "marked_crop_image", "original_image"}:
                    continue
                if isinstance(value, Path):
                    safe_record[key] = str(value)
                elif isinstance(value, tuple):
                    safe_record[key] = list(value)
                else:
                    safe_record[key] = value
            safe_record["saved_at"] = datetime.now().isoformat()
            with log_path.open("a", encoding="utf-8") as f:
                import json
                f.write(json.dumps(safe_record, ensure_ascii=False) + "\n")
        except Exception as e:
            self.log(f"Feedback log yazilamadi: {e}")

    def _category_for_class(self, class_name: str) -> str:
        """Sinif adindan egitim kategorisini bul."""
        weapon = config.get_weapon_from_class(class_name)
        if weapon in {"nora_b52", "zuzana", "obus"}:
            return weapon
        raise ValueError(f"Bu sinif icin kategori bulunamadi: {class_name}")

    def _yolo_bbox_from_original_bbox(self, bbox, image_shape, crop_bounds=None):
        """
        Orijinal bbox bilgisini secilen kayit goruntusune gore YOLO formatina cevir.

        crop_bounds verilirse bbox, kirpinti koordinatina donusturulur.
        Verilmezse bbox tam kare/resim koordinati kabul edilir.
        """
        if bbox is None:
            raise ValueError("BBox bilgisi yok")

        x1, y1, x2, y2 = [float(v) for v in bbox]

        if crop_bounds is not None:
            cx1, cy1, cx2, cy2 = [float(v) for v in crop_bounds]
            x1 -= cx1
            x2 -= cx1
            y1 -= cy1
            y2 -= cy1

        h, w = image_shape[:2]
        if w <= 0 or h <= 0:
            raise ValueError("Goruntu boyutu gecersiz")

        x1 = max(0.0, min(float(w), x1))
        x2 = max(0.0, min(float(w), x2))
        y1 = max(0.0, min(float(h), y1))
        y2 = max(0.0, min(float(h), y2))

        if x2 <= x1 or y2 <= y1:
            raise ValueError("BBox kayit goruntusunun disinda veya gecersiz")

        xc = ((x1 + x2) / 2.0) / w
        yc = ((y1 + y2) / 2.0) / h
        bw = (x2 - x1) / w
        bh = (y2 - y1) / h

        return (
            max(0.0, min(1.0, xc)),
            max(0.0, min(1.0, yc)),
            max(0.000001, min(1.0, bw)),
            max(0.000001, min(1.0, bh)),
        )

    def _save_positive_sample(self, item: dict, class_name: str, use_full_frame: bool = False):
        """
        Dogru hedef/parca feedbackini ilgili egitim klasorune image + label olarak kaydet.

        use_full_frame=False:
            Sadece kirpinti kaydedilir, bbox kirpinti koordinatina gore label'lanir.
        use_full_frame=True:
            Orijinal resim/frame kaydedilir, bbox tam kare koordinatina gore label'lanir.
        """
        class_name = str(class_name or "").strip()
        if class_name not in getattr(config, "CLASS_NAMES", []):
            QMessageBox.warning(self, "Sinif Secimi Gerekli", "Gecerli bir hedef/parca sinifi secmelisin.")
            return

        try:
            category = self._category_for_class(class_name)
            class_id = config.get_class_id(class_name)

            if use_full_frame:
                image = (self.analysis_results or {}).get("original_image")
                crop_bounds = None
                suffix = "fullframe"
            else:
                image = item.get("crop_image")
                crop_bounds = item.get("crop_bounds")
                suffix = "crop"

            if image is None:
                raise RuntimeError("Kaydedilecek goruntu bulunamadi.")

            bbox = item.get("bbox")
            yolo = self._yolo_bbox_from_original_bbox(bbox, image.shape, crop_bounds=crop_bounds)

            base_name = (
                f"feedback_pos_{self._safe_name(class_name)}_{suffix}_"
                f"{self._feedback_timestamp()}"
            )

            image_dir = Path(config.TRAINING_DATA_DIR) / category / "images" / "train"
            label_dir = Path(config.TRAINING_DATA_DIR) / category / "labels" / "train"
            self._ensure_dir(image_dir)
            self._ensure_dir(label_dir)

            image_path = image_dir / f"{base_name}.png"
            label_path = label_dir / f"{base_name}.txt"

            if not self._write_image_lossless(image_path, image):
                raise RuntimeError("Goruntu kaydedilemedi.")

            label_path.write_text(
                f"{class_id} {yolo[0]:.6f} {yolo[1]:.6f} {yolo[2]:.6f} {yolo[3]:.6f}\n",
                encoding="utf-8",
            )

            self._append_feedback_log({
                "action": "positive_sample",
                "class_name": class_name,
                "class_id": class_id,
                "category": category,
                "use_full_frame": use_full_frame,
                "image_path": image_path,
                "label_path": label_path,
                "bbox": item.get("bbox"),
                "crop_bounds": item.get("crop_bounds"),
                "confidence": item.get("confidence"),
                "source_filename": (self.analysis_results or {}).get("filename"),
            })

            self.log(f"Pozitif egitim ornegi kaydedildi: {image_path}")
            QMessageBox.information(
                self,
                "Kaydedildi",
                f"Pozitif egitim ornegi kaydedildi:\n{image_path}\n\nLabel:\n{label_path}",
            )

        except Exception as e:
            QMessageBox.critical(self, "Kayit Hatasi", f"Pozitif ornek kaydedilemedi:\n{e}")
            self.log(f"Pozitif feedback kayit hatasi: {e}")

    def _save_negative_crop_to_background(self, item: dict, reason: str = "wrong_alarm"):
        """Yanlis alarm kirpintisini background klasorune bos label ile kaydet."""
        try:
            image = item.get("crop_image")
            if image is None:
                raise RuntimeError("Kirpinti goruntusu bulunamadi.")

            base_name = f"feedback_neg_{self._safe_name(reason)}_{self._feedback_timestamp()}"
            image_dir = Path(config.TRAINING_DATA_DIR) / "background" / "images" / "train"
            label_dir = Path(config.TRAINING_DATA_DIR) / "background" / "labels" / "train"
            self._ensure_dir(image_dir)
            self._ensure_dir(label_dir)

            image_path = image_dir / f"{base_name}.png"
            label_path = label_dir / f"{base_name}.txt"

            if not self._write_image_lossless(image_path, image):
                raise RuntimeError("Background kirpinti goruntusu kaydedilemedi.")

            label_path.write_text("", encoding="utf-8")

            self._append_feedback_log({
                "action": "negative_crop_background",
                "reason": reason,
                "image_path": image_path,
                "label_path": label_path,
                "bbox": item.get("bbox"),
                "crop_bounds": item.get("crop_bounds"),
                "confidence": item.get("confidence"),
                "predicted_class": item.get("class_name"),
                "source_filename": (self.analysis_results or {}).get("filename"),
            })

            self.log(f"Yanlis alarm background'a eklendi: {image_path}")
            QMessageBox.information(
                self,
                "Background'a Eklendi",
                f"Yanlis alarm kirpintisi background'a kaydedildi:\n{image_path}",
            )

        except Exception as e:
            QMessageBox.critical(self, "Kayit Hatasi", f"Background ornegi kaydedilemedi:\n{e}")
            self.log(f"Negatif feedback kayit hatasi: {e}")

    def _save_full_frame_background(self):
        """
        Tam karede/resimde hic silah yoksa tum kareyi background'a bos label olarak kaydet.
        Bu aksiyon riskli oldugu icin onay ister.
        """
        image = (self.analysis_results or {}).get("original_image")
        if image is None:
            QMessageBox.warning(self, "Goruntu Yok", "Tam kare/resim goruntusu bulunamadi.")
            return

        answer = QMessageBox.question(
            self,
            "Tam Kare Background Onayi",
            "Bu tam karede/resimde gercekten Nora, Zuzana veya obus parcasi olmadigindan emin misin?\n\n"
            "Eger karede hedef varsa bunu background'a eklemek modeli bozabilir.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            base_name = f"feedback_full_background_{self._feedback_timestamp()}"
            image_dir = Path(config.TRAINING_DATA_DIR) / "background" / "images" / "train"
            label_dir = Path(config.TRAINING_DATA_DIR) / "background" / "labels" / "train"
            self._ensure_dir(image_dir)
            self._ensure_dir(label_dir)

            image_path = image_dir / f"{base_name}.png"
            label_path = label_dir / f"{base_name}.txt"

            if not self._write_image_lossless(image_path, image):
                raise RuntimeError("Tam kare background goruntusu kaydedilemedi.")

            label_path.write_text("", encoding="utf-8")

            self._append_feedback_log({
                "action": "full_frame_background",
                "image_path": image_path,
                "label_path": label_path,
                "source_filename": (self.analysis_results or {}).get("filename"),
            })

            self.log(f"Tam kare background'a eklendi: {image_path}")
            QMessageBox.information(
                self,
                "Background'a Eklendi",
                f"Tam kare/resim background'a kaydedildi:\n{image_path}",
            )

        except Exception as e:
            QMessageBox.critical(self, "Kayit Hatasi", f"Tam kare background'a eklenemedi:\n{e}")
            self.log(f"Tam kare background kayit hatasi: {e}")

    def _save_crop_to_review_bucket(self, item: dict, bucket_name: str, reason: str):
        """Kararsiz, manuel label gereken, bulanık veya referans kirpintilarini ayri klasorlere kaydet."""
        try:
            image = item.get("crop_image")
            marked = item.get("marked_crop_image")
            if image is None and marked is None:
                raise RuntimeError("Kaydedilecek kirpinti yok.")

            root = Path(config.TRAINING_DATA_DIR) / bucket_name
            self._ensure_dir(root)
            base_name = f"feedback_{self._safe_name(reason)}_{self._feedback_timestamp()}"

            saved_paths = []
            if image is not None:
                raw_path = root / f"{base_name}_raw.png"
                self._write_image_lossless(raw_path, image)
                saved_paths.append(raw_path)

            if marked is not None:
                marked_path = root / f"{base_name}_marked.png"
                self._write_image_lossless(marked_path, marked)
                saved_paths.append(marked_path)

            meta_path = root / f"{base_name}.json"
            meta = {
                "reason": reason,
                "bucket": bucket_name,
                "source_filename": (self.analysis_results or {}).get("filename"),
                "predicted_class": item.get("class_name"),
                "display_name": item.get("display_name"),
                "confidence": item.get("confidence"),
                "bbox": item.get("bbox"),
                "crop_bounds": item.get("crop_bounds"),
                "saved_paths": [str(p) for p in saved_paths],
                "saved_at": datetime.now().isoformat(),
            }
            import json
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            saved_paths.append(meta_path)

            self._append_feedback_log({
                "action": "review_bucket",
                "reason": reason,
                "bucket": bucket_name,
                "paths": [str(p) for p in saved_paths],
                "source_filename": (self.analysis_results or {}).get("filename"),
            })

            self.log(f"Kirpinti {bucket_name} klasorune kaydedildi: {root}")
            QMessageBox.information(
                self,
                "Kaydedildi",
                f"Kirpinti '{reason}' icin kaydedildi:\n{root}",
            )

        except Exception as e:
            QMessageBox.critical(self, "Kayit Hatasi", f"Kirpinti kaydedilemedi:\n{e}")
            self.log(f"Review feedback kayit hatasi: {e}")

    def _save_single_crop_as(self, item: dict, marked: bool = True):
        """Tek kirpintiyi kullanicinin sectigi dosyaya PNG olarak kaydet."""
        image = item.get("marked_crop_image") if marked else item.get("crop_image")
        if image is None:
            QMessageBox.warning(self, "Kirpinti Yok", "Kaydedilecek kirpinti bulunamadi.")
            return

        default_name = (
            f"{self._safe_name(item.get('class_name') or 'kirpinti')}_"
            f"{float(item.get('confidence', 0) or 0):.2f}.png"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Kırpıntıyı Farklı Kaydet",
            default_name,
            "PNG Görsel (*.png);;JPEG Görsel (*.jpg);;Tüm Dosyalar (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            path = path.with_suffix(".png")

        try:
            if not self._write_image_lossless(path, image):
                raise RuntimeError("Dosya kaydedilemedi.")
            self.log(f"Kırpıntı farklı kaydedildi: {path}")
            QMessageBox.information(self, "Kaydedildi", f"Kırpıntı kaydedildi:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Kayit Hatasi", f"Kırpıntı kaydedilemedi:\n{e}")

    def _save_all_crops_to_folder(self, crop_items):
        """
        Tum kirpintilari secilen klasore ham + isaretli PNG olarak kaydet.
        Bu islem egitim klasorlerini degistirmez, sadece disari aktarir.
        """
        if not crop_items:
            QMessageBox.warning(self, "Kirpinti Yok", "Kaydedilecek kirpinti yok.")
            return

        folder = QFileDialog.getExistingDirectory(self, "Kırpıntıların Kaydedileceği Klasörü Seç")
        if not folder:
            return

        try:
            root = Path(folder)
            raw_dir = self._ensure_dir(root / "raw")
            marked_dir = self._ensure_dir(root / "marked")
            meta = []

            for index, item in enumerate(crop_items, start=1):
                class_name = self._safe_name(item.get("class_name") or "kirpinti")
                conf_text = f"{float(item.get('confidence', 0) or 0):.3f}".replace(".", "_")
                stem = f"{index:03d}_{class_name}_{conf_text}"

                raw_path = raw_dir / f"{stem}.png"
                marked_path = marked_dir / f"{stem}.png"

                if item.get("crop_image") is not None:
                    self._write_image_lossless(raw_path, item.get("crop_image"))
                if item.get("marked_crop_image") is not None:
                    self._write_image_lossless(marked_path, item.get("marked_crop_image"))

                meta.append({
                    "index": index,
                    "class_name": item.get("class_name"),
                    "display_name": item.get("display_name"),
                    "decision": item.get("decision"),
                    "confidence": item.get("confidence"),
                    "bbox": item.get("bbox"),
                    "raw_path": str(raw_path),
                    "marked_path": str(marked_path),
                })

            import json
            (root / "crop_metadata.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            self.log(f"Tum kirpintilar klasore kaydedildi: {root}")
            QMessageBox.information(
                self,
                "Kaydedildi",
                f"{len(crop_items)} kırpıntı ham ve işaretli olarak kaydedildi:\n{root}",
            )

        except Exception as e:
            QMessageBox.critical(self, "Kayit Hatasi", f"Kırpıntılar kaydedilemedi:\n{e}")
            self.log(f"Toplu kirpinti kayit hatasi: {e}")

    def _show_multi_crop_dialog(self, crop_items):
        """Bir karede/resimde bulunan tum supheli parca kirpintilarini goster ve feedback toplar."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Tespit Kırpıntıları ve Eğitim Feedback ({len(crop_items)})")
        dialog.resize(1180, 820)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        info_label = QLabel(
            "Bu ekran test/feedback ekranıdır. Her kırpıntıyı ayrı değerlendirebilirsin. "
            "Yanlış alarmları background'a, doğru parçaları ilgili silah eğitim klasörüne kaydedebilirsin. "
            "Kaynak fotoğraf/video değiştirilmez; kaydedilen eğitim örnekleri PNG olarak orijinal pikselden alınır."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #2C3E50; font-weight: 500;")
        main_layout.addWidget(info_label)

        warning_label = QLabel(
            "Güvenlik notu: Karede gerçek hedef varsa 'Tam Karede Silah Yok' seçeneğini kullanma. "
            "O durumda sadece yanlış kırpıntıyı background'a ekle."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #B45309; font-weight: bold;")
        main_layout.addWidget(warning_label)

        top_button_row = QHBoxLayout()

        save_all_btn = QPushButton("Tüm Kırpıntıları Farklı Klasöre Kaydet")
        save_all_btn.setMinimumHeight(34)
        save_all_btn.clicked.connect(lambda _checked=False: self._save_all_crops_to_folder(crop_items))
        top_button_row.addWidget(save_all_btn)

        full_bg_btn = QPushButton("Tam Karede Silah Yok → Frame'i Background'a Ekle")
        full_bg_btn.setMinimumHeight(34)
        full_bg_btn.setStyleSheet("background-color: #F59E0B; color: white; font-weight: bold;")
        full_bg_btn.clicked.connect(lambda _checked=False: self._save_full_frame_background())
        top_button_row.addWidget(full_bg_btn)

        top_button_row.addStretch()
        main_layout.addLayout(top_button_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        grid = QGridLayout()
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setSpacing(14)

        columns = 2
        class_options = list(getattr(config, "CLASS_NAMES", []))

        for idx, item in enumerate(crop_items):
            card = QWidget()
            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(8, 8, 8, 8)
            card_layout.setSpacing(6)

            title = item.get("decision") or item.get("display_name") or item.get("class_name") or "Tespit"
            confidence = float(item.get("confidence", 0.0) or 0.0)
            crop_size = item.get("crop_size")
            size_text = f" | Kırpıntı: {crop_size[0]}x{crop_size[1]}" if crop_size else ""

            title_label = QLabel(f"#{idx + 1} - {title} | Güven: {confidence:.2%}{size_text}")
            title_label.setWordWrap(True)
            title_label.setStyleSheet("font-weight: bold; color: #1F2937;")
            card_layout.addWidget(title_label)

            crop_image = item.get("marked_crop_image")
            if crop_image is None:
                crop_image = item.get("crop_image")
            pixmap = self._cv_bgr_to_pixmap(crop_image)

            image_label = QLabel()
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setMinimumSize(420, 250)
            image_label.setStyleSheet("background-color: #111111; border: 1px solid #D1D5DB;")

            if pixmap is not None:
                scaled = pixmap.scaled(
                    500,
                    330,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                image_label.setPixmap(scaled)
            else:
                image_label.setText("Kırpıntı görüntüsü yok")

            card_layout.addWidget(image_label)

            bbox = item.get("bbox")
            meta_label = QLabel(
                f"Tahmin: {config.get_class_display_name(item.get('class_name', ''))} | "
                f"Seviye: {item.get('detection_level', 'N/A')} | BBox: {bbox}"
            )
            meta_label.setWordWrap(True)
            meta_label.setStyleSheet("color: #4B5563; font-size: 11px;")
            card_layout.addWidget(meta_label)

            class_row = QHBoxLayout()
            class_row.addWidget(QLabel("Doğru sınıf:"))
            class_combo = QComboBox()
            for class_name in class_options:
                class_combo.addItem(config.get_class_display_name(class_name), class_name)
            predicted = item.get("class_name")
            if predicted in class_options:
                class_combo.setCurrentIndex(class_options.index(predicted))
            class_row.addWidget(class_combo, 1)
            card_layout.addLayout(class_row)

            row1 = QHBoxLayout()
            same_class_btn = QPushButton("Doğru - Aynı Sınıfla Eğitime Ekle")
            same_class_btn.setMinimumHeight(32)
            same_class_btn.setStyleSheet("background-color: #16A34A; color: white;")
            same_class_btn.clicked.connect(
                lambda _checked=False, it=item: self._save_positive_sample(
                    it,
                    it.get("class_name"),
                    use_full_frame=False,
                )
            )
            row1.addWidget(same_class_btn)

            selected_class_btn = QPushButton("Doğru - Seçilen Sınıfla Eğitime Ekle")
            selected_class_btn.setMinimumHeight(32)
            selected_class_btn.setStyleSheet("background-color: #2563EB; color: white;")
            selected_class_btn.clicked.connect(
                lambda _checked=False, it=item, combo=class_combo: self._save_positive_sample(
                    it,
                    combo.currentData(),
                    use_full_frame=False,
                )
            )
            row1.addWidget(selected_class_btn)
            card_layout.addLayout(row1)

            row2 = QHBoxLayout()
            full_positive_btn = QPushButton("Tam Kareyi Seçilen Sınıfla Kaydet")
            full_positive_btn.setMinimumHeight(32)
            full_positive_btn.setStyleSheet("background-color: #0F766E; color: white;")
            full_positive_btn.clicked.connect(
                lambda _checked=False, it=item, combo=class_combo: self._save_positive_sample(
                    it,
                    combo.currentData(),
                    use_full_frame=True,
                )
            )
            row2.addWidget(full_positive_btn)

            false_crop_btn = QPushButton("Yanlış Alarm → Kırpıntıyı Background'a Ekle")
            false_crop_btn.setMinimumHeight(32)
            false_crop_btn.setStyleSheet("background-color: #DC2626; color: white;")
            false_crop_btn.clicked.connect(
                lambda _checked=False, it=item: self._save_negative_crop_to_background(
                    it,
                    reason="wrong_alarm_crop",
                )
            )
            row2.addWidget(false_crop_btn)
            card_layout.addLayout(row2)

            row3 = QHBoxLayout()
            target_exists_wrong_crop_btn = QPushButton("Hedef Var Ama Bu Kırpıntı Yanlış")
            target_exists_wrong_crop_btn.setMinimumHeight(30)
            target_exists_wrong_crop_btn.clicked.connect(
                lambda _checked=False, it=item: self._save_negative_crop_to_background(
                    it,
                    reason="target_exists_but_this_crop_wrong",
                )
            )
            row3.addWidget(target_exists_wrong_crop_btn)

            manual_btn = QPushButton("Kutu Yanlış → Manuel Label'a At")
            manual_btn.setMinimumHeight(30)
            manual_btn.clicked.connect(
                lambda _checked=False, it=item: self._save_crop_to_review_bucket(
                    it,
                    "feedback_manual_label_required",
                    "bbox_wrong_object_correct",
                )
            )
            row3.addWidget(manual_btn)
            card_layout.addLayout(row3)

            row4 = QHBoxLayout()
            unsure_btn = QPushButton("Emin Değilim → İncelemeye At")
            unsure_btn.setMinimumHeight(30)
            unsure_btn.clicked.connect(
                lambda _checked=False, it=item: self._save_crop_to_review_bucket(
                    it,
                    "feedback_review",
                    "unsure_review",
                )
            )
            row4.addWidget(unsure_btn)

            blurry_btn = QPushButton("Bulanık/Kullanılmaz → Reddet")
            blurry_btn.setMinimumHeight(30)
            blurry_btn.clicked.connect(
                lambda _checked=False, it=item: self._save_crop_to_review_bucket(
                    it,
                    "feedback_rejected",
                    "blurry_unusable",
                )
            )
            row4.addWidget(blurry_btn)
            card_layout.addLayout(row4)

            row5 = QHBoxLayout()
            duplicate_btn = QPushButton("Tekrar/Gereksiz Benzer → Ayır")
            duplicate_btn.setMinimumHeight(30)
            duplicate_btn.clicked.connect(
                lambda _checked=False, it=item: self._save_crop_to_review_bucket(
                    it,
                    "feedback_duplicate_or_unnecessary",
                    "duplicate_or_unnecessary",
                )
            )
            row5.addWidget(duplicate_btn)

            reference_btn = QPushButton("Sadece Referans Olarak Sakla")
            reference_btn.setMinimumHeight(30)
            reference_btn.clicked.connect(
                lambda _checked=False, it=item: self._save_crop_to_review_bucket(
                    it,
                    "feedback_reference",
                    "reference_only",
                )
            )
            row5.addWidget(reference_btn)
            card_layout.addLayout(row5)

            row6 = QHBoxLayout()
            save_marked_btn = QPushButton("Bu İşaretli Kırpıntıyı Farklı Kaydet")
            save_marked_btn.setMinimumHeight(30)
            save_marked_btn.clicked.connect(
                lambda _checked=False, it=item: self._save_single_crop_as(it, marked=True)
            )
            row6.addWidget(save_marked_btn)

            save_raw_btn = QPushButton("Bu Ham Kırpıntıyı Farklı Kaydet")
            save_raw_btn.setMinimumHeight(30)
            save_raw_btn.clicked.connect(
                lambda _checked=False, it=item: self._save_single_crop_as(it, marked=False)
            )
            row6.addWidget(save_raw_btn)
            card_layout.addLayout(row6)

            card.setLayout(card_layout)
            card.setStyleSheet(
                "QWidget { background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; }"
                "QLabel { border: none; }"
                "QPushButton { padding: 4px; border-radius: 4px; }"
            )

            row = idx // columns
            col = idx % columns
            grid.addWidget(card, row, col)

        container.setLayout(grid)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

        button_row = QHBoxLayout()
        button_row.addStretch()
        close_btn = QPushButton("Kapat")
        close_btn.setMinimumHeight(34)
        close_btn.clicked.connect(dialog.accept)
        button_row.addWidget(close_btn)
        main_layout.addLayout(button_row)

        dialog.setLayout(main_layout)
        dialog.exec_()

    def view_crop(self):

        """Tespit kirpintilarini goruntule."""
        if not self.analysis_results:
            QMessageBox.warning(self, "Kirpinti Yok", "Once analiz yapmalisin")
            return

        crop_items = self.analysis_results.get("crop_items") or []
        if crop_items:
            self._show_multi_crop_dialog(crop_items)
            return

        if self.analysis_results.get("crop_image") is None:
            QMessageBox.warning(self, "Kirpinti Yok", "Tespit kirpintisi mevcut degil")
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
            results = self.detector.model(
                frame,
                device=self.detector.device,
                conf=self.detector._model_confidence_value(),
                verbose=False,
            )
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

                    display_name = getattr(config, "get_class_display_name", lambda x: x)(class_name)
                    decision_text = config.get_weapon_decision(class_name, float(conf))

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
                    last_text = f"Son tespit: {decision_text} | {conf:.2%}"

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
    # EGITIM METODLARI - KATEGORI / ICERIK
    # =========================================================

    def _training_root(self) -> Path:
        return Path(getattr(config, "TRAINING_DATA_DIR", Path(config.PROJECT_ROOT) / "training_data"))

    def _get_available_categories(self):
        """training_data altindaki mevcut kategorileri getir"""
        training_data_dir = self._training_root()
        if not training_data_dir.exists():
            return ["default"]

        categories = []
        for item in sorted(training_data_dir.iterdir()):
            if not item.is_dir() or item.name.startswith("."):
                continue

            if item.name.lower() == "models":
                continue

            if "backup" in item.name.lower():
                continue

            if (item / "images").exists() and (item / "labels").exists():
                categories.append(item.name)

        return categories if categories else ["default"]

    def _refresh_combo_items(self, combo, items):
        current_text = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(items)
        index = combo.findText(current_text)
        if index >= 0:
            combo.setCurrentIndex(index)
        elif combo.count() > 0:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _refresh_combined_source_list(self):
        """Birlesik egitim kaynak kategorilerini yenile"""
        if not hasattr(self, "combined_source_categories_list"):
            return

        categories = self._get_available_categories()
        self.combined_source_categories_list.clear()

        for category in categories:
            lower_name = category.lower()

            if lower_name == "models":
                continue
            if lower_name == "weapon_dataset":
                continue
            if "backup" in lower_name:
                continue

            self.combined_source_categories_list.addItem(category)

    def _refresh_all_category_combos(self):
        """Tum kategori combolarini yenile"""
        categories = self._get_available_categories()

        if hasattr(self, "upload_category_combo"):
            self._refresh_combo_items(self.upload_category_combo, categories)

        if hasattr(self, "training_category_combo"):
            self._refresh_combo_items(self.training_category_combo, categories)

        if hasattr(self, "content_category_combo"):
            self._refresh_combo_items(self.content_category_combo, categories)

        if hasattr(self, "analysis_category_combo"):
            self._refresh_combo_items(self.analysis_category_combo, categories)

        self._refresh_combined_source_list()

    def refresh_upload_categories(self):
        self._refresh_all_category_combos()
        self.log("Upload kategorileri yenilendi")

    def refresh_training_categories(self):
        self._refresh_all_category_combos()
        self.log("Egitim kategorileri yenilendi")

    def refresh_content_categories(self):
        self._refresh_all_category_combos()
        self.log("Icerik kategorileri yenilendi")

    def refresh_analysis_categories(self):
        self._refresh_all_category_combos()
        self.log("Analiz kategorileri yenilendi")

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
        if not hasattr(self, "categories_list"):
            return

        self.categories_list.clear()
        for cat in self._get_available_categories():
            self.categories_list.addItem(cat)

    def refresh_content_display(self):
        """Icerigi yenile"""
        if not hasattr(self, "content_category_combo"):
            return

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

    # =========================================================
    # EGITIM METODLARI - PROGRESS / WORKER
    # =========================================================

    def _set_training_busy(self, busy: bool):
        self.training_task_running = busy

        if hasattr(self, "train_btn"):
            self.train_btn.setEnabled(not busy)

        if hasattr(self, "training_progress"):
            self.training_progress.setVisible(True)
            if busy:
                self.training_progress.setValue(0)

        if hasattr(self, "training_progress_label"):
            self.training_progress_label.setText("Calisiyor..." if busy else "Hazir")

    def _append_training_log(self, message: str):
        if hasattr(self, "training_log"):
            self.training_log.append(str(message))

    def on_training_progress_update(self, percent: int, message: str):
        if hasattr(self, "training_progress"):
            self.training_progress.setVisible(True)

            if percent >= 0:
                percent = max(0, min(100, int(percent)))
                self.training_progress.setValue(percent)

        if hasattr(self, "training_progress_label"):
            if percent >= 0:
                self.training_progress_label.setText(f"%{percent} - {message}")
            else:
                self.training_progress_label.setText(message)

        self._append_training_log(f"[{percent}] {message}")

    def _start_training_worker(self, mode: str, payload: dict):
        if self.training_task_running:
            QMessageBox.warning(self, "Egitim Devam Ediyor", "Zaten devam eden bir egitim islemi var.")
            return

        if hasattr(self, "training_log"):
            self.training_log.clear()

        self._set_training_busy(True)

        self.training_thread = QThread(self)
        self.training_worker = TrainingTaskWorker(self.model_trainer, mode, payload)
        self.training_worker.moveToThread(self.training_thread)

        self.training_thread.started.connect(self.training_worker.run)
        self.training_worker.progress_update.connect(self.on_training_progress_update)
        self.training_worker.log_update.connect(self._append_training_log)
        self.training_worker.task_complete.connect(self.on_training_task_complete)
        self.training_worker.error_occurred.connect(self.on_training_task_error)
        self.training_worker.finished.connect(self.training_thread.quit)
        self.training_worker.finished.connect(self.training_worker.deleteLater)
        self.training_thread.finished.connect(self.training_thread.deleteLater)
        self.training_thread.finished.connect(self._cleanup_training_worker)

        self.training_thread.start()

    def on_training_task_complete(self, message: str):
        self._append_training_log(message)

        if hasattr(self, "training_progress"):
            self.training_progress.setVisible(True)
            self.training_progress.setValue(100)

        if hasattr(self, "training_progress_label"):
            self.training_progress_label.setText("Tamamlandi")

        QMessageBox.information(self, "Basarili", message)
        self.log(message)

    def on_training_task_error(self, error_msg: str):
        self._append_training_log(f"HATA: {error_msg}")

        if hasattr(self, "training_progress_label"):
            self.training_progress_label.setText("Hata")

        QMessageBox.critical(self, "Egitim Hatasi", f"Islem basarisiz:\n{error_msg}")
        self.log(f"Egitim hatasi: {error_msg}")

    def _cleanup_training_worker(self):
        self.training_worker = None
        self.training_thread = None
        self._set_training_busy(False)

    # =========================================================
    # EGITIM METODLARI - KATEGORI BAZLI EGITIM
    # =========================================================

    def start_training(self):
        """Kategori bazli model egitimini baslat"""
        category = self.training_category_combo.currentText()

        if category == "default":
            QMessageBox.warning(self, "Hata", "Gecerli bir kategori seciniz!")
            return

        category_path = self._training_root() / category
        train_images = (
            list((category_path / "images" / "train").glob("*"))
            if (category_path / "images" / "train").exists()
            else []
        )
        train_labels = (
            list((category_path / "labels" / "train").glob("*.txt"))
            if (category_path / "labels" / "train").exists()
            else []
        )

        if len(train_images) == 0 or len(train_labels) == 0:
            QMessageBox.warning(
                self,
                "Hata",
                f"'{category}' kategorisinde yeterli egitim verisi yok!\n"
                f"Images: {len(train_images)}, Labels: {len(train_labels)}",
            )
            return

        reply = QMessageBox.question(
            self,
            "Kategori Bazli Egitim",
            f"'{category}' kategorisi egitilecek.\n\n"
            "Bu test amacli egitimdir. Nihai model icin Birlesik Final Model Egitimi onerilir.\n\n"
            "Devam etmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        payload = {
            "category": category,
            "epochs": self.epoch_spinbox.value(),
            "batch_size": self.batch_spinbox.value(),
            "imgsz": self.imgsz_spinbox.value(),
            "class_names": list(getattr(config, "CLASS_NAMES", ["obus"])),
        }

        self._start_training_worker("category_train", payload)

    # =========================================================
    # EGITIM METODLARI - BIRLESIK DATASET / FINAL MODEL
    # =========================================================

    def _get_combined_dataset_name(self) -> str:
        if hasattr(self, "combined_dataset_name_input"):
            name = self.combined_dataset_name_input.text().strip()
            if name:
                return str(name)
        return "weapon_dataset"

    def _get_selected_combined_sources(self):
        if not hasattr(self, "combined_source_categories_list"):
            return []

        selected_items = self.combined_source_categories_list.selectedItems()

        if selected_items:
            return [item.text() for item in selected_items]

        sources = []
        for i in range(self.combined_source_categories_list.count()):
            item = self.combined_source_categories_list.item(i)
            sources.append(item.text())

        return sources

    def prepare_combined_dataset_from_ui(self):
        """UI uzerinden secilen kaynaklarla birlesik dataset hazirla"""
        source_categories = self._get_selected_combined_sources()
        target_category = self._get_combined_dataset_name()

        if not source_categories:
            QMessageBox.warning(self, "Kaynak Yok", "Birlesik dataset icin en az bir kaynak kategori secin.")
            return

        reply = QMessageBox.question(
            self,
            "Birlesik Dataset Hazirla",
            f"Kaynak kategoriler:\n{', '.join(source_categories)}\n\n"
            f"Hedef dataset:\n{target_category}\n\n"
            "Hedef dataset varsa silinip yeniden olusturulacak.\n"
            "Devam etmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        payload = {
            "source_categories": source_categories,
            "target_category": target_category,
            "class_names": list(getattr(config, "CLASS_NAMES", ["obus"])),
        }

        self._start_training_worker("prepare_combined", payload)

    def start_combined_training(self):
        """Tum secili kategorilerden tek final model egit"""
        source_categories = self._get_selected_combined_sources()
        target_category = self._get_combined_dataset_name()

        if not source_categories:
            QMessageBox.warning(self, "Kaynak Yok", "Birlesik final model icin en az bir kaynak kategori secin.")
            return

        reply = QMessageBox.question(
            self,
            "Birlesik Final Model Egitimi",
            f"Kaynak kategoriler:\n{', '.join(source_categories)}\n\n"
            f"Hedef dataset:\n{target_category}\n\n"
            "Tum secili kategoriler tek dataset altinda toplanacak ve final model egitilecek.\n"
            "Egitim sonunda model models/howitzer_detector.pt olarak kaydedilecek.\n\n"
            "Devam etmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        payload = {
            "source_categories": source_categories,
            "target_category": target_category,
            "epochs": self.epoch_spinbox.value(),
            "batch_size": self.batch_spinbox.value(),
            "imgsz": self.imgsz_spinbox.value(),
            "class_names": list(getattr(config, "CLASS_NAMES", ["obus"])),
        }

        self._start_training_worker("combined_train", payload)

    # =========================================================
    # EGITIM METODLARI - DATASET ANALIZ
    # =========================================================

    def _class_display_name(self, class_name: str) -> str:
        func = getattr(config, "get_class_display_name", None)
        if callable(func):
            return str(func(class_name))
        return str(class_name)

    def _format_distribution_text(self, distribution: dict) -> str:
        category = distribution.get("category", "N/A")
        total_files = distribution.get("total_files", 0)
        total_lines = distribution.get("total_lines", 0)
        invalid_lines = distribution.get("invalid_lines", 0)
        named_distribution = distribution.get("named_distribution", {})
        split_stats = distribution.get("split_stats", {})

        lines = []
        lines.append(f"Kategori: {category}")
        lines.append(f"Toplam label dosyasi: {total_files}")
        lines.append(f"Toplam kutu/satir: {total_lines}")
        lines.append(f"Gecersiz satir: {invalid_lines}")
        lines.append("")
        lines.append("Split dagilimi:")

        for split, stats in split_stats.items():
            lines.append(
                f"  [{split}] files={stats.get('files', 0)}, "
                f"lines={stats.get('lines', 0)}, "
                f"invalid={stats.get('invalid_lines', 0)}"
            )

        lines.append("")
        lines.append("Sinif dagilimi:")

        if not named_distribution:
            lines.append("  Sinif satiri bulunamadi.")
        else:
            for cls_id, item in named_distribution.items():
                class_name = item.get("class_name", f"unknown_{cls_id}")
                count = item.get("count", 0)
                display_name = self._class_display_name(str(class_name))
                lines.append(f"  {cls_id:>2} | {class_name:<25} | {display_name:<25} | {count}")

        return "\n".join(lines)

    def _write_dataset_analysis(self, text: str):
        if hasattr(self, "dataset_analysis_text"):
            self.dataset_analysis_text.setPlainText(text)
        else:
            QMessageBox.information(self, "Dataset Analiz", text)

    def analyze_selected_training_dataset(self):
        """Secili kategoriyi analiz et"""
        if not hasattr(self, "analysis_category_combo"):
            QMessageBox.warning(self, "Hata", "Analiz kategori secimi bulunamadi.")
            return

        category = self.analysis_category_combo.currentText().strip()
        if not category:
            QMessageBox.warning(self, "Hata", "Analiz edilecek kategori yok.")
            return

        try:
            distribution = self.model_trainer.get_label_distribution(
                category=category,
                class_names=list(getattr(config, "CLASS_NAMES", ["obus"])),
            )
            self._write_dataset_analysis(self._format_distribution_text(distribution))
        except Exception as e:
            QMessageBox.critical(self, "Analiz Hatasi", str(e))

    def analyze_combined_training_dataset(self):
        """Birlesik dataset'i analiz et"""
        category = self._get_combined_dataset_name()

        try:
            distribution = self.model_trainer.get_label_distribution(
                category=category,
                class_names=list(getattr(config, "CLASS_NAMES", ["obus"])),
            )
            self._write_dataset_analysis(self._format_distribution_text(distribution))
        except Exception as e:
            QMessageBox.critical(self, "Analiz Hatasi", str(e))

    def analyze_all_training_datasets(self):
        """Tum kategorileri analiz et"""
        try:
            chunks = []
            for category in self._get_available_categories():
                if category.lower() == "models" or "backup" in category.lower():
                    continue

                distribution = self.model_trainer.get_label_distribution(
                    category=category,
                    class_names=list(getattr(config, "CLASS_NAMES", ["obus"])),
                )
                chunks.append(self._format_distribution_text(distribution))

            text = "\n\n" + ("-" * 80) + "\n\n"
            self._write_dataset_analysis(text.join(chunks) if chunks else "Analiz edilecek kategori bulunamadi.")
        except Exception as e:
            QMessageBox.critical(self, "Analiz Hatasi", str(e))

    # =========================================================
    # LOG
    # =========================================================

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