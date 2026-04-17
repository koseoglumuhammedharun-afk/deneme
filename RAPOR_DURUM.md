# 🎯 Drone Obüs Tespit Sistemi - Durumu ve Sorun Raporu

**Tarih:** 8 Nisan 2026  
**Python Sürümü:** 3.10.11  
**Durum:** ✅ Geliştirilmiş, İyileştirilmiş ve Türkçeleştirilmiş

---

## 📋 Özet
Uygulamada pip ve YOLO 8 ile ilgili hatalar bulundu ve çözüldü. Video dosyalarından direkt frame çıkartan yeni bir özellik eklendi. **Tüm analiz günlüğü mesajları Türkçeye çevrildi.** Sistem şu anda tam olarak çalışır durumda ve tam Türkçe arayüze sahiptir.

---

## 🔍 Sorunlar ve Çözümleri

### ❌ Problem 1: PyTorch DLL Yükleme Hatası
**Hata Mesajı:**
```
OSError: [WinError 1114] Error loading c10.dll or one of its dependencies
```

**Sebep:**
- PyTorch CPU sürümü Windows'ta DLL bağımlılığı sorununa neden oldu
- YOLO ve torch-dependent modüllerin sıralı imports'unda sorun çıktı

**Çözüm:**
- ✅ Visual C++ Redistributable (Microsoft.VCRedist.2015+.x64) kuruldu
- ✅ PyTorch CPU resmi index'ten kuruldu: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`
- ✅ Hata yakalama sistemi geliştirildi (`OSError` exception handling eklendi)
- ✅ Uygulama YOLO yüklenemese bile GUI'de başlamayı sürdürür

### ❌ Problem 2: torchvision Modülü Eksik
**Hata Mesajı:**
```
ModuleNotFoundError: No module named 'torchvision'
```

**Sebep:**
- Ultralytics SAM modeli torchvision'a ihtiyaç duyor
- torchvision kurulu değildi

**Çözüm:**
- ✅ `pip install torchvision --index-url https://download.pytorch.org/whl/cpu` kuruldu

### ❌ Problem 3: ObjectDetector vs HowitzerDetector Sınıf Adı Karışıklığı
**Hata Mesajı:**
```
ImportError: cannot import name 'ObjectDetector' from 'src.detector'
```

**Sebep:**
- Doğru sınıf adı `HowitzerDetector`, ama docstring/test'te `ObjectDetector` kullanılıyor

**Çözüm:**
- ✅ Doğru sınıf adı `HowitzerDetector` kullanıldı

---

## 📦 Kurulu Paketler (Python 3.10.11)

| Paket | Sürüm | Durum |
|-------|-------|-------|
| PyQt5 | 5.15.11+ | ✅ Kurulu |
| pandas | 2.3.3 | ✅ Kurulu |
| openpyxl | 3.1.5 | ✅ Kurulu |
| opencv-python | 4.13.0 | ✅ Kurulu |
| Pillow | 12.2.0 | ✅ Kurulu |
| PyTorch | 2.11.0+cpu | ✅ Kurulu |
| torchvision | 0.26.0+cpu | ✅ Kurulu |
| ultralytics | (latest) | ✅ Kurulu |
| exifread | 3.5.1 | ✅ Kurulu |
| numpy | 2.2.6 | ✅ Kurulu |
| PyYAML | 6.0.3 | ✅ Kurulu |

---

## 🚀 Uygulamanın Mevcut Durumu

### Çalışan Özellikler ✅

#### 1. **Obüs Tespit Sistemi (YOLO-tabanlı)**
- Resim dosyalarından obüs tespiti
- Video dosyalarından frame-by-frame tespit
- Güven eşiği dinamik ayarı (slider ile)
- GPU ve CPU desteği

#### 2. **Meta Veri Çıkarma**
- EXIF verisi (fotoğraflardan: konum, tarih, kamera bilgileri)
- Video meta verisi (süre, FPS, boyut vb.)
- Tespit sonuçları ile birleştirilmiş rapor

#### 3. **Rapor Oluşturma**
- **Excel (.xlsx) Rapor:** Tüm tespit sonuçları, meta veri, statistics
- **JSON Rapor:** Makine tarafından okunabilir format

#### 4. **Model Eğitim Sistemi**
- YOLO v8 custom model eğitimi
- Resim ve label upload
- **YENİ: Video'dan direkt frame çıkarma**

#### 5. **Grafik Arayüz (PyQt5)**
- 2 sekme tabanlı tasarım:
  - **Analiz Sekmesi:** Dosya yükleme, tespit, rapor
  - **Model Eğitim Sekmesi:** Veri import, eğitim ayarları, progress
- Modern styling (renkli, hover effects, rounded buttons)
- Turkish (Türkçe) arayüz

---

## 🎬 YENİ ÖZELLİK: Video'dan Frame Çıkarma

### What / Ne İşe Yarıyor?
Video dosyasından otomatik olarak eğitim için frame'ler çıkarır.

### How / Nasıl Kullanılır?

1. **Model Eğitim Sekmesine Git**
2. **"🎬 Video'dan Frame Çıkar" Butonuna Tıkla**
3. **Video dosyasını seç** (MP4, AVI, MOV, MKV, FLV)
4. **Ayarları Belirle:**
   - **Frame Aralığı:** Her kaçıncı frame'i çıkartacağı (5 = her 5. frame)
   - **Maksimum Frame Sayısı:** Kaç frame çıkartacağı (0 = sınırsız)
   - **Dataset Split:** train/val/test kategorisi
5. **OK'ye Basınca:**
   - ✅ Video işlenir
   - ✅ Frameler otomatik kaydedilir
   - ✅ Boş label dosyaları oluşturulur (daha sonra annotation aracıyla doldurulacak)

### Örnek Kullanım
- 20 dakikalık bir drone videosu var
- Her 5. frame çıkartmak istiyorum (çok yük azaltmak için)
- Maksimum 500 frame olsun
- Ayarlar:
  - Frame Aralığı: 5
  - Maksimum Frame: 500
  - Split: train

**Sonuç:** ~500 frame otomatik çıkartıldı, boş label dosyaları oluşturuldu!

---

## 🔧 Teknik Detaylar

### Video Frame Extraction
```python
# ModelTrainer sınıfında yeni metod
extract_frames_from_video(
    video_path: str,
    frame_interval: int = 5,        # Her N. frame
    max_frames: Optional[int] = None,  # Maksimum frame sayısı
    dataset_split: str = 'train'    # train/val/test
) -> Tuple[int, List[str]]
```

### Destekelenen Video Formatları
- MP4 (H.264, H.265)
- AVI (MPEG-4, XviD)
- MOV (QuickTime)
- MKV (Matroska)
- FLV (Flash Video)

---

## 📊 Uygulama Mimarisi

```
Drone Obüs Tespit Sistemi
├── main.py                    # PyQt5 GUI (2 sekme)
├── config.py                  # Yapılandırma
├── src/
│   ├── detector.py           # YOLOv8 tespit motoru
│   ├── metadata_extractor.py # EXIF + video meta
│   ├── report_generator.py   # Excel/JSON rapor
│   ├── model_trainer.py      # Model eğitim + VIDEO FRAME EXTRACTION
│   └── utils.py              # Yardımcı fonksiyonlar
├── models/                    # Eğitilmiş .pt dosyaları
├── training_data/             # Eğitim veri seti
├── outputs/                   # Oluşturulan raporlar
└── .github/copilot-instructions.md
```

---

## ⚠️ Bilinen Sınırlamalar

1. **YOLO Model Yükleme:**
   - PyTorch DLL sorunları Windows'ta nadiren meydana gelebilir
   - Çözüm: Uygulama yine de başlar, YOLO olmadan (detection özelliği devre dışı)

2. **Video Frame Çıkarma:**
   - Çok uzun videolar bellek tüketebilir
   - Çözüm: `max_frames` parametresi ile limitleyin

3. **Annotation Eksikliği:**
   - Çıkartılan frameler için dış annotation aracı gerekli (LabelImg, CVAT vb.)
   - Boş label dosyaları otomatik oluşturulur, ama manuel doldurmak gerekir

4. **GPU Desteği:**
   - PyTorch CPU kurulu (CUDA yok)
   - Çözüm: CUDA 11.8+ ile `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`

---

## 🎯 Sonral İyileştirmeler (İsteğe Bağlı)

- [ ] Otomatik annotation (bounding box suggestion) ile yardımcı sahne analizi
- [ ] Batch video işleme (birden çok video aynı anda)
- [ ] Frame quality filtering (blurlu/kötü frameler otomatik filtreleme)
- [ ] GUI'de video preview ve timeline
- [ ] Augmentation seçenekleri (rotation, flip vb.)

---

## 🚀 Başlatma

### Komut Satırından
```bash
cd "C:\Users\CASPER\OneDrive\Desktop\deneme projesi.v1"
.\venv\Scripts\python main.py
```

### Batch Dosyası ile
```bash
.\basla.bat
```

### PowerShell Script ile
```powershell
.\basla.ps1
```

---

## ✅ Test Kontrol Listesi

- [x] PyTorch başarıyla yükleniyor
- [x] YOLO modeli başarıyla yükleniyor
- [x] GUI 2 sekme ile açılıyor
- [x] Resim analizi çalışıyor
- [x] Video analizi çalışıyor
- [x] Meta veri çıkarma çalışıyor
- [x] Excel rapor oluşturuluyor
- [x] JSON rapor oluşturuluyor
- [x] Model eğitim UI yanıt veriyor
- [x] **YENİ: Video'dan frame çıkarma çalışıyor**
- [x] Label dosyaları otomatik oluşturuluyor

---

## 📝 Notlar

- Tüm kodlar Turkish (Türkçe) açıklamalar içeriyor
- UTF-8 encoding kullanılıyor (Türkçe karakterler destekli)
- Error handling kapsamlı (hata mesajları Türkçe)
- GUI responsive ve thread-safe

---

## 🎓 Örnek Workflow

1. **Drone'dan video çek**
2. **Uygulamayı aç** → Model Eğitim Sekmesi
3. **Video'dan frame çıkar** → 🎬 butonunda
4. **Dış tool'da (LabelImg) frameler'i annotate et** (bounding box)
5. **Annotate edilmiş frameler'i uygulamaya yükle** → 📷 ve 🏷️ butonları
6. **Model eğitimini başlat** → 🚀 butonu
7. **Eğitilmiş model otomatik kaydedilir** → Analiz'de kullanılabilir
8. **Yeni videolar'da analiz et** → Analiz Sekmesi

---

## 📞 Sorun Giderme

### Q: Video yüklemiyor?
**A:** Dosya formatı desteklenen sürümde mi kontrol edin (MP4, AVI, MOV, MKV, FLV)

### Q: Frame'ler çıkmıyor?
**A:** OpenCV kurulu mu kontrol edin: `pip list | find "opencv"`

### Q: YOLO model yüklemiyor?
**A:** ultralytics kurulu mu kontrol edin: `pip list | find "ultralytics"`

### Q: Hata mesajı görüyor?
**A:** `config.py`'de `LOG_LEVEL = "DEBUG"` yapıp detaylı log'ları görebilirsiniz

---

**Son Güncelleme:** 8 Nisan 2026  
**Durum:** ✅ Üretim Hazır (Production Ready)
