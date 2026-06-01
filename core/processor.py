"""
المنسّق (Orchestrator) — يجمع خطوات المعالجة في خط واحد.

التسلسل:
1. تحميل البيانات من Excel.
2. تنظيف صيغة أرقام الأضابير (تنسيق فقط) مع تسجيل التغييرات.
3. الدمج على أساس الآيبان وجمع المبالغ.
4. تفريد أرقام الأضابير على الصفوف المدموجة (فك التكرار) مع تسجيل التغييرات.
5. التحقق والتنبيهات على البيانات النهائية.
6. حساب الإحصائيات.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .excel_loader import LoadedData, load_excel, parse_amount
from .folder_number import FolderChange, clean_and_dedupe, clean_folder
from .merger import MergeResult, NameConflict, merge_by_iban
from .names import shorten_name
from .settings import Settings
from .validator import Alert, Severity, validate_rows


@dataclass
class Statistics:
    """إحصائيات موجزة للتقرير والملخص."""

    original_count: int = 0
    merged_count: int = 0
    merged_away: int = 0
    alerts_count: int = 0
    critical_count: int = 0
    warning_count: int = 0
    total_amount: float = 0.0


@dataclass
class ProcessResult:
    """الناتج الكامل للمعالجة — يُمرَّر للواجهة والمخرجات."""

    final_rows: List[Dict[str, object]] = field(default_factory=list)
    alerts: List[Alert] = field(default_factory=list)
    folder_changes: List[FolderChange] = field(default_factory=list)
    name_conflicts: List[NameConflict] = field(default_factory=list)
    stats: Statistics = field(default_factory=Statistics)
    source_path: str = ""


def process_file(path: str, settings: Settings) -> ProcessResult:
    """تحميل ملف ومعالجته بالكامل وفق الإعدادات."""
    data = load_excel(path, settings.columns, settings.has_header)
    return process_loaded(data, settings)


def process_loaded(data: LoadedData, settings: Settings) -> ProcessResult:
    """معالجة بيانات محمّلة مسبقاً (مفيد عند المعاينة قبل المعالجة)."""
    n = len(data)

    # 2) تنظيف صيغة أرقام الأضابير (تنسيق فقط، دون فك تكرار بعد).
    formatted_folders: List[str] = []
    format_changes: List[FolderChange] = []
    for i in range(n):
        raw = data.folders[i]
        cleaned, ok = clean_folder(raw)
        formatted_folders.append(cleaned)
        old_display = "" if raw is None else str(raw).strip()
        if cleaned != old_display:
            reason = "تنظيف الصيغة"
            if not ok:
                reason += " + تعذّر تحديد السنة — مراجعة مطلوبة"
            format_changes.append(
                FolderChange(
                    row_index=i + 1,
                    name=data.names[i] if i < len(data.names) else "",
                    old_value=old_display,
                    new_value=cleaned,
                    reason=reason,
                )
            )

    # 3) الدمج على أساس الآيبان.
    merge: MergeResult = merge_by_iban(
        folders=formatted_folders,
        amounts=data.amounts,
        names=data.names,
        ibans=data.ibans,
    )

    # 4) تفريد أرقام الأضابير على الصفوف المدموجة (فك التكرار).
    merged_folders = [row.folder for row in merge.rows]
    merged_names = [row.name for row in merge.rows]
    final_folders, dedupe_changes = clean_and_dedupe(merged_folders, merged_names)

    # بناء الصفوف النهائية.
    final_rows: List[Dict[str, object]] = []
    total_amount = 0.0
    for i, row in enumerate(merge.rows):
        total_amount += row.total_amount
        final_rows.append(
            {
                "row_index": i + 1,
                "folder": final_folders[i],
                "amount": row.total_amount,
                # تقصير الاسم الطويل إلى ثلاثي (المصارف لا تقبل الأسماء الطويلة).
                "name": shorten_name(row.name),
                "iban": row.iban,
                "component_amounts": row.component_amounts,
                "source_rows": row.source_rows,
            }
        )

    # 5) التحقق والتنبيهات على الصفوف النهائية.
    alerts = validate_rows(
        final_rows,
        iban_length=settings.iban_length,
        amount_max=settings.amount_max,
        iban_prefix=settings.iban_prefix,
        cancelled_ibans=settings.cancelled_ibans_set(),
        mod97_check=settings.iban_mod97_check,
    )

    # دمج تغييرات الأضابير (تنسيق + فك تكرار).
    all_changes = format_changes + dedupe_changes

    critical = sum(1 for a in alerts if a.severity == Severity.CRITICAL)
    warning = sum(1 for a in alerts if a.severity == Severity.WARNING)

    stats = Statistics(
        original_count=merge.original_count,
        merged_count=merge.merged_count,
        merged_away=merge.merged_away,
        alerts_count=len(alerts),
        critical_count=critical,
        warning_count=warning,
        total_amount=total_amount,
    )

    return ProcessResult(
        final_rows=final_rows,
        alerts=alerts,
        folder_changes=all_changes,
        name_conflicts=merge.name_conflicts,
        stats=stats,
        source_path=data.source_path,
    )
