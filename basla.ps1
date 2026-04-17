# Drone Obüs Tespit Sistemi - Uygulama Başlatıcı

# UTF-8 Encoding'i ayarla (Türkçe karakter desteği için)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "    🚀 DRONE OBÜS TESPIT SISTEMI" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Sanal ortam kontrol et
if (!(Test-Path "venv")) {
    Write-Host "❌ Sanal ortam bulunamadı!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Lütfen önce kurulum.bat veya kurulum.ps1'i çalıştırın" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Devam etmek için Enter tuşuna basın"
    exit 1
}

# Sanal ortamı etkinleştir
Write-Host "Sanal ortam etkinleştiriliyor..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

# Uygulamayı başlat
Write-Host "Uygulama başlatılıyor..." -ForegroundColor Green
Write-Host ""

& python main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Uygulama başlatılamadı" -ForegroundColor Red
    Write-Host ""
    Write-Host "Olası çözümler:" -ForegroundColor Yellow
    Write-Host "  1. Sanal ortamı kontrol et: venv klasörü var mı?" -ForegroundColor Yellow
    Write-Host "  2. Bağımlılıkları yeniden yükle: pip install -r requirements.txt" -ForegroundColor Yellow
    Write-Host "  3. test_dependencies.py'i çalıştır: python test_dependencies.py" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Devam etmek için Enter tuşuna basın"
    exit 1
}
