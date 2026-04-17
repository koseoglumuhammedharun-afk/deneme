# -*- coding: utf-8 -*-
"""
Model eğitimi sekmesi UI bileşenleri ve fonksiyonlar
"""

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QProgressBar,
    QListWidget,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QTabWidget,
    QWidget,
)
from PyQt5.QtGui import QFont


def create_training_ui(main_layout, parent_window):
    """Model eğitimi sekmesi UI'sini oluştur - Tab yapısı"""
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

    # Alt sekmeler
    training_tabs = QTabWidget()

    # TAB 1: İçerik Yükleme
    upload_tab = QWidget()
    upload_layout = QVBoxLayout()
    _init_training_upload_tab(upload_layout, parent_window)
    upload_tab.setLayout(upload_layout)
    training_tabs.addTab(upload_tab, "📥 İçerik Yükleme")

    # TAB 2: Kategori Yönetimi
    category_tab = QWidget()
    category_layout = QVBoxLayout()
    _init_category_management_tab(category_layout, parent_window)
    category_tab.setLayout(category_layout)
    training_tabs.addTab(category_tab, "🗂️ Kategori Yönetimi")

    # TAB 3: İçerik Kontrolü
    control_tab = QWidget()
    control_layout = QVBoxLayout()
    _init_content_control_tab(control_layout, parent_window)
    control_tab.setLayout(control_layout)
    training_tabs.addTab(control_tab, "📊 İçerik Kontrolü")

    # TAB 4: Eğitim Ayarları
    settings_tab = QWidget()
    settings_layout = QVBoxLayout()
    _init_training_settings_tab(settings_layout, parent_window)
    settings_tab.setLayout(settings_layout)
    training_tabs.addTab(settings_tab, "⚙️ Eğitim Ayarları")

    main_layout.addWidget(training_tabs)

    # İlk açılışta verileri senkronize et
    try:
        parent_window.refresh_categories_list()
        parent_window.refresh_upload_categories()
        parent_window.refresh_training_categories()
        parent_window.refresh_content_categories()
        parent_window.refresh_content_display()
    except Exception:
        pass


def _init_training_upload_tab(layout, parent_window):
    """TAB 1: İçerik Yükleme"""
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(12)

    # Kategori ve bölüm seçimi
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

    parent_window.upload_category_combo = QComboBox()
    parent_window.upload_category_combo.addItems(parent_window._get_available_categories())
    parent_window.upload_category_combo.setMinimumWidth(150)
    choice_layout.addWidget(parent_window.upload_category_combo)

    choice_layout.addWidget(QLabel("Bölüm:"))
    parent_window.upload_split_combo = QComboBox()
    parent_window.upload_split_combo.addItems(["train", "val", "test"])
    parent_window.upload_split_combo.setCurrentIndex(0)
    parent_window.upload_split_combo.setMinimumWidth(100)
    choice_layout.addWidget(parent_window.upload_split_combo)

    upload_refresh_btn = QPushButton("🔄 Kategorileri Yenile")
    upload_refresh_btn.setMinimumHeight(35)
    upload_refresh_btn.setStyleSheet("""
        QPushButton {
            background-color: #3498DB;
            color: white;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            font-size: 9px;
        }
        QPushButton:hover {
            background-color: #2980B9;
        }
    """)
    upload_refresh_btn.clicked.connect(parent_window.refresh_upload_categories)
    choice_layout.addWidget(upload_refresh_btn)

    choice_layout.addStretch()
    select_layout.addLayout(choice_layout)
    select_frame.setLayout(select_layout)
    layout.addWidget(select_frame)

    # Yükleme bölümü
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
    images_btn.clicked.connect(parent_window.browse_training_images)
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
    labels_btn.clicked.connect(parent_window.browse_training_labels)
    btn_row1.addWidget(labels_btn)

    upload_btn_layout.addLayout(btn_row1)

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
    video_btn.clicked.connect(parent_window.extract_video_frames)
    btn_row2.addWidget(video_btn)
    btn_row2.addStretch()

    upload_btn_layout.addLayout(btn_row2)

    upload_btn_layout.addWidget(QLabel("📝 Yükleme Geçmişi:"))
    parent_window.upload_history_list = QListWidget()
    parent_window.upload_history_list.setMaximumHeight(150)
    parent_window.upload_history_list.setStyleSheet("""
        QListWidget {
            border: 1px solid #DDD;
            border-radius: 3px;
            background-color: white;
            font-size: 9px;
        }
    """)
    upload_btn_layout.addWidget(parent_window.upload_history_list)

    upload_frame.setLayout(upload_btn_layout)
    layout.addWidget(upload_frame)
    layout.addStretch()


def _init_category_management_tab(layout, parent_window):
    """TAB 2: Kategori Yönetimi - CRUD işlemleri"""
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(12)

    header = QLabel("🗂️ Kategori Yönetim Araçları")
    header_font = QFont()
    header_font.setPointSize(11)
    header_font.setBold(True)
    header.setFont(header_font)
    layout.addWidget(header)

    # Kategori listesi
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
    parent_window.categories_list = QListWidget()
    parent_window.categories_list.setSelectionMode(QListWidget.SingleSelection)
    parent_window.categories_list.setMaximumHeight(150)
    parent_window.categories_list.setStyleSheet("""
        QListWidget {
            border: 1px solid #DDD;
            border-radius: 3px;
            background-color: white;
        }
    """)
    parent_window.refresh_categories_list()
    list_layout.addWidget(parent_window.categories_list)

    list_frame.setLayout(list_layout)
    layout.addWidget(list_frame)

    # İstatistik alanı
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
    parent_window.category_stats_text = QTextEdit()
    parent_window.category_stats_text.setReadOnly(True)
    parent_window.category_stats_text.setMaximumHeight(120)
    parent_window.category_stats_text.setStyleSheet("""
        QTextEdit {
            background-color: white;
            border: 1px solid #DDD;
            border-radius: 3px;
            font-size: 9px;
            font-family: 'Courier New', monospace;
        }
    """)
    stats_layout.addWidget(parent_window.category_stats_text)

    stats_frame.setLayout(stats_layout)
    layout.addWidget(stats_frame)

    # İşlem alanı
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

    new_cat_layout = QHBoxLayout()
    new_cat_layout.addWidget(QLabel("Yeni Kategori Adı:"))

    parent_window.new_category_input = QLineEdit()
    parent_window.new_category_input.setPlaceholderText("örn: nora_b52, zuzana, obus")
    parent_window.new_category_input.setMinimumWidth(220)
    new_cat_layout.addWidget(parent_window.new_category_input)

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
    add_cat_btn.clicked.connect(parent_window.create_new_category)
    new_cat_layout.addWidget(add_cat_btn)
    new_cat_layout.addStretch()
    ops_layout.addLayout(new_cat_layout)

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
    rename_cat_btn.clicked.connect(parent_window.rename_category)
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
    delete_cat_btn.clicked.connect(parent_window.delete_category)
    delete_cat_layout.addWidget(delete_cat_btn)

    delete_cat_layout.addStretch()
    ops_layout.addLayout(delete_cat_layout)

    ops_frame.setLayout(ops_layout)
    layout.addWidget(ops_frame)
    layout.addStretch()


def _init_content_control_tab(layout, parent_window):
    """TAB 3: İçerik Kontrolü - Görüntüleme, Silme, Değiştirme"""
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(12)

    header = QLabel("📊 Kategori İçeriğini Yönet")
    header_font = QFont()
    header_font.setPointSize(11)
    header_font.setBold(True)
    header.setFont(header_font)
    layout.addWidget(header)

    # Kategori ve bölüm seçimi
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
    parent_window.content_category_combo = QComboBox()
    parent_window.content_category_combo.addItems(parent_window._get_available_categories())
    parent_window.content_category_combo.currentTextChanged.connect(parent_window.refresh_content_display)
    select_layout.addWidget(parent_window.content_category_combo)

    select_layout.addWidget(QLabel("Bölüm:"))
    parent_window.content_split_combo = QComboBox()
    parent_window.content_split_combo.addItems(["train", "val", "test"])
    parent_window.content_split_combo.currentTextChanged.connect(parent_window.refresh_content_display)
    select_layout.addWidget(parent_window.content_split_combo)

    refresh_btn = QPushButton("🔄 Yenile")
    refresh_btn.setMinimumHeight(35)
    refresh_btn.clicked.connect(parent_window.refresh_content_display)
    select_layout.addWidget(refresh_btn)

    category_refresh_btn = QPushButton("📂 Kategorileri Yenile")
    category_refresh_btn.setMinimumHeight(35)
    category_refresh_btn.clicked.connect(parent_window.refresh_content_categories)
    select_layout.addWidget(category_refresh_btn)

    select_layout.addStretch()

    select_frame.setLayout(select_layout)
    layout.addWidget(select_frame)

    # Dosya listeleri
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

    img_section = QVBoxLayout()
    img_section.addWidget(QLabel("📷 Resimler:"))
    parent_window.content_images_list = QListWidget()
    parent_window.content_images_list.setSelectionMode(QListWidget.MultiSelection)
    parent_window.content_images_list.setStyleSheet("""
        QListWidget {
            border: 1px solid #DDD;
            border-radius: 3px;
            background-color: white;
            font-size: 9px;
        }
    """)
    img_section.addWidget(parent_window.content_images_list)
    files_layout.addLayout(img_section)

    lbl_section = QVBoxLayout()
    lbl_section.addWidget(QLabel("🏷️ Labellar:"))
    parent_window.content_labels_list = QListWidget()
    parent_window.content_labels_list.setSelectionMode(QListWidget.MultiSelection)
    parent_window.content_labels_list.setStyleSheet("""
        QListWidget {
            border: 1px solid #DDD;
            border-radius: 3px;
            background-color: white;
            font-size: 9px;
        }
    """)
    lbl_section.addWidget(parent_window.content_labels_list)
    files_layout.addLayout(lbl_section)

    files_frame.setLayout(files_layout)
    layout.addWidget(files_frame, 1)

    # İşlemler
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

    parent_window.content_stats_label = QLabel("Resimler: 0 | Labellar: 0")
    parent_window.content_stats_label.setStyleSheet("color: #333; font-weight: bold; font-size: 10px;")
    ops_layout.addWidget(parent_window.content_stats_label)

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
    del_img_btn.clicked.connect(parent_window.delete_selected_images)
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
    del_lbl_btn.clicked.connect(parent_window.delete_selected_labels)
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
    del_all_btn.clicked.connect(parent_window.delete_all_content)
    ops_btn_layout.addWidget(del_all_btn)

    ops_btn_layout.addStretch()
    ops_layout.addLayout(ops_btn_layout)

    ops_frame.setLayout(ops_layout)
    layout.addWidget(ops_frame)


def _init_training_settings_tab(layout, parent_window):
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

    cat_layout = QHBoxLayout()
    cat_layout.addWidget(QLabel("Eğitim Kategorisi:"))

    parent_window.training_category_combo = QComboBox()
    parent_window.training_category_combo.addItems(parent_window._get_available_categories())
    parent_window.training_category_combo.setMinimumWidth(150)
    cat_layout.addWidget(parent_window.training_category_combo)

    train_refresh_btn = QPushButton("🔄 Yenile")
    train_refresh_btn.setMinimumHeight(35)
    train_refresh_btn.setMaximumWidth(100)
    train_refresh_btn.setStyleSheet("""
        QPushButton {
            background-color: #3498DB;
            color: white;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            font-size: 9px;
        }
        QPushButton:hover {
            background-color: #2980B9;
        }
    """)
    train_refresh_btn.clicked.connect(parent_window.refresh_training_categories)
    cat_layout.addWidget(train_refresh_btn)

    cat_layout.addStretch()
    params_layout.addLayout(cat_layout)

    epoch_layout = QHBoxLayout()
    epoch_layout.addWidget(QLabel("Epoch Sayısı:"))
    parent_window.epoch_spinbox = QSpinBox()
    parent_window.epoch_spinbox.setMinimum(1)
    parent_window.epoch_spinbox.setMaximum(500)
    parent_window.epoch_spinbox.setValue(50)
    parent_window.epoch_spinbox.setMinimumWidth(100)
    epoch_layout.addWidget(parent_window.epoch_spinbox)
    epoch_layout.addStretch()
    params_layout.addLayout(epoch_layout)

    batch_layout = QHBoxLayout()
    batch_layout.addWidget(QLabel("Batch Boyutu:"))
    parent_window.batch_spinbox = QSpinBox()
    parent_window.batch_spinbox.setMinimum(1)
    parent_window.batch_spinbox.setMaximum(128)
    parent_window.batch_spinbox.setValue(16)
    parent_window.batch_spinbox.setMinimumWidth(100)
    batch_layout.addWidget(parent_window.batch_spinbox)
    batch_layout.addStretch()
    params_layout.addLayout(batch_layout)

    imgsz_layout = QHBoxLayout()
    imgsz_layout.addWidget(QLabel("Resim Boyutu:"))
    parent_window.imgsz_spinbox = QSpinBox()
    parent_window.imgsz_spinbox.setMinimum(320)
    parent_window.imgsz_spinbox.setMaximum(1280)
    parent_window.imgsz_spinbox.setValue(640)
    parent_window.imgsz_spinbox.setSingleStep(64)
    parent_window.imgsz_spinbox.setMinimumWidth(100)
    imgsz_layout.addWidget(parent_window.imgsz_spinbox)
    imgsz_layout.addStretch()
    params_layout.addLayout(imgsz_layout)

    params_frame.setLayout(params_layout)
    layout.addWidget(params_frame)

    # İlerleme ve günlük
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

    parent_window.training_progress = QProgressBar()
    parent_window.training_progress.setVisible(False)
    parent_window.training_progress.setMinimumHeight(25)
    parent_window.training_progress.setStyleSheet("""
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
    progress_layout.addWidget(parent_window.training_progress)

    progress_layout.addWidget(QLabel("📝 Eğitim Günlüğü:"))
    parent_window.training_log = QTextEdit()
    parent_window.training_log.setReadOnly(True)
    parent_window.training_log.setMaximumHeight(120)
    parent_window.training_log.setStyleSheet("""
        QTextEdit {
            background-color: #F5F5F5;
            border: 1px solid #DDD;
            border-radius: 3px;
            font-size: 8px;
            font-family: 'Courier New', monospace;
        }
    """)
    progress_layout.addWidget(parent_window.training_log)

    progress_frame.setLayout(progress_layout)
    layout.addWidget(progress_frame)

    parent_window.train_btn = QPushButton("🚀 EĞİTİMİ BAŞLAT")
    parent_window.train_btn.setMinimumHeight(60)
    parent_window.train_btn.setFont(QFont("Arial", 12, QFont.Bold))
    parent_window.train_btn.setStyleSheet("""
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
    parent_window.train_btn.clicked.connect(parent_window.start_training)
    layout.addWidget(parent_window.train_btn)