"""
دمج المكررات وجمع المبالغ.

القاعدة الأساسية:
- مفتاح الدمج هو الآيبان فقط (عمود I) — لا شيء غيره.
- كل الصفوف ذات نفس الآيبان تُدمج في صف واحد ويُجمع المبلغ.
- تكرار الأسماء لا يُدمج إطلاقاً (نفس الاسم بآيبان مختلف = حسابان مختلفان).
- الاسم يُؤخذ من أول ظهور للآيبان.
- اختلاف الاسم لنفس الآيبان يُسجَّل كتعارض ليراجعه المستخدم (مع إتمام الدمج).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .excel_loader import parse_amount


@dataclass
class MergedRow:
    """صف ناتج عن الدمج على الآيبان."""

    iban: str
    name: str                          # اسم أول ظهور
    total_amount: float                # مجموع المبالغ
    component_amounts: List[float] = field(default_factory=list)  # المبالغ قبل الجمع
    folder: object = ""                # رقم الإضبارة (أول ظهور، يُفرّد لاحقاً)
    source_rows: List[int] = field(default_factory=list)          # أرقام الصفوف الأصلية
    name_variants: List[str] = field(default_factory=list)        # كل الأسماء المشاهدة


@dataclass
class NameConflict:
    """تعارض في الاسم لنفس الآيبان."""

    iban: str
    names: List[str]
    rows: List[int]


@dataclass
class MergeResult:
    """نتيجة عملية الدمج."""

    rows: List[MergedRow]
    name_conflicts: List[NameConflict]
    original_count: int
    merged_count: int            # عدد الصفوف بعد الدمج

    @property
    def merged_away(self) -> int:
        """عدد الصفوف التي اختفت بفعل الدمج."""
        return self.original_count - self.merged_count


def merge_by_iban(
    folders: List[object],
    amounts: List[object],
    names: List[str],
    ibans: List[str],
) -> MergeResult:
    """
    دمج الصفوف على أساس الآيبان.

    المعطيات قوائم متوازية بنفس الطول (صف لكل عنصر).
    تعيد MergeResult يحوي الصفوف المدموجة وتعارضات الأسماء.
    """
    n = len(ibans)
    # نحافظ على ترتيب أول ظهور لكل آيبان.
    order: List[str] = []
    groups: Dict[str, MergedRow] = {}
    # صفوف بلا آيبان (فارغ) لا يمكن دمجها — تبقى منفصلة بمفتاح فريد.
    blank_counter = 0

    for i in range(n):
        iban = (ibans[i] or "").strip().upper()
        name = (names[i] or "").strip()
        amount = parse_amount(amounts[i]) or 0.0

        if iban == "":
            # آيبان فارغ: لا يُدمج، مفتاح فريد لكل صف.
            blank_counter += 1
            key = f"__BLANK__{blank_counter}"
        else:
            key = iban

        if key not in groups:
            order.append(key)
            groups[key] = MergedRow(
                iban=iban,
                name=name,
                total_amount=amount,
                component_amounts=[amount],
                folder=folders[i] if i < len(folders) else "",
                source_rows=[i + 1],
                name_variants=[name] if name else [],
            )
        else:
            row = groups[key]
            row.total_amount += amount
            row.component_amounts.append(amount)
            row.source_rows.append(i + 1)
            if name and name not in row.name_variants:
                row.name_variants.append(name)

    merged_rows = [groups[k] for k in order]

    # رصد تعارضات الأسماء (آيبان واحد بأسماء مختلفة).
    conflicts: List[NameConflict] = []
    for row in merged_rows:
        if row.iban and len(row.name_variants) > 1:
            conflicts.append(
                NameConflict(
                    iban=row.iban,
                    names=list(row.name_variants),
                    rows=list(row.source_rows),
                )
            )

    return MergeResult(
        rows=merged_rows,
        name_conflicts=conflicts,
        original_count=n,
        merged_count=len(merged_rows),
    )
