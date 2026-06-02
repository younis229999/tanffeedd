"""
معاينة وطباعة ملفات PDF عبر نافذة معاينة (QPrintPreviewDialog).

نولّد الكشف كـ PDF (reportlab) ثم نعرض صفحاته في نافذة معاينة فيها زر الطباعة
واختيار الطابعة — مع الحفاظ على نفس التصميم.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog


def _render_pdf_to_printer(pdf_path: str, printer: QPrinter) -> None:
    """رسم صفحات ملف PDF على الطابعة/المعاينة."""
    import fitz  # PyMuPDF — يُحمّل عند الحاجة فقط.

    doc = fitz.open(pdf_path)
    painter = QPainter(printer)
    try:
        for i in range(doc.page_count):
            if i > 0:
                printer.newPage()
            page = doc[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(200 / 72.0, 200 / 72.0), alpha=False)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                         QImage.Format_RGB888)
            target = painter.viewport()
            scaled = img.scaled(target.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = target.x() + (target.width() - scaled.width()) // 2
            y = target.y() + (target.height() - scaled.height()) // 2
            painter.drawImage(x, y, scaled)
    finally:
        painter.end()
        doc.close()


def preview_and_print_pdf(pdf_path: str, parent=None) -> bool:
    """
    عرض نافذة معاينة الطباعة (مع زر الطباعة واختيار الطابعة).

    يعيد True دائماً بعد عرض المعاينة.
    """
    printer = QPrinter(QPrinter.HighResolution)
    printer.setDocName("altanfith")
    preview = QPrintPreviewDialog(printer, parent)
    preview.setWindowTitle("معاينة وطباعة الكشف")
    preview.resize(900, 700)
    preview.paintRequested.connect(lambda pr: _render_pdf_to_printer(pdf_path, pr))
    preview.exec()
    return True
