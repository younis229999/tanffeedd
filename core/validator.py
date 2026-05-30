"""
التحقق والتنبيهات (Validation).

ينتج قائمة تنبيهات لكل صف مع: رقم الصف، الاسم، نوع المشكلة، القيمة، ومستوى الخطورة.
المستويات: ``critical`` (أحمر) و ``warning`` (برتقالي).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from .excel_loader import parse_amount


class Severity(str, Enum):
    """مستوى خطورة التنبيه (يُترجم إلى لون في الواجهة/التقرير)."""

    CRITICAL = "critical"   # أحمر — حرج
    WARNING = "warning"     # برتقالي — تحذير


# الألوان الدلالية (تُستخدم في الواجهة و PDF).
SEVERITY_COLORS = {
    Severity.CRITICAL: "#C0392B",   # أحمر
    Severity.WARNING: "#E67E22",    # برتقالي
}

SEVERITY_LABELS = {
    Severity.CRITICAL: "حرج",
    Severity.WARNING: "تحذير",
}


@dataclass
class Alert:
    """تنبيه واحد عن مشكلة في صف."""

    row_index: int          # رقم الصف للعرض (1-based)
    name: str
    issue: str              # وصف المشكلة بالعربية
    value: str              # القيمة المعنية (آيبان/مبلغ...)
    severity: Severity


def _iban_mod97_valid(iban: str) -> bool:
    """
    التحقق من خانات ضبط الآيبان عبر خوارزمية MOD-97 (ISO 13616).

    ينقل أول 4 خانات إلى النهاية، يحوّل الحروف إلى أرقام (A=10..Z=35)،
    ثم يتحقق أن الباقي على 97 يساوي 1.
    """
    s = iban.strip().upper().replace(" ", "")
    if len(s) < 5:
        return False
    rearranged = s[4:] + s[:4]
    digits = []
    for ch in rearranged:
        if ch.isdigit():
            digits.append(ch)
        elif "A" <= ch <= "Z":
            digits.append(str(ord(ch) - 55))  # A=10 ... Z=35
        else:
            return False
    try:
        return int("".join(digits)) % 97 == 1
    except ValueError:
        return False


def validate_row(
    row_index: int,
    name: str,
    amount: object,
    iban: str,
    *,
    iban_length: int,
    amount_max: float,
    iban_prefix: str,
    cancelled_ibans: set[str],
    mod97_check: bool = False,
) -> List[Alert]:
    """التحقق من صف واحد وإرجاع قائمة التنبيهات الخاصة به."""
    alerts: List[Alert] = []
    iban_norm = (iban or "").strip().upper().replace(" ", "")
    name = (name or "").strip()
    amount_val = parse_amount(amount)

    # حقول ناقصة.
    if not name:
        alerts.append(Alert(row_index, name, "حقل ناقص: الاسم فارغ", "", Severity.CRITICAL))
    if not iban_norm:
        alerts.append(Alert(row_index, name, "حقل ناقص: الآيبان فارغ", "", Severity.CRITICAL))
    if amount_val is None:
        alerts.append(
            Alert(row_index, name, "حقل ناقص: المبلغ فارغ أو غير صالح",
                  str(amount), Severity.CRITICAL)
        )

    # آيبان ملغي (أبرز تنبيه).
    if iban_norm and iban_norm in cancelled_ibans:
        alerts.append(
            Alert(row_index, name, "آيبان ملغي/كانسل — موجود ضمن القائمة الملغية",
                  iban_norm, Severity.CRITICAL)
        )

    # فحوص الآيبان (فقط إن لم يكن فارغاً).
    if iban_norm:
        if len(iban_norm) != iban_length:
            alerts.append(
                Alert(
                    row_index, name,
                    f"طول الآيبان غير صحيح — احتمال خطأ من الموظف (زيادة أو نقص). "
                    f"الطول={len(iban_norm)} والمتوقع={iban_length}",
                    iban_norm, Severity.CRITICAL,
                )
            )

        # نمط الآيبان العراقي: يبدأ بالبادئة، أرقام وحروف، بالطول المحدد.
        pattern = re.compile(rf"^{re.escape(iban_prefix)}[0-9A-Z]{{{iban_length - len(iban_prefix)}}}$")
        if not pattern.match(iban_norm):
            alerts.append(
                Alert(
                    row_index, name,
                    f"نمط الآيبان غير صحيح — يجب أن يبدأ بـ {iban_prefix} "
                    f"ويتكوّن من أرقام وحروف بطول {iban_length}",
                    iban_norm, Severity.CRITICAL,
                )
            )
        elif mod97_check and not _iban_mod97_valid(iban_norm):
            # فحص خانات الضبط الاختياري — تحذير لا حرج.
            alerts.append(
                Alert(
                    row_index, name,
                    "فشل التحقق من خانات الضبط (MOD-97) — راجع الآيبان",
                    iban_norm, Severity.WARNING,
                )
            )

    # المبلغ المرتفع.
    if amount_val is not None and amount_val > amount_max:
        alerts.append(
            Alert(
                row_index, name,
                f"مبلغ مرتفع، يرجى المراجعة (> {amount_max:,.0f})",
                f"{amount_val:,.0f}", Severity.WARNING,
            )
        )

    return alerts


def validate_rows(
    rows: List[dict],
    *,
    iban_length: int,
    amount_max: float,
    iban_prefix: str,
    cancelled_ibans: set[str],
    mod97_check: bool = False,
) -> List[Alert]:
    """
    التحقق من قائمة صفوف.

    كل صف قاموس فيه: name, amount, iban, و(اختياري) row_index.
    تعيد كل التنبيهات مجمّعة.
    """
    all_alerts: List[Alert] = []
    for i, row in enumerate(rows):
        ridx = int(row.get("row_index", i + 1))
        all_alerts.extend(
            validate_row(
                ridx,
                row.get("name", ""),
                row.get("amount", None),
                row.get("iban", ""),
                iban_length=iban_length,
                amount_max=amount_max,
                iban_prefix=iban_prefix,
                cancelled_ibans=cancelled_ibans,
                mod97_check=mod97_check,
            )
        )
    return all_alerts
