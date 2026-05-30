"""سجل عمليات بسيط (Log) يوثّق ما تم في كل تشغيل."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


def _logs_dir() -> Path:
    d = Path(__file__).resolve().parent.parent / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_logger() -> logging.Logger:
    """إرجاع مسجّل موحّد يكتب في ملف يومي وفي الطرفية."""
    logger = logging.getLogger("salary_processor")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            "%Y-%m-%d %H:%M:%S")

    stamp = datetime.now().strftime("%Y-%m-%d")
    fh = logging.FileHandler(_logs_dir() / f"run_{stamp}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger
