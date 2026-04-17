# -*- coding: utf-8 -*-
"""
Dialog pencereleri ve popup bileşenleri
"""

import cv2

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDialogButtonBox,
    QSpinBox,
    QComboBox,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt

from src.utils import save_image


class CropViewerWindow(QDialog):
    """Kırpılmış tespit görüntüsünü gösteren dialog"""

    def __init__(self, crop_image, confidence, parent=None):
        super().__init__(parent)
        self.crop_image = crop_image
        self.confidence = confidence
        self.init_ui()

    def init_ui(self):
        """UI'yi başlat"""
        self.setWindowTitle("Tespit Kırpısı Görüntüleyici")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("""
            QLabel {
                background-color: #F8F8F8;
                border: 1px solid #DDD;
                border-radius: 6px;
                padding: 8px;
            }
        """)

        if self.crop_image is not None:
            if len(self.crop_image.shape) == 3:
                h, w, ch = self.crop_image.shape
                img_rgb = cv2.cvtColor(self.crop_image, cv2.COLOR_BGR2RGB)
                bytes_per_line = 3 * w
                qt_image = QImage(
                    img_rgb.data,
                    w,
                    h,
                    bytes_per_line,
                    QImage.Format_RGB888,
                )
            else:
                h, w = self.crop_image.shape
                bytes_per_line = w
                qt_image = QImage(
                    self.crop_image.data,
                    w,
                    h,
                    bytes_per_line,
                    QImage.Format_Grayscale8,
                )

            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaledToWidth(
                500,
                Qt.TransformationMode.SmoothTransformation,
            )
            image_label.setPixmap(scaled_pixmap)
        else:
            image_label.setText("Görüntü mevcut değil")

        layout.addWidget(image_label)

        info_label = QLabel(f"Güven: {self.confidence:.2%}")
        info_font = QFont()
        info_font.setPointSize(12)
        info_font.setBold(True)
        info_label.setFont(info_font)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        button_layout = QHBoxLayout()

        save_btn = QPushButton("Kırpıyı Kaydet")
        save_btn.clicked.connect(self.save_crop)
        button_layout.addWidget(save_btn)

        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def save_crop(self):
        """Kırpı görüntüsünü dosyaya kaydet"""
        if self.crop_image is None:
            QMessageBox.warning(self, "Uyarı", "Kaydedilecek görüntü bulunamadı")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Tespit Kırpısını Kaydet",
            "",
            "JPEG (*.jpg);;PNG (*.png);;Tüm Dosyalar (*)",
        )

        if not file_path:
            return

        if save_image(self.crop_image, file_path):
            QMessageBox.information(self, "Başarılı", f"Kırpı kaydedildi:\n{file_path}")
        else:
            QMessageBox.critical(self, "Hata", "Kırpı görüntüsü kaydedilemedi")


class VideoFrameExtractionDialog(QDialog):
    """Video frame çıkarma ayarları dialog"""

    def __init__(self, available_categories, parent=None):
        super().__init__(parent)
        self.available_categories = available_categories
        self.init_ui()

    def init_ui(self):
        """Dialog UI'sini oluştur"""
        self.setWindowTitle("Video Frame Çıkarma Ayarları")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Kategori seçimi
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Kategori:"))

        self.category_combo = QComboBox()
        self.category_combo.addItems(self.available_categories)
        category_layout.addWidget(self.category_combo)

        layout.addLayout(category_layout)

        # Frame aralığı
        frame_interval_layout = QHBoxLayout()
        frame_interval_layout.addWidget(QLabel("Frame Aralığı (her N frame):"))

        self.frame_interval_spin = QSpinBox()
        self.frame_interval_spin.setMinimum(1)
        self.frame_interval_spin.setMaximum(30)
        self.frame_interval_spin.setValue(5)
        frame_interval_layout.addWidget(self.frame_interval_spin)

        layout.addLayout(frame_interval_layout)

        # Maksimum frame sayısı
        max_frames_layout = QHBoxLayout()
        max_frames_layout.addWidget(QLabel("Maksimum Frame Sayısı:"))

        self.max_frames_spin = QSpinBox()
        self.max_frames_spin.setMinimum(0)  # 0 = sınırsız
        self.max_frames_spin.setMaximum(10000)
        self.max_frames_spin.setValue(0)
        max_frames_layout.addWidget(self.max_frames_spin)

        layout.addLayout(max_frames_layout)

        # Dataset split seçimi
        split_layout = QHBoxLayout()
        split_layout.addWidget(QLabel("Dataset Split:"))

        self.split_combo = QComboBox()
        self.split_combo.addItems(["train", "val", "test"])
        self.split_combo.setCurrentIndex(0)
        split_layout.addWidget(self.split_combo)

        layout.addLayout(split_layout)

        info_label = QLabel(
            "Çıkartılan frameler seçtiğiniz kategori ve split altına kaydedilir.\n"
            "Label dosyalarını daha sonra harici annotation aracıyla hazırlayabilirsiniz."
        )
        info_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(info_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_values(self):
        """Dialog'dan değerleri al"""
        return {
            "category": self.category_combo.currentText(),
            "frame_interval": self.frame_interval_spin.value(),
            "max_frames": self.max_frames_spin.value() if self.max_frames_spin.value() > 0 else None,
            "dataset_split": self.split_combo.currentText(),
        }