@echo off
REM Drone Obüs Tespit Sistemi - Uygulama Başlatıcı

echo.
echo ================================================================================
echo     🚀 DRONE OBÜS TESPIT SISTEMI
echo ================================================================================
echo.

REM Sanal ortam kontrol et
if not exist venv (
    echo ❌ Sanal ortam bulunamadı!
    echo.
    echo Lütfen önce kurulum.bat'ı çalıştırın
    echo.
    pause
    exit /b 1
)

REM Sanal ortamı etkinleştir
call venv\Scripts\activate.bat

REM Uygulamayı başlat
echo Uygulama başlatılıyor...
echo.
python main.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ Uygulama başlatılamadı
    echo.
    echo Olası çözümler:
    echo   1. Sanal ortamı kontrol et: venv klasörü var mı?
    echo   2. Bağımlılıkları yeniden yükle: pip install -r requirements.txt
    echo   3. test_dependencies.py'i çalıştır: python test_dependencies.py
    echo.
    pause
    exit /b 1
)

