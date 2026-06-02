"""
النافذة الرئيسية.

تصميم حديث: ترويسة متدرّجة اللون + منطقة محتوى بطاقية + تذييل ظاهر دائماً.
التسلسل: اختيار الملف ← معاينة في جدول ← زر «معالجة» ← شاشة النتائج.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.excel_loader import ExcelLoadError, LoadedData, load_excel
from core.logger import get_logger
from core.processor import process_loaded
from core.settings import Settings
from ui.results_view import ResultsView
from ui.search_view import SearchView
from ui.settings_dialog import SettingsDialog
from ui.theme import C, asset_path, make_card


class MainWindow(QWidget):
    """النافذة الرئيسية للتطبيق."""

    def __init__(self):
        super().__init__()
        self.logger = get_logger()
        self.settings = Settings()
        self.loaded: LoadedData | None = None

        self.setWindowTitle("altanfith")
        self.setObjectName("root")
        self.resize(1200, 820)
        self.setMinimumSize(980, 680)

        self._build_ui()

    # ------------------------------ بناء الواجهة ------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 0)
        root.setSpacing(14)

        root.addWidget(self._build_header())

        # حاوية متبدّلة: صفحة المعاينة وصفحة النتائج.
        self.stack = QStackedWidget()
        root.addWidget(self.stack, stretch=1)

        self.stack.addWidget(self._build_preview_page())   # index 0
        self.results_view = ResultsView(self.settings)
        self.results_view.back_requested.connect(lambda: self.stack.setCurrentIndex(0))
        self.stack.addWidget(self.results_view)             # index 1

        self.search_view = SearchView(self.settings)
        self.search_view.back_requested.connect(lambda: self.stack.setCurrentIndex(0))
        self.stack.addWidget(self.search_view)              # index 2

        root.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        card = QFrame()
        card.setObjectName("headerCard")
        card.setFixedHeight(92)
        from ui.theme import add_shadow
        add_shadow(card, blur=30, y=8, alpha=55)

        lay = QHBoxLayout(card)
        lay.setContentsMargins(24, 12, 24, 12)
        lay.setSpacing(14)

        # الشعار (أقصى اليمين في RTL).
        logo = asset_path("assets", "images", "logo.jpg")
        if logo.exists():
            from PySide6.QtGui import QPixmap
            pix = QPixmap(str(logo)).scaledToHeight(58, Qt.SmoothTransformation)
            logo_lbl = QLabel()
            logo_lbl.setPixmap(pix)
            lay.addWidget(logo_lbl)

        # العنوان (يمين في RTL).
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("altanfith")
        title.setObjectName("appTitle")
        subtitle = QLabel("تنظيف • تحقق • دمج المكررات • تقرير احترافي")
        subtitle.setObjectName("appSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        lay.addLayout(titles)

        lay.addStretch(1)

        # أزرار الإجراءات (يسار).
        self.btn_open = QPushButton("📂  اختيار ملف Excel")
        self.btn_open.setObjectName("ghost")
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self.on_open)
        self.btn_search = QPushButton("🔎  الكشف والبحث")
        self.btn_search.setObjectName("ghost")
        self.btn_search.setCursor(Qt.PointingHandCursor)
        self.btn_search.clicked.connect(self.on_open_search)
        self.btn_settings = QPushButton("⚙  الإعدادات")
        self.btn_settings.setObjectName("ghost")
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.clicked.connect(self.on_settings)
        lay.addWidget(self.btn_open)
        lay.addWidget(self.btn_search)
        lay.addWidget(self.btn_settings)
        return card

    def _build_footer(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("footerBar")
        bar.setFixedHeight(70)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(1)

        lines = self.settings.footer_lines  # [المديرية, شعبة الحاسبة, @Younis shaker]
        self.footer_labels = []
        for i, text in enumerate(lines):
            lbl = QLabel(text)
            lbl.setObjectName(f"footerLine{i + 1}")
            lbl.setAlignment(Qt.AlignCenter)
            lay.addWidget(lbl)
            self.footer_labels.append(lbl)
        return bar

    def _refresh_footer(self) -> None:
        for lbl, text in zip(self.footer_labels, self.settings.footer_lines):
            lbl.setText(text)

    def _build_preview_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        card = make_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        head = QHBoxLayout()
        sec = QLabel("معاينة البيانات قبل المعالجة")
        sec.setObjectName("sectionTitle")
        head.addWidget(sec)
        head.addStretch(1)
        self.lbl_file = QLabel("لم يتم اختيار ملف بعد — اضغط «اختيار ملف Excel».")
        self.lbl_file.setObjectName("hint")
        head.addWidget(self.lbl_file)
        layout.addLayout(head)

        self.preview_table = QTableWidget(0, 4)
        self.preview_table.setHorizontalHeaderLabels(
            ["رقم الإضبارة (A)", "المبلغ (E)", "الاسم (H)", "الآيبان (I)"]
        )
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview_table.setShowGrid(False)
        layout.addWidget(self.preview_table, stretch=1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.btn_process = QPushButton("▶  بدء المعالجة")
        self.btn_process.setObjectName("success")
        self.btn_process.setCursor(Qt.PointingHandCursor)
        self.btn_process.setEnabled(False)
        self.btn_process.clicked.connect(self.on_process)
        bottom.addWidget(self.btn_process)
        layout.addLayout(bottom)

        outer.addWidget(card)
        return page

    # -------------------------------- الأحداث --------------------------------
    def on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف Excel", str(Path.home()),
            "ملفات Excel (*.xlsx *.xls)"
        )
        if not path:
            return
        try:
            self.loaded = load_excel(path, self.settings.columns, self.settings.has_header)
        except ExcelLoadError as exc:
            QMessageBox.critical(self, "خطأ في قراءة الملف", str(exc))
            self.logger.error("فشل تحميل الملف")
            return

        self.lbl_file.setText(f"📄 {Path(path).name}   •   {len(self.loaded)} صف")
        self._fill_preview(self.loaded)
        self.btn_process.setEnabled(True)
        self.stack.setCurrentIndex(0)
        self.logger.info("تم تحميل ملف للمعالجة (%d صف)", len(self.loaded))

    def _fill_preview(self, data: LoadedData) -> None:
        rows = data.as_rows()
        self.preview_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, key in enumerate(["folder", "amount", "name", "iban"]):
                item = QTableWidgetItem(str(row.get(key, "")))
                if key == "amount":
                    item.setTextAlignment(Qt.AlignCenter)
                self.preview_table.setItem(r, c, item)

    def on_process(self) -> None:
        if not self.loaded:
            return
        try:
            result = process_loaded(self.loaded, self.settings)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "خطأ أثناء المعالجة", str(exc))
            self.logger.exception("فشل المعالجة")
            return

        self.results_view.show_result(result)
        self.stack.setCurrentIndex(1)
        s = result.stats
        self.logger.info(
            "اكتملت المعالجة: أصلية=%d بعد الدمج=%d تنبيهات=%d",
            s.original_count, s.merged_count, s.alerts_count,
        )

    def on_open_search(self) -> None:
        # إعادة تحميل المخزن (في حال تغيّر الملف) ثم عرض شاشة الكشف.
        self.search_view.store.load()
        self.search_view._refresh_status()
        self.stack.setCurrentIndex(2)

    def on_settings(self) -> None:
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self.settings.load()
            self.results_view.settings = self.settings
            self._refresh_footer()
            QMessageBox.information(self, "الإعدادات", "تم حفظ الإعدادات بنجاح.")
            self.logger.info("تم تحديث الإعدادات")
