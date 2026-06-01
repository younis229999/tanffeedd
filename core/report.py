"""
توليد تقرير PDF احترافي مبسّط بالعربية (RTL) — على نمط «دمج المكررات».

يتضمن التقرير فقط:
- ترويسة: اسم المديرية + «دمج المكررات» + التاريخ.
- ثلاث بطاقات إحصائية: إجمالي المبالغ، عدد المكررات، إجمالي السجلات.
- قائمة «المعلومات» المرقّمة: لكل مستفيد مدموج (الاسم : مبلغ + مبلغ = الإجمالي).

ملاحظات: المبالغ بدون فواصل، ولا يُذكر اسم المبرمج في التقرير.
يستخدم arabic-reshaper + python-bidi وخط Amiri المضمّن.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


_FONT_NAME = "ArabicFont"
_font_registered = False


def _assets_font_path() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Amiri.ttf"


def ensure_font() -> str:
    """تسجيل الخط العربي مرة واحدة. يعيد اسم الخط المسجّل."""
    global _font_registered
    if _font_registered:
        return _FONT_NAME

    candidates = [
        _assets_font_path(),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont(_FONT_NAME, str(path)))
                _font_registered = True
                return _FONT_NAME
            except Exception:  # noqa: BLE001
                continue

    raise FileNotFoundError(
        "لم يُعثر على خط عربي. ضع ملف خط TTF في assets/fonts/Amiri.ttf"
    )


def ar(text: object) -> str:
    """تشكيل النص العربي وترتيبه ثنائي الاتجاه للعرض الصحيح في PDF."""
    s = "" if text is None else str(text)
    try:
        return get_display(arabic_reshaper.reshape(s))
    except Exception:  # noqa: BLE001
        return s


def _fmt_amount(value: float) -> str:
    """تنسيق المبلغ بدون فواصل آلاف وبلا كسور (لتقرير دمج المكررات)."""
    try:
        return f"{int(round(float(value)))}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_amount_sep(value: float) -> str:
    """تنسيق المبلغ بفواصل آلاف (لكشف الحساب)."""
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return str(value)


class _ReportDoc(BaseDocTemplate):
    """قالب مستند مع تذييل في كل صفحة."""

    def __init__(self, filename: str, footer_lines: List[str], **kwargs):
        super().__init__(filename, **kwargs)
        self._footer_lines = footer_lines
        frame = Frame(
            self.leftMargin, self.bottomMargin, self.width, self.height, id="main",
        )
        self.addPageTemplates([
            PageTemplate(id="with_footer", frames=[frame], onPage=self._draw_footer)
        ])

    def _draw_footer(self, canvas, doc):
        """تذييل بسيط: أسطر متمركزة بخط صغير (بلا اسم مبرمج)."""
        canvas.saveState()
        canvas.setFont(_FONT_NAME, 8)
        canvas.setFillColor(colors.grey)
        center = doc.pagesize[0] / 2.0
        y = 14 * mm
        for line in self._footer_lines:
            canvas.drawCentredString(center, y, ar(line))
            y -= 4.2 * mm
        # رقم الصفحة.
        canvas.drawCentredString(center, 6 * mm, ar(f"صفحة {doc.page}"))
        canvas.restoreState()


def _styles():
    return {
        "title": ParagraphStyle(
            "t", fontName=_FONT_NAME, fontSize=20, alignment=TA_CENTER,
            leading=26, textColor=colors.HexColor("#1F4E78"), spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "st", fontName=_FONT_NAME, fontSize=13, alignment=TA_CENTER,
            leading=18, textColor=colors.HexColor("#444444"), spaceAfter=2,
        ),
        "date": ParagraphStyle(
            "d", fontName=_FONT_NAME, fontSize=11, alignment=TA_CENTER,
            leading=15, textColor=colors.HexColor("#777777"), spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "sec", fontName=_FONT_NAME, fontSize=14, alignment=TA_RIGHT,
            leading=20, textColor=colors.HexColor("#1F4E78"),
            spaceBefore=8, spaceAfter=6,
        ),
        "card_label": ParagraphStyle(
            "cl", fontName=_FONT_NAME, fontSize=11, alignment=TA_CENTER,
            leading=15, textColor=colors.HexColor("#6B7280"),
        ),
        "item": ParagraphStyle(
            "it", fontName=_FONT_NAME, fontSize=11.5, alignment=TA_RIGHT,
            leading=18, textColor=colors.HexColor("#1F2937"),
        ),
        "item_sub": ParagraphStyle(
            "isub", fontName=_FONT_NAME, fontSize=10, alignment=TA_RIGHT,
            leading=15, textColor=colors.HexColor("#7A8699"), rightIndent=14,
        ),
        "empty": ParagraphStyle(
            "e", fontName=_FONT_NAME, fontSize=11, alignment=TA_CENTER,
            leading=16, textColor=colors.grey, spaceBefore=8,
        ),
    }


def _stats_cards(stats, st) -> Table:
    """ثلاث بطاقات إحصائية أنيقة بأشرطة لون علوية (على نمط الصورة)."""
    # الترتيب من اليسار لليمين ليطابق الصورة:
    # إجمالي المبالغ | عدد المكررات | إجمالي السجلات
    cards = [
        ("إجمالي المبالغ", _fmt_amount(stats.total_amount), "#16A34A"),
        ("عدد المكررات", f"{stats.merged_away}", "#E67E22"),
        ("إجمالي السجلات", f"{stats.original_count}", "#2563EB"),
    ]
    row = []
    for label, value, accent in cards:
        value_style = ParagraphStyle(
            f"cv_{accent}", fontName=_FONT_NAME, fontSize=21, alignment=TA_CENTER,
            leading=26, textColor=colors.HexColor(accent),
        )
        cell = [
            Paragraph(ar(label), st["card_label"]),
            Spacer(1, 3 * mm),
            Paragraph(ar(value), value_style),
        ]
        row.append(cell)

    tbl = Table([row], colWidths=[58 * mm, 58 * mm, 58 * mm], hAlign="CENTER")
    style = [
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F9FC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        # فاصل رفيع بين البطاقات.
        ("LINEAFTER", (0, 0), (0, 0), 0.7, colors.HexColor("#E5EAF1")),
        ("LINEAFTER", (1, 0), (1, 0), 0.7, colors.HexColor("#E5EAF1")),
    ]
    # شريط لون علوي مميّز لكل بطاقة.
    for i, (_l, _v, accent) in enumerate(cards):
        style.append(("LINEABOVE", (i, 0), (i, 0), 3, colors.HexColor(accent)))
    tbl.setStyle(TableStyle(style))
    return tbl


def _merged_items(final_rows, st, show_folder: bool = True) -> list:
    """
    قائمة «المعلومات»: المستفيدون المدموجون فقط.
    كل عنصر: (الاسم: مبلغ + مبلغ = الإجمالي)، وتحته رقم الإضبارة إن كان مُفعّلاً.
    """
    flow = [Paragraph(ar("المعلومات"), st["section"])]
    # خط تحت عنوان القسم.
    flow.append(HRFlowable(width="100%", thickness=1.2,
                           color=colors.HexColor("#1F4E78"),
                           spaceBefore=1, spaceAfter=6))

    merged = [r for r in final_rows if len(r.get("component_amounts", []) or []) > 1]
    if not merged:
        flow.append(Paragraph(ar("لا توجد سجلات مدموجة."), st["empty"]))
        return flow

    for i, row in enumerate(merged, start=1):
        name = row.get("name", "")
        comps = row.get("component_amounts", [])
        total = row.get("amount", 0)
        breakdown = " + ".join(_fmt_amount(c) for c in comps)
        line = f"{i}- {name} : {breakdown} = {_fmt_amount(total)}"
        flow.append(Spacer(1, 2.5 * mm))
        flow.append(Paragraph(ar(line), st["item"]))
        if show_folder:
            folder = row.get("folder", "")
            flow.append(Paragraph(ar(f"رقم الإضبارة: {folder}"), st["item_sub"]))
        flow.append(Spacer(1, 2.5 * mm))
        # خط فاصل خفيف بين الأسطر.
        flow.append(HRFlowable(width="100%", thickness=0.4,
                               color=colors.HexColor("#E0E6EF"),
                               spaceBefore=0, spaceAfter=0))
    return flow


def generate_report(
    result,
    out_path: str,
    directorate_name: str,
    footer_lines: List[str],
    show_folder: bool = True,
) -> str:
    """توليد تقرير PDF مبسّط من نتيجة المعالجة."""
    ensure_font()
    st = _styles()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    doc = _ReportDoc(
        out_path,
        footer_lines=footer_lines,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=24 * mm,
        title="تقرير دمج المكررات",
    )

    flow = []
    flow.append(Paragraph(ar(directorate_name), st["title"]))
    flow.append(Paragraph(ar("دمج المكررات"), st["subtitle"]))
    flow.append(Paragraph(ar(datetime.now().strftime("%Y-%m-%d")), st["date"]))
    flow.append(Spacer(1, 4 * mm))
    flow.append(_stats_cards(result.stats, st))
    flow.append(Spacer(1, 8 * mm))
    flow.extend(_merged_items(result.final_rows, st, show_folder=show_folder))

    doc.build(flow)
    return out_path


def build_report_filename(directory: str, prefix: str = "altanfith_report") -> str:
    """توليد اسم ملف تقرير يتضمن التاريخ والوقت."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return str(Path(directory) / f"{prefix}_{stamp}.pdf")


def generate_statement_pdf(
    person,
    out_path: str,
    directorate_name: str,
    footer_lines: List[str],
    until_label: str = "",
    until_key: Optional[int] = None,
) -> str:
    """
    توليد كشف حساب لشخص واحد بتنسيق A4 أنيق.

    يعرض: الاسم الكامل + الآيبان + رقم الإضبارة، جدول (التاريخ | المبلغ)،
    ثم المجموع لغاية التاريخ المحدد وعدد مرات الاستلام.
    """
    ensure_font()
    st = _styles()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    doc = _ReportDoc(
        out_path, footer_lines=footer_lines, pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=24 * mm,
        title="كشف حساب",
    )

    flow = []
    flow.append(Paragraph(ar(directorate_name), st["title"]))
    flow.append(Paragraph(ar("كشف حساب المستفيد"), st["subtitle"]))
    flow.append(Paragraph(ar(datetime.now().strftime("%Y-%m-%d")), st["date"]))
    flow.append(Spacer(1, 4 * mm))

    # بطاقة معلومات الشخص (رقم الإضبارة يظهر لكل عملية في الجدول).
    info = [
        [Paragraph(ar(person.name), st["item"]), Paragraph(ar("الاسم:"), st["card_label"])],
        [Paragraph(ar(person.iban or "—"), st["item"]), Paragraph(ar("الآيبان:"), st["card_label"])],
    ]
    info_tbl = Table(info, colWidths=[120 * mm, 40 * mm])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F9FC")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5EAF1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5EAF1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    flow.append(info_tbl)
    flow.append(Spacer(1, 6 * mm))

    flow.append(Paragraph(ar("سجل عمليات الاستلام"), st["section"]))
    flow.append(HRFlowable(width="100%", thickness=1.2,
                           color=colors.HexColor("#1F4E78"), spaceBefore=1, spaceAfter=4))

    # جدول العمليات (تنازلي): رقم الإضبارة | المبلغ (بفواصل) | التاريخ | #
    cell_h = ParagraphStyle("ch", fontName=_FONT_NAME, fontSize=11, alignment=TA_CENTER,
                            leading=15, textColor=colors.white)
    cell = ParagraphStyle("cc", fontName=_FONT_NAME, fontSize=10.5, alignment=TA_CENTER,
                          leading=14, textColor=colors.HexColor("#1F2937"))
    data = [[Paragraph(ar("رقم الإضبارة"), cell_h),
             Paragraph(ar("المبلغ"), cell_h),
             Paragraph(ar("التاريخ"), cell_h),
             Paragraph(ar("#"), cell_h)]]
    # تصفية لغاية التاريخ مع الإبقاء على الترتيب التنازلي (الأحدث أولاً).
    rows = [e for e in person.entries
            if until_key is None or not e.date_key or e.date_key <= until_key]
    total = 0.0
    for n, e in enumerate(rows, start=1):
        total += e.amount
        data.append([Paragraph(ar(e.folder or "—"), cell),
                     Paragraph(ar(_fmt_amount_sep(e.amount)), cell),
                     Paragraph(ar(e.date_fmt or "—"), cell),
                     Paragraph(ar(str(n)), cell)])
    n = len(rows)

    tbl = Table(data, colWidths=[45 * mm, 55 * mm, 45 * mm, 15 * mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDE4EC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
    ]
    tbl.setStyle(TableStyle(style))
    flow.append(tbl)
    flow.append(Spacer(1, 5 * mm))

    # صندوق المجموع.
    label = f"المجموع لغاية {until_label}" if until_label else "المجموع الكلي"
    summary = [[
        Paragraph(ar(_fmt_amount_sep(total)),
                  ParagraphStyle("sv", fontName=_FONT_NAME, fontSize=15, alignment=TA_CENTER,
                                 leading=20, textColor=colors.HexColor("#16A34A"))),
        Paragraph(ar(f"{label}  •  عدد مرات الاستلام: {n}"),
                  ParagraphStyle("sl", fontName=_FONT_NAME, fontSize=12, alignment=TA_RIGHT,
                                 leading=18, textColor=colors.HexColor("#1F2937"))),
    ]]
    sum_tbl = Table(summary, colWidths=[50 * mm, 110 * mm])
    sum_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF6EE")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#16A34A")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    flow.append(sum_tbl)

    doc.build(flow)
    return out_path
