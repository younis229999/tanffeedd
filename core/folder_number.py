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
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
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
        # الرقم = أول مجموعة أرقام غير السنة (نتجاهل التكرار، نحتفظ برقم واحد).
        rest = runs[:year_idx] + runs[year_idx + 1:]
        if not rest:
            # سنة فقط دون رقم — نعتبره ناقصاً.
            return year, None, False
        return year, _normalize_number(rest[0]), True

    # لا توجد مجموعة من 4 خانات: حالة مجموعة واحدة طويلة مثل 202565.
    joined = "".join(runs)
    if len(joined) > 4:
        head = joined[:4]
        if _MIN_YEAR <= int(head) <= _MAX_YEAR:
            return head, _normalize_number(joined[4:]), True

    # تعذّر تمييز السنة — نُعيد الأرقام كرقم دون سنة (يُعرض كحالة تحتاج مراجعة).
    return None, _normalize_number(joined), False


def build_folder(year: Optional[str], number: Optional[str]) -> str:
    """بناء النص النهائي ``YYYY_NN`` (السنة_الرقم فقط، بلا بادئات)."""
    if year and number:
        return f"{year}_{number}"
    if number:
        return number          # سنة مجهولة — نعرض الرقم فقط دون أي بادئة.
    if year:
        return year
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


def dominant_year(raw_folders: List[object]) -> str:
    """السنة الأكثر تكراراً بين القيم الصحيحة (للتعبئة التلقائية)؛ وإلا السنة الحالية."""
    years: List[str] = []
    for raw in raw_folders:
        y, _num, valid = parse_folder(raw)
        if valid and y:
            years.append(y)
    if years:
        return Counter(years).most_common(1)[0][0]
    return str(datetime.now().year)


def clean_and_dedupe(
    raw_folders: List[object],
    names: Optional[List[str]] = None,
    year_for_fill: Optional[str] = None,
) -> Tuple[List[str], List[FolderChange]]:
    """
    تنظيف أرقام الأضابير وتفريدها، مع تعبئة الحقول الفارغة/غير الصالحة تلقائياً.

    القواعد:
      - القيمة الصحيحة (سنة + رقم) تُنظَّف إلى ``YYYY_NN``؛ وإذا تكررت يُعاد ترقيمها
        بأصغر رقم متاح ضمن نفس سنتها.
      - القيمة الفارغة أو غير الصالحة (بلا سنة، مثل ``8479798``) تُملأ تلقائياً
        بالصيغة ``السنة_الرقم`` باستخدام السنة السائدة وأصغر رقم متاح.

    تعيد (folders, changes) بنفس ترتيب الإدخال.
    """
    if names is None:
        names = ["" for _ in raw_folders]
    n = len(raw_folders)
    fill_year = year_for_fill or dominant_year(raw_folders)

    result: List[Optional[str]] = [None] * n
    used: set[str] = set()
    changes: List[FolderChange] = []
    pending: List[Tuple[int, str]] = []   # حقول تحتاج تعبئة تلقائية

    def _name(i: int) -> str:
        return names[i] if i < len(names) else ""

    # المرحلة 1: القيم الصحيحة (سنة + رقم) — نثبّتها أولاً ونرصد الأرقام المستخدمة.
    for idx, raw in enumerate(raw_folders):
        old_display = "" if raw is None else str(raw).strip()
        cleaned, ok = clean_folder(raw)
        if ok and "_" in cleaned:
            reasons: List[str] = []
            final = cleaned
            if cleaned != old_display:
                reasons.append("تنظيف الصيغة")
            if final in used:
                year, _num, _v = parse_folder(final)
                final = _smallest_available(year or fill_year, used)
                reasons.append("فك تكرار")
            used.add(final)
            result[idx] = final
            if reasons and final != old_display:
                changes.append(FolderChange(idx + 1, _name(idx), old_display, final,
                                            " + ".join(reasons)))
        else:
            pending.append((idx, old_display))

    # المرحلة 2: الحقول الفارغة/غير الصالحة → تعبئة تلقائية بالسنة السائدة.
    for idx, old_display in pending:
        final = _smallest_available(fill_year, used)
        used.add(final)
        result[idx] = final
        reason = "تعبئة تلقائية (حقل فارغ)" if old_display == "" \
            else "تعبئة تلقائية (قيمة بلا سنة)"
        changes.append(FolderChange(idx + 1, _name(idx), old_display, final, reason))

    return [r or "" for r in result], changes
