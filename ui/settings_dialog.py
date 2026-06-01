"""
نافذة الإعدادات.

تتيح: تغيير اسم المديرية، إدارة قائمة الآيبانات الملغية (إضافة/حذف/استيراد)،
تعديل العتبات (حد المبلغ، طول الآيبان)، وربط الأعمدة (A/E/H/I).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.settings import Settings


class SettingsDialog(QDialog):
    """نافذة تعديل الإعدادات."""

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("الإعدادات")
        self.resize(620, 560)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        root.addWidget(tabs, stretch=1)

        tabs.addTab(self._tab_general(), "عام")
        tabs.addTab(self._tab_cancelled(), "الآيبانات الملغية")
        tabs.addTab(self._tab_columns(), "ربط الأعمدة")

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        btn_save = QPushButton("حفظ")
        btn_save.clicked.connect(self.on_save)
        btn_cancel = QPushButton("إلغاء")
        btn_cancel.setObjectName("ghostDark")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_save)
        buttons.addWidget(btn_cancel)
        root.addLayout(buttons)

    # -------------------------------- التبويبات --------------------------------
    def _tab_general(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.ed_directorate = QLineEdit()
        form.addRow("اسم المديرية (يظهر في رأس التقرير):", self.ed_directorate)

        self.sp_amount = QSpinBox()
        self.sp_amount.setRange(0, 2_000_000_000)
        self.sp_amount.setGroupSeparatorShown(True)
        self.sp_amount.setSingleStep(1_000_000)
        # ليس حداً مانعاً — مجرد عتبة تنبيه للمراجعة (قد يستحق الشخص المبلغ فعلاً).
        form.addRow("التنبيه عند مبلغ أكبر من:", self.sp_amount)

        self.sp_iban_len = QSpinBox()
        self.sp_iban_len.setRange(5, 40)
        form.addRow("طول الآيبان الصحيح:", self.sp_iban_len)

        self.ed_prefix = QLineEdit()
        self.ed_prefix.setMaxLength(4)
        form.addRow("بادئة الآيبان (الدولة):", self.ed_prefix)

        self.chk_mod97 = QCheckBox("تفعيل التحقق من خانات الضبط (MOD-97)")
        form.addRow("", self.chk_mod97)

        self.chk_header = QCheckBox("الصف الأول في الملف عنوان (يُتخطى)")
        form.addRow("", self.chk_header)

        # هل يريد الموظف تعديل أرقام الأضابير (عمود A)؟
        self.chk_process_folders = QCheckBox(
            "تعديل أرقام الأضابير (عمود A) — تنظيف وتفريد وتعبئة الفارغ تلقائياً"
        )
        form.addRow("", self.chk_process_folders)
        return w

    def _tab_cancelled(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("قائمة الآيبانات الملغية (يُنبَّه عليها أثناء المعالجة):"))

        self.list_cancelled = QListWidget()
        layout.addWidget(self.list_cancelled, stretch=1)

        add_row = QHBoxLayout()
        self.ed_new_iban = QLineEdit()
        self.ed_new_iban.setPlaceholderText("أدخل آيباناً ملغياً ثم اضغط إضافة")
        btn_add = QPushButton("إضافة")
        btn_add.clicked.connect(self.on_add_iban)
        add_row.addWidget(self.ed_new_iban, stretch=1)
        add_row.addWidget(btn_add)
        layout.addLayout(add_row)

        ops = QHBoxLayout()
        btn_remove = QPushButton("حذف المحدد")
        btn_remove.setObjectName("ghostDark")
        btn_remove.clicked.connect(self.on_remove_iban)
        btn_import = QPushButton("استيراد من ملف")
        btn_import.setObjectName("ghostDark")
        btn_import.clicked.connect(self.on_import_ibans)
        ops.addWidget(btn_remove)
        ops.addWidget(btn_import)
        ops.addStretch(1)
        layout.addLayout(ops)
        return w

    def _tab_columns(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.ed_col_folder = QLineEdit()
        self.ed_col_amount = QLineEdit()
        self.ed_col_name = QLineEdit()
        self.ed_col_iban = QLineEdit()
        for ed in (self.ed_col_folder, self.ed_col_amount, self.ed_col_name, self.ed_col_iban):
            ed.setMaxLength(3)
            ed.setFixedWidth(80)
        form.addRow("عمود رقم الإضبارة:", self.ed_col_folder)
        form.addRow("عمود المبلغ:", self.ed_col_amount)
        form.addRow("عمود الاسم:", self.ed_col_name)
        form.addRow("عمود الآيبان:", self.ed_col_iban)
        form.addRow(QLabel("استخدم حروف الأعمدة كما في Excel (مثل A أو E)."))
        return w

    # -------------------------------- تحميل/حفظ --------------------------------
    def _load_values(self) -> None:
        s = self.settings
        self.ed_directorate.setText(s.directorate_name)
        self.sp_amount.setValue(int(s.amount_max))
        self.sp_iban_len.setValue(int(s.iban_length))
        self.ed_prefix.setText(s.iban_prefix)
        self.chk_mod97.setChecked(s.iban_mod97_check)
        self.chk_header.setChecked(s.has_header)
        self.chk_process_folders.setChecked(s.process_folders)

        self.list_cancelled.clear()
        self.list_cancelled.addItems(s.cancelled_ibans)

        cols = s.columns
        self.ed_col_folder.setText(cols.get("folder", "A"))
        self.ed_col_amount.setText(cols.get("amount", "E"))
        self.ed_col_name.setText(cols.get("name", "H"))
        self.ed_col_iban.setText(cols.get("iban", "I"))

    def on_add_iban(self) -> None:
        iban = self.ed_new_iban.text().strip()
        if not iban:
            return
        # نضيف للعرض فقط؛ يُحفظ نهائياً عند الضغط على «حفظ».
        norm = "".join(iban.split()).upper()
        existing = {self.list_cancelled.item(i).text().upper()
                    for i in range(self.list_cancelled.count())}
        if norm in existing:
            QMessageBox.information(self, "موجود", "هذا الآيبان موجود مسبقاً.")
            return
        self.list_cancelled.addItem(norm)
        self.ed_new_iban.clear()

    def on_remove_iban(self) -> None:
        for item in self.list_cancelled.selectedItems():
            self.list_cancelled.takeItem(self.list_cancelled.row(item))

    def on_import_ibans(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "استيراد آيبانات ملغية", str(Path.home()),
            "ملفات نصية أو Excel (*.txt *.csv *.xlsx *.xls)"
        )
        if not path:
            return
        try:
            ibans = self._read_iban_file(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "خطأ", f"تعذّر قراءة الملف:\n{exc}")
            return
        existing = {self.list_cancelled.item(i).text().upper()
                    for i in range(self.list_cancelled.count())}
        added = 0
        for iban in ibans:
            norm = "".join(str(iban).split()).upper()
            if norm and norm not in existing:
                self.list_cancelled.addItem(norm)
                existing.add(norm)
                added += 1
        QMessageBox.information(self, "تم", f"تم استيراد {added} آيباناً.")

    @staticmethod
    def _read_iban_file(path: str) -> list[str]:
        """قراءة آيبانات من ملف نصي/CSV/Excel (عمود واحد)."""
        p = Path(path)
        suffix = p.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            import openpyxl
            wb = openpyxl.load_workbook(p, read_only=True)
            ws = wb.active
            values = []
            for row in ws.iter_rows(values_only=True):
                if row and row[0] is not None:
                    values.append(str(row[0]))
            return values
        # نص/CSV: سطر لكل آيبان (أو أول حقل قبل فاصلة).
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        return [ln.split(",")[0].strip() for ln in lines if ln.strip()]

    def on_save(self) -> None:
        s = self.settings
        s.data["directorate_name"] = self.ed_directorate.text().strip()
        s.data["thresholds"]["amount_max"] = int(self.sp_amount.value())
        s.data["thresholds"]["iban_length"] = int(self.sp_iban_len.value())
        s.data["iban_country_prefix"] = self.ed_prefix.text().strip().upper() or "IQ"
        s.data["iban_mod97_check"] = self.chk_mod97.isChecked()
        s.data["has_header"] = self.chk_header.isChecked()
        s.data["process_folders"] = self.chk_process_folders.isChecked()

        s.data["cancelled_ibans"] = [
            self.list_cancelled.item(i).text()
            for i in range(self.list_cancelled.count())
        ]

        cols = {
            "folder": self.ed_col_folder.text().strip().upper() or "A",
            "amount": self.ed_col_amount.text().strip().upper() or "E",
            "name": self.ed_col_name.text().strip().upper() or "H",
            "iban": self.ed_col_iban.text().strip().upper() or "I",
        }
        s.data["columns"] = cols

        try:
            s.save()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "خطأ", f"تعذّر حفظ الإعدادات:\n{exc}")
            return
        self.accept()
