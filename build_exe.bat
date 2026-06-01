@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   بناء الملف التنفيذي (.exe) لويندوز
echo ============================================
echo.
echo [1/3] تحديث pip...
python -m pip install --upgrade pip
echo.
echo [2/3] تثبيت المتطلبات...
python -m pip install -r requirements.txt
echo.
echo [3/3] بناء altanfith.exe ...
pyinstaller build.spec --noconfirm
echo.
echo ============================================
echo   تم! الملف التنفيذي موجود في:
echo   dist\altanfith.exe
echo ============================================
echo انسخ هذا الملف إلى أي حاسبة ويندوز وشغّله مباشرة.
echo.
pause
