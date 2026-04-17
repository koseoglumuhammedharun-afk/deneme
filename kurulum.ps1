# Drone Obüs Tespit Sistemi - Otomatik Kurulum Scripti

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "    🚀 DRONE OBÜS TESPIT SISTEMI - KURULUM" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Python kontrol et
try {
    $pythonVersion = & python --version 2>&1
    Write-Host "✓ Python bulundu: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python bulunamadı!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Lütfen Python 3.10+ kurun: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Kurulum sırasında 'Add Python to PATH' kutusunu işaretleyin." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Devam etmek için Enter tuşuna basın"
    exit 1
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "    📦 ADIM 1: SANAL ORTAM OLUŞTURULUYOR" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path "venv") {
    Write-Host "⚠ Sanal ortam zaten var. Kullanılıyor..." -ForegroundColor Yellow
} else {
    Write-Host "Sanal ortam oluşturuluyor..." -ForegroundColor Cyan
    & python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Sanal ortam oluşturulamadı" -ForegroundColor Red
        Read-Host "Devam etmek için Enter tuşuna basın"
        exit 1
    }
    Write-Host "✓ Sanal ortam oluşturuldu" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "    🔄 ADIM 2: SANAL ORTAM ETKINLEŞTIRILIYOR" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

& ".\venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Sanal ortam etkinleştirilemedi" -ForegroundColor Red
    Read-Host "Devam etmek için Enter tuşuna basın"
    exit 1
}

Write-Host "✓ Sanal ortam etkinleştirildi" -ForegroundColor Green

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "    ⬆️ ADIM 3: PIP GÜNCELLENİYOR" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

& python -m pip install --upgrade pip --quiet

Write-Host "✓ Pip hazır" -ForegroundColor Green

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "    📥 ADIM 4: BAĞIMLILIKLARI YÜKLEMEYİ BAŞLATIYOR" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "⏳ Bu 5-10 dakika sürebilir. Lütfen bekleyin..." -ForegroundColor Yellow
Write-Host ""

& pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Bağımlılıkları yüklemede sorun oldu" -ForegroundColor Red
    Write-Host ""
    Write-Host "Lütfen şunu deneyin:" -ForegroundColor Yellow
    Write-Host "  1. İnternet bağlantınızı kontrol edin" -ForegroundColor Yellow
    Write-Host "  2. Komutu tekrar çalıştırın" -ForegroundColor Yellow
    Write-Host "  3. Sorun devam ederse, requirements.txt'deki sıradaki paketi kontrol edin" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Devam etmek için Enter tuşuna basın"
    exit 1
}

Write-Host ""
Write-Host "✓ Tüm bağımlılıklar yüklendi" -ForegroundColor Green

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "    ✅ KURULUM TAMAMLANDI!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Uygulamayı çalıştırmak için şunu yazın:" -ForegroundColor Cyan
Write-Host ""
Write-Host "    python main.py" -ForegroundColor Green
Write-Host ""
Write-Host "Not: Sanal ortam her zaman aktif olmalıdır" -ForegroundColor Yellow
Write-Host ""
