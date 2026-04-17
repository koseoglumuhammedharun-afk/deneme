# -*- coding: utf-8 -*-
"""
Drone Obüs Tespit Sistemi - PyQt5 GUI Uygulaması
Ana giriş noktası
"""
import os

# DLL hatasını önlemek için kütüphane yolunu manuel ekliyoruz
dll_path = r"C:\Users\CASPER\Desktop\drone_detection\venv\lib\site-packages\torch\lib"
if os.path.exists(dll_path):
    os.add_dll_directory(dll_path)

try:
    import torch # Şimdi güvenle import edebiliriz
except (ImportError, OSError) as e:
    torch = None
    print(f"Warning: PyTorch uygulanamıyor: {e}")
    print("Uygulama GUI çalışacak ancak YOLO tespit devre dışı olacak")
import sys
import logging
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QMessageBox, QProgressBar,
    QTextEdit, QFrame, QScrollArea, QDialog, QDialogButtonBox, QSpinBox,
    QGridLayout, QTabWidget, QListWidget, QListWidgetItem, QComboBox, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint
from PyQt5.QtGui import QPixmap, QImage, QFont, QColor, QIcon

import config
from src import HowitzerDetector, MetadataExtractor, ReportGenerator, ModelTrainer
from src.utils import (
    setup_logging, validate_file, get_file_preview, 
    ensure_output_directory, frames_to_mmss, save_image
)

logger = setup_logging("GUI")

class AnalysisWorker(QThread):
    """Worker thread for background analysis"""
    
    progress_update = pyqtSignal(str)  # Log message
    frame_progress = pyqtSignal(int, int, float)  # current_frame, total_frames, confidence
    analysis_complete = pyqtSignal(dict)  # Results dict
    error_occurred = pyqtSignal(str)  # Error message
    
    def __init__(self, detector, file_path, metadata_extractor, report_generator):
        super().__init__()
        self.detector = detector
        self.file_path = file_path
        self.metadata_extractor = metadata_extractor
        self.report_generator = report_generator
        self.results = {}
    
    def run(self):
        """Execute analysis in background thread"""
        try:
            file_path = Path(self.file_path)
            file_suffix = file_path.suffix.lower()
            
            self.progress_update.emit(f"Analiz başlanıyor: {file_path.name}")
            
            # Determine file type and analyze
            if file_suffix in config.SUPPORTED_IMAGE_FORMATS:
                self._analyze_image()
            elif file_suffix in config.SUPPORTED_VIDEO_FORMATS:
                self._analyze_video()
            else:
                raise ValueError(f"Unsupported file format: {file_suffix}")
            
            self.analysis_complete.emit(self.results)
            
        except Exception as e:
            logger.error(f"Analiz hatası: {e}")
            self.error_occurred.emit(str(e))
    
    def _analyze_image(self):
        """Tek bir resmi analiz et"""
        try:
            self.progress_update.emit("Resim analiz ediliyor...")
            
            # Detect in image
            detection = self.detector.detect_in_image(self.file_path)
            
            # Extract metadata
            metadata = self.metadata_extractor.extract_image_metadata(self.file_path)
            
            # Prepare results
            self.results = {
                'filename': Path(self.file_path).name,
                'file_type': 'image',
                'detected': detection['detected'],
                'confidence': detection['confidence'],
                'capture_date': metadata['capture_date'],
                'capture_time': metadata['capture_time'],
                'analysis_date': datetime.now().strftime(config.REPORT_DATE_FORMAT),
                'analysis_time': datetime.now().strftime(config.REPORT_TIME_FORMAT),
                'analysis_datetime': datetime.now().isoformat(),
                'gps_latitude': metadata.get('gps_latitude'),
                'gps_longitude': metadata.get('gps_longitude'),
                'distance_m': None,
                'time_in_video': None,
                'crop_image': detection.get('crop'),
                'annotated_image': detection.get('annotated_image'),
                'original_image': detection.get('image'),
                'camera_make': metadata.get('camera_make'),
                'camera_model': metadata.get('camera_model'),
            }
            
            if detection['detected']:
                self.progress_update.emit(f"✓ Tespit bulundu! Güven: {detection['confidence']:.2%}")
            else:
                self.progress_update.emit("✗ Tespit bulunamadı")
        
        except Exception as e:
            logger.error(f"Resim analiz hatası: {e}")
            raise
    
    def _analyze_video(self):
        """Video dosyasını analiz et"""
        try:
            self.progress_update.emit("Video analiz ediliyor...")
            
            def progress_callback(current_frame, total_frames, confidence):
                self.frame_progress.emit(current_frame, total_frames, confidence)
                self.progress_update.emit(f"Frame {current_frame}/{total_frames} - Güven: {confidence:.2%}")
            
            # Detect in video
            detection = self.detector.detect_in_video(self.file_path, progress_callback)
            
            # Extract metadata
            metadata = self.metadata_extractor.extract_video_metadata(self.file_path)
            
            # Prepare results
            self.results = {
                'filename': Path(self.file_path).name,
                'file_type': 'video',
                'detected': detection['detected'],
                'confidence': detection['confidence'],
                'capture_date': metadata['capture_date'],
                'capture_time': metadata['capture_time'],
                'analysis_date': datetime.now().strftime(config.REPORT_DATE_FORMAT),
                'analysis_time': datetime.now().strftime(config.REPORT_TIME_FORMAT),
                'analysis_datetime': datetime.now().isoformat(),
                'gps_latitude': metadata.get('gps_latitude'),
                'gps_longitude': metadata.get('gps_longitude'),
                'distance_m': None,
                'time_in_video': detection.get('timestamp_mmss'),
                'crop_image': detection.get('crop'),
                'annotated_image': detection.get('annotated_frame'),
                'original_image': detection.get('detection_frame'),
                'fps': metadata.get('fps'),
                'total_frames': metadata.get('total_frames'),
            }
            
            if detection['detected']:
                msg = f"✓ Tespit: {detection['timestamp_mmss']} | Güven: {detection['confidence']:.2%}"
                self.progress_update.emit(msg)
            else:
                self.progress_update.emit("✗ Videoda tespit bulunamadı")
        
        except Exception as e:
            logger.error(f"Video analiz hatası: {e}")
            raise

class CropViewerWindow(QDialog):
    """Kirpilmis tespit goruntusunu gosteren dialog"""
    
    def __init__(self, crop_image, confidence, parent=None):
        super().__init__(parent)
        self.crop_image = crop_image
        self.confidence = confidence
        self.init_ui()
    
    def init_ui(self):
        """UI'yi baslat"""
        self.setWindowTitle("Tespit Kirpisi Goruntuyleyici")
        self.setGeometry(100, 100, 600, 500)
        
        layout = QVBoxLayout()
        
        # Image label
        image_label = QLabel()
        
        # Convert numpy array to QPixmap
        import cv2
        if len(self.crop_image.shape) == 3:
            h, w, ch = self.crop_image.shape
            img_rgb = cv2.cvtColor(self.crop_image, cv2.COLOR_BGR2RGB)
            bytes_per_line = 3 * w
            qt_image = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            h, w = self.crop_image.shape
            bytes_per_line = w
            qt_image = QImage(self.crop_image.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        
        pixmap = QPixmap.fromImage(qt_image)
        
        # Scale to fit window
        scaled_pixmap = pixmap.scaledToWidth(500, Qt.TransformationMode.SmoothTransformation)
        image_label.setPixmap(scaled_pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(image_label)
        
        # Confidence info
        info_label = QLabel(f"Confidence: {self.confidence:.2%}")
        info_font = QFont()
        info_font.setPointSize(12)
        info_font.setBold(True)
        info_label.setFont(info_font)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Kirpiyi Kaydet")
        save_btn.clicked.connect(self.save_crop)
        button_layout.addWidget(save_btn)
        
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(lambda: (self.close(), None)[1])
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def save_crop(self):
        """Kirpi goruntusunu dosyaya kaydet"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            self, "Tespit Kirpisini Kaydet", "",
            "JPEG (*.jpg);;PNG (*.png);;Tum Dosyalar (*)"
        )
        
        if file_path:
            if save_image(self.crop_image, file_path):
                QMessageBox.information(self, "Basarili", f"Kirpi kaydedildi:\n{file_path}")
            else:
                QMessageBox.critical(self, "Hata", "Kirpi goruntsu kaydedilemedi")

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.detector = None
        self.metadata_extractor = MetadataExtractor()
        self.report_generator = ReportGenerator()
        self.model_trainer = ModelTrainer()
        self.selected_files = []
        self.current_file = None
        self.analysis_results = None
        self.analysis_thread = None
        self.training_thread = None
        self.training_images = []
        self.training_labels = []
        self.ui_ready = False
        
        self.init_ui()
        self.ui_ready = True
        self.load_model()
    
    def init_ui(self):
        """Kullanici arayuzunu baslat"""
        self.setWindowTitle("Drone Obus Tespit Sistemi")
        self.setGeometry(50, 50, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        
        # Tab Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        
        # Tab widget olustur
        self.tabs = QTabWidget()
        
        # Tab 1: Analiz
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout()
        self._init_analysis_ui(analysis_layout)
        analysis_tab.setLayout(analysis_layout)
        self.tabs.addTab(analysis_tab, "Analiz")
        
        # Tab 2: Model Egitimi
        training_tab = QWidget()
        training_layout = QVBoxLayout()
        self._init_training_ui(training_layout)
        training_tab.setLayout(training_layout)
        self.tabs.addTab(training_tab, "Model Egitimi")
        
        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)
    
    def _init_analysis_ui(self, main_layout):
        """Analiz sekmesinin UI'sini olustur"""
        
        # ============ BAŞLIK ============
        header_label = QLabel("🚁 Drone Obüs Tespit Sistemi")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setStyleSheet("color: #1a1a1a; margin-bottom: 10px;")
        main_layout.addWidget(header_label)
        
        # ============ DOSYA YÜKLEME BÖLÜMÜ (Büyük ve Belirgin) ============
        file_section = QFrame()
        file_section.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4A90E2, stop:1 #357ABD);
                border-radius: 8px;
                border: 2px solid #2E5FA3;
            }
        """)
        file_section.setMinimumHeight(140)
        file_layout = QVBoxLayout()
        file_layout.setContentsMargins(20, 20, 20, 20)
        file_layout.setSpacing(10)
        
        upload_title = QLabel("📁 Dosya Seçin")
        upload_title_font = QFont()
        upload_title_font.setPointSize(13)
        upload_title_font.setBold(True)
        upload_title.setFont(upload_title_font)
        upload_title.setStyleSheet("color: white;")
        file_layout.addWidget(upload_title)
        
        self.file_label = QLabel("Henüz dosya seçilmedi")
        self.file_label.setStyleSheet("color: #E8F0FF; font-size: 11px;")
        file_layout.addWidget(self.file_label)
        
        browse_btn = QPushButton("📂 Resim veya Video Yükle")
        browse_btn.setMinimumHeight(50)
        browse_btn.setFont(QFont("Arial", 11, QFont.Bold))
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFD700;
                color: #1a1a1a;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FFC700;
            }
            QPushButton:pressed {
                background-color: #FFB700;
            }
        """)
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        
        file_section.setLayout(file_layout)
        main_layout.addWidget(file_section)
        
        # ============ ÖN İZLEME VE KONTROLLER ============
        preview_control_layout = QHBoxLayout()
        preview_control_layout.setSpacing(15)
        
        # --- ÖN İZLEME ---
        preview_section = QFrame()
        preview_section.setStyleSheet("""
            QFrame {
                border: 2px solid #4A90E2;
                border-radius: 8px;
                background-color: #FAFAFA;
            }
        """)
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(10, 10, 10, 10)
        
        preview_title = QLabel("📸 Ön İzleme")
        preview_title_font = QFont()
        preview_title_font.setPointSize(10)
        preview_title_font.setBold(True)
        preview_title.setFont(preview_title_font)
        preview_layout.addWidget(preview_title)
        
        self.preview_image = QLabel()
        self.preview_image.setMinimumSize(200, 200)
        self.preview_image.setMaximumSize(250, 250)
        self.preview_image.setStyleSheet("""
            border: 2px dashed #4A90E2; 
            background-color: white;
            border-radius: 5px;
        """)
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setText("Resim/Video\nYüklenmemişi")
        self.preview_image.setStyleSheet("""
            border: 2px dashed #4A90E2; 
            background-color: white;
            border-radius: 5px;
            color: #999;
        """)
        preview_layout.addWidget(self.preview_image, alignment=Qt.AlignmentFlag.AlignCenter)
        preview_layout.addStretch()
        
        preview_section.setLayout(preview_layout)
        preview_control_layout.addWidget(preview_section)
        
        # --- KONTROLLER ---
        control_section = QFrame()
        control_section.setStyleSheet("""
            QFrame {
                border: 2px solid #E8E8E8;
                border-radius: 8px;
                background-color: #FAFAFA;
            }
        """)
        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(15, 15, 15, 15)
        control_layout.setSpacing(15)
        
        control_title = QLabel("⚙️ Ayarlar")
        control_title_font = QFont()
        control_title_font.setPointSize(10)
        control_title_font.setBold(True)
        control_title.setFont(control_title_font)
        control_layout.addWidget(control_title)
        
        # Güven Eşiği
        threshold_container = QVBoxLayout()
        threshold_label = QLabel("Güven Eşiği:")
        threshold_label.setFont(QFont("Arial", 10, QFont.Bold))
        threshold_container.addWidget(threshold_label)
        
        threshold_slider_layout = QHBoxLayout()
        self.threshold_slider = QSlider()
        self.threshold_slider.setEnabled(False)
        self.threshold_slider.setOrientation(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(int(config.DEFAULT_CONFIDENCE_MIN * 100))
        self.threshold_slider.setMaximum(int(config.DEFAULT_CONFIDENCE_MAX * 100))
        self.threshold_slider.setValue(int(config.CONFIDENCE_THRESHOLD * 100))
        self.threshold_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999;
                height: 8px;
                background: #E0E0E0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4A90E2;
                border: 1px solid #2E5FA3;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)
        self.threshold_slider.valueChanged.connect(self.update_threshold)
        threshold_slider_layout.addWidget(self.threshold_slider)
        
        self.threshold_value_label = QLabel(f"{config.CONFIDENCE_THRESHOLD:.0%}")
        self.threshold_value_label.setMinimumWidth(45)
        self.threshold_value_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.threshold_value_label.setStyleSheet("color: #4A90E2;")
        threshold_slider_layout.addWidget(self.threshold_value_label)
        
        threshold_container.addLayout(threshold_slider_layout)
        control_layout.addLayout(threshold_container)
        
        control_layout.addSpacing(10)
        
        # Analiz Butonu (Büyük ve Göz Çarpıcı)
        self.analyze_btn = QPushButton("🔍 ANALIZI BAŞLAT")
        self.analyze_btn.setMinimumHeight(60)
        self.analyze_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1E8449;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
                color: #7F8C8D;
            }
        """)
        self.analyze_btn.clicked.connect(self.start_analysis)
        control_layout.addWidget(self.analyze_btn)
        
        control_layout.addStretch()
        
        control_section.setLayout(control_layout)
        preview_control_layout.addWidget(control_section)
        
        main_layout.addLayout(preview_control_layout)
        
        # ============ İlerleme Çubuğu ============
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4A90E2;
                border-radius: 5px;
                background-color: #F0F0F0;
                text-align: center;
                color: #1a1a1a;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4A90E2, stop:1 #2E5FA3);
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # ============ SONUÇ BÖLÜMÜ ============
        results_section = QFrame()
        results_section.setStyleSheet("""
            QFrame {
                border: 2px solid #E8E8E8;
                border-radius: 8px;
                background-color: #FAFAFA;
            }
        """)
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(15, 15, 15, 15)
        results_layout.setSpacing(12)
        
        results_title = QLabel("📊 Analiz Sonuçları")
        results_title_font = QFont()
        results_title_font.setPointSize(11)
        results_title_font.setBold(True)
        results_title.setFont(results_title_font)
        results_layout.addWidget(results_title)
        
        # Sonuç ızgarası (daha kompakt)
        results_grid = QGridLayout()
        results_grid.setSpacing(8)
        
        # Tespit durumu
        status_label = QLabel("Tespit Durumu:")
        status_label.setStyleSheet("font-weight: bold; color: #333;")
        results_grid.addWidget(status_label, 0, 0)
        self.status_value = QLabel("N/A")
        self.status_value.setFont(QFont("Arial", 11, QFont.Bold))
        self.status_value.setStyleSheet("color: #999;")
        results_grid.addWidget(self.status_value, 0, 1)
        
        # Güven puanı
        conf_label = QLabel("Güven Puanı:")
        conf_label.setStyleSheet("font-weight: bold; color: #333;")
        results_grid.addWidget(conf_label, 0, 2)
        self.conf_value = QLabel("N/A")
        self.conf_value.setStyleSheet("color: #999;")
        results_grid.addWidget(self.conf_value, 0, 3)
        
        # Çekim tarihi
        capture_date_label = QLabel("Çekim Tarihi:")
        capture_date_label.setStyleSheet("font-weight: bold; color: #333;")
        results_grid.addWidget(capture_date_label, 1, 0)
        self.capture_date_value = QLabel("N/A")
        self.capture_date_value.setStyleSheet("color: #999;")
        results_grid.addWidget(self.capture_date_value, 1, 1)
        
        # Çekim saati
        capture_time_label = QLabel("Çekim Saati:")
        capture_time_label.setStyleSheet("font-weight: bold; color: #333;")
        results_grid.addWidget(capture_time_label, 1, 2)
        self.capture_time_value = QLabel("N/A")
        self.capture_time_value.setStyleSheet("color: #999;")
        results_grid.addWidget(self.capture_time_value, 1, 3)
        
        # GPS
        gps_label = QLabel("GPS Koordinatları:")
        gps_label.setStyleSheet("font-weight: bold; color: #333;")
        results_grid.addWidget(gps_label, 2, 0)
        self.gps_value = QLabel("N/A")
        self.gps_value.setStyleSheet("color: #999;")
        results_grid.addWidget(self.gps_value, 2, 1, 1, 3)
        
        # Tespit zamanı (videolar için)
        time_video_label = QLabel("Tespit Zamanı (DD:SS):")
        time_video_label.setStyleSheet("font-weight: bold; color: #333;")
        results_grid.addWidget(time_video_label, 3, 0)
        self.time_video_value = QLabel("N/A")
        self.time_video_value.setStyleSheet("color: #999;")
        results_grid.addWidget(self.time_video_value, 3, 1)
        
        results_layout.addLayout(results_grid)
        results_layout.addSpacing(8)
        
        # Düğmeler (daha güçlü stiller)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.crop_btn = QPushButton("🖼️ Kırpıyı Görüntüle")
        self.crop_btn.setMinimumHeight(40)
        self.crop_btn.setEnabled(False)
        self.crop_btn.setStyleSheet("""
            QPushButton {
                background-color: #9B59B6;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #884BA3;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
            }
        """)
        self.crop_btn.clicked.connect(self.view_crop)
        button_layout.addWidget(self.crop_btn)
        
        self.export_excel_btn = QPushButton("📋 Excel'e Aktar")
        self.export_excel_btn.setMinimumHeight(40)
        self.export_excel_btn.setEnabled(False)
        self.export_excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
            }
        """)
        self.export_excel_btn.clicked.connect(self.export_excel)
        button_layout.addWidget(self.export_excel_btn)
        
        self.export_json_btn = QPushButton("📄 JSON'a Aktar")
        self.export_json_btn.setMinimumHeight(40)
        self.export_json_btn.setEnabled(False)
        self.export_json_btn.setStyleSheet("""
            QPushButton {
                background-color: #E67E22;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D35400;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
            }
        """)
        self.export_json_btn.clicked.connect(self.export_json)
        button_layout.addWidget(self.export_json_btn)
        
        results_layout.addLayout(button_layout)
        
        results_section.setLayout(results_layout)
        main_layout.addWidget(results_section)
        
        # ============ LOG BÖLÜMÜ ============
        log_section = QFrame()
        log_section.setStyleSheet("""
            QFrame {
                border: 1px solid #DDD;
                border-radius: 5px;
                background-color: #FFF;
            }
        """)
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(8)
        
        log_label = QLabel("📝 Analiz Günlüğü")
        log_label_font = QFont()
        log_label_font.setPointSize(9)
        log_label_font.setBold(True)
        log_label.setFont(log_label_font)
        log_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(80)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #F5F5F5;
                border: 1px solid #DDD;
                border-radius: 3px;
                font-size: 9px;
                font-family: 'Courier New', monospace;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        log_section.setLayout(log_layout)
        main_layout.addWidget(log_section)
    
    def _init_training_ui(self, main_layout):
        """Model egitimi sekmesinin UI'sini olustur - Tab yapısı"""
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Başlık
        header_label = QLabel("🔬 YOLO Model Eğitimi Sistemi")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setStyleSheet("color: #1a1a1a; margin-bottom: 5px;")
        main_layout.addWidget(header_label)
        
        # Alt Sekmeler
        training_tabs = QTabWidget()
        
        # TAB 1: İçerik Yükleme
        upload_tab = QWidget()
        upload_layout = QVBoxLayout()
        self._init_training_upload_tab(upload_layout)
        upload_tab.setLayout(upload_layout)
        training_tabs.addTab(upload_tab, "📥 İçerik Yükleme")
        
        # TAB 2: Kategori Yönetimi
        category_tab = QWidget()
        category_layout = QVBoxLayout()
        self._init_category_management_tab(category_layout)
        category_tab.setLayout(category_layout)
        training_tabs.addTab(category_tab, "🗂️ Kategori Yönetimi")
        
        # TAB 3: İçerik Kontrolü
        control_tab = QWidget()
        control_layout = QVBoxLayout()
        self._init_content_control_tab(control_layout)
        control_tab.setLayout(control_layout)
        training_tabs.addTab(control_tab, "📊 İçerik Kontrolü")
        
        # TAB 4: Eğitim Ayarları
        settings_tab = QWidget()
        settings_layout = QVBoxLayout()
        self._init_training_settings_tab(settings_layout)
        settings_tab.setLayout(settings_layout)
        training_tabs.addTab(settings_tab, "⚙️ Eğitim Ayarları")
        
        main_layout.addWidget(training_tabs)
    
    def _init_training_upload_tab(self, layout):
        """TAB 1: İçerik Yükleme"""
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Kategori ve Bölüm Seçimi
        select_frame = QFrame()
        select_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #16A085;
                border-radius: 8px;
                background-color: #E8F8F5;
            }
        """)
        select_layout = QVBoxLayout()
        select_layout.setContentsMargins(15, 15, 15, 15)
        select_layout.setSpacing(10)
        
        select_title = QLabel("📚 Hedef Kategori ve Bölümü Seçin")
        select_title_font = QFont()
        select_title_font.setPointSize(11)
        select_title_font.setBold(True)
        select_title.setFont(select_title_font)
        select_layout.addWidget(select_title)
        
        choice_layout = QHBoxLayout()
        choice_layout.addWidget(QLabel("Kategori:"))
        self.upload_category_combo = QComboBox()
        self.upload_category_combo.addItems(self._get_available_categories())
        self.upload_category_combo.setMinimumWidth(150)
        choice_layout.addWidget(self.upload_category_combo)
        
        choice_layout.addWidget(QLabel("Bölüm:"))
        self.upload_split_combo = QComboBox()
        self.upload_split_combo.addItems(['train', 'val', 'test'])
        self.upload_split_combo.setCurrentIndex(0)
        self.upload_split_combo.setMinimumWidth(100)
        choice_layout.addWidget(self.upload_split_combo)
        choice_layout.addStretch()
        
        select_layout.addLayout(choice_layout)
        select_frame.setLayout(select_layout)
        layout.addWidget(select_frame)
        
        # Yükleme Butonları
        upload_frame = QFrame()
        upload_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #E67E22;
                border-radius: 8px;
                background-color: #FEF5E7;
            }
        """)
        upload_btn_layout = QVBoxLayout()
        upload_btn_layout.setContentsMargins(15, 15, 15, 15)
        upload_btn_layout.setSpacing(10)
        
        upload_title = QLabel("📁 Dosya Yükleyin")
        upload_title_font = QFont()
        upload_title_font.setPointSize(11)
        upload_title_font.setBold(True)
        upload_title.setFont(upload_title_font)
        upload_btn_layout.addWidget(upload_title)
        
        # Buton satırı
        btn_row1 = QHBoxLayout()
        
        images_btn = QPushButton("📷 Resimler Yükle")
        images_btn.setMinimumHeight(45)
        images_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)
        images_btn.clicked.connect(self.browse_training_images)
        btn_row1.addWidget(images_btn)
        
        labels_btn = QPushButton("🏷️ Labellar Yükle")
        labels_btn.setMinimumHeight(45)
        labels_btn.setStyleSheet("""
            QPushButton {
                background-color: #9B59B6;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #884BA3;
            }
        """)
        labels_btn.clicked.connect(self.browse_training_labels)
        btn_row1.addWidget(labels_btn)
        
        upload_btn_layout.addLayout(btn_row1)
        
        # Video Processing
        btn_row2 = QHBoxLayout()
        
        video_btn = QPushButton("🎬 Video'dan Frame Çıkar")
        video_btn.setMinimumHeight(45)
        video_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        video_btn.clicked.connect(self.extract_video_frames)
        btn_row2.addWidget(video_btn)
        btn_row2.addStretch()
        
        upload_btn_layout.addLayout(btn_row2)
        
        # Yükleme Listesi
        upload_btn_layout.addWidget(QLabel("📝 Yükleme Geçmişi:"))
        self.upload_history_list = QListWidget()
        self.upload_history_list.setMaximumHeight(150)
        self.upload_history_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #DDD;
                border-radius: 3px;
                background-color: white;
                font-size: 9px;
            }
        """)
        upload_btn_layout.addWidget(self.upload_history_list)
        
        upload_frame.setLayout(upload_btn_layout)
        layout.addWidget(upload_frame)
        layout.addStretch()
    
    def _init_category_management_tab(self, layout):
        """TAB 2: Kategori Yönetimi - CRUD işlemleri"""
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        header = QLabel("🗂️ Kategori Yönetim Araçları")
        header_font = QFont()
        header_font.setPointSize(11)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Kategorileri Listele
        list_frame = QFrame()
        list_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #3498DB;
                border-radius: 8px;
                background-color: #EBF5FB;
            }
        """)
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(15, 15, 15, 15)
        list_layout.setSpacing(10)
        
        list_layout.addWidget(QLabel("📋 Mevcut Kategoriler:"))
        self.categories_list = QListWidget()
        self.categories_list.setSelectionMode(QListWidget.SingleSelection)
        self.categories_list.setMaximumHeight(150)
        self.categories_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #DDD;
                border-radius: 3px;
                background-color: white;
            }
        """)
        self.refresh_categories_list()
        list_layout.addWidget(self.categories_list)
        
        list_frame.setLayout(list_layout)
        layout.addWidget(list_frame)
        
        # Kategori İçeriği İstatistikleri
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #27AE60;
                border-radius: 8px;
                background-color: #EAFAF1;
            }
        """)
        stats_layout = QVBoxLayout()
        stats_layout.setContentsMargins(15, 15, 15, 15)
        stats_layout.setSpacing(10)
        
        stats_layout.addWidget(QLabel("📊 Kategori İstatistikleri:"))
        self.category_stats_text = QTextEdit()
        self.category_stats_text.setReadOnly(True)
        self.category_stats_text.setMaximumHeight(120)
        self.category_stats_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #DDD;
                border-radius: 3px;
                font-size: 9px;
                font-family: 'Courier New', monospace;
            }
        """)
        stats_layout.addWidget(self.category_stats_text)
        
        stats_frame.setLayout(stats_layout)
        layout.addWidget(stats_frame)
        
        # Kategori İşlemleri
        ops_frame = QFrame()
        ops_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #E67E22;
                border-radius: 8px;
                background-color: #FEF5E7;
            }
        """)
        ops_layout = QVBoxLayout()
        ops_layout.setContentsMargins(15, 15, 15, 15)
        ops_layout.setSpacing(10)
        
        ops_layout.addWidget(QLabel("🛠️ Kategori İşlemleri:"))
        
        # Yeni Kategori Oluştur
        new_cat_layout = QHBoxLayout()
        new_cat_layout.addWidget(QLabel("Yeni Kategori Adı:"))
        self.new_category_input = QLineEdit()
        self.new_category_input.setPlaceholderText("örn: nora_b52, zuzna, etc.")
        self.new_category_input.setMinimumWidth(200)
        new_cat_layout.addWidget(self.new_category_input)
        
        add_cat_btn = QPushButton("➕ Kategori Oluştur")
        add_cat_btn.setMinimumHeight(35)
        add_cat_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        add_cat_btn.clicked.connect(self.create_new_category)
        new_cat_layout.addWidget(add_cat_btn)
        new_cat_layout.addStretch()
        ops_layout.addLayout(new_cat_layout)
        
        # Kategori Silme/Çıkarma
        delete_cat_layout = QHBoxLayout()
        
        rename_cat_btn = QPushButton("✏️ Kategoriyi Yeniden Adlandır")
        rename_cat_btn.setMinimumHeight(35)
        rename_cat_btn.setStyleSheet("""
            QPushButton {
                background-color: #F39C12;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E67E22;
            }
        """)
        rename_cat_btn.clicked.connect(self.rename_category)
        delete_cat_layout.addWidget(rename_cat_btn)
        
        delete_cat_btn = QPushButton("❌ Kategoriyi Sil")
        delete_cat_btn.setMinimumHeight(35)
        delete_cat_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        delete_cat_btn.clicked.connect(self.delete_category)
        delete_cat_layout.addWidget(delete_cat_btn)
        delete_cat_layout.addStretch()
        ops_layout.addLayout(delete_cat_layout)
        
        ops_frame.setLayout(ops_layout)
        layout.addWidget(ops_frame)
        
        layout.addStretch()
    
    def _init_content_control_tab(self, layout):
        """TAB 3: İçerik Kontrolü - Görüntüleme, Silme, Değiştirme"""
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        header = QLabel("📊 Kategori İçeriğini Yönet")
        header_font = QFont()
        header_font.setPointSize(11)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Kategori ve Bölüm Seçimi
        select_frame = QFrame()
        select_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #16A085;
                border-radius: 8px;
                background-color: #E8F8F5;
            }
        """)
        select_layout = QHBoxLayout()
        select_layout.setContentsMargins(15, 10, 15, 10)
        select_layout.setSpacing(10)
        
        select_layout.addWidget(QLabel("Kategori:"))
        self.content_category_combo = QComboBox()
        self.content_category_combo.addItems(self._get_available_categories())
        self.content_category_combo.currentTextChanged.connect(self.refresh_content_display)
        select_layout.addWidget(self.content_category_combo)
        
        select_layout.addWidget(QLabel("Bölüm:"))
        self.content_split_combo = QComboBox()
        self.content_split_combo.addItems(['train', 'val', 'test'])
        self.content_split_combo.currentTextChanged.connect(self.refresh_content_display)
        select_layout.addWidget(self.content_split_combo)
        
        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.setMinimumHeight(35)
        refresh_btn.clicked.connect(self.refresh_content_display)
        select_layout.addWidget(refresh_btn)
        select_layout.addStretch()
        
        select_frame.setLayout(select_layout)
        layout.addWidget(select_frame)
        
        # Dosya Listesi
        files_frame = QFrame()
        files_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #3498DB;
                border-radius: 8px;
                background-color: #EBF5FB;
            }
        """)
        files_layout = QHBoxLayout()
        files_layout.setContentsMargins(15, 15, 15, 15)
        files_layout.setSpacing(10)
        
        # Resimler
        img_section = QVBoxLayout()
        img_section.addWidget(QLabel("📷 Resimler:"))
        self.content_images_list = QListWidget()
        self.content_images_list.setSelectionMode(QListWidget.MultiSelection)
        self.content_images_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #DDD;
                border-radius: 3px;
                background-color: white;
                font-size: 9px;
            }
        """)
        img_section.addWidget(self.content_images_list)
        files_layout.addLayout(img_section)
        
        # Labellar
        lbl_section = QVBoxLayout()
        lbl_section.addWidget(QLabel("🏷️ Labellar:"))
        self.content_labels_list = QListWidget()
        self.content_labels_list.setSelectionMode(QListWidget.MultiSelection)
        self.content_labels_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #DDD;
                border-radius: 3px;
                background-color: white;
                font-size: 9px;
            }
        """)
        lbl_section.addWidget(self.content_labels_list)
        files_layout.addLayout(lbl_section)
        
        files_frame.setLayout(files_layout)
        layout.addWidget(files_frame, 1)
        
        # İstatistik ve İşlemler
        ops_frame = QFrame()
        ops_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #E74C3C;
                border-radius: 8px;
                background-color: #FADBD8;
            }
        """)
        ops_layout = QVBoxLayout()
        ops_layout.setContentsMargins(15, 15, 15, 15)
        ops_layout.setSpacing(10)
        
        # İstatistik
        self.content_stats_label = QLabel("Resimler: 0 | Labellar: 0")
        self.content_stats_label.setStyleSheet("color: #333; font-weight: bold; font-size: 10px;")
        ops_layout.addWidget(self.content_stats_label)
        
        # Işlemler
        ops_btn_layout = QHBoxLayout()
        
        del_img_btn = QPushButton("❌ Seçili Resimleri Sil")
        del_img_btn.setMinimumHeight(35)
        del_img_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B6B;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #FF5252;
            }
        """)
        del_img_btn.clicked.connect(self.delete_selected_images)
        ops_btn_layout.addWidget(del_img_btn)
        
        del_lbl_btn = QPushButton("❌ Seçili Labelları Sil")
        del_lbl_btn.setMinimumHeight(35)
        del_lbl_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #FB8C00;
            }
        """)
        del_lbl_btn.clicked.connect(self.delete_selected_labels)
        ops_btn_layout.addWidget(del_lbl_btn)
        
        del_all_btn = QPushButton("⚠️ Tümünü Sil")
        del_all_btn.setMinimumHeight(35)
        del_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #A52A2A;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #8B2323;
            }
        """)
        del_all_btn.clicked.connect(self.delete_all_content)
        ops_btn_layout.addWidget(del_all_btn)
        ops_btn_layout.addStretch()
        
        ops_layout.addLayout(ops_btn_layout)
        
        ops_frame.setLayout(ops_layout)
        layout.addWidget(ops_frame)
    
    def _init_training_settings_tab(self, layout):
        """TAB 4: Eğitim Ayarları ve Başlat"""
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        header = QLabel("⚙️ Eğitim Parametreleri")
        header_font = QFont()
        header_font.setPointSize(11)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Parametreler
        params_frame = QFrame()
        params_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #3498DB;
                border-radius: 8px;
                background-color: #EBF5FB;
            }
        """)
        params_layout = QVBoxLayout()
        params_layout.setContentsMargins(15, 15, 15, 15)
        params_layout.setSpacing(15)
        
        # Kategori Seçimi
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("Eğitim Kategorisi:"))
        self.training_category_combo = QComboBox()
        self.training_category_combo.addItems(self._get_available_categories())
        self.training_category_combo.setMinimumWidth(150)
        cat_layout.addWidget(self.training_category_combo)
        cat_layout.addStretch()
        params_layout.addLayout(cat_layout)
        
        # Epoch
        epoch_layout = QHBoxLayout()
        epoch_layout.addWidget(QLabel("Epoch Sayısı:"))
        self.epoch_spinbox = QSpinBox()
        self.epoch_spinbox.setMinimum(1)
        self.epoch_spinbox.setMaximum(500)
        self.epoch_spinbox.setValue(50)
        self.epoch_spinbox.setMinimumWidth(100)
        epoch_layout.addWidget(self.epoch_spinbox)
        epoch_layout.addStretch()
        params_layout.addLayout(epoch_layout)
        
        # Batch Size
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(QLabel("Batch Boyutu:"))
        self.batch_spinbox = QSpinBox()
        self.batch_spinbox.setMinimum(1)
        self.batch_spinbox.setMaximum(128)
        self.batch_spinbox.setValue(16)
        self.batch_spinbox.setMinimumWidth(100)
        batch_layout.addWidget(self.batch_spinbox)
        batch_layout.addStretch()
        params_layout.addLayout(batch_layout)
        
        # İmg Size
        imgsz_layout = QHBoxLayout()
        imgsz_layout.addWidget(QLabel("Resim Boyutu:"))
        self.imgsz_spinbox = QSpinBox()
        self.imgsz_spinbox.setMinimum(320)
        self.imgsz_spinbox.setMaximum(1280)
        self.imgsz_spinbox.setValue(640)
        self.imgsz_spinbox.setSingleStep(64)
        self.imgsz_spinbox.setMinimumWidth(100)
        imgsz_layout.addWidget(self.imgsz_spinbox)
        imgsz_layout.addStretch()
        params_layout.addLayout(imgsz_layout)
        
        params_frame.setLayout(params_layout)
        layout.addWidget(params_frame)
        
        # İlerleme ve Günlük
        progress_frame = QFrame()
        progress_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #27AE60;
                border-radius: 8px;
                background-color: #EAFAF1;
            }
        """)
        progress_layout = QVBoxLayout()
        progress_layout.setContentsMargins(15, 15, 15, 15)
        progress_layout.setSpacing(10)
        
        progress_layout.addWidget(QLabel("📈 Eğitim İlerlemesi:"))
        
        self.training_progress = QProgressBar()
        self.training_progress.setVisible(False)
        self.training_progress.setMinimumHeight(25)
        self.training_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #27AE60;
                border-radius: 5px;
                background-color: #F0F0F0;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #27AE60;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.training_progress)
        
        progress_layout.addWidget(QLabel("📝 Eğitim Günlüğü:"))
        self.training_log = QTextEdit()
        self.training_log.setReadOnly(True)
        self.training_log.setMaximumHeight(120)
        self.training_log.setStyleSheet("""
            QTextEdit {
                background-color: #F5F5F5;
                border: 1px solid #DDD;
                border-radius: 3px;
                font-size: 8px;
                font-family: 'Courier New', monospace;
            }
        """)
        progress_layout.addWidget(self.training_log)
        
        progress_frame.setLayout(progress_layout)
        layout.addWidget(progress_frame)
        
        # Başlat Butonu
        self.train_btn = QPushButton("🚀 EGITIMI BAŞLAT")
        self.train_btn.setMinimumHeight(60)
        self.train_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.train_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
                color: #7F8C8D;
            }
        """)
        self.train_btn.clicked.connect(self.start_training)
        layout.addWidget(self.train_btn)
    
    def load_model(self):
        """YOLOv8 modelini yükle"""
        try:
            self.log("YOLO modeli yukleniyor...")
            self.detector = HowitzerDetector()
            if self.detector.model is None:
                self.log("UYARI: YOLO modeli yüklenemedi")
                QMessageBox.warning(self, "YOLO Uyarisi", 
                                   "YOLO modeli yuklenemedi. Ultralytics ve Torch kurulu mu kontrol edin.")
            else:
                self.log("YOLO modeli basarili yüklendi")
        except Exception as e:
            self.log(f"HATA: Model yukleme basarisiz: {e}")
            QMessageBox.critical(self, "Model Yukleme Hatasi", 
                               f"YOLO modeli yüklenemedi: {str(e)}")
    
    def browse_training_images(self):
        """Egitim resimlerini seç ve kategoriye/bölüme kopyala"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Egitim Resimlerini Sec",
            "", "Resim Dosyalari (*.jpg *.png *.jpeg);;Tum Dosyalar (*)"
        )
        if files:
            category = self.upload_category_combo.currentText()
            split = self.upload_split_combo.currentText()
            
            try:
                copied_count = 0
                for file_path in files:
                    if self.model_trainer.copy_image_to_category(
                        file_path, 
                        category=category, 
                        dataset_split=split
                    ):
                        self.training_files_list.addItem(f"📷 {Path(file_path).name} → {category}/{split}")
                        copied_count += 1
                    else:
                        self.training_files_list.addItem(f"❌ {Path(file_path).name}")
                
                QMessageBox.information(self, "Basarili", 
                                      f"{copied_count}/{len(files)} resim '{category}' kategorisine '{split}' bölümüne yüklendi.")
                self.train_btn.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Resim yükleme hatası: {e}")
    
    def browse_training_labels(self):
        """Egitim labellarini seç ve kategoriye/bölüme kopyala"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Egitim Labellarini Sec",
            "", "Label Dosyalari (*.txt);;Tum Dosyalar (*)"
        )
        if files:
            category = self.upload_category_combo.currentText()
            split = self.upload_split_combo.currentText()
            
            try:
                copied_count = 0
                for file_path in files:
                    if self.model_trainer.copy_label_to_category(
                        file_path,
                        category=category,
                        dataset_split=split
                    ):
                        self.training_files_list.addItem(f"🏷️ {Path(file_path).name} → {category}/{split}")
                        copied_count += 1
                    else:
                        self.training_files_list.addItem(f"❌ {Path(file_path).name}")
                
                QMessageBox.information(self, "Basarili", 
                                      f"{copied_count}/{len(files)} label '{category}' kategorisine '{split}' bölümüne yüklendi.")
                self.train_btn.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Label yükleme hatası: {e}")
    
    def extract_video_frames(self):
        """Video dosyasından frame çıkar ve dataset'e ekle"""
        # Video dosyasını seç
        video_path, _ = QFileDialog.getOpenFileName(
            self, "Eğitim Video'sunu Seç",
            "", "Video Dosyaları (*.mp4 *.avi *.mov *.mkv *.flv);;Tüm Dosyalar (*)"
        )
        
        if not video_path:
            return
        
        # Dialog oluştur
        dialog = QDialog(self)
        dialog.setWindowTitle("Video Frame Çıkarma Ayarları")
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout()
        
        # Kategori seçimi
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Kategori:"))
        category_combo = QComboBox()
        category_combo.addItems(self._get_available_categories())
        category_layout.addWidget(category_combo)
        layout.addLayout(category_layout)
        
        # Frame aralığı
        frame_interval_layout = QHBoxLayout()
        frame_interval_layout.addWidget(QLabel("Frame Aralığı (her N frame):"))
        frame_interval_spin = QSpinBox()
        frame_interval_spin.setMinimum(1)
        frame_interval_spin.setMaximum(30)
        frame_interval_spin.setValue(5)
        frame_interval_layout.addWidget(frame_interval_spin)
        layout.addLayout(frame_interval_layout)
        
        # Maksimum frame sayısı
        max_frames_layout = QHBoxLayout()
        max_frames_layout.addWidget(QLabel("Maksimum Frame Sayısı:"))
        max_frames_spin = QSpinBox()
        max_frames_spin.setMinimum(0)  # 0 = sınırsız
        max_frames_spin.setMaximum(10000)
        max_frames_spin.setValue(0)
        max_frames_layout.addWidget(max_frames_spin)
        layout.addLayout(max_frames_layout)
        
        # Data split seçimi
        split_layout = QHBoxLayout()
        split_layout.addWidget(QLabel("Dataset Split:"))
        split_combo = QComboBox()
        split_combo.addItems(['train', 'val', 'test'])
        split_combo.setCurrentIndex(0)
        split_layout.addWidget(split_combo)
        layout.addLayout(split_layout)
        
        # İnfo label
        info_label = QLabel("Boş label dosyaları otomatik oluşturulacak.\nDaha sonra annotation aracıyla doldurabilirsiniz.")
        info_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(info_label)
        
        # Butonlar
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            frame_interval = frame_interval_spin.value()
            max_frames = max_frames_spin.value() if max_frames_spin.value() > 0 else None
            dataset_split = split_combo.currentText()
            category = category_combo.currentText()
            
            # Frame çıkarma işlemini başlat
            self.training_progress.setVisible(True)
            self.training_progress.setValue(0)
            self.train_btn.setEnabled(False)
            
            def video_progress(progress, msg):
                if isinstance(progress, int):
                    self.training_progress.setValue(progress)
                self.training_log.append(f"[Video] {msg}")
            
            try:
                self.training_log.append(f"Video işleniyor: {Path(video_path).name}")
                self.training_log.append(f"  - Kategori: {category}")
                self.training_log.append(f"  - Frame Aralığı: Her {frame_interval}. frame")
                self.training_log.append(f"  - Max Frame: {max_frames if max_frames else 'Sınırsız'}")
                self.training_log.append(f"  - Split: {dataset_split}")
                
                # Frame çıkarma
                frame_count, frame_paths = self.model_trainer.extract_frames_from_video(
                    video_path,
                    frame_interval=frame_interval,
                    max_frames=max_frames,
                    dataset_split=dataset_split,
                    category=category,
                    progress_callback=video_progress
                )
                
                if frame_count > 0:
                    # Boş label dosyaları oluştur
                    self.training_log.append(f"Label dosyaları oluşturuluyor...")
                    self.model_trainer.create_empty_labels(frame_paths)
                    
                    # Dosya listesine ekle
                    for frame_path in frame_paths:
                        self.training_files_list.addItem(f"🎬 {Path(frame_path).name} → {category}/{dataset_split}")
                    
                    self.training_log.append(f"✅ {frame_count} frame başarıyla çıkartıldı!")
                    QMessageBox.information(self, "Başarılı", 
                                          f"{frame_count} frame çıkartıldı ve {category}/{dataset_split}'a eklendi.\n\nLütfen annotation aracıyla label dosyalarını doldurunuz.")
                else:
                    self.training_log.append("❌ Video işleme başarısız!")
                    QMessageBox.warning(self, "Hata", "Video işlenemedi!")
                    
            except Exception as e:
                self.training_log.append(f"❌ HATA: {e}")
                QMessageBox.critical(self, "Video İşleme Hatası", str(e))
            finally:
                self.training_progress.setVisible(False)
                self.train_btn.setEnabled(True)
    
    def _get_available_categories(self):
        """training_data/ altındaki mevcut kategorileri getir"""
        training_data_dir = Path(config.PROJECT_ROOT) / 'training_data'
        if not training_data_dir.exists():
            return ["default"]
        
        categories = []
        for item in training_data_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Kategorileri kontrol et (images ve labels subdirs var mı)
                if (item / 'images').exists() and (item / 'labels').exists():
                    categories.append(item.name)
        
        return categories if categories else ["default"]
    
    def refresh_category_files(self):
        """Seçili kategorideki dosyaları listele"""
        category = self.mgmt_category_combo.currentText()
        split = self.mgmt_split_combo.currentText()
        
        category_path = Path(config.PROJECT_ROOT) / 'training_data' / category
        
        # Resimleri listele
        self.mgmt_images_list.clear()
        images_dir = category_path / 'images' / split
        if images_dir.exists():
            for img_file in sorted(images_dir.glob('*')):
                self.mgmt_images_list.addItem(img_file.name)
        
        # Labelları listele
        self.mgmt_labels_list.clear()
        labels_dir = category_path / 'labels' / split
        if labels_dir.exists():
            for lbl_file in sorted(labels_dir.glob('*')):
                self.mgmt_labels_list.addItem(lbl_file.name)
        
        # İstatistik güncelle
        img_count = self.mgmt_images_list.count()
        lbl_count = self.mgmt_labels_list.count()
        self.mgmt_stats_label.setText(f"Resimler: {img_count} | Labellar: {lbl_count}")
    
    def delete_selected_images(self):
        """Seçili resimleri sil"""
        category = self.mgmt_category_combo.currentText()
        split = self.mgmt_split_combo.currentText()
        
        selected_items = self.mgmt_images_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Silmek için resim seçiniz!")
            return
        
        reply = QMessageBox.question(self, "Onay", 
                                    f"{len(selected_items)} resmi silmek istediğinize emin misiniz?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        try:
            deleted_count = 0
            images_dir = Path(config.PROJECT_ROOT) / 'training_data' / category / 'images' / split
            
            for item in selected_items:
                file_path = images_dir / item.text()
                if file_path.exists():
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Resim silindi: {file_path}")
            
            QMessageBox.information(self, "Başarılı", f"{deleted_count} resim silindi!")
            self.refresh_category_files()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatası: {e}")
    
    def delete_selected_labels(self):
        """Seçili labelları sil"""
        category = self.mgmt_category_combo.currentText()
        split = self.mgmt_split_combo.currentText()
        
        selected_items = self.mgmt_labels_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Silmek için label seçiniz!")
            return
        
        reply = QMessageBox.question(self, "Onay",
                                    f"{len(selected_items)} label'ı silmek istediğinize emin misiniz?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        try:
            deleted_count = 0
            labels_dir = Path(config.PROJECT_ROOT) / 'training_data' / category / 'labels' / split
            
            for item in selected_items:
                file_path = labels_dir / item.text()
                if file_path.exists():
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Label silindi: {file_path}")
            
            QMessageBox.information(self, "Başarılı", f"{deleted_count} label silindi!")
            self.refresh_category_files()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatası: {e}")
    
    def delete_all_category_files(self):
        """Kategorideki tüm dosyaları sil"""
        category = self.mgmt_category_combo.currentText()
        split = self.mgmt_split_combo.currentText()
        
        img_count = self.mgmt_images_list.count()
        lbl_count = self.mgmt_labels_list.count()
        
        if img_count + lbl_count == 0:
            QMessageBox.warning(self, "Uyarı", "Silinecek dosya yok!")
            return
        
        reply = QMessageBox.warning(self, "Dikkat!",
                                   f"'{category}/{split}' içindeki TÜM dosyaları silmek üzeresiniz!\n"
                                   f"Resimler: {img_count}\nLabellar: {lbl_count}\n\n"
                                   f"Devam etmek istiyor musunuz?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            deleted_count = 0
            
            # Resimleri sil
            images_dir = Path(config.PROJECT_ROOT) / 'training_data' / category / 'images' / split
            if images_dir.exists():
                for img_file in images_dir.glob('*'):
                    img_file.unlink()
                    deleted_count += 1
            
            # Labelları sil
            labels_dir = Path(config.PROJECT_ROOT) / 'training_data' / category / 'labels' / split
            if labels_dir.exists():
                for lbl_file in labels_dir.glob('*'):
                    lbl_file.unlink()
                    deleted_count += 1
            
            QMessageBox.information(self, "Başarılı", f"Toplam {deleted_count} dosya silindi!")
            self.refresh_category_files()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatası: {e}")
    
    def start_training(self):
        """Model egitimini basla"""
        # Kategori seç
        category = self.training_category_combo.currentText()
        
        if category == "default":
            QMessageBox.warning(self, "Hata", "Geçerli bir kategori seçiniz!")
            return
        
        # Seçili kategoride eğitim verisi var mı kontrol et
        category_path = Path(config.PROJECT_ROOT) / 'training_data' / category
        train_images = list((category_path / 'images' / 'train').glob('*')) if (category_path / 'images' / 'train').exists() else []
        train_labels = list((category_path / 'labels' / 'train').glob('*')) if (category_path / 'labels' / 'train').exists() else []
        
        if len(train_images) == 0 or len(train_labels) == 0:
            QMessageBox.warning(self, "Hata", 
                              f"'{category}' kategorisinde yeterli eğitim verisi yok!\n"
                              f"Images: {len(train_images)}, Labels: {len(train_labels)}")
            return
        
        self.train_btn.setEnabled(False)
        self.training_progress.setVisible(True)
        self.training_progress.setValue(0)
        
        def training_progress(epoch, msg):
            self.training_log.append(f"[{epoch}] {msg}")
            if isinstance(epoch, int) and epoch >= 0:
                self.training_progress.setValue(epoch)
        
        try:
            # Dataset YAML olustur
            self.training_log.append(f"Kategori '{category}' için model eğitimi başlanıyor...")
            self.training_log.append("Dataset YAML oluşturuluyor...")
            self.model_trainer.create_dataset_yaml()
            
            # Egitimi basla
            self.training_log.append("Model eğitimi başlanıyor...")
            self.model_trainer.train_model(
                epochs=self.epoch_spinbox.value(),
                batch_size=self.batch_spinbox.value(),
                imgsz=self.imgsz_spinbox.value(),
                progress_callback=training_progress
            )
            
            self.training_log.append("✅ Egitim tamamlandi!")
            self.training_progress.setValue(100)
            QMessageBox.information(self, "Basarili", "Model egitimi tamamlandi!")
            
        except Exception as e:
            self.training_log.append(f"❌ HATA: {e}")
            QMessageBox.critical(self, "Egitim Hatasi", f"Egitim basarisiz: {e}")
        finally:
            self.train_btn.setEnabled(True)
            self.training_progress.setVisible(False)
    
    
    def browse_file(self):
        """Çoklu dosya seç ve yükle"""
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(
            self, "Resim veya Video Sec (Çoklu)",
            "", "Desteklenen Dosyalar (*.jpg *.jpeg *.png *.bmp *.mp4 *.avi *.mov *.mkv);;Resimler (*.jpg *.jpeg *.png *.bmp);;Videolar (*.mp4 *.avi *.mov *.mkv);;Tum Dosyalar (*)"
        )
        
        if not file_paths:
            return
        
        # Dosyalari valide et
        valid_files = []
        for file_path in file_paths:
            is_valid, error_msg = validate_file(file_path)
            if is_valid:
                valid_files.append(file_path)
            else:
                self.log(f"UYARI: {Path(file_path).name} - {error_msg}")
        
        if not valid_files:
            QMessageBox.critical(self, "Hata", "Gecerli dosya yok!")
            return
        
        self.selected_files = valid_files
        self.current_file = None
        
        # Dosya labelini guncelle
        if len(valid_files) == 1:
            self.file_label.setText(f"Secili: {Path(valid_files[0]).name}")
        else:
            self.file_label.setText(f"Secili: {len(valid_files)} dosya")
        
        self.analyze_btn.setEnabled(True)
        self.analysis_results = None
        self.update_results_display()
        
        # Ilk dosyanin onizlemesini goster
        preview = get_file_preview(valid_files[0])
        if preview:
            self.preview_image.setPixmap(QPixmap.fromImage(
                self._pil_to_qimage(preview)
            ))
        
        self.log(f"Secili: {len(valid_files)} dosya")
    
    def update_threshold(self):
        """Update confidence threshold"""
        value = self.threshold_slider.value() / 100.0
        self.threshold_value_label.setText(f"{value:.0%}")
        if self.detector:
            self.detector.set_confidence_threshold(value)
    
    def start_analysis(self):
        """Arka planda analiz basla"""
        if not self.selected_files:
            QMessageBox.warning(self, "Dosya Yok", "Lutfen once bir dosya secin")
            return
        
        self.log(f"Analiz baslaniyou: {len(self.selected_files)} dosya")
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Her dosya icin analiz yap
        for idx, file_path in enumerate(self.selected_files):
            self.current_file = file_path
            self.log(f"Analiz: {idx+1}/{len(self.selected_files)} - {Path(file_path).name}")
            
            # Worker thread olustur ve calistigir
            analysis_worker = AnalysisWorker(
                self.detector, file_path,
                self.metadata_extractor, self.report_generator
            )
            analysis_worker.progress_update.connect(self.log)
            analysis_worker.frame_progress.connect(self.update_frame_progress)
            analysis_worker.analysis_complete.connect(self.on_analysis_complete)
            analysis_worker.error_occurred.connect(self.on_analysis_error)
            
            self.analysis_thread = analysis_worker
            self.analysis_thread.run()  # Bloke yontem (async degil)
            
            # Ilerlemeyi guncelle
            progress = int(((idx + 1) / len(self.selected_files)) * 100)
            self.progress_bar.setValue(progress)
        
        self.log(f"Tum dosyalarin analizi tamamlandi!")
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Basarili", f"{len(self.selected_files)} dosya analiz edildi!")
    
    def update_frame_progress(self, current, total, confidence):
        """Video analizi sırasında ilerlemeyi güncelle"""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
    
    def on_analysis_complete(self, results):
        """Analiz tamamlandığında işle"""
        self.analysis_results = results
        self.update_results_display()
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Analiz Tamamlandı", "Analiz başarıyla tamamlandı!")
    
    def on_analysis_error(self, error_msg):
        """Analiz hatasını işle"""
        self.log(f"✗ Hata: {error_msg}")
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Analiz Hatası", f"Analiz başarısız:\n{error_msg}")
    
    def update_results_display(self):
        """Update result labels based on latest results"""
        if not self.analysis_results:
            self.status_value.setText("N/A")
            self.conf_value.setText("N/A")
            self.capture_date_value.setText("N/A")
            self.capture_time_value.setText("N/A")
            self.gps_value.setText("N/A")
            self.time_video_value.setText("N/A")
            self.crop_btn.setEnabled(False)
            self.export_excel_btn.setEnabled(False)
            self.export_json_btn.setEnabled(False)
            return
        
        # Update display
        detected = self.analysis_results.get('detected', False)
        self.status_value.setText("✓ EVET" if detected else "✗ HAYIR")
        self.status_value.setStyleSheet(
            "color: green;" if detected else "color: red;"
        )
        
        confidence = self.analysis_results.get('confidence', 0)
        self.conf_value.setText(f"{confidence:.2%}")
        
        self.capture_date_value.setText(
            self.analysis_results.get('capture_date', 'N/A')
        )
        self.capture_time_value.setText(
            self.analysis_results.get('capture_time', 'N/A')
        )
        
        gps_lat = self.analysis_results.get('gps_latitude')
        gps_lon = self.analysis_results.get('gps_longitude')
        if gps_lat is not None and gps_lon is not None:
            self.gps_value.setText(f"({gps_lat:.6f}, {gps_lon:.6f})")
        else:
            self.gps_value.setText("Mevcut değil")
        
        time_video = self.analysis_results.get('time_in_video')
        self.time_video_value.setText(time_video if time_video else "N/A")
        
        # Enable export buttons
        self.crop_btn.setEnabled(detected and self.analysis_results.get('crop_image') is not None)
        self.export_excel_btn.setEnabled(True)
        self.export_json_btn.setEnabled(True)
    
    def view_crop(self):
        """Kırpılmış tespiti görüntüle"""
        if not self.analysis_results or self.analysis_results.get('crop_image') is None:
            QMessageBox.warning(self, "Kırpı Yok", "Tespit kırpısı mevcut değil")
            return
        
        crop_viewer = CropViewerWindow(
            self.analysis_results['crop_image'],
            self.analysis_results.get('confidence', 0),
            self
        )
        crop_viewer.exec_()
    
    def export_excel(self):
        """Analizi Excel'e aktar"""
        if not self.analysis_results:
            QMessageBox.warning(self, "Sonuç Yok", "Önce analizi çalıştırın")
            return
        
        try:
            excel_path = self.report_generator.create_excel_report(self.analysis_results)
            if excel_path:
                self.log(f"✓ Excel raporu kaydedildi")
                QMessageBox.information(self, "Başarılı", f"Rapor kaydedildi:\n{excel_path}")
            else:
                raise Exception("Excel raporu oluşturulamadı")
        except Exception as e:
            self.log(f"✗ Excel ihracat hatası: {e}")
            QMessageBox.critical(self, "İhracat Hatası", f"Excel ihracatı başarısız:\n{e}")
    
    def export_json(self):
        """Analizi JSON'a aktar"""
        if not self.analysis_results:
            QMessageBox.warning(self, "Sonuç Yok", "Önce analizi çalıştırın")
            return
        
        try:
            json_path = self.report_generator.create_json_report(self.analysis_results)
            if json_path:
                self.log(f"✓ JSON raporu kaydedildi")
                QMessageBox.information(self, "Başarılı", f"Rapor kaydedildi:\n{json_path}")
            else:
                raise Exception("JSON raporu oluşturulamadı")
        except Exception as e:
            self.log(f"✗ JSON ihracat hatası: {e}")
            QMessageBox.critical(self, "İhracat Hatası", f"JSON ihracatı başarısız:\n{e}")
    
    def log(self, message: str):
        """Gunluge mesaj ekle"""
        if not self.ui_ready or self.log_text is None:
            return
        try:
            current_text = self.log_text.toPlainText()
            timestamp = datetime.now().strftime("%H:%M:%S")
            new_message = f"[{timestamp}] {message}"
            self.log_text.setText(f"{current_text}\n{new_message}")
            scrollbar = self.log_text.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())
        except Exception:
            pass
    
    def refresh_categories_list(self):
        """Kategori listesini yenile"""
        self.categories_list.clear()
        for cat in self._get_available_categories():
            self.categories_list.addItem(cat)
    
    def create_new_category(self):
        """Yeni kategori oluştur"""
        category_name = self.new_category_input.text().strip()
        
        if not category_name:
            QMessageBox.warning(self, "Uyarı", "Kategori adı boş olmamalıdır!")
            return
        
        if not category_name.replace('_', '').replace('-', '').isalnum():
            QMessageBox.warning(self, "Uyarı", "Kategori adında sadece harf, rakam, _ ve - kullanılabilir!")
            return
        
        try:
            category_path = Path(config.PROJECT_ROOT) / 'training_data' / category_name
            
            # Subdirectorileri oluştur
            for split in ['train', 'val', 'test']:
                (category_path / 'images' / split).mkdir(parents=True, exist_ok=True)
                (category_path / 'labels' / split).mkdir(parents=True, exist_ok=True)
            
            QMessageBox.information(self, "Başarılı", f"Kategori '{category_name}' oluşturuldu!")
            self.new_category_input.clear()
            self.refresh_categories_list()
            self.upload_category_combo.addItems([category_name])
            self.content_category_combo.addItems([category_name])
            self.training_category_combo.addItems([category_name])
            logger.info(f"Kategori oluşturuldu: {category_name}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kategori oluşturma hatası: {e}")
    
    def rename_category(self):
        """Kategoriyi yeniden adlandır"""
        current = self.categories_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Uyarı", "Yeniden adlandıracak kategori seçiniz!")
            return
        
        old_name = current.text()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Kategoriyi Yeniden Adlandır")
        layout = QVBoxLayout()
        
        label = QLabel(f"Yeni kategori adı ({old_name} → ?):")
        layout.addWidget(label)
        
        input_field = QLineEdit()
        input_field.setText(old_name)
        input_field.selectAll()
        layout.addWidget(input_field)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        new_name = input_field.text().strip()
        
        if not new_name:
            QMessageBox.warning(self, "Uyarı", "Kategori adı boş olmamalıdır!")
            return
        
        if new_name == old_name:
            return
        
        try:
            old_path = Path(config.PROJECT_ROOT) / 'training_data' / old_name
            new_path = Path(config.PROJECT_ROOT) / 'training_data' / new_name
            
            old_path.rename(new_path)
            
            QMessageBox.information(self, "Başarılı", f"'{old_name}' → '{new_name}' olarak yeniden adlandırıldı!")
            self.refresh_categories_list()
            logger.info(f"Kategori yeniden adlandırıldı: {old_name} → {new_name}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Yeniden adlandırma hatası: {e}")
    
    def delete_category(self):
        """Kategoriyi sil"""
        current = self.categories_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Uyarı", "Silinecek kategori seçiniz!")
            return
        
        category_name = current.text()
        
        reply = QMessageBox.warning(self, "Dikkat!",
                                   f"'{category_name}' kategorisini silmek üzeresiniz!\n"
                                   f"Bu işlem geri alınamaz.",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        try:
            category_path = Path(config.PROJECT_ROOT) / 'training_data' / category_name
            
            import shutil
            if category_path.exists():
                shutil.rmtree(category_path)
            
            QMessageBox.information(self, "Başarılı", f"'{category_name}' kategorisi silindi!")
            self.refresh_categories_list()
            logger.info(f"Kategori silindi: {category_name}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatası: {e}")
    
    def refresh_content_display(self):
        """İçerik kontrolü sekmesi - Dosyaları listele"""
        category = self.content_category_combo.currentText()
        split = self.content_split_combo.currentText()
        
        category_path = Path(config.PROJECT_ROOT) / 'training_data' / category
        
        # Resimleri listele
        self.content_images_list.clear()
        images_dir = category_path / 'images' / split
        if images_dir.exists():
            for img_file in sorted(images_dir.glob('*')):
                self.content_images_list.addItem(img_file.name)
        
        # Labelları listele
        self.content_labels_list.clear()
        labels_dir = category_path / 'labels' / split
        if labels_dir.exists():
            for lbl_file in sorted(labels_dir.glob('*')):
                self.content_labels_list.addItem(lbl_file.name)
        
        # İstatistik güncelle
        img_count = self.content_images_list.count()
        lbl_count = self.content_labels_list.count()
        self.content_stats_label.setText(f"Resimler: {img_count} | Labellar: {lbl_count}")
    
  
        """Seçili resimleri sil"""
        category = self.content_category_combo.currentText()
        split = self.content_split_combo.currentText()
        
        selected_items = self.content_images_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Silmek için resim seçiniz!")
            return
        
        reply = QMessageBox.question(self, "Onay", 
                                    f"{len(selected_items)} resmi silmek istediğinize emin misiniz?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        try:
            deleted_count = 0
            images_dir = Path(config.PROJECT_ROOT) / 'training_data' / category / 'images' / split
            
            for item in selected_items:
                file_path = images_dir / item.text()
                if file_path.exists():
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Resim silindi: {file_path}")
            
            QMessageBox.information(self, "Başarılı", f"{deleted_count} resim silindi!")
            self.refresh_content_display()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatası: {e}")
    
  
        """Seçili labelları sil"""
        category = self.content_category_combo.currentText()
        split = self.content_split_combo.currentText()
        
        selected_items = self.content_labels_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Silmek için label seçiniz!")
            return
        
        reply = QMessageBox.question(self, "Onay",
                                    f"{len(selected_items)} label'ı silmek istediğinize emin misiniz?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        try:
            deleted_count = 0
            labels_dir = Path(config.PROJECT_ROOT) / 'training_data' / category / 'labels' / split
            
            for item in selected_items:
                file_path = labels_dir / item.text()
                if file_path.exists():
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Label silindi: {file_path}")
            
            QMessageBox.information(self, "Başarılı", f"{deleted_count} label silindi!")
            self.refresh_content_display()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatası: {e}")
    
    def delete_all_content(self):
        """Kategorideki tüm dosyaları sil"""
        category = self.content_category_combo.currentText()
        split = self.content_split_combo.currentText()
        
        img_count = self.content_images_list.count()
        lbl_count = self.content_labels_list.count()
        
        if img_count + lbl_count == 0:
            QMessageBox.warning(self, "Uyarı", "Silinecek dosya yok!")
            return
        
        reply = QMessageBox.warning(self, "Dikkat!",
                                   f"'{category}/{split}' içindeki TÜM dosyaları silmek üzeresiniz!\n"
                                   f"Resimler: {img_count}\nLabellar: {lbl_count}\n\n"
                                   f"Devam etmek istiyor musunuz?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            deleted_count = 0
            
            # Resimleri sil
            images_dir = Path(config.PROJECT_ROOT) / 'training_data' / category / 'images' / split
            if images_dir.exists():
                for img_file in images_dir.glob('*'):
                    img_file.unlink()
                    deleted_count += 1
            
            # Labelları sil
            labels_dir = Path(config.PROJECT_ROOT) / 'training_data' / category / 'labels' / split
            if labels_dir.exists():
                for lbl_file in labels_dir.glob('*'):
                    lbl_file.unlink()
                    deleted_count += 1
            
            QMessageBox.information(self, "Başarılı", f"Toplam {deleted_count} dosya silindi!")
            self.refresh_content_display()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatası: {e}")
    
    @staticmethod
    def _pil_to_qimage(pil_image):
        """Convert PIL image to QImage"""
        if pil_image.mode == 'RGB':
            h, w = pil_image.size[1], pil_image.size[0]
            str_data = pil_image.tobytes('raw', 'RGB')
            return QImage(str_data, w, h, QImage.Format_RGB888)
        else:
            return QImage(pil_image.tobytes('raw', pil_image.mode),
                         pil_image.size[0], pil_image.size[1],
                         QImage.Format_Grayscale8)

def main():
    """Uygulama giriş noktası"""
    app = QApplication(sys.argv)
    
    # Uygulama stilini ayarla
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
