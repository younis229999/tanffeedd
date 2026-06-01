"""اختبار يدوي شامل لخط المعالجة (تشغيل: python -m tests.test_pipeline)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openpyxl

from core.settings import Settings
from core.excel_loader import (
    load_excel, write_output_excel, build_output_filename,
)
from core.processor import process_file
from core.report import generate_report, build_report_filename


def make_sample(path):
    """إنشاء ملف Excel تجريبي يغطي كل الحالات الحرجة."""
    wb = openpyxl.Workbook()
    ws = wb.active
    # صف العنوان (A..I).
    ws.append(["A_folder", "B", "C", "D", "E_amount", "F", "G", "H_name", "I_iban"])
    valid = "IQ98NBIQ850123456789012"   # طول 23، يبدأ بـ IQ
    rows = [
        # تكرار آيبان -> دمج وجمع المبالغ (100000 + 100000 = 200000)
        ["اضبارة 2025/65", "", "", "", 100000, "", "", "أحمد علي", valid],
        ["٢٠٢٥-٦٥",        "", "", "", 100000, "", "", "أحمد علي", valid],
        # تعارض اسم لنفس الآيبان آخر
        ["2025/66", "", "", "", 50000, "", "", "محمد حسن", "IQ12ABCD850123456789099"],
        ["2025/66", "", "", "", 50000, "", "", "محمد حسين", "IQ12ABCD850123456789099"],
        # آيبان ملغي
        ["66/2025", "", "", "", 75000, "", "", "سعد كريم", "IQ00CANC000000000000001"],
        # طول آيبان خاطئ
        ["xx 70 yy 2025", "", "", "", 30000, "", "", "نور الدين", "IQ123SHORT"],
        # مبلغ مرتفع
        ["2025/80", "", "", "", 15000000, "", "", "علي وليد", "IQ55RAFB850123456789012"],
        # حقل ناقص (اسم فارغ)
        ["2025/81", "", "", "", 20000, "", "", "", "IQ77RAFB850123456789012"],
        # رقم إضبارة مكرر بعد التنظيف (سيتعارض مع 2025_80 أعلاه) -> فك تكرار
        ["إضبارة رقم 80 لسنة 2025", "", "", "", 12000, "", "", "حسين جابر", "IQ88RAFB850123456789012"],
        # حقل إضبارة فارغ -> تعبئة تلقائية بالسنة السائدة (2025)
        ["", "", "", "", 40000, "", "", "كرار عبد الرحمن محمد علي سعيد", "IQ11RAFB850123456789012"],
        # رقم بلا سنة (8479798) -> يُحوَّل إلى السنة_الرقم
        ["8479798", "", "", "", 25000, "", "", "نور الدين قاسم", "IQ22RAFB850123456789012"],
    ]
    for r in rows:
        ws.append(r)
    wb.save(path)


def main():
    out_dir = Path(__file__).resolve().parent / "_out"
    out_dir.mkdir(exist_ok=True)
    sample = out_dir / "sample_input.xlsx"
    make_sample(sample)

    settings = Settings()
    # نضيف آيباناً ملغياً للقائمة لاختبار التنبيه (دون حفظ دائم).
    settings.data["cancelled_ibans"] = ["IQ00CANC000000000000001"]
    settings.data["iban_mod97_check"] = False

    result = process_file(str(sample), settings)
    s = result.stats

    print("=== الإحصائيات ===")
    print(f"الأصلية={s.original_count}  بعد الدمج={s.merged_count}  مدموجة={s.merged_away}")
    print(f"تنبيهات={s.alerts_count} (حرج={s.critical_count}, تحذير={s.warning_count})")
    print(f"إجمالي المبالغ={s.total_amount:,.0f}")

    print("\n=== الصفوف النهائية ===")
    for row in result.final_rows:
        comps = row["component_amounts"]
        print(f"  {row['folder']:>12} | {row['amount']:>12,.0f} | "
              f"{row['name']:<12} | {row['iban']} | comps={comps}")

    print("\n=== تغييرات الأضابير (القديم -> الجديد) ===")
    for c in result.folder_changes:
        print(f"  صف {c.row_index}: '{c.old_value}' -> '{c.new_value}'  ({c.reason})")

    print("\n=== تعارضات الأسماء ===")
    for c in result.name_conflicts:
        print(f"  {c.iban}: {c.names}")

    print("\n=== التنبيهات ===")
    for a in result.alerts:
        print(f"  [{a.severity.value:8}] صف {a.row_index} {a.name}: {a.issue} ({a.value})")

    # المخرجات
    xlsx_path = build_output_filename(str(out_dir))
    write_output_excel(result.final_rows, xlsx_path, settings.directorate_name)
    # فحص اتجاه LTR
    wb = openpyxl.load_workbook(xlsx_path)
    print(f"\nExcel rightToLeft = {wb.active.sheet_view.rightToLeft} (المتوقع False)")

    pdf_path = build_report_filename(str(out_dir))
    generate_report(result, pdf_path, settings.directorate_name, settings.report_footer_lines,
                    show_folder=settings.report_show_folder)
    print(f"تم توليد PDF: {pdf_path} ({Path(pdf_path).stat().st_size} bytes)")

    # تحققات صريحة (assertions)
    assert s.original_count == 11
    merged_amount = next(r["amount"] for r in result.final_rows
                         if r["iban"] == "IQ98NBIQ850123456789012")
    assert merged_amount == 200000, merged_amount
    folders = [r["folder"] for r in result.final_rows]
    assert all(f for f in folders), f"يوجد رقم إضبارة فارغ! {folders}"
    assert len(folders) == len(set(folders)), f"أرقام أضابير مكررة! {folders}"
    assert all("_" in f for f in folders), f"يوجد رقم إضبارة بلا صيغة سنة_رقم! {folders}"
    # تقصير الاسم الطويل إلى ثلاثي مع مراعاة المركّب (عبد الرحمن وحدة واحدة)
    long_name = next(r["name"] for r in result.final_rows
                     if r["iban"] == "IQ11RAFB850123456789012")
    assert long_name == "كرار عبد الرحمن محمد", long_name
    assert wb.active.sheet_view.rightToLeft is False
    print("\n✅ كل التحققات نجحت.")


if __name__ == "__main__":
    main()
