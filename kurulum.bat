@echo off
REM Drone Obüs Tespit Sistemi - Otomatik Kurulum Scripti

echo.
echo ================================================================================
echo     🚀 DRONE OBÜS TESPIT SISTEMI - KURULUM
echo ================================================================================
echo.

REM Python kontrol et
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python bulunamadı!
    echo.
    echo Lütfen Python 3.10+ kurun: https://www.python.org/downloads/
    echo Kurulum sırasında "Add Python to PATH" kutusunu işaretleyin.
    echo.
    pause
    exit /b 1
)

echo ✓ Python bulundu
python --version

echo.
echo ================================================================================
echo     📦 ADIM 1: SANAl ORTAM OLUŞTURULUYOR
echo ================================================================================
echo.

if exist venv (
    echo ⚠ Sanal ortam zaten var. Kullanılıyor...
) else (
    echo Sanal ortam oluşturuluyor...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ❌ Sanal ortam oluşturulamadı
        pause
        exit /b 1
    )
    echo ✓ Sanal ortam oluşturuldu
)

echo.
echo ================================================================================
echo     🔄 ADIM 2: SANAl ORTAM ETKINLEŞTIRILIYOR
echo ================================================================================
echo.

call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ❌ Sanal ortam etkinleştirilemedi
    pause
    exit /b 1
)

echo ✓ Sanal ortam etkinleştirildi

echo.
echo ================================================================================
echo     ⬆️ ADIM 3: PIP GÜNCELLENİYOR
echo ================================================================================
echo.

python -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo ⚠ Pip güncellemesinde sorun oldu (devam ediliyor)
)

echo ✓ Pip hazır

echo.
echo ================================================================================
echo     📥 ADIM 4: BAĞIMLILIKLARI YÜKLEMEYİ BAŞLATIYOR
echo ================================================================================
echo.
echo ⏳ Bu 5-10 dakika sürebilir. Lütfen bekleyin...
echo.

pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ❌ Bağımlılıkları yüklemede sorun oldu
    echo.
    echo Lütfen şunu deneyin:
    echo   1. İnternet bağlantınızı kontrol edin
    echo   2. Komutu tekrar çalıştırın
    echo   3. Sorun devam ederse, torch'u SSL hatasısı yoksa atla:
    echo      pip install -r requirements.txt --no-deps
    echo.
    pause
    exit /b 1
)

echo.
echo ✓ Tüm bağımlılıklar yüklendi

echo.
echo ================================================================================
echo     ✅ KURULUM TAMAMLANDI!
echo ================================================================================
echo.
echo Uygulamayı çalıştırmak için şunu yazın:
echo.
echo     python main.py
echo.
echo Not: Sanal ortam her zaman aktif olmalıdır
echo.
pause
