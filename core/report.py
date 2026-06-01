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
    """تنسيق المبلغ بدون فواصل آلاف وبلا كسور."""
    try:
        return f"{int(round(float(value)))}"
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
            leading=15, textColor=colors.HexColor("#777777"),
        ),
        "card_value": ParagraphStyle(
            "cv", fontName=_FONT_NAME, fontSize=19, alignment=TA_CENTER,
            leading=24, textColor=colors.HexColor("#1F4E78"),
        ),
        "item": ParagraphStyle(
            "it", fontName=_FONT_NAME, fontSize=11.5, alignment=TA_RIGHT,
            leading=20, textColor=colors.HexColor("#222222"),
        ),
        "empty": ParagraphStyle(
            "e", fontName=_FONT_NAME, fontSize=11, alignment=TA_CENTER,
            leading=16, textColor=colors.grey, spaceBefore=8,
        ),
    }


def _stats_cards(stats, st) -> Table:
    """ثلاث بطاقات إحصائية في صف واحد (على نمط الصورة)."""
    # الترتيب من اليسار لليمين ليطابق الصورة:
    # إجمالي المبالغ | عدد المكررات | إجمالي السجلات
    cards = [
        ("إجمالي المبالغ", _fmt_amount(stats.total_amount)),
        ("عدد المكررات", f"{stats.merged_away}"),
        ("إجمالي السجلات", f"{stats.original_count}"),
    ]
    row = []
    for label, value in cards:
        cell = [
            Paragraph(ar(label), st["card_label"]),
            Spacer(1, 3 * mm),
            Paragraph(ar(value), st["card_value"]),
        ]
        row.append(cell)

    tbl = Table([row], colWidths=[60 * mm, 60 * mm, 60 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7FB")),
        ("BOX", (0, 0), (0, 0), 0.6, colors.HexColor("#D6E0EC")),
        ("BOX", (1, 0), (1, 0), 0.6, colors.HexColor("#D6E0EC")),
        ("BOX", (2, 0), (2, 0), 0.6, colors.HexColor("#D6E0EC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tbl


def _merged_items(final_rows, st) -> list:
    """قائمة «المعلومات»: المستفيدون المدموجون فقط (الاسم: مبلغ + مبلغ = الإجمالي)."""
    flow = [Paragraph(ar("المعلومات"), st["section"])]

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
        flow.append(Paragraph(ar(line), st["item"]))
    return flow


def generate_report(
    result,
    out_path: str,
    directorate_name: str,
    footer_lines: List[str],
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
    flow.extend(_merged_items(result.final_rows, st))

    doc.build(flow)
    return out_path


def build_report_filename(directory: str, prefix: str = "localization_report") -> str:
    """توليد اسم ملف تقرير يتضمن التاريخ والوقت."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return str(Path(directory) / f"{prefix}_{stamp}.pdf")
