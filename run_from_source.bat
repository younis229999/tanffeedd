@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   معالج ملفات التوطين - تشغيل من المصدر
echo ============================================
echo.
echo [1/2] تثبيت المتطلبات (يحتاج إنترنت أول مرة فقط)...
python -m pip install -r requirements.txt
echo.
echo [2/2] تشغيل التطبيق...
python main.py
echo.
pause
