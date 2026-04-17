#!/usr/bin/env python
"""Comprehensive testing of GUI widgets and methods"""
import sys
import traceback
from PyQt5 import QtWidgets, QtCore

try:
    print("="*60)
    print("YOĞUN TEST: GUI İçi Kontrol")
    print("="*60)
    
    print("\n1. QApplication oluşturuluyor...")
    app = QtWidgets.QApplication(sys.argv)
    print("   ✓ QApplication başarılı")
    
    print("\n2. MainWindow içe aktarılıyor...")
    from main import MainWindow
    print("   ✓ MainWindow import başarılı")
    
    print("\n3. MainWindow örneği oluşturuluyor...")
    window = MainWindow()
    print("   ✓ MainWindow örneği başarılı")
    
    print("\n4. Tab widgetleri kontrol ediliyor...")
    # Check if all tab-related widgets exist
    required_widgets = [
        # Tab 1 - Upload
        'upload_category_combo', 'upload_split_combo', 'upload_history_list',
        # Tab 2 - Category Management
        'categories_list', 'new_category_input', 'category_stats_text',
        # Tab 3 - Content Control
        'content_category_combo', 'content_split_combo', 'content_images_list', 'content_labels_list',
        # Tab 4 - Training Settings
        'training_category_combo', 'epoch_spinbox', 'batch_spinbox', 'imgsz_spinbox',
        'training_progress', 'training_log'
    ]
    
    missing_widgets = []
    for widget_name in required_widgets:
        if hasattr(window, widget_name):
            print(f"   ✓ {widget_name} var")
        else:
            print(f"   ✗ {widget_name} EKSIK")
            missing_widgets.append(widget_name)
    
    if missing_widgets:
        print(f"\n   HATA: {len(missing_widgets)} widget eksik: {missing_widgets}")
    else:
        print(f"\n   ✓ Tüm {len(required_widgets)} widget mevcut")
    
    print("\n5. Önemli metodlar kontrol ediliyor...")
    required_methods = [
        'refresh_categories_list', 'create_new_category', 'delete_category',
        'browse_training_images', 'refresh_content_display', 'delete_selected_images',
        'start_training', 'log'
    ]
    
    missing_methods = []
    for method_name in required_methods:
        if hasattr(window, method_name) and callable(getattr(window, method_name)):
            print(f"   ✓ {method_name}() var")
        else:
            print(f"   ✗ {method_name}() EKSIK")
            missing_methods.append(method_name)
    
    if missing_methods:
        print(f"\n   HATA: {len(missing_methods)} metod eksik: {missing_methods}")
    else:
        print(f"\n   ✓ Tüm {len(required_methods)} metod mevcut")
    
    print("\n6. ModelTrainer modülü kontrol ediliyor...")
    from src import ModelTrainer
    print("   ✓ ModelTrainer import başarılı")
    
    print("\n7. Detector modülü kontrol ediliyor...")
    from src import HowitzerDetector
    print("   ✓ HowitzerDetector import başarılı")
    
    print("\n8. Report generator modülü kontrol ediliyor...")
    from src import ReportGenerator
    print("   ✓ ReportGenerator import başarılı")
    
    print("\n" + "="*60)
    if missing_widgets or missing_methods:
        print("SONUÇ: ✗ HATALAR BULUNDU")
        print("="*60)
        sys.exit(1)
    else:
        print("SONUÇ: ✓ TÜM KONTROLLER BAŞARILI")
        print("="*60)
        print("\nGUI penceresi gösteriliyor (5 saniye)...")
        window.show()
        QtCore.QTimer.singleShot(5000, app.quit)
        app.exec_()
        print("GUI kapatıldı. Test tamamlandı.")

except Exception as e:
    print(f"\n✗ HATA OLUŞTU: {type(e).__name__}: {e}")
    print("\nTam hata takibi:")
    traceback.print_exc()
    sys.exit(1)
