"""
نافذة منفصلة لإدارة ملف الكشف (رفع/تحديث وحذف) — على نمط نافذة الإعدادات.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.ledger import LedgerStore


class LedgerDialog(QDialog):
    """نافذة إدارة ملف الكشف المخزّن."""

    def __init__(self, store: LedgerStore, parent=None):
        super().__init__(parent)
        self.store = store
        self.changed = False
        self.setWindowTitle("إدارة ملف الكشف")
        self.resize(520, 300)
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("إدارة ملف الكشف المخزّن")
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        # بطاقة الحالة.
        self.card = QFrame()
        self.card.setObjectName("card")
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(6)
        self.lbl_status = QLabel()
        self.lbl_status.setWordWrap(True)
        cl.addWidget(self.lbl_status)
        root.addWidget(self.card)

        hint = QLabel(
            "الأعمدة المتوقّعة: A=رقم الإضبارة، B=التاريخ، E=المبلغ، "
            "H=الاسم، I=الآيبان (قابلة للتعديل من الإعدادات)."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        root.addStretch(1)

        # الأزرار.
        btns = QHBoxLayout()
        self.btn_import = QPushButton("⬆  رفع / تحديث الملف")
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.clicked.connect(self.on_import)
        self.btn_clear = QPushButton("🗑  حذف الملف المخزّن")
        self.btn_clear.setObjectName("ghostDark")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self.on_clear)
        btns.addWidget(self.btn_import)
        btns.addWidget(self.btn_clear)
        btns.addStretch(1)
        btn_close = QPushButton("إغلاق")
        btn_close.setObjectName("ghostDark")
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_close)
        root.addLayout(btns)

    def _refresh(self) -> None:
        if self.store.has_data():
            name = self.store.source_name or "ledger.xlsx"
            self.lbl_status.setText(
                f"✅ يوجد ملف مخزّن\n\n"
                f"الاسم: {name}\n"
                f"عدد الصفوف: {self.store.row_count}\n"
                f"عدد المستفيدين: {len(self.store.persons)}"
            )
            self.btn_clear.setEnabled(True)
        else:
            self.lbl_status.setText("لا يوجد ملف مخزّن حالياً.\nاضغط «رفع / تحديث الملف».")
            self.btn_clear.setEnabled(False)

    def on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف الكشف (Excel)", str(Path.home()),
            "ملفات Excel (*.xlsx *.xls)")
        if not path:
            return
        try:
            count = self.store.import_file(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "خطأ", f"تعذّر قراءة الملف:\n{exc}")
            return
        self.changed = True
        self._refresh()
        QMessageBox.information(self, "تم", f"تم تخزين الملف بنجاح ({count} صف).")

    def on_clear(self) -> None:
        if not self.store.has_data():
            return
        if QMessageBox.question(self, "تأكيد", "حذف ملف الكشف المخزّن؟") != QMessageBox.Yes:
            return
        self.store.clear()
        self.changed = True
        self._refresh()
