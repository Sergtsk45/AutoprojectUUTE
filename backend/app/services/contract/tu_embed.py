"""
* @file: tu_embed.py
* @description: Растр страниц PDF ТУ в PNG, лимит размера DOCX.
* @created: 2026-04-22
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Лестница DPI: 150 → 120 → 100, пока DOCX не уложится в лимит вложения SMTP.
TU_DPI_LADDER: list[int] = [150, 120, 100]
MAX_DOCX_SIZE_BYTES = 25 * 1024 * 1024  # 25 МБ с запасом


def render_tu_pages_to_png(
    tu_pdf_path: Path,
    dpi: int,
    out_dir: Path | None = None,
) -> list[Path]:
    """Рендерит каждую страницу PDF ТУ в PNG-файл на диске."""
    if out_dir is None:
        out_dir = Path(
            tempfile.mkdtemp(prefix="tu_pages_", dir="/tmp"),
        )

    paths: list[Path] = []
    try:
        pdf = fitz.open(str(tu_pdf_path))
    except Exception as exc:
        logger.warning("Не удалось открыть ТУ %s: %s", tu_pdf_path, exc)
        return []

    try:
        for page_num in range(len(pdf)):
            pix = pdf[page_num].get_pixmap(
                dpi=dpi,
            )
            png_path = out_dir / f"tu_p{page_num:03d}.png"
            pix.save(str(png_path))
            paths.append(png_path)
    finally:
        pdf.close()

    return paths


def cleanup_png_files(paths: list[Path]) -> None:
    """Удаляет временные PNG-файлы; при пустом родителе — каталог `tu_pages_*`."""
    for p in paths:
        try:
            p.unlink()
        except OSError:
            pass
    if paths:
        try:
            paths[0].parent.rmdir()
        except OSError:
            pass
