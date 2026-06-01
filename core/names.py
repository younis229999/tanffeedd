"""
تقصير الأسماء الطويلة إلى اسم ثلاثي.

المصارف لا تقبل الأسماء الطويلة، لذا نُبقي أول ثلاثة «أجزاء» من الاسم،
مع مراعاة الأسماء المركّبة (مثل «عبد الرحمن» تُعدّ جزءاً واحداً،
و«نور الدين» / «عبد الله» كذلك).
"""

from __future__ import annotations

import re

# بادئات تلتصق بالكلمة التالية لتُكوّن وحدة اسم واحدة.
_PREFIX_JOIN = {
    "عبد", "عبدال",
    "ابو", "أبو", "ابن", "بن", "آل", "ال",
    "ام", "أم",
}

# لواحق تلتصق بالكلمة السابقة (… الدين / … الله / … الإسلام).
_SUFFIX_JOIN = {
    "الدين", "الله", "اللّه", "الإسلام", "الاسلام", "الرحمن", "الرحيم",
}


def shorten_name(name: str, max_units: int = 3) -> str:
    """
    إرجاع الاسم مقتصراً على أول ``max_units`` أجزاء (افتراضياً ثلاثي)،
    مع دمج الأسماء المركّبة في جزء واحد.
    """
    if not name:
        return name

    # توحيد المسافات.
    tokens = re.split(r"\s+", str(name).strip())
    tokens = [t for t in tokens if t]
    if not tokens:
        return ""

    units: list[str] = []
    pending = ""  # بادئة تنتظر الكلمة التالية.

    for tok in tokens:
        # لاحقة تلتصق بالوحدة السابقة (مثل «الدين»).
        if tok in _SUFFIX_JOIN and units and not pending:
            units[-1] = units[-1] + " " + tok
            continue
        # كلمة تُكمل بادئة سابقة (مثل «عبد» + «الرحمن»).
        if pending:
            units.append(pending + " " + tok)
            pending = ""
            continue
        # بادئة تلتصق بالكلمة التالية.
        if tok in _PREFIX_JOIN:
            pending = tok
            continue
        units.append(tok)

    if pending:  # بادئة في نهاية الاسم بلا تكملة.
        units.append(pending)

    return " ".join(units[:max_units])
