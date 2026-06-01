"""
طباعة مباشرة لملفات PDF عبر نافذة اختيار الطابعة (QPrintDialog).

نولّد الكشف كـ PDF (reportlab) ثم نعرض صفحاته عبر PyMuPDF ونرسلها للطابعة
التي يختارها المستخدم — مع الحفاظ على نفس التصميم الجميل.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPrintSupport import QPrintDialog, QPrinter


def print_pdf_file(pdf_path: str, parent=None) -> bool:
    """
    عرض نافذة اختيار الطابعة وطباعة ملف PDF مباشرةً.

    يعيد True إذا تمّت الطباعة، False إذا أُلغيت.
    """
    import fitz  # PyMuPDF — يُحمّل عند الحاجة فقط.

    printer = QPrinter(QPrinter.HighResolution)
    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle("طباعة الكشف")
    if dialog.exec() != QPrintDialog.Accepted:
        return False

    doc = fitz.open(pdf_path)
    painter = QPainter()
    if not painter.begin(printer):
        return False
    try:
        for i in range(doc.page_count):
            if i > 0:
                printer.newPage()
            page = doc[i]
            # عرض الصفحة بدقة 200 نقطة/إنش (جودة طباعة جيدة دون استهلاك ذاكرة مفرط).
            zoom = 200.0 / 72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
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
    return True
