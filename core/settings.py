"""
إدارة الإعدادات (settings.json).

- تحميل الإعدادات من الملف، أو إنشاء إعدادات افتراضية إذا لم يوجد.
- حفظ الإعدادات مع إنشاء نسخة احتياطية تلقائية لقائمة الآيبانات الملغية.
- توفير دوال مساعدة لإدارة قائمة الآيبانات الملغية.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


# الإعدادات الافتراضية — تُستخدم عند غياب الملف أو نقص مفتاح ما.
DEFAULT_SETTINGS: Dict[str, Any] = {
    "directorate_name": "مديرية تنفيذ كركوك",
    # اسم الشعبة واسم المبرمج ثابتان (غير قابلين للتعديل من الإعدادات).
    "section_name": "شعبة الحاسبة",
    "programmer_name": "@Younis shaker",
    "columns": {
        "folder": "A",
        "amount": "E",
        "name": "H",
        "iban": "I",
        "date": "B",     # عمود التاريخ (يُستخدم في ميزة الكشف والبحث).
    },
    "has_header": True,
    # هل يعالج البرنامج عمود رقم الإضبارة (A)؟ إن كان False يُترك كما هو.
    "process_folders": True,
    # هل يُظهر التقرير رقم الإضبارة تحت كل مبلغ؟
    "report_show_folder": True,
    "thresholds": {
        "amount_max": 10_000_000,
        "iban_length": 23,
    },
    "iban_country_prefix": "IQ",
    "iban_mod97_check": False,
    "cancelled_ibans": [],
}


def _project_root() -> Path:
    """جذر المشروع (المجلد الذي يحوي مجلد config) — يصلح للتطوير والتغليف."""
    if getattr(sys, "frozen", False):
        # وضع التغليف (PyInstaller): مجلد الملف التنفيذي للحفظ الدائم.
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _bundled_settings_path() -> Path:
    """مسار النسخة المضمّنة من الإعدادات (للبذر عند أول تشغيل)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", _project_root()))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "config" / "settings.json"


def default_settings_path() -> Path:
    """المسار الدائم لملف الإعدادات (قابل للكتابة)."""
    return _project_root() / "config" / "settings.json"


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """دمج قاموسين بعمق: قيم override تطغى مع الإبقاء على المفاتيح الناقصة من base."""
    result = deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


class Settings:
    """غلاف حول قاموس الإعدادات مع تحميل/حفظ."""

    def __init__(self, path: str | os.PathLike | None = None):
        self.path = Path(path) if path else default_settings_path()
        self.data: Dict[str, Any] = deepcopy(DEFAULT_SETTINGS)
        self.load()

    # ----------------------------- تحميل/حفظ -----------------------------
    def load(self) -> None:
        """تحميل الإعدادات من الملف ودمجها مع الافتراضي."""
        # عند أول تشغيل (لا يوجد ملف قابل للكتابة) نبذر من النسخة المضمّنة إن وُجدت.
        if not self.path.exists():
            bundled = _bundled_settings_path()
            if bundled.exists() and bundled.resolve() != self.path.resolve():
                try:
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(bundled, self.path)
                except OSError:
                    pass

        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self.data = _deep_merge(DEFAULT_SETTINGS, loaded)
            except (json.JSONDecodeError, OSError):
                # ملف تالف — نرجع للافتراضي دون أن نتعطل.
                self.data = deepcopy(DEFAULT_SETTINGS)
        else:
            self.data = deepcopy(DEFAULT_SETTINGS)
            self.save()

    def save(self) -> None:
        """حفظ الإعدادات مع نسخة احتياطية تلقائية إن وُجد ملف سابق."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self._backup()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _backup(self) -> None:
        """إنشاء نسخة احتياطية من ملف الإعدادات (يحفظ قائمة الآيبانات الملغية)."""
        backup_dir = self.path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"settings_{stamp}.json"
        try:
            shutil.copy2(self.path, backup_path)
        except OSError:
            pass  # فشل النسخ الاحتياطي لا يجب أن يمنع الحفظ.

    # --------------------------- وصول مختصر ---------------------------
    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    @property
    def directorate_name(self) -> str:
        return self.data.get("directorate_name", "")

    @property
    def section_name(self) -> str:
        # ثابت (غير قابل للتعديل من الإعدادات).
        return self.data.get("section_name", "شعبة الحاسبة")

    @property
    def programmer_name(self) -> str:
        # ثابت (غير قابل للتعديل من الإعدادات) — يظهر في التذييل فقط.
        return self.data.get("programmer_name", "@Younis shaker")

    @property
    def footer_lines(self) -> List[str]:
        """
        أسطر التذييل مشتقّة تلقائياً:
        السطر الأول = اسم المديرية (يتبع الإعدادات)،
        والثاني = اسم الشعبة الثابت، والثالث = اسم المبرمج الثابت.
        """
        return [self.directorate_name, self.section_name, self.programmer_name]

    @property
    def report_footer_lines(self) -> List[str]:
        """تذييل التقرير (PDF) — بدون اسم المبرمج إطلاقاً."""
        return [self.directorate_name, self.section_name]

    @property
    def columns(self) -> Dict[str, str]:
        return dict(self.data.get("columns", {}))

    @property
    def has_header(self) -> bool:
        return bool(self.data.get("has_header", True))

    @property
    def process_folders(self) -> bool:
        """هل يعالج البرنامج أرقام الأضابير (عمود A)؟"""
        return bool(self.data.get("process_folders", True))

    @property
    def report_show_folder(self) -> bool:
        """هل يُظهر التقرير رقم الإضبارة تحت كل مبلغ؟"""
        return bool(self.data.get("report_show_folder", True))

    @property
    def amount_max(self) -> float:
        return float(self.data.get("thresholds", {}).get("amount_max", 10_000_000))

    @property
    def iban_length(self) -> int:
        return int(self.data.get("thresholds", {}).get("iban_length", 23))

    @property
    def iban_prefix(self) -> str:
        return str(self.data.get("iban_country_prefix", "IQ"))

    @property
    def iban_mod97_check(self) -> bool:
        return bool(self.data.get("iban_mod97_check", False))

    # ----------------------- قائمة الآيبانات الملغية -----------------------
    @property
    def cancelled_ibans(self) -> List[str]:
        return list(self.data.get("cancelled_ibans", []))

    def _normalize_iban(self, iban: str) -> str:
        """توحيد الآيبان للمقارنة: إزالة المسافات وتحويله لأحرف كبيرة."""
        return "".join(str(iban).split()).upper()

    def add_cancelled_iban(self, iban: str) -> bool:
        """إضافة آيبان للقائمة الملغية. يعيد True إذا أُضيف فعلاً."""
        norm = self._normalize_iban(iban)
        if not norm:
            return False
        existing = {self._normalize_iban(x) for x in self.cancelled_ibans}
        if norm in existing:
            return False
        self.data.setdefault("cancelled_ibans", []).append(norm)
        return True

    def remove_cancelled_iban(self, iban: str) -> bool:
        """حذف آيبان من القائمة الملغية. يعيد True إذا حُذف فعلاً."""
        norm = self._normalize_iban(iban)
        current = self.data.get("cancelled_ibans", [])
        new_list = [x for x in current if self._normalize_iban(x) != norm]
        if len(new_list) != len(current):
            self.data["cancelled_ibans"] = new_list
            return True
        return False

    def import_cancelled_ibans(self, ibans: List[str]) -> int:
        """استيراد قائمة آيبانات ملغية من ملف. يعيد عدد المضاف فعلاً."""
        added = 0
        for iban in ibans:
            if self.add_cancelled_iban(iban):
                added += 1
        return added

    def cancelled_ibans_set(self) -> set[str]:
        """مجموعة موحّدة من الآيبانات الملغية للمقارنة السريعة."""
        return {self._normalize_iban(x) for x in self.cancelled_ibans}
