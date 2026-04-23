"""
@file: scheme_pdf_renderer.py
@description: Рендер PDF с ГОСТ-рамкой из SVG через WeasyPrint.
              Интеграция SVG схемы с HTML-шаблоном и генерация PDF для печати.
@dependencies: weasyprint, jinja2, scheme_gost_frame
@created: 2026-04-23
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Literal, Mapping

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.schemas.scheme import SchemeParams

# Путь к шаблонам (относительно корня backend/)
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "scheme_pdf"


def _get_jinja_env() -> Environment:
    """Создает Jinja2 окружение для рендеринга HTML-шаблонов."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _prepare_stamp_data(params: SchemeParams | None = None) -> dict[str, str]:
    """
    Формирует словарь данных для штампа ГОСТ-рамки из параметров схемы.

    Args:
        params: Параметры схемы с данными заявки

    Returns:
        Словарь с полями для основной надписи ГОСТ
    """
    stamp = {
        "project_number": "",
        "object_name": "",
        "sheet_name": "Схема функциональная",
        "sheet_title": "Узел учета тепловой энергии",
        "company": "",
        "gip": "",
        "executor": "",
        "inspector": "",
        "head": "",
        "stage": "П",  # Проектная документация
        "sheet_num": "1",
        "total_sheets": "1",
        "format": "A3",
    }

    if params:
        if params.project_number:
            stamp["project_number"] = params.project_number
        if params.object_address:
            stamp["object_name"] = params.object_address
        if params.company_name:
            stamp["company"] = params.company_name
        if params.engineer_name:
            stamp["executor"] = params.engineer_name

    return stamp


def render_scheme_pdf(
    svg_content: str,
    stamp_data: Mapping[str, Any] | None = None,
    format: Literal["A3", "A4"] = "A3",
) -> bytes:
    """
    Генерирует PDF из SVG-контента схемы с ГОСТ-рамкой.

    Args:
        svg_content: Полный SVG (уже с ГОСТ-рамкой из gost_frame_a3/a4)
        stamp_data: Данные для штампа (передаются в gost_frame при генерации SVG)
        format: Формат страницы (A3 landscape или A4 portrait)

    Returns:
        PDF документ в виде байтов

    Example:
        >>> from app.services.scheme_gost_frame import gost_frame_a3
        >>> from app.services.scheme_svg_renderer import render_scheme
        >>> from app.schemas.scheme import SchemeType, SchemeParams
        >>>
        >>> params = SchemeParams(...)
        >>> stamp = {"project_number": "123", "object_name": "Объект"}
        >>>
        >>> # Генерация SVG с контентом и рамкой
        >>> content = render_scheme(SchemeType.DEP_SIMPLE, params)
        >>> svg = gost_frame_a3(content, stamp)
        >>>
        >>> # Генерация PDF
        >>> pdf_bytes = render_scheme_pdf(svg, stamp, "A3")
    """
    env = _get_jinja_env()

    # Выбор шаблона по формату
    template_name = "gost_frame_a3.html" if format == "A3" else "gost_frame_a4.html"
    template = env.get_template(template_name)

    # Рендер HTML
    html_content = template.render(svg_content=svg_content)

    # Генерация PDF через WeasyPrint
    pdf_file = io.BytesIO()
    HTML(string=html_content, encoding="utf-8").write_pdf(pdf_file)
    pdf_file.seek(0)

    return pdf_file.read()


def render_scheme_pdf_from_params(
    svg_content: str,
    params: SchemeParams | None = None,
    format: Literal["A3", "A4"] = "A3",
) -> bytes:
    """
    Удобная обертка: генерирует PDF из SVG и автоматически формирует stamp_data из params.

    Args:
        svg_content: Полный SVG схемы с ГОСТ-рамкой
        params: Параметры схемы с данными заявки
        format: Формат страницы

    Returns:
        PDF документ в виде байтов
    """
    stamp_data = _prepare_stamp_data(params)
    return render_scheme_pdf(svg_content, stamp_data, format)


# Для обратной совместимости и удобства импорта
__all__ = [
    "render_scheme_pdf",
    "render_scheme_pdf_from_params",
]
