"""
توليد تقرير PDF احترافي بالعربية (RTL).

يستخدم reportlab مع arabic-reshaper و python-bidi وخطاً عربياً مضمّناً (TTF)
لضمان ظهور العربية بشكل صحيح. التقرير يتضمن:
- رأساً فيه اسم المديرية + التاريخ + إحصائيات.
- قائمة تفصيلية مرقّمة لكل مستفيد.
- قسم تنبيهات، وقسم تغييرات أرقام الأضابير.
- تذييلاً في أسفل كل صفحة (3 أسطر متمركزة، خط صغير).
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

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
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .validator import SEVERITY_COLORS, SEVERITY_LABELS, Alert, Severity


_FONT_NAME = "ArabicFont"
_FONT_BOLD = "ArabicFont"   # نفس الخط للعريض إن لم يتوفر وزن منفصل.
_font_registered = False


def _assets_font_path() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Amiri.ttf"


def ensure_font() -> str:
    """
    تسجيل الخط العربي مرة واحدة. يعيد اسم الخط المسجّل.

    يبحث عن assets/fonts/Amiri.ttf؛ وإن لم يوجد يحاول خطوطاً نظامية شائعة.
    """
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
    except Exception:  # noqa: BLE001 — في أسوأ الأحوال نعرض النص كما هو.
        return s


def _fmt_amount(value: float) -> str:
    """تنسيق المبلغ بفواصل آلاف بلا كسور."""
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


class _ReportDoc(BaseDocTemplate):
    """قالب مستند مع تذييل في كل صفحة."""

    def __init__(self, filename: str, footer_lines: List[str], **kwargs):
        super().__init__(filename, **kwargs)
        self._footer_lines = footer_lines
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="main",
        )
        self.addPageTemplates([
            PageTemplate(id="with_footer", frames=[frame], onPage=self._draw_footer)
        ])

    def _draw_footer(self, canvas, doc):
        """رسم التذييل: 3 أسطر متمركزة بخط صغير أسفل كل صفحة."""
        canvas.saveState()
        canvas.setFont(_FONT_NAME, 8)
        canvas.setFillColor(colors.grey)
        page_center = doc.pagesize[0] / 2.0
        y = 16 * mm
        for line in self._footer_lines:
            canvas.drawCentredString(page_center, y, ar(line))
            y -= 4.2 * mm
        canvas.restoreState()


def _styles():
    """أنماط الفقرات المستخدمة في التقرير."""
    return {
        "title": ParagraphStyle(
            "ar_title", fontName=_FONT_NAME, fontSize=18, alignment=TA_CENTER,
            leading=24, textColor=colors.HexColor("#1F4E78"), spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "ar_subtitle", fontName=_FONT_NAME, fontSize=11, alignment=TA_CENTER,
            leading=16, textColor=colors.HexColor("#555555"), spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "ar_section", fontName=_FONT_NAME, fontSize=14, alignment=TA_RIGHT,
            leading=20, textColor=colors.HexColor("#1F4E78"), spaceBefore=10,
            spaceAfter=6,
        ),
        "item_name": ParagraphStyle(
            "ar_item_name", fontName=_FONT_NAME, fontSize=12, alignment=TA_RIGHT,
            leading=18, textColor=colors.black,
        ),
        "item_line": ParagraphStyle(
            "ar_item_line", fontName=_FONT_NAME, fontSize=10.5, alignment=TA_RIGHT,
            leading=16, textColor=colors.HexColor("#333333"), rightIndent=10,
        ),
        "cell": ParagraphStyle(
            "ar_cell", fontName=_FONT_NAME, fontSize=9.5, alignment=TA_RIGHT,
            leading=13,
        ),
        "cell_white": ParagraphStyle(
            "ar_cell_white", fontName=_FONT_NAME, fontSize=10, alignment=TA_CENTER,
            leading=14, textColor=colors.white,
        ),
        "empty": ParagraphStyle(
            "ar_empty", fontName=_FONT_NAME, fontSize=11, alignment=TA_CENTER,
            leading=16, textColor=colors.grey, spaceBefore=6,
        ),
    }


def _stats_table(stats, st) -> Table:
    """جدول إحصائيات موجز في رأس التقرير."""
    rows_data = [
        ("عدد الصفوف الأصلية", f"{stats.original_count:,}"),
        ("عدد الصفوف بعد الدمج", f"{stats.merged_count:,}"),
        ("عدد الصفوف المدموجة", f"{stats.merged_away:,}"),
        ("عدد التنبيهات", f"{stats.alerts_count:,}"),
        ("إجمالي المبالغ", _fmt_amount(stats.total_amount)),
    ]
    table_data = []
    for label, value in rows_data:
        table_data.append([
            Paragraph(ar(value), st["cell"]),
            Paragraph(ar(label), st["cell"]),
        ])
    tbl = Table(table_data, colWidths=[70 * mm, 90 * mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#EAF1F8")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B5C7DA")),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tbl


def _detail_items(final_rows, st) -> list:
    """قائمة تفصيلية مرقّمة لكل مستفيد."""
    flow = []
    for i, row in enumerate(final_rows, start=1):
        name = row.get("name", "")
        flow.append(Paragraph(ar(f"{i}- الاسم: {name}"), st["item_name"]))

        comps = row.get("component_amounts", []) or [row.get("amount", 0)]
        total = row.get("amount", 0)
        if len(comps) > 1:
            comp_str = " + ".join(_fmt_amount(c) for c in comps)
            amounts_line = f"المبالغ: {comp_str} = {_fmt_amount(total)}"
        else:
            amounts_line = f"المبلغ: {_fmt_amount(total)}"
        flow.append(Paragraph(ar(amounts_line), st["item_line"]))
        flow.append(Paragraph(ar(f"رقم الإضبارة: {row.get('folder', '')}"), st["item_line"]))
        flow.append(Paragraph(ar(f"الآيبان: {row.get('iban', '')}"), st["item_line"]))
        flow.append(Spacer(1, 4 * mm))
    return flow


def _alerts_section(alerts: List[Alert], st) -> list:
    """قسم التنبيهات كجدول ملوّن حسب الخطورة."""
    flow = [Paragraph(ar("قسم التنبيهات"), st["section"])]
    if not alerts:
        flow.append(Paragraph(ar("لا توجد تنبيهات."), st["empty"]))
        return flow

    header = [
        Paragraph(ar("القيمة"), st["cell_white"]),
        Paragraph(ar("نوع المشكلة"), st["cell_white"]),
        Paragraph(ar("الاسم"), st["cell_white"]),
        Paragraph(ar("الصف"), st["cell_white"]),
        Paragraph(ar("الخطورة"), st["cell_white"]),
    ]
    data = [header]
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for r, a in enumerate(alerts, start=1):
        color = colors.HexColor(SEVERITY_COLORS[a.severity])
        data.append([
            Paragraph(ar(a.value), st["cell"]),
            Paragraph(ar(a.issue), st["cell"]),
            Paragraph(ar(a.name), st["cell"]),
            Paragraph(ar(str(a.row_index)), st["cell"]),
            Paragraph(ar(SEVERITY_LABELS[a.severity]), st["cell_white"]),
        ])
        style_cmds.append(("BACKGROUND", (4, r), (4, r), color))
    tbl = Table(data, colWidths=[35 * mm, 70 * mm, 35 * mm, 12 * mm, 18 * mm], repeatRows=1)
    tbl.setStyle(TableStyle(style_cmds))
    flow.append(tbl)
    return flow


def _changes_section(changes, st) -> list:
    """قسم تغييرات أرقام الأضابير (القديم ← الجديد)."""
    flow = [Paragraph(ar("تغييرات أرقام الأضابير"), st["section"])]
    if not changes:
        flow.append(Paragraph(ar("لا توجد تغييرات."), st["empty"]))
        return flow

    header = [
        Paragraph(ar("السبب"), st["cell_white"]),
        Paragraph(ar("الجديد"), st["cell_white"]),
        Paragraph(ar("القديم"), st["cell_white"]),
        Paragraph(ar("الاسم"), st["cell_white"]),
        Paragraph(ar("الصف"), st["cell_white"]),
    ]
    data = [header]
    for c in changes:
        data.append([
            Paragraph(ar(c.reason), st["cell"]),
            Paragraph(ar(c.new_value), st["cell"]),
            Paragraph(ar(c.old_value), st["cell"]),
            Paragraph(ar(c.name), st["cell"]),
            Paragraph(ar(str(c.row_index)), st["cell"]),
        ])
    tbl = Table(data, colWidths=[45 * mm, 35 * mm, 35 * mm, 35 * mm, 12 * mm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    flow.append(tbl)
    return flow


def _conflicts_section(conflicts, st) -> list:
    """قسم تعارضات الأسماء لنفس الآيبان (إن وُجدت)."""
    if not conflicts:
        return []
    flow = [Paragraph(ar("تعارضات الأسماء لنفس الآيبان"), st["section"])]
    for c in conflicts:
        names = " / ".join(c.names)
        flow.append(Paragraph(ar(f"الآيبان: {c.iban} — الأسماء: {names}"), st["item_line"]))
    return flow


def generate_report(
    result,
    out_path: str,
    directorate_name: str,
    footer_lines: List[str],
) -> str:
    """
    توليد تقرير PDF كامل من نتيجة المعالجة.

    المعطيات:
      result: ProcessResult.
      out_path: مسار حفظ الـ PDF.
      directorate_name: اسم المديرية (يظهر في الرأس فقط، دون اسم المبرمج).
      footer_lines: أسطر التذييل (تظهر أسفل كل صفحة).

    تعيد مسار الملف المكتوب.
    """
    ensure_font()
    st = _styles()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    doc = _ReportDoc(
        out_path,
        footer_lines=footer_lines,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=28 * mm,   # مساحة للتذييل.
        title="تقرير معالجة التوطين",
    )

    flow = []
    # الرأس: اسم المديرية فقط (دون اسم المبرمج) + التاريخ.
    flow.append(Paragraph(ar(directorate_name), st["title"]))
    today = datetime.now().strftime("%Y-%m-%d")
    flow.append(Paragraph(ar(f"تقرير معالجة ملف التوطين — التاريخ: {today}"), st["subtitle"]))
    flow.append(Spacer(1, 4 * mm))
    flow.append(_stats_table(result.stats, st))
    flow.append(Spacer(1, 6 * mm))

    # القائمة التفصيلية.
    flow.append(Paragraph(ar("التقرير التفصيلي للمستفيدين"), st["section"]))
    flow.extend(_detail_items(result.final_rows, st))

    # الأقسام المنفصلة.
    flow.extend(_conflicts_section(result.name_conflicts, st))
    flow.extend(_alerts_section(result.alerts, st))
    flow.extend(_changes_section(result.folder_changes, st))

    doc.build(flow)
    return out_path


def build_report_filename(directory: str, prefix: str = "localization_report") -> str:
    """توليد اسم ملف تقرير يتضمن التاريخ والوقت."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return str(Path(directory) / f"{prefix}_{stamp}.pdf")
