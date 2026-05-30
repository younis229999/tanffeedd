"""
نظام التصميم (Design System) للواجهة.

يوفّر لوحة ألوان موحّدة، ورقة ستايل عامة عصرية، ودوال مساعدة
(ظلال، بطاقات، بطاقات إحصائية) لمظهر حديث ونظيف.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


# ------------------------------- لوحة الألوان -------------------------------
class C:
    BG = "#EDF1F7"            # خلفية التطبيق
    SURFACE = "#FFFFFF"       # سطح البطاقات
    PRIMARY = "#2563EB"       # اللون الأساسي (أزرق عصري)
    PRIMARY_DARK = "#1D4ED8"
    PRIMARY_DEEP = "#17489A"
    TEXT = "#1F2937"          # نص أساسي
    MUTED = "#6B7280"         # نص ثانوي
    BORDER = "#E5EAF1"        # حدود ناعمة
    TRACK = "#F3F6FB"         # خلفيات خفيفة
    SUCCESS = "#16A34A"
    DANGER = "#DC2626"
    WARNING = "#F59E0B"
    INFO = "#0EA5E9"
    ALT_ROW = "#F7F9FC"       # تظليل صفوف الجدول المتناوب


def add_shadow(widget: QWidget, blur: int = 28, y: int = 6, alpha: int = 38) -> None:
    """إضافة ظل ناعم لإعطاء إحساس الارتفاع (بطاقات حديثة)."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(y)
    effect.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(effect)


def make_card(object_name: str = "card") -> QFrame:
    """إنشاء بطاقة بيضاء بحواف دائرية وظل."""
    card = QFrame()
    card.setObjectName(object_name)
    add_shadow(card)
    return card


def stat_card(title: str, value: str, accent: str = C.PRIMARY) -> QFrame:
    """بطاقة إحصائية: رقم كبير بارز + عنوان + شريط لون جانبي."""
    card = QFrame()
    card.setObjectName("statCard")
    card.setProperty("accent", accent)
    card.setMinimumSize(190, 96)
    card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    add_shadow(card, blur=22, y=4, alpha=30)

    lay = QVBoxLayout(card)
    lay.setContentsMargins(18, 14, 18, 14)
    lay.setSpacing(4)

    val = QLabel(value)
    val.setObjectName("statValue")
    val.setStyleSheet(f"color:{accent}; font-size:26px; font-weight:800;")
    ttl = QLabel(title)
    ttl.setObjectName("statTitle")
    ttl.setStyleSheet(f"color:{C.MUTED}; font-size:12px; font-weight:600;")

    lay.addWidget(val)
    lay.addWidget(ttl)
    # شريط لوني علوي رفيع عبر حد ملوّن.
    card.setStyleSheet(
        f"#statCard {{ background:{C.SURFACE}; border:1px solid {C.BORDER};"
        f" border-radius:16px; border-top:3px solid {accent}; }}"
    )
    return card


# ------------------------------- الستايل العام -------------------------------
def global_stylesheet() -> str:
    return f"""
* {{
    font-family: "Cairo";
    color: {C.TEXT};
}}
QWidget#root {{ background: {C.BG}; }}
QStackedWidget {{ background: transparent; }}

/* ------- البطاقات والمجموعات ------- */
QFrame#card {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: 18px;
}}
QFrame#headerCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {C.PRIMARY_DEEP}, stop:1 {C.PRIMARY});
    border: none;
    border-radius: 18px;
}}
QFrame#footerBar {{
    background: {C.SURFACE};
    border-top: 1px solid {C.BORDER};
    border-radius: 0px;
}}

/* ------- النصوص ------- */
QLabel#appTitle {{ font-size: 21px; font-weight: 800; color: white; }}
QLabel#appSubtitle {{ font-size: 12px; color: #DCE6F7; }}
QLabel#sectionTitle {{ font-size: 15px; font-weight: 700; color: {C.PRIMARY_DEEP}; }}
QLabel#hint {{ color: {C.MUTED}; font-size: 12px; }}
QLabel#footerLine1 {{ color: {C.TEXT}; font-size: 12px; font-weight: 700; }}
QLabel#footerLine2 {{ color: {C.MUTED}; font-size: 11px; font-weight: 600; }}
QLabel#footerLine3 {{ color: {C.PRIMARY}; font-size: 11px; font-weight: 700; }}

/* ------- الأزرار ------- */
QPushButton {{
    background: {C.PRIMARY};
    color: white;
    border: none;
    padding: 10px 18px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 13px;
}}
QPushButton:hover {{ background: {C.PRIMARY_DARK}; }}
QPushButton:pressed {{ background: {C.PRIMARY_DEEP}; }}
QPushButton:disabled {{ background: #BBD0F0; color: #EAF1FB; }}

QPushButton#ghost {{
    background: transparent;
    color: white;
    border: 1px solid rgba(255,255,255,0.55);
}}
QPushButton#ghost:hover {{ background: rgba(255,255,255,0.15); }}

QPushButton#ghostDark {{
    background: {C.SURFACE};
    color: {C.PRIMARY_DEEP};
    border: 1px solid {C.BORDER};
}}
QPushButton#ghostDark:hover {{ background: {C.TRACK}; }}

QPushButton#success {{ background: {C.SUCCESS}; }}
QPushButton#success:hover {{ background: #138A3E; }}

/* ------- التبويبات (شكل مقسّم/حبوب) ------- */
QTabWidget::pane {{ border: none; background: transparent; top: -1px; }}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: {C.TRACK};
    color: {C.MUTED};
    padding: 9px 20px;
    margin-left: 6px;
    border: 1px solid {C.BORDER};
    border-radius: 10px;
    font-weight: 700;
    font-size: 12.5px;
}}
QTabBar::tab:selected {{
    background: {C.PRIMARY};
    color: white;
    border: 1px solid {C.PRIMARY};
}}
QTabBar::tab:hover:!selected {{ background: #E8EEF8; }}

/* ------- الجداول ------- */
QTableWidget {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: 14px;
    gridline-color: transparent;
    alternate-background-color: {C.ALT_ROW};
    selection-background-color: #DCE9FE;
    selection-color: {C.TEXT};
}}
/* ملاحظة: لا نضبط خلفية ::item في الـ QSS كي لا نُلغي ألوان الخلايا
   المضبوطة برمجياً (الخطورة، الصفوف المدموجة). نكتفي بالحشو فقط. */
QTableWidget::item {{ padding: 7px 8px; }}
QHeaderView::section {{
    background: {C.TRACK};
    color: {C.PRIMARY_DEEP};
    padding: 10px 8px;
    border: none;
    border-bottom: 2px solid {C.BORDER};
    font-weight: 800;
    font-size: 12.5px;
}}
QTableCornerButton::section {{ background: {C.TRACK}; border: none; }}
QTableWidget QTableCornerButton::section {{ background: {C.TRACK}; }}

/* ------- الحقول ------- */
QLineEdit, QSpinBox {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: 9px;
    padding: 8px 10px;
    selection-background-color: {C.PRIMARY};
}}
QLineEdit:focus, QSpinBox:focus {{ border: 1px solid {C.PRIMARY}; }}
QListWidget {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: 10px;
    padding: 4px;
}}
QListWidget::item {{ padding: 7px 8px; border-radius: 6px; }}
QListWidget::item:selected {{ background: #DCE9FE; color: {C.TEXT}; }}
QCheckBox {{ spacing: 8px; }}

/* ------- مجموعات الإعدادات ------- */
QGroupBox {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: 14px;
    margin-top: 14px;
    padding: 14px;
    font-weight: 700;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top right;
    right: 14px;
    padding: 0 6px;
    color: {C.PRIMARY_DEEP};
}}

/* ------- أشرطة التمرير ------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px; }}
QScrollBar::handle:vertical {{ background: #CBD5E1; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #94A3B8; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 4px; }}
QScrollBar::handle:horizontal {{ background: #CBD5E1; border-radius: 5px; min-width: 30px; }}

/* ------- التبويبات الداخلية للإعدادات ------- */
QDialog {{ background: {C.BG}; }}
"""
