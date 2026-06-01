# -*- mode: python ; coding: utf-8 -*-
"""
إعداد PyInstaller لإنتاج ملف تنفيذي واحد (.exe) لويندوز.

طريقة الاستخدام (على جهاز ويندوز فيه Python والمتطلبات مثبّتة):
    pip install -r requirements.txt
    pyinstaller build.spec

سيُنتج الملف في مجلد dist/SalaryProcessor.exe ويعمل دون تنصيب Python.
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # تضمين الخط العربي وملف الإعدادات داخل الملف التنفيذي.
    datas=[
        ('assets/fonts/Amiri.ttf', 'assets/fonts'),
        ('config/settings.json', 'config'),
    ],
    hiddenimports=[
        'arabic_reshaper',
        'bidi',
        'bidi.algorithm',
        'openpyxl',
        'reportlab.graphics.barcode',
        'fitz',
        'pymupdf',
        'PySide6.QtPrintSupport',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SalaryProcessor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # تطبيق نافذي بلا نافذة طرفية.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/app.ico',   # أضِف أيقونة إن رغبت.
)
