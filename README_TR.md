# 🎯 Drone Obüs Tespit Sistemi

Drone görüntülerinde (fotoğraf/video) gizlenmiş obüs modellerini tespit eden, YOLOv8 nesne algılaması kullanan, meta veriler çıkaran ve otomatik raporlar oluşturan profesyonel Python uygulaması.

---

## ⚡ HIZLI BAŞLANGIÇ

**Windows'ta en hızlı kurulum:**

1. **Python 3.10+ yüklü mü?** 
   ```powershell
   python --version
   ```
   
2. **`kurulum.bat` dosyasını çift tıkla** veya PowerShell'de:
   ```powershell
   .\kurulum.ps1
   ```

3. **Bitince, uygulamayı çalıştır:**
   ```
   .\basla.bat
   ```
   
Bitti! GUI açılacak.

---

## ✨ Özellikler

- **🖼️ Çok Format Desteği**: JPEG, PNG resimleri ve MP4 video dosyalarını analiz edin
- **🤖 Gelişmiş Tespit**: Doğru obüs tanımlaması için YOLOv8 sinir ağı (GPU/CPU uyumlu)
- **📍 Meta Veri Çıkarma**: 
  - Resimlerden: EXIF verilerini (tarih, saat, GPS, kamera bilgileri)
  - Videodan: FPS, frame sayısı, çözünürlük, dosya saati
  - Hata işlemesi: Eksik meta verilerde otomatik yedek çözüm
- **⏱️ Video Analizi**: Frame-by-frame analiz, özellik tespit zaman damgası (DD:SS), frame atlama desteği
- **📊 Otomatik Raporlama**: 
  - Excel: Renkli başlıklar, tespit durumu vurgulama, biçimlendirilmiş tablolar
  - JSON: Yapılandırılmış ve detaylı çıktı
- **🎨 Modern GUI**: PyQt5 tabbed arayüzü, ön izleme, kırpı görüntüleyici 
- **🔍 Ayarlanabilir Duyarlılık**: Güven eşiği kaydırıcısı (0-100%)
- **🧠 Model Eğitimi Sekmesi**: Kustom obüs modeli eğitim desteği (video frame çıkarma)
- **📋 Kapsamlı Günlük**: Gerçek zamanlı analiz durumu, otomatik hata ızleme ve işlem takibi
- **✅ Robust Error Handling**: Eksik bağımlılıklar, PyTorch DLL sorunları, dosya hataları gracefully işlenir

## 📋 Gereksinimler

- Python 3.8+
- 8GB RAM önerilir (minimum 4GB)
- CUDA destekli GPU opsiyonel (CPU'ya geri döner)
- Disk alanı: bağımlılıklar için ~500MB + model için ~100MB

## 🚀 Kurulum

### 🤖 Otomatik Kurulum (ÖNERİLEN)

Python 3.10+ kurulu mu? Evet ise:

**Windows Explorer:** `kurulum.bat` dosyasını çift tıkla

**PowerShell:**
```powershell
.\kurulum.ps1
```

Bitince `.\basla.bat` ile uygulamayı başlat

---

### 📖 Ayrıntılı Kurulum Rehberi

Bkz. [KURULUM.md](KURULUM.md) adım-adım talimatlar için

**Not**: Model dosyası bulunamazsa, uygulama genel bir YOLOv8n modelini yedek olarak kullanır.

### 4. Uygulamayı Çalıştırın
```bash
python main.py
```

## 📖 Kullanım Rehberi

### Adım 1: Dosya Yükleyin
1. **"Dosya Seç ve Yükle"** düğmesine tıklayın
2. Bir resim (.jpg, .png) veya video (.mp4) seçin
3. Dosya ön izlemesi otomatik olarak görünür

### Adım 2: Analizi Yapılandırın
- **Güven Eşiği** kaydırıcısını ayarlayın (varsayılan: 0.5)
  - Düşük = daha fazla tespit (yanlış pozitifleri artırır)
  - Yüksek = daha az tespit (doğruluğu artırır)

### Adım 3: Analizi Çalıştırın
1. **"Analizi Başlat"** düğmesine tıklayın
2. Videolar için: frame-by-frame ilerlemeyi görün
3. Sonuçlar **Analiz Sonuçları** panelinde görüntülenir

### Adım 4: Sonuçları İnceleyin
- **Tespit Durumu**: Evet/Hayır göstergesi
- **Güven Puanı**: Tespit güven yüzdesi
- **Çekim Tarihi/Saati**: Dosya meta verisinden
- **GPS Koordinatları**: EXIF'te mevcutsa (sadece fotoğraflar)
- **Tespit Zamanı (DD:SS)**: Videolar için, tespitinin ne zaman olduğunu gösterir

### Adım 5: Sonuçları Dışa Aktarın
- **Kırpıyı Görüntüle**: Kırpılmış tespit bölgesini yeni pencerede göster
- **Excel'e Aktar**: `analysis_report_YYYY-MM-DD_HH-MM-SS.xlsx` kaydeder
- **JSON'a Aktar**: `analysis_report_YYYY-MM-DD_HH-MM-SS.json` kaydeder

Tüm raporlar `./outputs/` dizinine kaydedilir

## 📊 Çıktı Formatları

### Excel Raporu Sütunları
| Sütun | İçerik |
|-------|---------|
| Dosya Adı | Giriş dosyası adı |
| Tespit Durumu | Evet/Hayır |
| Güven Puanı | 0-1 (4 ondalık) |
| Tespit Zamanı (DD:SS) | Sadece video |
| Çekim Tarihi | YYYY-AA-GG |
| Çekim Saati | SS:DD:SS |
| Analiz Tarihi | Rapor tarihi |
| Analiz Saati | Rapor saati |
| Tahmini Mesafe (m) | Uygulanmadı* |
| GPS Enlem | EXIF'ten veya N/A |
| GPS Boylam | EXIF'ten veya N/A |

*Mesafe tahmini drone yüksekliği ve lens özellikleri gerektirir

### JSON Raporu Şeması
```json
{
  "detected": true/false,
  "confidence": 0.0-1.0,
  "time_in_video": "DD:SS",
  "capture_date": "YYYY-AA-GG",
  "capture_time": "SS:DD:SS",
  "analysis_datetime": "ISO zaman damgası",
  "distance_m": null,
  "gps": {
    "lat": 0.0,
    "lon": 0.0
  },
  "crop_image_path": "yol/kırpı.jpg",
  "metadata": {
    "filename": "resim.jpg",
    "file_type": "image/video",
    "capture_source": "exif/file_time"
  }
}
```

## 🗂️ Proje Yapısı

```
howitzer-detector/
├── main.py                          # PyQt5 GUI giriş noktası
├── config.py                        # Yapılandırma ve sabitler
├── requirements.txt                 # Python bağımlılıkları
├── README.md                        # Bu dosya (İngilizce)
├── README_TR.md                     # Türkçe dokümantasyon
│
├── src/
│   ├── __init__.py                 # Paket başlatması
│   ├── detector.py                 # YOLOv8 tespit motoru
│   ├── metadata_extractor.py       # EXIF & video meta verisi
│   ├── report_generator.py         # Excel & JSON dışa aktarma
│   └── utils.py                    # Yardımcı işlevler
│
├── models/
│   └── howitzer_detector.pt        # Özel YOLOv8 modeli (kullanıcı tarafından sağlanır)
│
└── outputs/
    ├── analysis_report_*.xlsx      # Oluşturulan Excel raporları
    ├── analysis_report_*.json      # Oluşturulan JSON raporları
    └── detection_crop_*.jpg        # Kırpılmış tespit resimleri
```

## ⚙️ Yapılandırma

Özelleştirmek için `config.py` dosyasını düzenleyin:

```python
# Model & Tespit
MODEL_PATH = "models/howitzer_detector.pt"
CONFIDENCE_THRESHOLD = 0.5
SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.mp4', ...)

# Dosya Boyutu Limitleri
MAX_IMAGE_SIZE_MB = 100
MAX_VIDEO_SIZE_MB = 500

# Video İşleme
VIDEO_SKIP_FRAMES = 1               # Her frame'i analiz et
VIDEO_PROGRESS_UPDATE_INTERVAL = 10

# GUI
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900
THUMBNAIL_SIZE = (200, 150)
CROP_PADDING = 20

# Çıktı
OUTPUTS_DIR = Path(__file__).parent / "outputs"
EXCEL_SHEET_NAME = "Analiz Sonuçları"
JSON_INDENT = 2

# GPU
USE_GPU = True
```

## 🐛 Sorun Giderme

### Model Bulunamadı
**Hata**: `Model ./models/howitzer_detector.pt adresinde bulunamadı`
- Eğitilmiş model dosyanızı sağlayın
- Veya program otomatik olarak YOLOv8n önceden eğitilmiş modeline geri döner

### CUDA/GPU Sorunları
**Hata**: Model yavaş yükleniyor veya Bellek yetersiz
```bash
# CPU modunu zorla
# config.py'da: USE_GPU = False

# Veya GPU'yu kontrol et
python -c "import torch; print(torch.cuda.is_available())"
```

### EXIF Çıkarılamıyor
**Sorun**: Resimden GPS veya tarih yakalanamıyor
- Dosya değiştirme saatini kullan (otomatik yedek)
- Bazı kameralar GPS gömmez; manuel giriş kullanın
- Fotoğrafın drone/kamera ile GPS tarafından çekilip çekilmediğini kontrol edin

### Video Format Hatası
**Hata**: "Video açılamıyor"
- H.264 codec MP4 dosyalarını kullanın
- FFmpeg ile dönüştürün: `ffmpeg -i input.mp4 -c:v libx264 output.mp4`

### Excel Dışa Aktarma Hatası
**Hata**: outputs/ dosyasına yazma izni reddedildi
- `outputs/` dizininin var olduğundan ve yazılabilir olduğundan emin olun
- Önceki çalışmalardan açık Excel dosyalarını kapatın

## 📈 Performans

| Görev | Zaman | Donanım |
|-------|-------|---------|
| Modeli Yükle | 2-3s | CPU/GPU |
| Tek Resim | < 2s | GPU |
| Tek Resim | 5-10s | CPU |
| 30fps 1min Video | 30-40s | GPU |
| 30fps 1min Video | 120s+ | CPU |

## 🔮 Gelecek Geliştirmeler

- [ ] Drone yüksekliği girdisiyle mesafe tahmini
- [ ] Toplu işleme (birden çok dosya)
- [ ] Özel model eğitim arayüzü
- [ ] Gerçek zamanlı drone beslemeleri analizi
- [ ] GIS entegrasyonu ve harita gösterimi
- [ ] Gelişmiş yanlış pozitif filtreleme
- [ ] Çoklu nesne kırpılması
- [ ] Video akışı desteği

## 📝 Lisans

Askeri/güvenlik uygulamaları için lisans gereksinimlerini kontrol edin.

## 🤝 Katkı

Tespiti iyileştirmek için:
1. Yanlış pozitif/negatif örnekleri toplayın
2. Genişletilmiş veri seti ile modeli yeniden eğitin
3. `models/howitzer_detector.pt` dosyasını güncelleyin

## 📞 Destek

Sorunlar veya sorular için:
1. Ayrıntılı hata mesajları için `./log.txt` kontrol edin
2. `config.py`'da ayrıntılı günlüğü etkinleştirin
3. Bağımlılıkları doğrulayın: `pip list`
4. Örnek resim/video ile test edin

---

**Sürüm**: 1.0  
**Son Güncelleme**: 2024-01-15  
**Geliştiren**: AI Geliştirme Ekibi
