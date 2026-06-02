# -*- mode: python ; coding: utf-8 -*-
"""
إعداد PyInstaller لإنتاج ملف تنفيذي واحد (.exe) لويندوز.

طريقة الاستخدام (على جهاز ويندوز فيه Python والمتطلبات مثبّتة):
    pip install -r requirements.txt
    pyinstaller build.spec

سيُنتج الملف في مجلد dist/altanfith.exe ويعمل دون تنصيب Python.
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # تضمين الخط العربي وملف الإعدادات داخل الملف التنفيذي.
    datas=[
        ('assets/fonts/Amiri.ttf', 'assets/fonts'),
        ('assets/fonts/Cairo.ttf', 'assets/fonts'),
        ('assets/images/logo.jpg', 'assets/images'),
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
    # استبعاد وحدات Qt الضخمة غير المستخدمة (تسريع الإقلاع وتصغير الحجم بشكل كبير).
    excludes=[
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineQuick', 'PySide6.QtWebChannel',
        'PySide6.QtQuick', 'PySide6.QtQuick3D', 'PySide6.QtQml',
        'PySide6.QtQmlModels', 'PySide6.QtQuickWidgets',
        'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput',
        'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras', 'PySide6.Qt3DLogic',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization',
        'PySide6.QtDesigner', 'PySide6.QtUiTools', 'PySide6.QtTest',
        'PySide6.QtSql', 'PySide6.QtBluetooth', 'PySide6.QtNfc',
        'PySide6.QtSerialPort', 'PySide6.QtSensors', 'PySide6.QtPositioning',
        'PySide6.QtLocation', 'PySide6.QtWebSockets', 'PySide6.QtScxml',
        'tkinter', 'matplotlib', 'scipy', 'PyQt5', 'PyQt6', 'IPython',
    ],
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
    name='altanfith',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # إطفاء UPX: إقلاع أسرع وتقليل إنذارات مكافح الفيروسات.
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # تطبيق نافذي بلا نافذة طرفية.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/images/logo.ico',   # أيقونة البرنامج (شعار الوزارة).
)
