"""
ميزة «الكشف والبحث».

تخزّن ملف إكسل كاملاً للمستلمين (الاسم، المبلغ، رقم الإضبارة، الآيبان، التاريخ)
بنفس خريطة أعمدة المعالجة (A/E/H/I) مع عمود التاريخ (B). تتيح:
- استيراد ملف وتخزينه دائماً (وحذفه ورفع أحدث منه).
- بحثاً ذكياً بالاسم (يعالج الأحرف العربية والمسافات).
- بناء كشف لكل شخص: مبالغه وتواريخه ومجموعه وآيبانه وإضبارته واسمه الكامل.

التجميع للشخص يكون على أساس الآيبان (الحساب الفريد)، وإلا الاسم.
"""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from openpyxl.utils import column_index_from_string

from .excel_loader import parse_amount
from .folder_number import normalize_digits
from .names import name_matches, normalize_ar


def _writable_root() -> Path:
    """جذر قابل للكتابة (يصلح للتطوير والتغليف)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


@dataclass
class LedgerEntry:
    """عملية استلام واحدة (تاريخ + مبلغ + رقم الإضبارة الخاص بها)."""

    date_raw: str
    date_key: int          # YYYYMMDD كعدد للفرز والتصفية (0 إن تعذّر).
    date_fmt: str          # صيغة منتظمة "YYYY-MM-DD".
    amount: float
    folder: str = ""       # رقم الإضبارة الخاص بهذه العملية.


@dataclass
class Person:
    """شخص (حساب) وكل عملياته."""

    name: str                              # الاسم الكامل
    iban: str
    folder: str
    entries: List[LedgerEntry] = field(default_factory=list)
    name_variants: List[str] = field(default_factory=list)
    _norm: str = ""                        # اسم مطبّع للبحث
    _norm_nospace: str = ""

    @property
    def total(self) -> float:
        return sum(e.amount for e in self.entries)

    @property
    def count(self) -> int:
        return len(self.entries)

    def total_until(self, date_key: int) -> float:
        """مجموع المبالغ لغاية تاريخ معيّن (شاملاً)."""
        return sum(e.amount for e in self.entries
                   if e.date_key == 0 or e.date_key <= date_key)


def format_date(raw: object) -> tuple[str, int]:
    """
    تحويل قيمة تاريخ خام إلى (صيغة منتظمة YYYY-MM-DD، مفتاح فرز رقمي).

    يتعامل مع الصيغة 20260502 والأرقام العربية والتواريخ الجاهزة.
    """
    if raw is None:
        return "", 0
    # تاريخ/وقت جاهز من إكسل.
    if isinstance(raw, pd.Timestamp) or hasattr(raw, "strftime"):
        try:
            return raw.strftime("%Y-%m-%d"), int(raw.strftime("%Y%m%d"))
        except Exception:  # noqa: BLE001
            pass
    s = normalize_digits(str(raw)).strip()
    digits = re.sub(r"\D", "", s)
    if len(digits) == 8:                       # YYYYMMDD
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}", int(digits)
    if len(digits) == 6:                       # YYYYMM
        return f"{digits[:4]}-{digits[4:6]}", int(digits + "00")
    return (s, int(digits) if digits else 0)


class LedgerStore:
    """مخزن ملف الكشف الدائم وعملياته."""

    def __init__(self, settings):
        self.settings = settings
        self.persons: List[Person] = []
        self.row_count: int = 0
        self.source_name: str = ""
        self.load()

    # ------------------------------- المسارات -------------------------------
    def _data_dir(self) -> Path:
        d = _writable_root() / "data"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def ledger_path(self) -> Path:
        return self._data_dir() / "ledger.xlsx"

    def name_path(self) -> Path:
        return self._data_dir() / "ledger_name.txt"

    def has_data(self) -> bool:
        return self.ledger_path().exists() and bool(self.persons)

    # ------------------------------ استيراد/حذف ------------------------------
    def import_file(self, src_path: str) -> int:
        """نسخ ملف الكشف وتخزينه دائماً ثم تحليله. يعيد عدد الصفوف."""
        shutil.copy2(src_path, self.ledger_path())
        self.name_path().write_text(Path(src_path).name, encoding="utf-8")
        self.load()
        return self.row_count

    def clear(self) -> None:
        """حذف الملف المخزّن."""
        for p in (self.ledger_path(), self.name_path()):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        self.persons = []
        self.row_count = 0
        self.source_name = ""

    # ------------------------------- التحميل -------------------------------
    def load(self) -> None:
        self.persons = []
        self.row_count = 0
        path = self.ledger_path()
        if not path.exists():
            return
        if self.name_path().exists():
            self.source_name = self.name_path().read_text(encoding="utf-8").strip()
        try:
            self._parse(path)
        except Exception:  # noqa: BLE001 — ملف تالف لا يُعطّل التطبيق.
            self.persons = []
            self.row_count = 0

    def _col(self, key: str, default: str) -> int:
        letter = self.settings.columns.get(key, default)
        return column_index_from_string(str(letter).strip().upper()) - 1

    def _parse(self, path: Path) -> None:
        raw = pd.read_excel(path, header=None, dtype=object, engine="openpyxl")
        if self.settings.has_header and len(raw) > 0:
            raw = raw.iloc[1:].reset_index(drop=True)

        ci = {
            "folder": self._col("folder", "A"),
            "amount": self._col("amount", "E"),
            "name": self._col("name", "H"),
            "iban": self._col("iban", "I"),
            "date": self._col("date", "B"),
        }
        max_needed = max(ci.values())

        groups: Dict[str, Person] = {}
        order: List[str] = []
        count = 0

        for _, row in raw.iterrows():
            if raw.shape[1] <= max_needed:
                break
            name = _txt(row.iloc[ci["name"]])
            iban = _txt(row.iloc[ci["iban"]]).replace(" ", "").upper()
            folder = _txt(row.iloc[ci["folder"]])
            amount = parse_amount(row.iloc[ci["amount"]]) or 0.0
            date_fmt, date_key = format_date(row.iloc[ci["date"]])

            if not name and not iban:
                continue
            count += 1

            key = iban if iban else f"__name__{normalize_ar(name)}"
            person = groups.get(key)
            if person is None:
                person = Person(name=name, iban=iban, folder=folder)
                groups[key] = person
                order.append(key)
            person.entries.append(
                LedgerEntry(date_raw=_txt(row.iloc[ci["date"]]),
                            date_key=date_key, date_fmt=date_fmt, amount=amount,
                            folder=folder)
            )
            if name and name not in person.name_variants:
                person.name_variants.append(name)
                # نختار أطول اسم كاسم كامل للعرض.
                if len(name) > len(person.name):
                    person.name = name

        # ترتيب العمليات تنازلياً (الأحدث أولاً) وحساب التطبيع للبحث.
        for key in order:
            p = groups[key]
            p.entries.sort(key=lambda e: e.date_key, reverse=True)
            variants = p.name_variants or [p.name]
            norm = " ".join(normalize_ar(v) for v in variants)
            p._norm = norm
            p._norm_nospace = norm.replace(" ", "")

        self.persons = [groups[k] for k in order]
        self.row_count = count

    # -------------------------------- البحث --------------------------------
    def search(self, query: str, limit: int = 60) -> List[Person]:
        """بحث ذكي بالاسم؛ يعيد الأشخاص المطابقين (حتى limit)."""
        q = normalize_ar(query)
        if not q:
            return []
        tokens = q.split()
        results: List[Person] = []
        for p in self.persons:
            if all(t in p._norm or t in p._norm_nospace for t in tokens):
                results.append(p)
                if len(results) >= limit:
                    break
        # الأقصر اسماً أولاً (الأقرب للمطابقة التامة) ثم أبجدياً.
        results.sort(key=lambda p: (len(p.name), p.name))
        return results


def _txt(value: object) -> str:
    """تحويل خلية إلى نص نظيف."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    s = str(value).strip()
    return "" if s.lower() == "nan" else s
