"""
شاشة النتائج — تبويبات: ملخص (بطاقات إحصائية)، تنبيهات (ملوّنة)،
النتيجة بعد الدمج، تغييرات أرقام الأضابير. مع أزرار تصدير Excel و PDF.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.excel_loader import build_output_filename, write_output_excel
from core.logger import get_logger
from core.report import build_report_filename, generate_report
from core.settings import Settings
from core.validator import SEVERITY_COLORS, SEVERITY_LABELS
from ui.theme import C, make_card, stat_card


def _fmt(value) -> str:
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


# علامة اتجاه من اليسار لليمين — تمنع إعادة ترتيب أرقام الأضابير في خلايا RTL.
_LRM = "‎"


def _ltr(text) -> str:
    """تغليف النص بعلامة LTR ليظهر بشكل صحيح (مثل 2025_65) داخل واجهة RTL."""
    s = str(text)
    return f"{_LRM}{s}{_LRM}" if s else s


def _style_table(table: QTableWidget) -> None:
    """تطبيق المظهر الحديث الموحّد على جدول."""
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectRows)


class ResultsView(QWidget):
    """عرض نتائج المعالجة."""

    back_requested = Signal()

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.logger = get_logger()
        self.result = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # ----- شريط أدوات علوي داخل بطاقة -----
        bar = make_card()
        bar.setFixedHeight(72)
        top = QHBoxLayout(bar)
        top.setContentsMargins(16, 12, 16, 12)
        self.btn_back = QPushButton("◀  رجوع للمعاينة")
        self.btn_back.setObjectName("ghostDark")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_requested.emit)
        top.addWidget(self.btn_back)
        top.addStretch(1)
        self.btn_excel = QPushButton("💾  حفظ Excel")
        self.btn_excel.setObjectName("success")
        self.btn_excel.setCursor(Qt.PointingHandCursor)
        self.btn_excel.clicked.connect(self.on_export_excel)
        self.btn_pdf = QPushButton("📄  تصدير تقرير PDF")
        self.btn_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_pdf.clicked.connect(self.on_export_pdf)
        top.addWidget(self.btn_excel)
        top.addWidget(self.btn_pdf)
        root.addWidget(bar)

        # ----- التبويبات داخل بطاقة -----
        body = make_card()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(14, 14, 14, 14)
        self.tabs = QTabWidget()
        body_lay.addWidget(self.tabs)
        root.addWidget(body, stretch=1)

        self.tab_summary = QWidget()
        self.tab_alerts = QTableWidget(0, 5)
        self.tab_merged = QTableWidget(0, 4)
        self.tab_changes = QTableWidget(0, 5)

        self._init_summary_tab()
        self._init_alerts_tab()
        self._init_merged_tab()
        self._init_changes_tab()

        self.tabs.addTab(self.tab_summary, "📊  ملخص وإحصائيات")
        self.tabs.addTab(self.tab_alerts, "⚠  التنبيهات")
        self.tabs.addTab(self.tab_merged, "🔗  النتيجة بعد الدمج")
        self.tabs.addTab(self.tab_changes, "✎  تغييرات الأضابير")

    # ------------------------------ تهيئة التبويبات ------------------------------
    def _init_summary_tab(self) -> None:
        outer = QVBoxLayout(self.tab_summary)
        outer.setContentsMargins(6, 10, 6, 6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QWidget()
        self.summary_layout = QVBoxLayout(host)
        self.summary_layout.setContentsMargins(4, 4, 4, 4)
        self.summary_layout.setSpacing(14)
        scroll.setWidget(host)
        outer.addWidget(scroll)

    def _init_alerts_tab(self) -> None:
        self.tab_alerts.setHorizontalHeaderLabels(
            ["الخطورة", "الصف", "الاسم", "نوع المشكلة", "القيمة"]
        )
        _style_table(self.tab_alerts)

    def _init_merged_tab(self) -> None:
        self.tab_merged.setHorizontalHeaderLabels(
            ["رقم الإضبارة", "المبلغ", "الاسم", "الآيبان"]
        )
        _style_table(self.tab_merged)

    def _init_changes_tab(self) -> None:
        self.tab_changes.setHorizontalHeaderLabels(
            ["الصف", "الاسم", "القديم", "الجديد", "السبب"]
        )
        _style_table(self.tab_changes)

    # -------------------------------- عرض النتيجة --------------------------------
    def show_result(self, result) -> None:
        self.result = result
        self._fill_summary(result)
        self._fill_alerts(result)
        self._fill_merged(result)
        self._fill_changes(result)
        self.tabs.setCurrentIndex(0)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _fill_summary(self, result) -> None:
        self._clear_layout(self.summary_layout)
        s = result.stats

        cards = [
            ("عدد الصفوف الأصلية", f"{s.original_count:,}", C.INFO),
            ("عدد الصفوف بعد الدمج", f"{s.merged_count:,}", C.PRIMARY),
            ("صفوف مدموجة", f"{s.merged_away:,}", C.WARNING),
            ("إجمالي المبالغ", _fmt(s.total_amount), C.SUCCESS),
            ("تنبيهات حرجة", f"{s.critical_count:,}", C.DANGER),
            ("تنبيهات تحذيرية", f"{s.warning_count:,}", C.WARNING),
            ("إجمالي التنبيهات", f"{s.alerts_count:,}", C.PRIMARY_DEEP),
            ("تعارضات الأسماء", f"{len(result.name_conflicts):,}",
             C.DANGER if result.name_conflicts else C.SUCCESS),
        ]

        grid = QGridLayout()
        grid.setSpacing(14)
        for i, (title, value, accent) in enumerate(cards):
            grid.addWidget(stat_card(title, value, accent), i // 4, i % 4)
        wrap = QWidget()
        wrap.setLayout(grid)
        self.summary_layout.addWidget(wrap)

        # بطاقة تعارضات الأسماء (إن وُجدت).
        if result.name_conflicts:
            card = make_card()
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 14, 18, 14)
            ttl = QLabel("⚠ تعارضات في الاسم لنفس الآيبان — يرجى المراجعة")
            ttl.setStyleSheet(f"color:{C.DANGER}; font-weight:800; font-size:14px;")
            cl.addWidget(ttl)
            for c in result.name_conflicts:
                lbl = QLabel(f"• {_ltr(c.iban)}  —  " + "  /  ".join(c.names))
                lbl.setStyleSheet(f"color:{C.TEXT}; font-size:12.5px;")
                cl.addWidget(lbl)
            self.summary_layout.addWidget(card)

        self.summary_layout.addStretch(1)

    def _fill_alerts(self, result) -> None:
        alerts = result.alerts
        self.tab_alerts.setRowCount(len(alerts))
        self.tab_alerts.setColumnWidth(0, 90)
        self.tab_alerts.setColumnWidth(1, 60)
        for r, a in enumerate(alerts):
            color = QColor(SEVERITY_COLORS[a.severity])
            cells = [SEVERITY_LABELS[a.severity], str(a.row_index), a.name, a.issue, _ltr(a.value)]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if c == 0:
                    item.setBackground(color)
                    item.setForeground(QColor("white"))
                    item.setTextAlignment(Qt.AlignCenter)
                elif c == 1:
                    item.setTextAlignment(Qt.AlignCenter)
                self.tab_alerts.setItem(r, c, item)

    def _fill_merged(self, result) -> None:
        rows = result.final_rows
        self.tab_merged.setRowCount(len(rows))
        for r, row in enumerate(rows):
            merged = len(row.get("component_amounts", [])) > 1
            values = [
                _ltr(row.get("folder", "")),
                _fmt(row.get("amount", 0)),
                row.get("name", ""),
                _ltr(row.get("iban", "")),
            ]
            for c, text in enumerate(values):
                item = QTableWidgetItem(text)
                if c in (0, 1):
                    item.setTextAlignment(Qt.AlignCenter)
                if merged:
                    item.setBackground(QColor("#FFF6E5"))
                self.tab_merged.setItem(r, c, item)

    def _fill_changes(self, result) -> None:
        changes = result.folder_changes
        self.tab_changes.setRowCount(len(changes))
        self.tab_changes.setColumnWidth(0, 60)
        for r, ch in enumerate(changes):
            dup = "فك تكرار" in ch.reason
            values = [str(ch.row_index), ch.name,
                      _ltr(ch.old_value), _ltr(ch.new_value), ch.reason]
            for c, text in enumerate(values):
                item = QTableWidgetItem(text)
                if c == 0:
                    item.setTextAlignment(Qt.AlignCenter)
                if dup:
                    item.setBackground(QColor("#FDECEA"))
                self.tab_changes.setItem(r, c, item)

    # -------------------------------- التصدير --------------------------------
    def on_export_excel(self) -> None:
        if not self.result:
            return
        default = build_output_filename(str(Path.home()))
        path, _ = QFileDialog.getSaveFileName(
            self, "حفظ ملف Excel", default, "ملف Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            write_output_excel(self.result.final_rows, path, self.settings.directorate_name)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "خطأ", f"تعذّر حفظ الملف:\n{exc}")
            return
        self.logger.info("تم حفظ Excel: %s", path)
        QMessageBox.information(self, "تم", f"تم حفظ الملف:\n{path}")

    def on_export_pdf(self) -> None:
        if not self.result:
            return
        default = build_report_filename(str(Path.home()))
        path, _ = QFileDialog.getSaveFileName(
            self, "حفظ تقرير PDF", default, "ملف PDF (*.pdf)"
        )
        if not path:
            return
        try:
            generate_report(
                self.result, path,
                self.settings.directorate_name, self.settings.footer_lines,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "خطأ", f"تعذّر إنشاء التقرير:\n{exc}")
            return
        self.logger.info("تم تصدير PDF: %s", path)
        QMessageBox.information(self, "تم", f"تم إنشاء التقرير:\n{path}")
