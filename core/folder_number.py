"""
تنظيف أرقام الأضابير وتفريدها.

المهام:
1. تحويل أي صيغة مدخلة إلى الصيغة القياسية: ``YYYY_NN`` (السنة_الرقم).
   - إزالة كل الأحرف (عربية/إنجليزية) والرموز، والإبقاء على الأرقام فقط.
   - استخدام regex لاستخراج مجموعات الأرقام وتمييز السنة (4 خانات) عن الرقم.
2. منع تكرار رقم الإضبارة داخل الملف الواحد: إذا تكرر رقم، نُبقي نفس السنة
   ونُسند أصغر رقم متاح غير مستخدم في الملف، ونُسجّل التغيير (القديم ← الجديد).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

# سنة منطقية معقولة لأرقام الأضابير.
_MIN_YEAR = 1990
_MAX_YEAR = 2100

# تطبيع الأرقام العربية-الهندية والفارسية إلى أرقام غربية (ASCII).
_DIGIT_MAP = {ord(c): str(i % 10) for i, c in enumerate(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹"
)}

# بعد التطبيع نبحث فقط عن أرقام ASCII لتجنّب رموز يونيكود أخرى.
_DIGIT_RUN = re.compile(r"[0-9]+")


def normalize_digits(text: str) -> str:
    """تحويل الأرقام العربية-الهندية/الفارسية إلى أرقام غربية."""
    return str(text).translate(_DIGIT_MAP)


@dataclass
class FolderChange:
    """سجل تغيير رقم إضبارة (لعرضه للمستخدم: لا تغييرات صامتة)."""

    row_index: int          # رقم الصف (1-based لأغراض العرض)
    name: str               # اسم المستفيد لتسهيل التتبع
    old_value: str          # القيمة كما وردت في الملف الأصلي
    new_value: str          # القيمة بعد التنظيف/التفريد
    reason: str             # سبب التغيير (تنظيف / فك تكرار)


def _normalize_number(num_str: str) -> str:
    """إزالة الأصفار البادئة من الرقم مع الإبقاء على خانة واحدة على الأقل."""
    stripped = num_str.lstrip("0")
    return stripped if stripped else "0"


def parse_folder(raw: object) -> Tuple[Optional[str], Optional[str], bool]:
    """
    تحليل قيمة إضبارة خام إلى (السنة، الرقم، هل النجاح تام؟).

    تعيد (year, number, ok):
    - year, number نصوص أو None إذا تعذّر الاستخراج.
    - ok = True إذا أمكن تحديد سنة (4 خانات) ورقم بوضوح.
    """
    if raw is None:
        return None, None, False

    text = normalize_digits(str(raw).strip())
    if not text:
        return None, None, False

    runs = _DIGIT_RUN.findall(text)
    if not runs:
        return None, None, False

    # حدد مجموعة السنة: أول مجموعة من 4 خانات ضمن مدى منطقي،
    # وإلا أول مجموعة من 4 خانات أياً كانت.
    year_idx = None
    for i, run in enumerate(runs):
        if len(run) == 4 and _MIN_YEAR <= int(run) <= _MAX_YEAR:
            year_idx = i
            break
    if year_idx is None:
        for i, run in enumerate(runs):
            if len(run) == 4:
                year_idx = i
                break

    if year_idx is not None:
        year = runs[year_idx]
        # الرقم = بقية المجموعات (بالترتيب) مدموجة.
        rest = runs[:year_idx] + runs[year_idx + 1:]
        number = "".join(rest) if rest else ""
        if number == "":
            # سنة فقط دون رقم — نعتبره ناقصاً.
            return year, None, False
        return year, _normalize_number(number), True

    # لا توجد مجموعة من 4 خانات: حالة مجموعة واحدة طويلة مثل 202565.
    joined = "".join(runs)
    if len(joined) > 4:
        head = joined[:4]
        if _MIN_YEAR <= int(head) <= _MAX_YEAR:
            return head, _normalize_number(joined[4:]), True

    # تعذّر تمييز السنة — نُعيد الأرقام كرقم دون سنة (يُعرض كحالة تحتاج مراجعة).
    return None, _normalize_number(joined), False


def build_folder(year: Optional[str], number: Optional[str]) -> str:
    """بناء النص النهائي ``YYYY_NN``. عند نقص السنة نستخدم بادئة فارغة واضحة."""
    if year and number:
        return f"{year}_{number}"
    if number:
        return f"____{number}"   # سنة مجهولة — علامة بصرية تستدعي المراجعة.
    if year:
        return f"{year}_"
    return ""


def clean_folder(raw: object) -> Tuple[str, bool]:
    """
    تنظيف قيمة إضبارة واحدة إلى الصيغة ``YYYY_NN``.

    تعيد (cleaned, ok) حيث ok=False إذا تعذّر استخراج سنة صحيحة.
    """
    year, number, ok = parse_folder(raw)
    return build_folder(year, number), ok


def _smallest_available(year: str, used: set[str]) -> str:
    """أصغر رقم صحيح ≥ 1 بحيث ``year_n`` غير مستخدم في الملف."""
    n = 1
    while f"{year}_{n}" in used:
        n += 1
    return f"{year}_{n}"


def clean_and_dedupe(
    raw_folders: List[object],
    names: Optional[List[str]] = None,
) -> Tuple[List[str], List[FolderChange]]:
    """
    تنظيف قائمة أرقام أضابير وتفريدها داخل الملف الواحد.

    المعطيات:
      raw_folders: القيم الخام بترتيب الصفوف.
      names: أسماء المستفيدين (اختياري) لإثراء سجل التغييرات.

    تعيد:
      (cleaned_folders, changes)
      - cleaned_folders: القيم النهائية الفريدة بنفس ترتيب الإدخال.
      - changes: قائمة بكل تغيير حصل (تنظيف غيّر الشكل، أو فك تكرار).
    """
    if names is None:
        names = ["" for _ in raw_folders]

    used: set[str] = set()
    result: List[str] = []
    changes: List[FolderChange] = []

    for idx, raw in enumerate(raw_folders):
        old_display = "" if raw is None else str(raw).strip()
        cleaned, ok = clean_folder(raw)

        reason_parts: List[str] = []
        # هل غيّر التنظيف الشكل الظاهر؟
        if cleaned != old_display:
            reason_parts.append("تنظيف الصيغة")
        if not ok:
            reason_parts.append("تعذّر تحديد السنة — مراجعة مطلوبة")

        final = cleaned
        # فك التكرار: إن كان الشكل النهائي مستخدماً ولديه سنة معروفة.
        if final and final in used:
            year, _number, year_ok = parse_folder(final)
            if year and year_ok is not None and "_" in final and not final.startswith("____"):
                final = _smallest_available(year, used)
                reason_parts.append("فك تكرار")
            else:
                # سنة مجهولة — لا يمكن تفريدها بأمان؛ نضيف لاحقة فريدة بسيطة.
                suffix = 1
                base = final
                while f"{base}#{suffix}" in used:
                    suffix += 1
                final = f"{base}#{suffix}"
                reason_parts.append("فك تكرار (سنة مجهولة)")

        used.add(final)
        result.append(final)

        if reason_parts and final != old_display:
            changes.append(
                FolderChange(
                    row_index=idx + 1,
                    name=names[idx] if idx < len(names) else "",
                    old_value=old_display,
                    new_value=final,
                    reason=" + ".join(reason_parts),
                )
            )

    return result, changes
