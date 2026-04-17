# 🚀 BAŞLANGÇIÇ

## 1. İlk Defa Kurulum Yapacaksan

### Windows Explorer (Çift Tık - Hepsi Bu!)

Proje klasöründe `kurulum.bat` dosyasını çift tıkla.
- Sanal ortamı oluşturur
- Tüm bağımlılıkları yükler
- Tamamen otomatik

### PowerShell Alternatifi

```powershell
cd "C:\Users\CASPER\OneDrive\Desktop\deneme projesi.v1"
.\kurulum.ps1
```

---

## 2. Uygulamayı Çalıştırma

Kurulum bittikten sonra **proje klasörüne git** ve çift tıkla:

### `basla.bat` ← EN KOLAY

Veya PowerShell'de:
```powershell
.\basla.ps1
```

---

## 3. Uygulamayı Kullanma

GUI açıldığında:

1. **Dosya Seç** → Drone fotoğrafı veya video seç
2. **Başla** → Tespit analizi başlar
3. **Sonuçlar** → Tespit edilen obüsleri gösterir
4. **Excel/JSON** → Rapor oluştur

---

## 4. Sorun Mu Var?

### "kurulum.bat çalışmıyor"
- Python yüklü mü? `python --version` kontrol et
- Python'u https://python.org adresinden yükle

### "basla.bat çalışmıyor"
- Kurulum bitmiş mi?
- Sanal ortam oluşturulmuş mu? (`venv` klasörü var mı?)

### "Başka Sorunlar"
Bkz. [KURULUM.md](KURULUM.md) sorun çözüm bölümü

---

## 5. Bilgisayarın Iyiyse Bilmen Gereken Şey

- 🔴 **Birinci Defa**: kurulum.bat → 5-10 dakika
- ♻️ **Sonraki Defalar**: basla.bat → 30 saniye
- 🖥️ **Gereksinimler**: Python 3.10+, 4GB RAM, 500MB disk
- ⚙️ **GPU**: Kuruluysa otomatik kullanır, yoksa CPU çalışır

---

**Hepsi bu! İyi çalışmalar.** 🎯
