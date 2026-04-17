# 🚀 Drone Obüs Tespit Sistemi - KURULUM REHBERI

---

## ⚡ HIZLI KURULUM (ÖNERİLEN) - TAM OTOMATİK

**Python 3.10+ kurulu mu?** (Kontrol et: `python --version`)

Evet ise, proje klasörüne git ve çift tıkla:

### Windows Explorer (En Kolay)
1. **`kurulum.bat`** dosyasını çift tıkla
2. Biter, bitti! `python main.py` yazarak uygulamayı çalıştır

### PowerShell (Alternatif)
```powershell
cd "C:\Users\CASPER\OneDrive\Desktop\deneme projesi.v1"
.\kurulum.ps1
```

---

## ⚠️ HEMEN YAPIN - Python Kurulması

### Adım 1: Python Kurulumu
1. **https://www.python.org/downloads/** adresine gidin
2. **Python 3.10 veya 3.11** indirin (Windows için)
3. **Kurulum sırasında ÇOK ÖNEMLİ:**
   - ✅ **"Add Python to PATH"** kutusunu İŞARETLE
   - "Install Now" seç

### Adım 2: Python Yüklendiğini Kontrol Et
PowerShell açın ve yazın:
```powershell
python --version
```
Çıkış: `Python 3.11.x` (sürüm önemli değil)

---

## 📦 Bağımlılıkları Yükleme

### Adım 1: Proje Klasörüne Git
```powershell
cd "C:\Users\CASPER\OneDrive\Desktop\deneme projesi.v1"
```

### Adım 2: Sanal Ortam Oluştur
```powershell
python -m venv venv
```

### Adım 3: Sanal Ortamı Başlat
```powershell
.\venv\Scripts\Activate.ps1
```

**Başarılı olursa bu çıkacak:**
```
(venv) C:\Users\CASPER\OneDrive\Desktop\deneme projesi.v1>
```

### Adım 4: Pip'i Güncelle (Önemli!)
```powershell
python -m pip install --upgrade pip
```

### Adım 5: Bağımlılıkları Yükle (YAVAŞ OLACAK - 5-10 dakika)
```powershell
pip install -r requirements.txt
```

**CİDDEN UZUN SÜREBİLİR. Bitene kadar bekleyin!**

---

## ▶️ Uygulamayı Çalıştırma

Sanal ortam aktifken:
```powershell
python main.py
```

----

## 🆘 Sorunlar ve Çözümleri

### Sorun 1: "Python bulunamadı"
**Çözüm:** Python'u yeniden kur ve PATH'e ekle

### Sorun 2: "pip not found"
**Çözüm:**
```powershell
python -m pip install --upgrade pip
```

### Sorun 3: "torch" URL error
**Çözüm:** İnternet yavaşsa bu normal. Tekrar dene
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Sorun 4: "permission denied"
**Çözüm:** PowerShell'i yönetici olarak aç

### Sorun 5: Sanal ortam aktifleşmiyor
**Çözüm:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

---

## 📋 Kontrol Listesi

- [ ] Python 3.10+ kurulu
- [ ] `python --version` çalışıyor
- [ ] Sanal ortam oluşturuldu (`venv` klasörü var)
- [ ] Sanal ortam aktif (`(venv)` gösteriyor)
- [ ] `pip install -r requirements.txt` başarılı
- [ ] `python main.py` çalışıyor

✅ Tümü tamamlandığında uygulama açılacak!
