# -*- coding: utf-8 -*-
"""
Model eğitimi sekmesi UI bileşenleri ve fonksiyonlar.

Bu sayfa iki eğitim mantığını destekleyecek şekilde hazırlanmıştır:

1. Kategori Bazlı Eğitim
   - Sadece seçili kategoriyi eğitir.
   - Test amaçlı kullanılabilir.

2. Birleşik Final Model Eğitimi
   - nora_b52, zuzana, obus gibi kategori klasörlerindeki verileri tek dataset altında toplar.
   - training_data/weapon_dataset oluşturur.
   - Tek final model üretir.
   - models/howitzer_detector.pt olarak kaydedilecek yapıya hizmet eder.

Not:
Bu dosyadaki yeni butonların asıl işlevleri main.py içinde eklenecek.
main.py güncellenmeden bu butonlar uyarı verir ama uygulamayı çökertmez.
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
    QMessageBox,
    QAbstractItemView,
)
from PyQt5.QtGui import QFont


# =========================================================
# GENEL YARDIMCI FONKSİYONLAR
# =========================================================

def _title_label(text: str, size: int = 14) -> QLabel:
    label = QLabel(text)
    font = QFont()
    font.setPointSize(size)
    font.setBold(True)
    label.setFont(font)
    label.setStyleSheet("color: #1f2937; margin-bottom: 5px;")
    return label


def _section_title(text: str, size: int = 11) -> QLabel:
    label = QLabel(text)
    font = QFont()
    font.setPointSize(size)
    font.setBold(True)
    label.setFont(font)
    label.setStyleSheet("color: #111827;")
    return label


def _frame_style(border_color: str, bg_color: str) -> str:
    return f"""
        QFrame {{
            border: 1px solid {border_color};
            border-radius: 10px;
            background-color: {bg_color};
        }}
    """


def _button_style(bg_color: str, hover_color: str, font_size: int = 10) -> str:
    return f"""
        QPushButton {{
            background-color: {bg_color};
            color: white;
            border: none;
            border-radius: 7px;
            font-weight: bold;
            font-size: {font_size}px;
            padding: 8px 12px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
        QPushButton:disabled {{
            background-color: #BDC3C7;
            color: #7F8C8D;
        }}
    """


def _soft_button_style(bg_color: str, hover_color: str, text_color: str = "#111827") -> str:
    return f"""
        QPushButton {{
            background-color: {bg_color};
            color: {text_color};
            border: 1px solid #CBD5E1;
            border-radius: 7px;
            font-weight: bold;
            font-size: 9px;
            padding: 7px 10px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
        QPushButton:disabled {{
            background-color: #E5E7EB;
            color: #9CA3AF;
        }}
    """


def _list_style() -> str:
    return """
        QListWidget {
            border: 1px solid #CBD5E1;
            border-radius: 6px;
            background-color: white;
            font-size: 9px;
            padding: 4px;
        }
    """


def _textedit_style() -> str:
    return """
        QTextEdit {
            background-color: #F8FAFC;
            border: 1px solid #CBD5E1;
            border-radius: 6px;
            font-size: 9px;
            font-family: 'Consolas', 'Courier New', monospace;
            padding: 6px;
        }
    """


def _safe_connect(button: QPushButton, parent_window, method_name: str, friendly_name: str):
    """
    Yeni main.py fonksiyonları henüz eklenmediyse uygulama çökmesin diye güvenli bağlantı.

    Pylance'ın PyQt slot tipi uyarısı vermemesi için callable metod direkt connect edilmez.
    Onun yerine None dönen küçük bir wrapper slot kullanılır.
    """
    method = getattr(parent_window, method_name, None)

    if callable(method):
        def _wrapped_slot(_checked=False):
            method()
            return None

        button.clicked.connect(_wrapped_slot)
        return

    def _missing_method_warning(_checked=False):
        QMessageBox.warning(
            parent_window,
            "Fonksiyon Henüz Eklenmedi",
            f"'{friendly_name}' işlemi için main.py içinde şu metod eklenecek:\n\n"
            f"{method_name}()\n\n"
            "Sıradaki adımda main.py dosyasını revize edeceğiz.",
        )
        return None

    button.clicked.connect(_missing_method_warning)


def _get_categories(parent_window):
    try:
        categories = parent_window._get_available_categories()
    except Exception:
        categories = ["default"]

    if not categories:
        categories = ["default"]

    return categories


def _fill_combined_source_list(parent_window):
    """
    Birleşik final eğitim için kaynak kategori listesini doldur.
    models, weapon_dataset ve backup klasörleri kaynak olarak gösterilmez.
    """
    if not hasattr(parent_window, "combined_source_categories_list"):
        return

    parent_window.combined_source_categories_list.clear()

    categories = _get_categories(parent_window)

    for category in categories:
        if not category:
            continue

        lower_name = category.lower()

        if lower_name == "models":
            continue

        if lower_name == "weapon_dataset":
            continue

        if "backup" in lower_name:
            continue

        parent_window.combined_source_categories_list.addItem(category)


def _select_all_combined_sources(parent_window):
    if not hasattr(parent_window, "combined_source_categories_list"):
        return

    for i in range(parent_window.combined_source_categories_list.count()):
        item = parent_window.combined_source_categories_list.item(i)
        item.setSelected(True)


def _clear_combined_sources_selection(parent_window):
    if not hasattr(parent_window, "combined_source_categories_list"):
        return

    parent_window.combined_source_categories_list.clearSelection()


# =========================================================
# ANA TRAINING UI
# =========================================================

def create_training_ui(main_layout, parent_window):
    """Model eğitimi sekmesi UI'sini oluştur."""
    main_layout.setContentsMargins(10, 10, 10, 10)
    main_layout.setSpacing(10)

    header_label = _title_label("YOLO Model Eğitimi Sistemi", 14)
    main_layout.addWidget(header_label)

    info_label = QLabel(
        "Kategori bazlı test eğitimleri yapabilir veya tüm kategorileri birleştirerek tek final model eğitebilirsiniz."
    )
    info_label.setStyleSheet("color: #4B5563; font-size: 10px; margin-bottom: 4px;")
    main_layout.addWidget(info_label)

    training_tabs = QTabWidget()
    training_tabs.setStyleSheet("""
        QTabWidget::pane {
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            background: white;
        }
        QTabBar::tab {
            background: #E5E7EB;
            color: #111827;
            padding: 8px 12px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 2px;
            font-weight: bold;
        }
        QTabBar::tab:selected {
            background: #2563EB;
            color: white;
        }
    """)

    # TAB 1: İçerik Yükleme
    upload_tab = QWidget()
    upload_layout = QVBoxLayout()
    _init_training_upload_tab(upload_layout, parent_window)
    upload_tab.setLayout(upload_layout)
    training_tabs.addTab(upload_tab, "İçerik Yükleme")

    # TAB 2: Kategori Yönetimi
    category_tab = QWidget()
    category_layout = QVBoxLayout()
    _init_category_management_tab(category_layout, parent_window)
    category_tab.setLayout(category_layout)
    training_tabs.addTab(category_tab, "Kategori Yönetimi")

    # TAB 3: İçerik Kontrolü
    control_tab = QWidget()
    control_layout = QVBoxLayout()
    _init_content_control_tab(control_layout, parent_window)
    control_tab.setLayout(control_layout)
    training_tabs.addTab(control_tab, "İçerik Kontrolü")

    # TAB 4: Dataset Analiz
    analysis_tab = QWidget()
    analysis_layout = QVBoxLayout()
    _init_dataset_analysis_tab(analysis_layout, parent_window)
    analysis_tab.setLayout(analysis_layout)
    training_tabs.addTab(analysis_tab, "Dataset Analiz")

    # TAB 5: Eğitim Ayarları
    settings_tab = QWidget()
    settings_layout = QVBoxLayout()
    _init_training_settings_tab(settings_layout, parent_window)
    settings_tab.setLayout(settings_layout)
    training_tabs.addTab(settings_tab, "Eğitim Ayarları")

    main_layout.addWidget(training_tabs)

    try:
        parent_window.refresh_categories_list()
        parent_window.refresh_upload_categories()
        parent_window.refresh_training_categories()
        parent_window.refresh_content_categories()
        parent_window.refresh_content_display()
        _fill_combined_source_list(parent_window)
    except Exception:
        pass


# =========================================================
# TAB 1: İÇERİK YÜKLEME
# =========================================================

def _init_training_upload_tab(layout, parent_window):
    """TAB 1: İçerik Yükleme"""
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(12)

    select_frame = QFrame()
    select_frame.setStyleSheet(_frame_style("#10B981", "#ECFDF5"))
    select_layout = QVBoxLayout()
    select_layout.setContentsMargins(15, 15, 15, 15)
    select_layout.setSpacing(10)

    select_layout.addWidget(_section_title("Hedef Kategori ve Bölümü Seçin"))

    choice_layout = QHBoxLayout()
    choice_layout.addWidget(QLabel("Kategori:"))

    parent_window.upload_category_combo = QComboBox()
    parent_window.upload_category_combo.addItems(_get_categories(parent_window))
    parent_window.upload_category_combo.setMinimumWidth(170)
    choice_layout.addWidget(parent_window.upload_category_combo)

    choice_layout.addWidget(QLabel("Bölüm:"))

    parent_window.upload_split_combo = QComboBox()
    parent_window.upload_split_combo.addItems(["train", "val", "test"])
    parent_window.upload_split_combo.setCurrentIndex(0)
    parent_window.upload_split_combo.setMinimumWidth(100)
    choice_layout.addWidget(parent_window.upload_split_combo)

    upload_refresh_btn = QPushButton("Kategorileri Yenile")
    upload_refresh_btn.setMinimumHeight(34)
    upload_refresh_btn.setStyleSheet(_button_style("#2563EB", "#1D4ED8", 9))
    upload_refresh_btn.clicked.connect(parent_window.refresh_upload_categories)
    choice_layout.addWidget(upload_refresh_btn)

    choice_layout.addStretch()
    select_layout.addLayout(choice_layout)
    select_frame.setLayout(select_layout)
    layout.addWidget(select_frame)

    upload_frame = QFrame()
    upload_frame.setStyleSheet(_frame_style("#F97316", "#FFF7ED"))
    upload_btn_layout = QVBoxLayout()
    upload_btn_layout.setContentsMargins(15, 15, 15, 15)
    upload_btn_layout.setSpacing(10)

    upload_btn_layout.addWidget(_section_title("Dosya Yükleyin"))

    btn_row1 = QHBoxLayout()

    images_btn = QPushButton("Resimler Yükle")
    images_btn.setMinimumHeight(44)
    images_btn.setStyleSheet(_button_style("#2563EB", "#1D4ED8"))
    images_btn.clicked.connect(parent_window.browse_training_images)
    btn_row1.addWidget(images_btn)

    labels_btn = QPushButton("Labellar Yükle")
    labels_btn.setMinimumHeight(44)
    labels_btn.setStyleSheet(_button_style("#7C3AED", "#6D28D9"))
    labels_btn.clicked.connect(parent_window.browse_training_labels)
    btn_row1.addWidget(labels_btn)

    upload_btn_layout.addLayout(btn_row1)

    btn_row2 = QHBoxLayout()

    video_btn = QPushButton("Video'dan Frame Çıkar")
    video_btn.setMinimumHeight(44)
    video_btn.setStyleSheet(_button_style("#DC2626", "#B91C1C"))
    video_btn.clicked.connect(parent_window.extract_video_frames)
    btn_row2.addWidget(video_btn)
    btn_row2.addStretch()

    upload_btn_layout.addLayout(btn_row2)

    upload_btn_layout.addWidget(QLabel("Yükleme Geçmişi:"))

    parent_window.upload_history_list = QListWidget()
    parent_window.upload_history_list.setMaximumHeight(160)
    parent_window.upload_history_list.setStyleSheet(_list_style())
    upload_btn_layout.addWidget(parent_window.upload_history_list)

    upload_frame.setLayout(upload_btn_layout)
    layout.addWidget(upload_frame)
    layout.addStretch()


# =========================================================
# TAB 2: KATEGORİ YÖNETİMİ
# =========================================================

def _init_category_management_tab(layout, parent_window):
    """TAB 2: Kategori Yönetimi."""
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(12)

    layout.addWidget(_section_title("Kategori Yönetim Araçları"))

    list_frame = QFrame()
    list_frame.setStyleSheet(_frame_style("#2563EB", "#EFF6FF"))
    list_layout = QVBoxLayout()
    list_layout.setContentsMargins(15, 15, 15, 15)
    list_layout.setSpacing(10)

    list_layout.addWidget(QLabel("Mevcut Kategoriler:"))

    parent_window.categories_list = QListWidget()
    parent_window.categories_list.setSelectionMode(QListWidget.SingleSelection)
    parent_window.categories_list.setMaximumHeight(155)
    parent_window.categories_list.setStyleSheet(_list_style())

    try:
        parent_window.refresh_categories_list()
    except Exception:
        pass

    list_layout.addWidget(parent_window.categories_list)

    list_frame.setLayout(list_layout)
    layout.addWidget(list_frame)

    stats_frame = QFrame()
    stats_frame.setStyleSheet(_frame_style("#10B981", "#ECFDF5"))
    stats_layout = QVBoxLayout()
    stats_layout.setContentsMargins(15, 15, 15, 15)
    stats_layout.setSpacing(10)

    stats_layout.addWidget(QLabel("Kategori İstatistikleri:"))

    parent_window.category_stats_text = QTextEdit()
    parent_window.category_stats_text.setReadOnly(True)
    parent_window.category_stats_text.setMaximumHeight(125)
    parent_window.category_stats_text.setStyleSheet(_textedit_style())
    stats_layout.addWidget(parent_window.category_stats_text)

    stats_frame.setLayout(stats_layout)
    layout.addWidget(stats_frame)

    ops_frame = QFrame()
    ops_frame.setStyleSheet(_frame_style("#F97316", "#FFF7ED"))
    ops_layout = QVBoxLayout()
    ops_layout.setContentsMargins(15, 15, 15, 15)
    ops_layout.setSpacing(10)

    ops_layout.addWidget(QLabel("Kategori İşlemleri:"))

    new_cat_layout = QHBoxLayout()
    new_cat_layout.addWidget(QLabel("Yeni Kategori Adı:"))

    parent_window.new_category_input = QLineEdit()
    parent_window.new_category_input.setPlaceholderText("örn: nora_b52, zuzana, obus")
    parent_window.new_category_input.setMinimumWidth(240)
    new_cat_layout.addWidget(parent_window.new_category_input)

    add_cat_btn = QPushButton("Kategori Oluştur")
    add_cat_btn.setMinimumHeight(34)
    add_cat_btn.setStyleSheet(_button_style("#16A34A", "#15803D"))
    add_cat_btn.clicked.connect(parent_window.create_new_category)
    new_cat_layout.addWidget(add_cat_btn)

    new_cat_layout.addStretch()
    ops_layout.addLayout(new_cat_layout)

    category_ops_layout = QHBoxLayout()

    rename_cat_btn = QPushButton("Kategoriyi Yeniden Adlandır")
    rename_cat_btn.setMinimumHeight(34)
    rename_cat_btn.setStyleSheet(_button_style("#F59E0B", "#D97706"))
    rename_cat_btn.clicked.connect(parent_window.rename_category)
    category_ops_layout.addWidget(rename_cat_btn)

    delete_cat_btn = QPushButton("Kategoriyi Sil")
    delete_cat_btn.setMinimumHeight(34)
    delete_cat_btn.setStyleSheet(_button_style("#DC2626", "#B91C1C"))
    delete_cat_btn.clicked.connect(parent_window.delete_category)
    category_ops_layout.addWidget(delete_cat_btn)

    refresh_cat_btn = QPushButton("Listeyi Yenile")
    refresh_cat_btn.setMinimumHeight(34)
    refresh_cat_btn.setStyleSheet(_soft_button_style("#E0F2FE", "#BAE6FD"))
    refresh_cat_btn.clicked.connect(parent_window.refresh_categories_list)
    category_ops_layout.addWidget(refresh_cat_btn)

    category_ops_layout.addStretch()
    ops_layout.addLayout(category_ops_layout)

    ops_frame.setLayout(ops_layout)
    layout.addWidget(ops_frame)
    layout.addStretch()


# =========================================================
# TAB 3: İÇERİK KONTROLÜ
# =========================================================

def _init_content_control_tab(layout, parent_window):
    """TAB 3: İçerik Kontrolü."""
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(12)

    layout.addWidget(_section_title("Kategori İçeriğini Yönet"))

    select_frame = QFrame()
    select_frame.setStyleSheet(_frame_style("#10B981", "#ECFDF5"))
    select_layout = QHBoxLayout()
    select_layout.setContentsMargins(15, 10, 15, 10)
    select_layout.setSpacing(10)

    select_layout.addWidget(QLabel("Kategori:"))

    parent_window.content_category_combo = QComboBox()
    parent_window.content_category_combo.addItems(_get_categories(parent_window))
    parent_window.content_category_combo.currentTextChanged.connect(parent_window.refresh_content_display)
    select_layout.addWidget(parent_window.content_category_combo)

    select_layout.addWidget(QLabel("Bölüm:"))

    parent_window.content_split_combo = QComboBox()
    parent_window.content_split_combo.addItems(["train", "val", "test"])
    parent_window.content_split_combo.currentTextChanged.connect(parent_window.refresh_content_display)
    select_layout.addWidget(parent_window.content_split_combo)

    refresh_btn = QPushButton("Yenile")
    refresh_btn.setMinimumHeight(34)
    refresh_btn.setStyleSheet(_soft_button_style("#DCFCE7", "#BBF7D0"))
    refresh_btn.clicked.connect(parent_window.refresh_content_display)
    select_layout.addWidget(refresh_btn)

    category_refresh_btn = QPushButton("Kategorileri Yenile")
    category_refresh_btn.setMinimumHeight(34)
    category_refresh_btn.setStyleSheet(_soft_button_style("#DBEAFE", "#BFDBFE"))
    category_refresh_btn.clicked.connect(parent_window.refresh_content_categories)
    select_layout.addWidget(category_refresh_btn)

    select_layout.addStretch()

    select_frame.setLayout(select_layout)
    layout.addWidget(select_frame)

    files_frame = QFrame()
    files_frame.setStyleSheet(_frame_style("#2563EB", "#EFF6FF"))
    files_layout = QHBoxLayout()
    files_layout.setContentsMargins(15, 15, 15, 15)
    files_layout.setSpacing(10)

    img_section = QVBoxLayout()
    img_section.addWidget(QLabel("Resimler:"))

    parent_window.content_images_list = QListWidget()
    parent_window.content_images_list.setSelectionMode(QListWidget.MultiSelection)
    parent_window.content_images_list.setStyleSheet(_list_style())
    img_section.addWidget(parent_window.content_images_list)

    files_layout.addLayout(img_section)

    lbl_section = QVBoxLayout()
    lbl_section.addWidget(QLabel("Labellar:"))

    parent_window.content_labels_list = QListWidget()
    parent_window.content_labels_list.setSelectionMode(QListWidget.MultiSelection)
    parent_window.content_labels_list.setStyleSheet(_list_style())
    lbl_section.addWidget(parent_window.content_labels_list)

    files_layout.addLayout(lbl_section)

    files_frame.setLayout(files_layout)
    layout.addWidget(files_frame, 1)

    ops_frame = QFrame()
    ops_frame.setStyleSheet(_frame_style("#EF4444", "#FEF2F2"))
    ops_layout = QVBoxLayout()
    ops_layout.setContentsMargins(15, 15, 15, 15)
    ops_layout.setSpacing(10)

    parent_window.content_stats_label = QLabel("Resimler: 0 | Labellar: 0")
    parent_window.content_stats_label.setStyleSheet("color: #111827; font-weight: bold; font-size: 10px;")
    ops_layout.addWidget(parent_window.content_stats_label)

    ops_btn_layout = QHBoxLayout()

    del_img_btn = QPushButton("Seçili Resimleri Sil")
    del_img_btn.setMinimumHeight(34)
    del_img_btn.setStyleSheet(_button_style("#EF4444", "#DC2626", 9))
    del_img_btn.clicked.connect(parent_window.delete_selected_images)
    ops_btn_layout.addWidget(del_img_btn)

    del_lbl_btn = QPushButton("Seçili Labelları Sil")
    del_lbl_btn.setMinimumHeight(34)
    del_lbl_btn.setStyleSheet(_button_style("#F97316", "#EA580C", 9))
    del_lbl_btn.clicked.connect(parent_window.delete_selected_labels)
    ops_btn_layout.addWidget(del_lbl_btn)

    del_all_btn = QPushButton("Tümünü Sil")
    del_all_btn.setMinimumHeight(34)
    del_all_btn.setStyleSheet(_button_style("#991B1B", "#7F1D1D", 9))
    del_all_btn.clicked.connect(parent_window.delete_all_content)
    ops_btn_layout.addWidget(del_all_btn)

    ops_btn_layout.addStretch()
    ops_layout.addLayout(ops_btn_layout)

    ops_frame.setLayout(ops_layout)
    layout.addWidget(ops_frame)


# =========================================================
# TAB 4: DATASET ANALİZ
# =========================================================

def _init_dataset_analysis_tab(layout, parent_window):
    """TAB 4: Dataset Analiz."""
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(12)

    layout.addWidget(_section_title("Dataset Analiz ve Sınıf Dağılımı"))

    info_frame = QFrame()
    info_frame.setStyleSheet(_frame_style("#6366F1", "#EEF2FF"))
    info_layout = QVBoxLayout()
    info_layout.setContentsMargins(15, 15, 15, 15)

    info_text = QLabel(
        "Bu bölüm eğitimden önce label dosyalarının sınıf dağılımını kontrol etmek için kullanılır.\n"
        "Örnek: Zuzana için çoğunlukla 4 = zuzana_govde görünmelidir.\n"
        "Birleşik final eğitim öncesinde tüm kategorilerin doğru sınıf id'leriyle geldiğini buradan kontrol edebilirsiniz."
    )
    info_text.setStyleSheet("color: #374151; font-size: 10px;")
    info_layout.addWidget(info_text)

    info_frame.setLayout(info_layout)
    layout.addWidget(info_frame)

    control_frame = QFrame()
    control_frame.setStyleSheet(_frame_style("#2563EB", "#EFF6FF"))
    control_layout = QVBoxLayout()
    control_layout.setContentsMargins(15, 15, 15, 15)
    control_layout.setSpacing(10)

    row = QHBoxLayout()
    row.addWidget(QLabel("Analiz Edilecek Kategori:"))

    parent_window.analysis_category_combo = QComboBox()
    parent_window.analysis_category_combo.addItems(_get_categories(parent_window))
    parent_window.analysis_category_combo.setMinimumWidth(180)
    row.addWidget(parent_window.analysis_category_combo)

    refresh_analysis_categories_btn = QPushButton("Yenile")
    refresh_analysis_categories_btn.setMinimumHeight(34)
    refresh_analysis_categories_btn.setStyleSheet(_soft_button_style("#DBEAFE", "#BFDBFE"))
    _safe_connect(
        refresh_analysis_categories_btn,
        parent_window,
        "refresh_analysis_categories",
        "Analiz kategori listesini yenile",
    )
    row.addWidget(refresh_analysis_categories_btn)

    row.addStretch()
    control_layout.addLayout(row)

    btn_row = QHBoxLayout()

    selected_analysis_btn = QPushButton("Seçili Kategoriyi Analiz Et")
    selected_analysis_btn.setMinimumHeight(40)
    selected_analysis_btn.setStyleSheet(_button_style("#2563EB", "#1D4ED8"))
    _safe_connect(
        selected_analysis_btn,
        parent_window,
        "analyze_selected_training_dataset",
        "Seçili kategoriyi analiz et",
    )
    btn_row.addWidget(selected_analysis_btn)

    all_analysis_btn = QPushButton("Tüm Kategorileri Analiz Et")
    all_analysis_btn.setMinimumHeight(40)
    all_analysis_btn.setStyleSheet(_button_style("#7C3AED", "#6D28D9"))
    _safe_connect(
        all_analysis_btn,
        parent_window,
        "analyze_all_training_datasets",
        "Tüm kategorileri analiz et",
    )
    btn_row.addWidget(all_analysis_btn)

    combined_analysis_btn = QPushButton("Birleşik Dataset'i Analiz Et")
    combined_analysis_btn.setMinimumHeight(40)
    combined_analysis_btn.setStyleSheet(_button_style("#0F766E", "#0D9488"))
    _safe_connect(
        combined_analysis_btn,
        parent_window,
        "analyze_combined_training_dataset",
        "Birleşik dataset'i analiz et",
    )
    btn_row.addWidget(combined_analysis_btn)

    btn_row.addStretch()
    control_layout.addLayout(btn_row)

    control_frame.setLayout(control_layout)
    layout.addWidget(control_frame)

    output_frame = QFrame()
    output_frame.setStyleSheet(_frame_style("#64748B", "#F8FAFC"))
    output_layout = QVBoxLayout()
    output_layout.setContentsMargins(15, 15, 15, 15)

    output_layout.addWidget(QLabel("Analiz Çıktısı:"))

    parent_window.dataset_analysis_text = QTextEdit()
    parent_window.dataset_analysis_text.setReadOnly(True)
    parent_window.dataset_analysis_text.setStyleSheet(_textedit_style())
    parent_window.dataset_analysis_text.setMinimumHeight(260)
    parent_window.dataset_analysis_text.setText(
        "Henüz analiz yapılmadı.\n\n"
        "Önerilen kontrol:\n"
        "- Zuzana label dağılımı: 4 = zuzana_govde\n"
        "- Nora B-52 label dağılımı: 0/1/2/3 aralığı\n"
        "- Obüs label dağılımı: 8/9/10/11 aralığı\n"
    )
    output_layout.addWidget(parent_window.dataset_analysis_text)

    output_frame.setLayout(output_layout)
    layout.addWidget(output_frame, 1)


# =========================================================
# TAB 5: EĞİTİM AYARLARI
# =========================================================

def _init_training_settings_tab(layout, parent_window):
    """TAB 5: Eğitim Ayarları ve Başlat."""
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(12)

    layout.addWidget(_section_title("Eğitim Parametreleri ve Final Model Araçları"))

    params_frame = QFrame()
    params_frame.setStyleSheet(_frame_style("#2563EB", "#EFF6FF"))
    params_layout = QVBoxLayout()
    params_layout.setContentsMargins(15, 15, 15, 15)
    params_layout.setSpacing(12)

    params_layout.addWidget(_section_title("Ortak Eğitim Parametreleri", 10))

    param_row = QHBoxLayout()

    param_row.addWidget(QLabel("Epoch:"))
    parent_window.epoch_spinbox = QSpinBox()
    parent_window.epoch_spinbox.setMinimum(1)
    parent_window.epoch_spinbox.setMaximum(500)
    parent_window.epoch_spinbox.setValue(50)
    parent_window.epoch_spinbox.setMinimumWidth(90)
    param_row.addWidget(parent_window.epoch_spinbox)

    param_row.addWidget(QLabel("Batch:"))
    parent_window.batch_spinbox = QSpinBox()
    parent_window.batch_spinbox.setMinimum(1)
    parent_window.batch_spinbox.setMaximum(128)
    parent_window.batch_spinbox.setValue(16)
    parent_window.batch_spinbox.setMinimumWidth(90)
    param_row.addWidget(parent_window.batch_spinbox)

    param_row.addWidget(QLabel("Resim Boyutu:"))
    parent_window.imgsz_spinbox = QSpinBox()
    parent_window.imgsz_spinbox.setMinimum(320)
    parent_window.imgsz_spinbox.setMaximum(1280)
    parent_window.imgsz_spinbox.setValue(640)
    parent_window.imgsz_spinbox.setSingleStep(64)
    parent_window.imgsz_spinbox.setMinimumWidth(90)
    param_row.addWidget(parent_window.imgsz_spinbox)

    param_row.addStretch()
    params_layout.addLayout(param_row)

    params_frame.setLayout(params_layout)
    layout.addWidget(params_frame)

    # -----------------------------------------------------
    # KATEGORİ BAZLI EĞİTİM
    # -----------------------------------------------------

    category_train_frame = QFrame()
    category_train_frame.setStyleSheet(_frame_style("#10B981", "#ECFDF5"))
    category_train_layout = QVBoxLayout()
    category_train_layout.setContentsMargins(15, 15, 15, 15)
    category_train_layout.setSpacing(10)

    category_train_layout.addWidget(_section_title("Kategori Bazlı Eğitim", 10))

    category_info = QLabel(
        "Test amaçlıdır. Sadece seçili kategoriyle model eğitir. "
        "Nihai sistem için aşağıdaki Birleşik Final Model Eğitimi kullanılmalıdır."
    )
    category_info.setStyleSheet("color: #374151; font-size: 9px;")
    category_train_layout.addWidget(category_info)

    cat_layout = QHBoxLayout()
    cat_layout.addWidget(QLabel("Eğitim Kategorisi:"))

    parent_window.training_category_combo = QComboBox()
    parent_window.training_category_combo.addItems(_get_categories(parent_window))
    parent_window.training_category_combo.setMinimumWidth(170)
    cat_layout.addWidget(parent_window.training_category_combo)

    train_refresh_btn = QPushButton("Yenile")
    train_refresh_btn.setMinimumHeight(34)
    train_refresh_btn.setMaximumWidth(100)
    train_refresh_btn.setStyleSheet(_soft_button_style("#DBEAFE", "#BFDBFE"))
    train_refresh_btn.clicked.connect(parent_window.refresh_training_categories)
    cat_layout.addWidget(train_refresh_btn)

    cat_layout.addStretch()
    category_train_layout.addLayout(cat_layout)

    parent_window.train_btn = QPushButton("SEÇİLİ KATEGORİYİ EĞİT")
    parent_window.train_btn.setMinimumHeight(48)
    parent_window.train_btn.setFont(QFont("Arial", 11, QFont.Bold))
    parent_window.train_btn.setStyleSheet(_button_style("#16A34A", "#15803D", 11))
    parent_window.train_btn.clicked.connect(parent_window.start_training)
    category_train_layout.addWidget(parent_window.train_btn)

    category_train_frame.setLayout(category_train_layout)
    layout.addWidget(category_train_frame)

    # -----------------------------------------------------
    # BİRLEŞİK FİNAL MODEL EĞİTİMİ
    # -----------------------------------------------------

    combined_frame = QFrame()
    combined_frame.setStyleSheet(_frame_style("#7C3AED", "#F5F3FF"))
    combined_layout = QVBoxLayout()
    combined_layout.setContentsMargins(15, 15, 15, 15)
    combined_layout.setSpacing(10)

    combined_layout.addWidget(_section_title("Birleşik Final Model Eğitimi", 10))

    combined_info = QLabel(
        "Nora B-52, Zuzana ve Obüs gibi kategori klasörlerini tek dataset altında toplar. "
        "Final model için önerilen eğitim şekli budur."
    )
    combined_info.setStyleSheet("color: #374151; font-size: 9px;")
    combined_layout.addWidget(combined_info)

    dataset_name_row = QHBoxLayout()
    dataset_name_row.addWidget(QLabel("Birleşik Dataset Adı:"))

    parent_window.combined_dataset_name_input = QLineEdit()
    parent_window.combined_dataset_name_input.setText("weapon_dataset")
    parent_window.combined_dataset_name_input.setPlaceholderText("weapon_dataset")
    parent_window.combined_dataset_name_input.setMinimumWidth(200)
    dataset_name_row.addWidget(parent_window.combined_dataset_name_input)

    dataset_name_row.addStretch()
    combined_layout.addLayout(dataset_name_row)

    source_title_row = QHBoxLayout()
    source_title_row.addWidget(QLabel("Kaynak Kategoriler:"))
    source_title_row.addStretch()

    refresh_sources_btn = QPushButton("Kaynakları Yenile")
    refresh_sources_btn.setMinimumHeight(32)
    refresh_sources_btn.setStyleSheet(_soft_button_style("#EDE9FE", "#DDD6FE"))
    refresh_sources_btn.clicked.connect(lambda _checked=False: _fill_combined_source_list(parent_window))
    source_title_row.addWidget(refresh_sources_btn)

    select_all_sources_btn = QPushButton("Tümünü Seç")
    select_all_sources_btn.setMinimumHeight(32)
    select_all_sources_btn.setStyleSheet(_soft_button_style("#DCFCE7", "#BBF7D0"))
    select_all_sources_btn.clicked.connect(lambda _checked=False: _select_all_combined_sources(parent_window))
    source_title_row.addWidget(select_all_sources_btn)

    clear_sources_btn = QPushButton("Seçimi Temizle")
    clear_sources_btn.setMinimumHeight(32)
    clear_sources_btn.setStyleSheet(_soft_button_style("#FEF3C7", "#FDE68A"))
    clear_sources_btn.clicked.connect(lambda _checked=False: _clear_combined_sources_selection(parent_window))
    source_title_row.addWidget(clear_sources_btn)

    combined_layout.addLayout(source_title_row)

    parent_window.combined_source_categories_list = QListWidget()
    parent_window.combined_source_categories_list.setSelectionMode(QAbstractItemView.MultiSelection)
    parent_window.combined_source_categories_list.setMaximumHeight(95)
    parent_window.combined_source_categories_list.setStyleSheet(_list_style())
    combined_layout.addWidget(parent_window.combined_source_categories_list)

    _fill_combined_source_list(parent_window)

    combined_btn_row = QHBoxLayout()

    prepare_combined_btn = QPushButton("Birleşik Dataset Hazırla")
    prepare_combined_btn.setMinimumHeight(44)
    prepare_combined_btn.setStyleSheet(_button_style("#7C3AED", "#6D28D9", 10))
    _safe_connect(
        prepare_combined_btn,
        parent_window,
        "prepare_combined_dataset_from_ui",
        "Birleşik dataset hazırla",
    )
    combined_btn_row.addWidget(prepare_combined_btn)

    train_combined_btn = QPushButton("BİRLEŞİK FİNAL MODELİ EĞİT")
    train_combined_btn.setMinimumHeight(44)
    train_combined_btn.setStyleSheet(_button_style("#0F766E", "#0D9488", 10))
    _safe_connect(
        train_combined_btn,
        parent_window,
        "start_combined_training",
        "Birleşik final modeli eğit",
    )
    combined_btn_row.addWidget(train_combined_btn)

    combined_btn_row.addStretch()
    combined_layout.addLayout(combined_btn_row)

    combined_frame.setLayout(combined_layout)
    layout.addWidget(combined_frame)

    # -----------------------------------------------------
    # İLERLEME VE GÜNLÜK
    # -----------------------------------------------------

    progress_frame = QFrame()
    progress_frame.setStyleSheet(_frame_style("#64748B", "#F8FAFC"))
    progress_layout = QVBoxLayout()
    progress_layout.setContentsMargins(15, 15, 15, 15)
    progress_layout.setSpacing(10)

    progress_header_row = QHBoxLayout()
    progress_header_row.addWidget(QLabel("Eğitim İlerlemesi:"))

    parent_window.training_progress_label = QLabel("Hazır")
    parent_window.training_progress_label.setStyleSheet("color: #374151; font-weight: bold;")
    progress_header_row.addWidget(parent_window.training_progress_label)

    progress_header_row.addStretch()
    progress_layout.addLayout(progress_header_row)

    parent_window.training_progress = QProgressBar()
    parent_window.training_progress.setVisible(False)
    parent_window.training_progress.setMinimum(0)
    parent_window.training_progress.setMaximum(100)
    parent_window.training_progress.setValue(0)
    parent_window.training_progress.setMinimumHeight(25)
    parent_window.training_progress.setStyleSheet("""
        QProgressBar {
            border: 1px solid #94A3B8;
            border-radius: 6px;
            background-color: #E5E7EB;
            text-align: center;
            font-weight: bold;
            color: #111827;
        }
        QProgressBar::chunk {
            background: #22C55E;
            border-radius: 5px;
        }
    """)
    progress_layout.addWidget(parent_window.training_progress)

    progress_layout.addWidget(QLabel("Eğitim Günlüğü:"))

    parent_window.training_log = QTextEdit()
    parent_window.training_log.setReadOnly(True)
    parent_window.training_log.setMaximumHeight(150)
    parent_window.training_log.setStyleSheet(_textedit_style())
    progress_layout.addWidget(parent_window.training_log)

    progress_frame.setLayout(progress_layout)
    layout.addWidget(progress_frame, 1)