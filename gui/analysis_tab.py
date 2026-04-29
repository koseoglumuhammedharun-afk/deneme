# -*- coding: utf-8 -*-
"""
Analiz sekmesi
"""

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFrame,
    QSlider,
    QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import config


def _create_value_label(default_text="N/A"):
    """Sonuc deger label'i olustur"""
    label = QLabel(default_text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    label.setStyleSheet("""
        QLabel {
            color: #2C3E50;
            font-weight: 600;
            background-color: #FFFFFF;
            border: 1px solid #D5D8DC;
            border-radius: 6px;
            padding: 6px 8px;
        }
    """)
    return label


def _create_field_title(text):
    """Alan basligi olustur"""
    label = QLabel(text)
    label.setStyleSheet("""
        QLabel {
            color: #34495E;
            font-weight: bold;
            padding-top: 2px;
            padding-bottom: 2px;
        }
    """)
    return label


def create_analysis_ui(main_layout, parent_window):
    """Analiz sekmesi UI'sini olustur"""
    main_layout.setContentsMargins(15, 15, 15, 15)
    main_layout.setSpacing(12)

    # Baslik
    title = QLabel("Dosya Analizi")
    title_font = QFont()
    title_font.setPointSize(12)
    title_font.setBold(True)
    title.setFont(title_font)
    main_layout.addWidget(title)

    # Ust kontrol alani
    control_frame = QFrame()
    control_frame.setStyleSheet("""
        QFrame {
            border: 2px solid #3498DB;
            border-radius: 8px;
            background-color: #EBF5FB;
        }
    """)

    control_layout = QHBoxLayout()
    control_layout.setContentsMargins(12, 12, 12, 12)
    control_layout.setSpacing(10)

    parent_window.browse_btn = QPushButton("Dosya Sec")
    parent_window.browse_btn.setMinimumHeight(42)
    parent_window.browse_btn.clicked.connect(parent_window.browse_file)
    control_layout.addWidget(parent_window.browse_btn)

    parent_window.analyze_btn = QPushButton("Analizi Baslat")
    parent_window.analyze_btn.setMinimumHeight(42)
    parent_window.analyze_btn.setEnabled(False)
    parent_window.analyze_btn.clicked.connect(parent_window.start_analysis)
    control_layout.addWidget(parent_window.analyze_btn)

    control_layout.addStretch()

    parent_window.file_label = QLabel("Dosya secilmedi")
    parent_window.file_label.setStyleSheet("""
        QLabel {
            color: #2C3E50;
            font-weight: 500;
        }
    """)
    control_layout.addWidget(parent_window.file_label)

    control_frame.setLayout(control_layout)
    main_layout.addWidget(control_frame)

    # Orta alan
    content_layout = QHBoxLayout()
    content_layout.setSpacing(12)

    # Sol panel: onizleme + ayarlar
    left_panel = QVBoxLayout()
    left_panel.setSpacing(12)

    preview_frame = QFrame()
    preview_frame.setStyleSheet("""
        QFrame {
            border: 1px solid #D5D8DC;
            border-radius: 8px;
            background-color: #FFFFFF;
        }
    """)

    preview_layout = QVBoxLayout()
    preview_layout.setContentsMargins(10, 10, 10, 10)
    preview_layout.setSpacing(8)

    preview_title = QLabel("Dosya Onizleme")
    preview_title.setStyleSheet("font-weight: bold;")
    preview_layout.addWidget(preview_title)

    parent_window.preview_image = QLabel("Onizleme burada gosterilecek")
    parent_window.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
    parent_window.preview_image.setMinimumSize(320, 320)
    parent_window.preview_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    parent_window.preview_image.setStyleSheet("""
        QLabel {
            color: #7F8C8D;
            background-color: #F8F9F9;
            border: 1px dashed #BDC3C7;
            border-radius: 6px;
            padding: 10px;
        }
    """)
    preview_layout.addWidget(parent_window.preview_image, 1)

    preview_frame.setLayout(preview_layout)
    left_panel.addWidget(preview_frame, 1)

    threshold_frame = QFrame()
    threshold_frame.setStyleSheet("""
        QFrame {
            border: 1px solid #D5D8DC;
            border-radius: 8px;
            background-color: #FFFFFF;
        }
    """)

    threshold_layout = QVBoxLayout()
    threshold_layout.setContentsMargins(10, 10, 10, 10)
    threshold_layout.setSpacing(8)

    threshold_title = QLabel("Guven Esigi")
    threshold_title.setStyleSheet("font-weight: bold;")
    threshold_layout.addWidget(threshold_title)

    threshold_row = QHBoxLayout()
    threshold_row.setSpacing(10)

    parent_window.threshold_slider = QSlider(Qt.Orientation.Horizontal)
    parent_window.threshold_slider.setRange(
        0,
        int(config.DEFAULT_CONFIDENCE_MAX * 100),
    )
    parent_window.threshold_slider.setValue(int(config.CONFIDENCE_THRESHOLD * 100))
    parent_window.threshold_slider.setSingleStep(1)
    parent_window.threshold_slider.setStyleSheet("""
        QSlider::groove:horizontal {
            border: 1px solid #BFC9CA;
            height: 8px;
            background: #EAECEE;
            border-radius: 4px;
        }
        QSlider::sub-page:horizontal {
            background: #3498DB;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #FFFFFF;
            border: 1px solid #AEB6BF;
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
    """)
    threshold_row.addWidget(parent_window.threshold_slider, 1)

    parent_window.threshold_value_label = QLabel(f"{config.CONFIDENCE_THRESHOLD:.0%}")
    parent_window.threshold_value_label.setMinimumWidth(55)
    parent_window.threshold_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    parent_window.threshold_value_label.setStyleSheet("""
        QLabel {
            color: #1F618D;
            font-weight: bold;
            background-color: #EBF5FB;
            border: 1px solid #AED6F1;
            border-radius: 6px;
            padding: 4px 6px;
        }
    """)
    threshold_row.addWidget(parent_window.threshold_value_label)

    threshold_layout.addLayout(threshold_row)

    threshold_hint = QLabel("%0 = test modu; modelin urettigi neredeyse tum dusuk guvenli parcalar gosterilir.")
    threshold_hint.setStyleSheet("color: #566573; font-size: 11px;")
    threshold_layout.addWidget(threshold_hint)

    threshold_frame.setLayout(threshold_layout)
    left_panel.addWidget(threshold_frame)

    content_layout.addLayout(left_panel, 1)

    # Sag panel: sonuclar
    result_frame = QFrame()
    result_frame.setStyleSheet("""
        QFrame {
            border: 1px solid #D5D8DC;
            border-radius: 8px;
            background-color: #FFFFFF;
        }
    """)

    result_layout = QVBoxLayout()
    result_layout.setContentsMargins(12, 12, 12, 12)
    result_layout.setSpacing(10)

    result_title = QLabel("Analiz Sonuclari")
    result_title.setStyleSheet("font-weight: bold;")
    result_layout.addWidget(result_title)

    grid = QGridLayout()
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(8)

    grid.addWidget(_create_field_title("Tespit Edildi"), 0, 0)
    parent_window.status_value = _create_value_label()
    grid.addWidget(parent_window.status_value, 0, 1)

    grid.addWidget(_create_field_title("Guven Orani"), 1, 0)
    parent_window.conf_value = _create_value_label()
    grid.addWidget(parent_window.conf_value, 1, 1)

    grid.addWidget(_create_field_title("Cekim Tarihi"), 2, 0)
    parent_window.capture_date_value = _create_value_label()
    grid.addWidget(parent_window.capture_date_value, 2, 1)

    grid.addWidget(_create_field_title("Cekim Saati"), 3, 0)
    parent_window.capture_time_value = _create_value_label()
    grid.addWidget(parent_window.capture_time_value, 3, 1)

    grid.addWidget(_create_field_title("GPS"), 4, 0)
    parent_window.gps_value = _create_value_label()
    grid.addWidget(parent_window.gps_value, 4, 1)

    grid.addWidget(_create_field_title("Video Ici Zaman"), 5, 0)
    parent_window.time_video_value = _create_value_label()
    grid.addWidget(parent_window.time_video_value, 5, 1)

    grid.addWidget(_create_field_title("Silah Sinifi"), 6, 0)
    parent_window.weapon_value = _create_value_label()
    grid.addWidget(parent_window.weapon_value, 6, 1)

    grid.setColumnStretch(0, 0)
    grid.setColumnStretch(1, 1)

    result_layout.addLayout(grid)

    action_row = QHBoxLayout()
    action_row.setSpacing(10)

    parent_window.crop_btn = QPushButton("Kirpintilari Goster")
    parent_window.crop_btn.setMinimumHeight(40)
    parent_window.crop_btn.setEnabled(False)
    parent_window.crop_btn.clicked.connect(parent_window.view_crop)
    action_row.addWidget(parent_window.crop_btn)

    parent_window.export_excel_btn = QPushButton("Excel'e Aktar")
    parent_window.export_excel_btn.setMinimumHeight(40)
    parent_window.export_excel_btn.setEnabled(False)
    parent_window.export_excel_btn.clicked.connect(parent_window.export_excel)
    action_row.addWidget(parent_window.export_excel_btn)

    parent_window.export_json_btn = QPushButton("JSON'a Aktar")
    parent_window.export_json_btn.setMinimumHeight(40)
    parent_window.export_json_btn.setEnabled(False)
    parent_window.export_json_btn.clicked.connect(parent_window.export_json)
    action_row.addWidget(parent_window.export_json_btn)

    result_layout.addStretch()
    result_layout.addLayout(action_row)

    result_frame.setLayout(result_layout)
    content_layout.addWidget(result_frame, 1)

    main_layout.addLayout(content_layout, 1)

    # Alt log alani
    log_frame = QFrame()
    log_frame.setStyleSheet("""
        QFrame {
            border: 1px solid #D5D8DC;
            border-radius: 8px;
            background-color: #FFFFFF;
        }
    """)

    log_layout = QVBoxLayout()
    log_layout.setContentsMargins(10, 10, 10, 10)
    log_layout.setSpacing(6)

    log_title = QLabel("Analiz Logu")
    log_title.setStyleSheet("font-weight: bold;")
    log_layout.addWidget(log_title)

    parent_window.log_text = QTextEdit()
    parent_window.log_text.setReadOnly(True)
    parent_window.log_text.setMinimumHeight(140)
    parent_window.log_text.setStyleSheet("""
        QTextEdit {
            font-family: Consolas, monospace;
            font-size: 9px;
            background-color: #F8F9F9;
            border: 1px solid #D5D8DC;
            border-radius: 4px;
        }
    """)
    log_layout.addWidget(parent_window.log_text)

    log_frame.setLayout(log_layout)
    main_layout.addWidget(log_frame)

    parent_window.threshold_slider.valueChanged.connect(parent_window.update_threshold)
    parent_window.update_threshold()