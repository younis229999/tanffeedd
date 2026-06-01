"""
نقطة تشغيل التطبيق.

يضبط اتجاه الواجهة من اليمين لليسار (RTL)، ويحمّل خطاً عربياً عصرياً (Cairo)،
ثم يفتح النافذة الرئيسية بثيم حديث.
"""

from __future__ import annotations

import sys
from pathlib import Path

# دعم التشغيل المباشر (python main.py) والتشغيل كحزمة.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from core.logger import get_logger
from ui.main_window import MainWindow
from ui.theme import global_stylesheet


def _fonts_dir() -> Path:
    return Path(__file__).resolve().parent / "assets" / "fonts"


def load_fonts(app: QApplication) -> None:
    """تحميل خط Cairo العصري للواجهة (مع تضمين Amiri للـ PDF أيضاً)."""
    family = "Segoe UI"  # احتياطي على ويندوز.
    fonts_dir = _fonts_dir()
    for fname, is_ui in [("Cairo.ttf", True), ("Amiri.ttf", False)]:
        fpath = fonts_dir / fname
        if fpath.exists():
            fid = QFontDatabase.addApplicationFont(str(fpath))
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams and is_ui:
                family = fams[0]
    font = QFont(family, 11)
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)


# للحفاظ على التوافق مع نقاط الاستدعاء القديمة.
load_arabic_font = load_fonts
APP_STYLE = global_stylesheet()


def main() -> int:
    logger = get_logger()
    logger.info("بدء تشغيل التطبيق")

    app = QApplication(sys.argv)
    app.setApplicationName("altanfith")
    # اتجاه الواجهة من اليمين لليسار.
    app.setLayoutDirection(Qt.RightToLeft)
    load_fonts(app)
    app.setStyleSheet(global_stylesheet())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
