# RTX 3060 GPU Kurulum Kılavuzu

## Mevcut Durum

- ✅ Donanım: NVIDIA GeForce RTX 3060 mevcut
- ✅ Hedef kurulum: PyTorch 2.5.1 + CUDA 12.1 wheel
- ❌ Mevcut Python ortamı temiz değil
- ❌ `pip list` ile `import torch` çıktısı birbiriyle uyuşmuyor
- ❌ Bu nedenle uygulama şu anda CPU moduna düşüyor

## Sorunun Özeti

Şu an sistemde asıl problem ekran kartı değil, Python ortamının bozulmuş olmasıdır.

Örnek tutarsızlık:
- `pip list` → `torch 2.5.1+cu121`
- `python -c "import torch; print(torch.__version__)"` → `2.11.0+cpu`

Bu durumda uygulama GPU kullanmaz.

---

## Doğru Yaklaşım

Bu proje için en güvenli yöntem:

1. Mevcut `venv` klasörünü sil
2. Yeni bir sanal ortam oluştur
3. CUDA'lı PyTorch wheel'i resmi PyTorch index'inden kur
4. Diğer paketleri ayrıca kur
5. `torch.cuda.is_available()` ile doğrula

---

## Adım 1: Eski Ortamı Temizle

PowerShell:

```powershell
cd C:\Users\CASPER\Desktop\drone_detection
deactivate
Remove-Item -Recurse -Force .\venv