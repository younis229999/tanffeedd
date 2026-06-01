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


# تشكيل وتطويل لإزالتها عند التطبيع.
_TASHKEEL = re.compile(r"[ً-ْٰـ]")


def normalize_ar(text: str) -> str:
    """
    تطبيع نص عربي للبحث الذكي:
    - إزالة التشكيل والتطويل.
    - توحيد الألف (أ إ آ ٱ → ا)، والتاء المربوطة (ة → ه)،
      والألف المقصورة (ى → ي)، والهمزات (ؤ ئ).
    - توحيد المسافات.
    """
    if not text:
        return ""
    t = str(text)
    t = _TASHKEEL.sub("", t)
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"),
                 ("ة", "ه"), ("ى", "ي"), ("ئ", "ي"), ("ؤ", "و")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def name_matches(query: str, name: str) -> bool:
    """
    مطابقة ذكية لاسم: كل كلمة في البحث يجب أن ترد في الاسم (بأي ترتيب)،
    مع تجاهل الفروق في المسافات والأحرف (عبد الرحمن = عبدالرحمن، خولة = خوله).
    """
    nq = normalize_ar(query)
    if not nq:
        return False
    nn = normalize_ar(name)
    nn_nospace = nn.replace(" ", "")
    for token in nq.split():
        if token in nn or token in nn_nospace:
            continue
        return False
    return True


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
