"""
شاشة «الكشف والبحث» — تصميم حديث.

- شريط علوي: رفع/تحديث ملف الكشف، حذفه، ورجوع.
- بحث ذكي بالاسم (يعالج الأحرف العربية والمسافات).
- عند اختيار شخص: كشف بترتيب تنازلي (الأحدث أولاً)، لكل عملية تاريخها ومبلغها
  (بفواصل) ورقم إضبارتها، مع الآيبان والاسم الكامل والمجموع لغاية تاريخ،
  وزر طباعة بتنسيق A4.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import tempfile

from core.ledger import LedgerStore
from core.logger import get_logger
from core.report import generate_statement_pdf
from core.settings import Settings
from ui.ledger_dialog import LedgerDialog
from ui.printing import print_pdf_file
from ui.theme import C, make_card

_LRM = "‎"


def _fmt(value) -> str:
    """تنسيق المبلغ بفواصل آلاف."""
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return str(value)


def _ltr(text) -> str:
    s = str(text)
    return f"{_LRM}{s}{_LRM}" if s else s


class SearchView(QWidget):
    """شاشة الكشف والبحث."""

    back_requested = Signal()

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.logger = get_logger()
        self.store = LedgerStore(settings)
        self.results = []
        self.current = None
        self._build_ui()
        self._refresh_status()

    # ------------------------------ بناء الواجهة ------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # ----- شريط علوي -----
        bar = make_card()
        bar.setFixedHeight(72)
        tb = QHBoxLayout(bar)
        tb.setContentsMargins(18, 12, 18, 12)
        title = QLabel("🔎  الكشف والبحث")
        title.setObjectName("sectionTitle")
        tb.addWidget(title)
        tb.addStretch(1)
        self.btn_manage = QPushButton("📁  إدارة ملف الكشف")
        self.btn_manage.setCursor(Qt.PointingHandCursor)
        self.btn_manage.clicked.connect(self.on_manage)
        self.btn_back = QPushButton("◀  رجوع للمعالجة")
        self.btn_back.setObjectName("ghostDark")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_requested.emit)
        tb.addWidget(self.btn_manage)
        tb.addWidget(self.btn_back)
        root.addWidget(bar)

        # ----- بطاقة البحث -----
        search_card = make_card()
        sc = QVBoxLayout(search_card)
        sc.setContentsMargins(18, 14, 18, 14)
        sc.setSpacing(10)
        self.lbl_status = QLabel()
        self.lbl_status.setObjectName("hint")
        sc.addWidget(self.lbl_status)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("ابحث باسم المستفيد…  (مثال: احمد محمد)")
        self.search_box.setMinimumHeight(42)
        self.search_box.setStyleSheet("font-size:15px;")
        self.search_box.textChanged.connect(self.on_search)
        sc.addWidget(self.search_box)
        root.addWidget(search_card)

        # ----- المنطقة الرئيسية: النتائج (يمين) + الكشف (يسار) -----
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(10)

        res_card = make_card()
        rl = QVBoxLayout(res_card)
        rl.setContentsMargins(14, 14, 14, 14)
        rl.addWidget(QLabel("نتائج البحث:"))
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.on_pick)
        rl.addWidget(self.results_list, stretch=1)
        splitter.addWidget(res_card)

        self.statement_card = make_card()
        self._build_statement(self.statement_card)
        splitter.addWidget(self.statement_card)

        splitter.setSizes([330, 850])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

    def _build_statement(self, card: QFrame) -> None:
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        # رأس: الاسم + شارة المجموع.
        head = QHBoxLayout()
        self.lbl_name = QLabel("اختر مستفيداً من نتائج البحث لعرض كشفه")
        self.lbl_name.setStyleSheet(
            f"font-size:18px; font-weight:800; color:{C.PRIMARY_DEEP};")
        head.addWidget(self.lbl_name)
        head.addStretch(1)
        self.badge_total = QLabel("")
        self.badge_total.setStyleSheet(
            f"background:{C.SUCCESS}; color:white; font-size:15px; font-weight:800;"
            f" padding:8px 16px; border-radius:10px;")
        self.badge_total.setVisible(False)
        head.addWidget(self.badge_total)
        lay.addLayout(head)

        # شارة الآيبان.
        self.lbl_iban = QLabel("")
        self.lbl_iban.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_iban.setStyleSheet(
            f"color:{C.TEXT}; font-size:13px; background:{C.TRACK};"
            f" padding:6px 12px; border-radius:8px;")
        self.lbl_iban.setVisible(False)
        lay.addWidget(self.lbl_iban, alignment=Qt.AlignRight)

        # أدوات: المجموع لغاية + طباعة.
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("المجموع لغاية:"))
        self.date_until = QDateEdit()
        self.date_until.setCalendarPopup(True)
        self.date_until.setDisplayFormat("yyyy-MM-dd")
        self.date_until.setDate(QDate.currentDate())
        self.date_until.setMinimumHeight(34)
        self.date_until.dateChanged.connect(self._refresh_statement)
        ctrl.addWidget(self.date_until)
        ctrl.addStretch(1)
        self.btn_print = QPushButton("🖨  طباعة مباشرة")
        self.btn_print.setCursor(Qt.PointingHandCursor)
        self.btn_print.setEnabled(False)
        self.btn_print.clicked.connect(self.on_print_direct)
        self.btn_save_pdf = QPushButton("💾  حفظ PDF")
        self.btn_save_pdf.setObjectName("ghostDark")
        self.btn_save_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_save_pdf.setEnabled(False)
        self.btn_save_pdf.clicked.connect(self.on_save_pdf)
        ctrl.addWidget(self.btn_print)
        ctrl.addWidget(self.btn_save_pdf)
        lay.addLayout(ctrl)

        # جدول الكشف (تنازلي): التاريخ | المبلغ | رقم الإضبارة.
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["التاريخ", "المبلغ", "رقم الإضبارة"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setMinimumHeight(120)
        lay.addWidget(self.table, stretch=1)

        self.lbl_total = QLabel("")
        self.lbl_total.setStyleSheet(
            f"font-size:14px; font-weight:700; color:{C.PRIMARY_DEEP}; padding:4px;")
        lay.addWidget(self.lbl_total)

    # -------------------------------- الأحداث --------------------------------
    def _refresh_status(self) -> None:
        if self.store.has_data():
            name = self.store.source_name or "ledger.xlsx"
            self.lbl_status.setText(
                f"📂 الملف المخزّن: {name}   •   {self.store.row_count} صف   •   "
                f"{len(self.store.persons)} مستفيد")
            self.search_box.setEnabled(True)
        else:
            self.lbl_status.setText("لا يوجد ملف مخزّن — اضغط «إدارة ملف الكشف» لرفع ملف.")
            self.search_box.setEnabled(False)

    def on_manage(self) -> None:
        """فتح نافذة إدارة ملف الكشف (رفع/حذف) المنفصلة."""
        dlg = LedgerDialog(self.store, self)
        dlg.exec()
        if dlg.changed:
            self._refresh_status()
            self.results_list.clear()
            self.search_box.clear()
            self._clear_statement()

    def on_search(self, text: str) -> None:
        self.results_list.clear()
        if not self.store.has_data() or len(text.strip()) < 2:
            return
        self.results = self.store.search(text)
        for p in self.results:
            tail = p.iban[-6:] if p.iban else ""
            label = f"{p.name}"
            if tail:
                label += f"   •   {_LRM}…{tail}{_LRM}"
            label += f"   ({p.count} عملية)"
            self.results_list.addItem(QListWidgetItem(label))
        if not self.results:
            self.results_list.addItem("لا توجد نتائج مطابقة.")

    def on_pick(self, item: QListWidgetItem) -> None:
        row = self.results_list.row(item)
        if row < 0 or row >= len(self.results):
            return
        self.current = self.results[row]
        max_key = max((e.date_key for e in self.current.entries if e.date_key), default=0)
        if max_key:
            y, m, d = max_key // 10000, (max_key // 100) % 100, max_key % 100
            try:
                self.date_until.setDate(QDate(y, m, d))
            except Exception:  # noqa: BLE001
                self.date_until.setDate(QDate.currentDate())
        self.btn_print.setEnabled(True)
        self.btn_save_pdf.setEnabled(True)
        self._refresh_statement()

    def _until_key(self) -> int:
        d = self.date_until.date()
        return d.year() * 10000 + d.month() * 100 + d.day()

    def _refresh_statement(self) -> None:
        p = self.current
        if not p:
            return
        self.lbl_name.setText(p.name)
        self.lbl_iban.setText(f"الآيبان:  {_LRM}{p.iban or '—'}{_LRM}")
        self.lbl_iban.setVisible(True)

        until = self._until_key()
        # تنازلي: الأحدث أولاً (entries مرتّبة تنازلياً مسبقاً).
        rows = [e for e in p.entries if not e.date_key or e.date_key <= until]
        self.table.setRowCount(len(rows))
        total = 0.0
        for r, e in enumerate(rows):
            total += e.amount
            di = QTableWidgetItem(_ltr(e.date_fmt or "—"))
            ai = QTableWidgetItem(_fmt(e.amount))
            fi = QTableWidgetItem(_ltr(e.folder or "—"))
            for it in (di, ai, fi):
                it.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 0, di)
            self.table.setItem(r, 1, ai)
            self.table.setItem(r, 2, fi)

        until_lbl = self.date_until.date().toString("yyyy-MM-dd")
        self.badge_total.setText(f"المجموع: {_fmt(total)}")
        self.badge_total.setVisible(True)
        self.lbl_total.setText(
            f"المجموع لغاية {until_lbl}:  {_fmt(total)}     •     عدد مرات الاستلام: {len(rows)}")

    def _clear_statement(self) -> None:
        self.current = None
        self.btn_print.setEnabled(False)
        self.btn_save_pdf.setEnabled(False)
        self.table.setRowCount(0)
        self.lbl_name.setText("اختر مستفيداً من نتائج البحث لعرض كشفه")
        self.lbl_iban.setVisible(False)
        self.badge_total.setVisible(False)
        self.lbl_total.setText("")

    def _make_statement_pdf(self, path: str) -> None:
        """توليد كشف PDF في المسار المحدّد."""
        until_lbl = self.date_until.date().toString("yyyy-MM-dd")
        generate_statement_pdf(
            self.current, path,
            self.settings.directorate_name, self.settings.report_footer_lines,
            until_label=until_lbl, until_key=self._until_key())

    def on_save_pdf(self) -> None:
        """حفظ الكشف كملف PDF."""
        if not self.current:
            return
        until_lbl = self.date_until.date().toString("yyyy-MM-dd")
        default = str(Path.home() / f"كشف_{self.current.name}_{until_lbl}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "حفظ الكشف PDF", default, "ملف PDF (*.pdf)")
        if not path:
            return
        try:
            self._make_statement_pdf(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "خطأ", f"تعذّر إنشاء الكشف:\n{exc}")
            return
        self.logger.info("تم حفظ كشف: %s", path)
        QMessageBox.information(self, "تم", f"تم حفظ الكشف:\n{path}")

    def on_print_direct(self) -> None:
        """طباعة الكشف مباشرةً عبر نافذة اختيار الطابعة."""
        if not self.current:
            return
        tmp_path = ""
        printed = False
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp.close()
            tmp_path = tmp.name
            self._make_statement_pdf(tmp_path)
            printed = print_pdf_file(tmp_path, self)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "خطأ", f"تعذّر الطباعة:\n{exc}")
            return
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:  # noqa: BLE001
                    pass
        if printed:
            self.logger.info("تمت طباعة كشف مباشرة: %s", self.current.name)
