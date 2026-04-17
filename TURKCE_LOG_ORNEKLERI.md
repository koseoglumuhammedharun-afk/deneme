# 📝 Analiz Günlüğü - Türkçe Örnek

## Uygulama Başlatıldı

```
[INFO] Drone Obüs Tespit Sistemi başlanıyor...
[INFO] Python 3.10.11 test ortamı
[INFO] Yapılandırma yükleniyor...
[INFO] Model yolu yapılandırıldı: C:\...\models\howitzer_detector.pt
[INFO] Çıktı dizini: C:\...\outputs
```

---

## Resim Analizi

### ✅ Başarılı Tespit

```
[2026-04-08 14:32:15] Analiz başlanıyor: drone_foto_1.jpg

[INFO] Resim analiz ediliyor...
[INFO] Resim başarıyla yüklendi
[INFO] YOLO modeli üzerinde çıkarsal işlem yapılıyor...
✓ Tespit bulundu! Güven: %92.5
[INFO] Tespit bulundu: güven=0.925
[INFO] Meta veri çıkartılıyor...
[INFO] EXIF: Tarih=2026-04-08, Konum=40.7128°N, 74.0060°W
[INFO] Rapor oluşturuluyor...

✅ ANALIZ TAMAMLANDI
├─ Dosya: drone_foto_1.jpg
├─ Tespit: BULUNDU
├─ Güven: 92.50%
├─ Konum: 40.7128°N, 74.0060°W
├─ Tarih: 8 Nisan 2026, 14:32
└─ Rapor: drone_foto_1_report.xlsx
```

### ✗ Tespit Bulunamadı

```
[2026-04-08 14:35:22] Analiz başlanıyor: drone_foto_2.jpg

[INFO] Resim analiz ediliyor...
[INFO] Resim başarıyla yüklendi
[INFO] YOLO modeli üzerinde çıkarsal işlem yapılıyor...
✗ Tespit bulunamadı
[INFO] Meta veri çıkartılıyor...
[INFO] Rapor oluşturuluyor...

✅ ANALIZ TAMAMLANDI
├─ Dosya: drone_foto_2.jpg
├─ Tespit: BULUNAMADI
├─ Güven: 0.00%
├─ Rapor: drone_foto_2_report.xlsx
```

---

## Video Analizi

```
[2026-04-08 14:40:10] Analiz başlanıyor: drone_video.mp4

[INFO] Video analiz ediliyor...
[INFO] Video başarıyla açıldı
[INFO] Toplam Frame: 1200, FPS: 30.0
[INFO] Video işleme başlanıyor...

Frame 0/1200 - Güven: %0.00
Frame 30/1200 - Güven: %0.00
Frame 60/1200 - Güven: %15.32
Frame 90/1200 - Güven: %22.18
Frame 120/1200 - Güven: %45.67
Frame 150/1200 - Güven: %78.92
[INFO] Frame 150 da tespit: güven=0.789
Frame 180/1200 - Güven: %89.45
[INFO] Frame 180 da tespit: güven=0.895
Frame 210/1200 - Güven: %91.23
[INFO] Frame 210 da tespit: güven=0.912 ← EN YÜKSEK
Frame 240/1200 - Güven: %88.34
...
Frame 1200/1200 - Güven: %91.23

✓ Tespit: 00:07 (Frame 210) | Güven: %91.23
[INFO] Meta veri çıkartılıyor...
[INFO] Video süresi: 40 saniye, FPS: 30
[INFO] Rapor oluşturuluyor...

✅ ANALIZ TAMAMLANDI
├─ Dosya: drone_video.mp4
├─ Tespit: BULUNDU
├─ Bulunduğu Zaman: 00:07 (210. frame)
├─ Güven: 91.23%
├─ Video Süresi: 40 saniye
├─ FPS: 30.0
└─ Rapor: drone_video_report.xlsx
```

---

## Çoklu Dosya Analizi

```
[2026-04-08 15:00:00] 5 dosya analiz edilecek

[1/5] Analiz başlanıyor: foto_01.jpg
      ✓ Tespit bulundu! Güven: %87.45
      
[2/5] Analiz başlanıyor: foto_02.jpg
      ✗ Tespit bulunamadı
      
[3/5] Analiz başlanıyor: video_01.mp4
      ✓ Tespit: 00:15 | Güven: %92.18
      
[4/5] Analiz başlanıyor: foto_03.jpg
      ✓ Tespit bulundu! Güven: %79.34
      
[5/5] Analiz başlanıyor: video_02.mp4
      ✗ Tespit bulunamadı

=====================================
✅ TOPLU ANALIZ TAMAMLANDI
=====================================
Toplam Dosya: 5
Tespit Bulunan: 3
Başarı Oranı: 60%
Ortalama Güven: 86.32%

Oluşturulan Raporlar:
  ✓ batch_analysis_2026-04-08_150000.xlsx
  ✓ batch_analysis_2026-04-08_150000.json
```

---

## Model Eğitimi Günlükleri

```
[2026-04-08 16:30:00] Model eğitimi başlanıyor

[INFO] Eğitim verisi import ediliyor...
[INFO] 150 resim + 150 label dosyası bulundu
[INFO] Train setine 150 örnek eklendi
[INFO] Dataset YAML oluşturuluyor...
[INFO] Sınıflar: obus (1), toplam sınıf: 1

[INFO] Model eğitimi başlanıyor: yolov8n.pt
[INFO] Epoch 1/50 - Loss: 2.341
[INFO] Epoch 2/50 - Loss: 1.892
[INFO] Epoch 3/50 - Loss: 1.456
...
[INFO] Epoch 50/50 - Loss: 0.234
[INFO] Eğitim tamamlandı!
[INFO] En iyi model kaydedildi: best.pt
[INFO] Model validation mAP: 0.876

✅ MODEL EĞİTİMİ BAŞARILI
├─ Epoch: 50/50
├─ Toplam Eğitim Süresi: 2 saat 15 dakika
├─ Final Loss: 0.234
├─ Validation mAP: 87.60%
└─ Model: training_data/models/custom_howitzer/weights/best.pt
```

---

## Video'dan Frame Çıkarma Günlüğü

```
[2026-04-08 17:00:00] Video Frame Çıkarma başlanıyor

📂 Video işleniyor: field_surveillance_video.mp4
  - Frame Aralığı: Her 5. frame
  - Max Frame: 500
  - Split: train

[INFO] Video açıldı: 1500 frame, 30.0 FPS
[INFO] Frame çıkartılıyor...

Frame çıkartılıyor: 10 ▓▓░░░░░░░ (10%)
Frame çıkartılıyor: 25 ▓▓▓▓▓░░░░ (25%)
Frame çıkartılıyor: 50 ▓▓▓▓▓▓▓▓░░ (50%)
Frame çıkartılıyor: 75 ▓▓▓▓▓▓▓▓▓░ (75%)
Frame çıkartılıyor: 100 ▓▓▓▓▓▓▓▓▓▓ (100%)

✅ Video işleme tamamlandı: 300 frame çıkartıldı!
[INFO] 300 boş label dosyası oluşturuldu
[INFO] Frameler kaydedildi: training_data/datasets/train/images/
[INFO] Label dosyaları: training_data/datasets/train/labels/

📝 Sonraki Adım:
   LabelImg veya CVAT gibi bir annotation aracını kullanarak
   label dosyalarını doldurunuz. Her dosya:
   └─ class_id center_x center_y width height
   Formatında YOLO koordinatları içermelidir.
```

---

## Hata Günlükleri

### ⚠️ Uyarı Örneği

```
[2026-04-08 18:15:30] Analiz başlanıyor: damaged_photo.jpg

[WARNING] UYARI: Dosya bozuk veya okunabilir değil
[INFO] Dosya formatı algılanamıyor, tekrar deneniyor...
[INFO] File başarıyla okunamadı

✗ DOSYA HATASI
└─ Dosya:damaged_photo.jpg açılamadı
   Çözüm: Dosyayı kontrol edin veya başka bir dosya yüklemek deneyin
```

### ❌ Hata Örneği

```
[2026-04-08 18:45:00] Analiz başlanıyor: unsupported_video.avi

[ERROR] Video analiz hatası: Codec desteklenmiyor
[ERROR] Video açılamadı: Video codec desteklenmiyor

❌ VIDEO HATASI
├─ Dosya: unsupported_video.avi
├─ Sorun: Desteklenmeyen codec
└─ Çözüm: MP4, MOV, MKV formatlarına dönüştürün

   OpenCV'nin desteklediği codecler:
     - H.264, H.265 (MP4)
     - MPEG-4 (AVI)
     - VP8, VP9 (WebM)
```

---

## Raporlar

Tüm analizlerden sonra otomatik raporlar oluşturulur:

### 📊 Excel Raporu (XLSX)
```
Sheet 1 - Tespit Özeti
├─ Dosya Adı
├─ Türü (Resim/Video)
├─ Tespit Var Mı
├─ Güven Yüzdesi
├─ Tarih/Zaman
└─ Konum (GPS)

Sheet 2 - Detaylı Sonuçlar
├─ Çerçeve Koordinatları
├─ Meta Veriler
├─ Hatalı Dosyalar
└─ İstatistikler
```

### 📋 JSON Raporu
```json
{
  "analysis_timestamp": "2026-04-08T15:30:45",
  "files_analyzed": 5,
  "detections": [
    {
      "filename": "drone_foto_1.jpg",
      "detected": true,
      "confidence": 0.925,
      "location": "40.7128°N, 74.0060°W",
      "timestamp": "2026-04-08 14:32:15"
    }
  ],
  "summary": {
    "total_files": 5,
    "detected_count": 3,
    "success_rate": 0.60,
    "average_confidence": 0.8632
  }
}
```

---

## 🎯 Önemli Notlar

- Tüm mesajlar **Türkçe** yazılmıştır
- Tespit bulundu = ✓, Tespit bulunamadı = ✗ sembolları kullanılır
- Güven yüzdeleri otomatik hesaplanır (0-100%)
- Video analizinde tüm frameler işlenir (VIDEO_SKIP_FRAMES parametresi ile)
- Progress bar bütün işlemler için gösterilir
- Raporlar otomatik birleştirilmiş formatda kaydedilir

