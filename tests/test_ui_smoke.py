"""اختبار دخان للواجهة دون شاشة (offscreen): بناء + تحميل + معالجة + تصدير."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from core.settings import Settings
from tests.test_pipeline import make_sample
from ui.main_window import MainWindow
from ui.results_view import ResultsView
from ui.settings_dialog import SettingsDialog


def main():
    app = QApplication(sys.argv)

    out = Path(__file__).resolve().parent / "_out"
    out.mkdir(exist_ok=True)
    sample = out / "sample_ui.xlsx"
    make_sample(sample)

    win = MainWindow()
    # محاكاة اختيار ملف ومعالجته دون فتح حوارات.
    win.loaded = __import__("core.excel_loader", fromlist=["load_excel"]).load_excel(
        str(sample), win.settings.columns, win.settings.has_header
    )
    win._fill_preview(win.loaded)
    assert win.preview_table.rowCount() == len(win.loaded)
    win.on_process()
    assert win.stack.currentIndex() == 1, "لم تنتقل لشاشة النتائج"

    rv = win.results_view
    assert rv.tab_merged.rowCount() == 7
    assert rv.tab_alerts.rowCount() >= 4
    assert rv.tab_changes.rowCount() >= 9
    # تحقق تلوين خلية الخطورة.
    sev_item = rv.tab_alerts.item(0, 0)
    assert sev_item is not None and sev_item.background().color().isValid()

    # تصدير مباشر عبر الدوال الأساسية (دون حوار حفظ).
    from core.excel_loader import write_output_excel
    from core.report import generate_report
    xlsx = out / "ui_export.xlsx"
    pdf = out / "ui_export.pdf"
    write_output_excel(rv.result.final_rows, str(xlsx), win.settings.directorate_name)
    generate_report(rv.result, str(pdf), win.settings.directorate_name,
                    win.settings.footer_lines)
    assert xlsx.exists() and pdf.exists()

    # بناء نافذة الإعدادات والتحقق من تحميل القيم.
    dlg = SettingsDialog(Settings())
    assert dlg.ed_directorate.text() != ""
    dlg.ed_new_iban.setText("IQ99TEST000000000000099")
    dlg.on_add_iban()
    assert dlg.list_cancelled.count() >= 1

    print("✅ اختبار دخان الواجهة نجح: بناء + معاينة + معالجة + تبويبات + تصدير + إعدادات")


if __name__ == "__main__":
    main()
