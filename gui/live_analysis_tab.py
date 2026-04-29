# -*- coding: utf-8 -*-
"""
Canli video takip sekmesi
"""

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFrame,
    QSlider,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


def create_live_analysis_ui(main_layout, parent_window):
    """Canli video takip sekmesi UI'sini olustur"""
    main_layout.setContentsMargins(15, 15, 15, 15)
    main_layout.setSpacing(12)

    title = QLabel("Canli Video Takip")
    title_font = QFont()
    title_font.setPointSize(12)
    title_font.setBold(True)
    title.setFont(title_font)
    main_layout.addWidget(title)

    # ---------------------------------------------------------
    # UST KONTROL ALANI
    # ---------------------------------------------------------
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

    parent_window.live_select_video_btn = QPushButton("Video Sec")
    parent_window.live_select_video_btn.setMinimumHeight(42)
    parent_window.live_select_video_btn.clicked.connect(parent_window.select_live_video)
    control_layout.addWidget(parent_window.live_select_video_btn)

    parent_window.live_play_btn = QPushButton("Oynat / Devam Et")
    parent_window.live_play_btn.setMinimumHeight(42)
    parent_window.live_play_btn.setEnabled(False)
    parent_window.live_play_btn.clicked.connect(parent_window.start_live_video_tracking)
    control_layout.addWidget(parent_window.live_play_btn)

    parent_window.live_pause_btn = QPushButton("Duraklat")
    parent_window.live_pause_btn.setMinimumHeight(42)
    parent_window.live_pause_btn.setEnabled(False)
    parent_window.live_pause_btn.clicked.connect(parent_window.pause_live_video_tracking)
    control_layout.addWidget(parent_window.live_pause_btn)

    parent_window.live_stop_btn = QPushButton("Durdur")
    parent_window.live_stop_btn.setMinimumHeight(42)
    parent_window.live_stop_btn.setEnabled(False)
    parent_window.live_stop_btn.clicked.connect(parent_window.stop_live_video_tracking)
    control_layout.addWidget(parent_window.live_stop_btn)

    # Geriye donuk uyumluluk
    parent_window.live_start_btn = parent_window.live_play_btn

    control_layout.addStretch()

    parent_window.live_video_file_label = QLabel("Video secilmedi")
    parent_window.live_video_file_label.setStyleSheet("""
        QLabel {
            color: #2C3E50;
            font-weight: 500;
        }
    """)
    control_layout.addWidget(parent_window.live_video_file_label)

    control_frame.setLayout(control_layout)
    main_layout.addWidget(control_frame)

    # ---------------------------------------------------------
    # VIDEO GORUNTU ALANI
    # ---------------------------------------------------------
    video_frame = QFrame()
    video_frame.setStyleSheet("""
        QFrame {
            border: 2px solid #2C3E50;
            border-radius: 8px;
            background-color: #111111;
        }
    """)

    video_layout = QVBoxLayout()
    video_layout.setContentsMargins(10, 10, 10, 10)
    video_layout.setSpacing(10)

    parent_window.live_video_label = QLabel("Canli analiz goruntusu burada gosterilecek")
    parent_window.live_video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    parent_window.live_video_label.setMinimumHeight(420)
    parent_window.live_video_label.setStyleSheet("""
        QLabel {
            color: #DDDDDD;
            background-color: #111111;
            border-radius: 4px;
            font-size: 12px;
        }
    """)
    video_layout.addWidget(parent_window.live_video_label, 1)

    # ---------------------------------------------------------
    # VIDEO PLAYER ZAMAN CUBUGU
    # ---------------------------------------------------------
    timeline_frame = QFrame()
    timeline_frame.setStyleSheet("""
        QFrame {
            border: 1px solid #2C3E50;
            border-radius: 6px;
            background-color: #1C1C1C;
        }
    """)

    timeline_layout = QHBoxLayout()
    timeline_layout.setContentsMargins(10, 8, 10, 8)
    timeline_layout.setSpacing(10)

    parent_window.live_current_time_label = QLabel("00:00")
    parent_window.live_current_time_label.setMinimumWidth(55)
    parent_window.live_current_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    parent_window.live_current_time_label.setStyleSheet("""
        QLabel {
            color: #ECF0F1;
            font-weight: bold;
            background: transparent;
        }
    """)
    timeline_layout.addWidget(parent_window.live_current_time_label)

    parent_window.live_timeline_slider = QSlider(Qt.Orientation.Horizontal)
    parent_window.live_timeline_slider.setRange(0, 0)
    parent_window.live_timeline_slider.setValue(0)
    parent_window.live_timeline_slider.setEnabled(True)
    parent_window.live_timeline_slider.sliderPressed.connect(parent_window.on_live_slider_pressed)
    parent_window.live_timeline_slider.sliderMoved.connect(parent_window.on_live_slider_moved)
    parent_window.live_timeline_slider.sliderReleased.connect(parent_window.on_live_slider_released)
    parent_window.live_timeline_slider.setStyleSheet("""
        QSlider::groove:horizontal {
            border: 1px solid #566573;
            height: 8px;
            background: #2C3E50;
            border-radius: 4px;
        }
        QSlider::sub-page:horizontal {
            background: #3498DB;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #ECF0F1;
            border: 1px solid #BDC3C7;
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
    """)
    timeline_layout.addWidget(parent_window.live_timeline_slider, 1)

    parent_window.live_total_time_label = QLabel("00:00")
    parent_window.live_total_time_label.setMinimumWidth(55)
    parent_window.live_total_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    parent_window.live_total_time_label.setStyleSheet("""
        QLabel {
            color: #ECF0F1;
            font-weight: bold;
            background: transparent;
        }
    """)
    timeline_layout.addWidget(parent_window.live_total_time_label)

    timeline_frame.setLayout(timeline_layout)
    video_layout.addWidget(timeline_frame)

    video_frame.setLayout(video_layout)
    main_layout.addWidget(video_frame, 1)

    # ---------------------------------------------------------
    # ALT BILGI ALANI
    # ---------------------------------------------------------
    bottom_layout = QHBoxLayout()
    bottom_layout.setSpacing(12)

    info_frame = QFrame()
    info_frame.setStyleSheet("""
        QFrame {
            border: 1px solid #D5D8DC;
            border-radius: 8px;
            background-color: #F8F9F9;
        }
    """)

    info_layout = QVBoxLayout()
    info_layout.setContentsMargins(10, 10, 10, 10)
    info_layout.setSpacing(6)

    info_title = QLabel("Canli Durum")
    info_title.setStyleSheet("font-weight: bold;")
    info_layout.addWidget(info_title)

    parent_window.live_status_label = QLabel("Hazir")
    info_layout.addWidget(parent_window.live_status_label)

    parent_window.live_stats_label = QLabel("Frame: 0 | Tespit: 0 | FPS: 0.00")
    info_layout.addWidget(parent_window.live_stats_label)

    parent_window.live_last_detection_label = QLabel("Son tespit: Yok")
    info_layout.addWidget(parent_window.live_last_detection_label)

    info_frame.setLayout(info_layout)
    bottom_layout.addWidget(info_frame, 1)

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

    log_title = QLabel("Canli Log")
    log_title.setStyleSheet("font-weight: bold;")
    log_layout.addWidget(log_title)

    parent_window.live_log_text = QTextEdit()
    parent_window.live_log_text.setReadOnly(True)
    parent_window.live_log_text.setMaximumHeight(130)
    parent_window.live_log_text.setStyleSheet("""
        QTextEdit {
            font-family: Consolas, monospace;
            font-size: 9px;
            background-color: #F8F9F9;
            border: 1px solid #D5D8DC;
            border-radius: 4px;
        }
    """)
    log_layout.addWidget(parent_window.live_log_text)

    log_frame.setLayout(log_layout)
    bottom_layout.addWidget(log_frame, 1)

    main_layout.addLayout(bottom_layout)