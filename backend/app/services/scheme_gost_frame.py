"""
@file: scheme_gost_frame.py
@description: Генератор SVG с ГОСТ-рамкой чертежа (A3 landscape, A4 portrait) и основной надписью.
@dependencies: нет (чистые строки SVG)
@created: 2026-04-20
"""

from __future__ import annotations

from typing import Any, Mapping

STROKE = "#000000"
SW = "1.5"
FONT = "Arial, sans-serif"

# Штамп: 185×55 мм ≈ 524×156 px при ~72 dpi (как в ТЗ)
STAMP_W = 524
STAMP_H = 156


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _default_stamp_data() -> dict[str, str]:
    return {
        "project_number": "",
        "object_name": "",
        "sheet_name": "Схема функциональная",
        "sheet_title": "Узел учета тепловой энергии",
        "company": "",
        "gip": "",
        "executor": "",
        "inspector": "",
        "head": "",
        "stage": "",
        "sheet_num": "",
        "total_sheets": "",
        "format": "A3",
    }


def _merge_stamp(stamp_data: Mapping[str, Any] | None) -> dict[str, str]:
    out = _default_stamp_data()
    if stamp_data:
        for k, v in stamp_data.items():
            if k in out and v is not None:
                out[k] = str(v)
    return out


def _text_el(xa: float, ya: float, s: str, fss: int = 10, anc: str = "start") -> str:
    return (
        '<text x="{:.1f}" y="{:.1f}" font-family="{}" font-size="{}" fill="{}" text-anchor="{}">{}</text>'
    ).format(xa, ya, FONT, fss, STROKE, anc, _xml_escape(s))


def _stamp_block(sx: float, sy: float, data: dict[str, str]) -> str:
    """
    Основная надпись (упрощённая сетка по ГОСТ): прямоугольник sx,sy размером STAMP_W×STAMP_H.
    """
    w = float(STAMP_W)
    h = float(STAMP_H)
    lines: list[str] = [
        '<g id="gost-stamp">',
        '<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}" '
        'fill="none" stroke="{}" stroke-width="1" />'.format(sx, sy, w, h, STROKE),
    ]
    y1 = sy + 28
    y2 = sy + 52
    y3 = sy + 76
    y4 = sy + 100
    y5 = sy + 124
    for yy in (y1, y2, y3, y4, y5):
        lines.append(
            '<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="{}" stroke-width="1" />'.format(
                sx, yy, sx + w, yy, STROKE
            )
        )
    x_mid = sx + w * 0.62
    x_right = sx + w - 48
    for xx in (x_mid, x_right):
        lines.append(
            '<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="{}" stroke-width="1" />'.format(
                xx, sy, xx, sy + h, STROKE
            )
        )
    y_rsep = sy + h - 40
    lines.append(
        '<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="{}" stroke-width="1" />'.format(
            x_right, y4, sx + w, y4, STROKE
        )
    )
    lines.append(
        '<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="{}" stroke-width="1" />'.format(
            x_right, y_rsep, sx + w, y_rsep, STROKE
        )
    )

    fs = 10
    fs_s = 9
    lines.append(_text_el(sx + 6, sy + 18, "Проект / шифр:", fs_s))
    lines.append(_text_el(sx + 96, sy + 18, data["project_number"], fs_s))

    lines.append(_text_el(sx + 6, sy + 42, "Объект:", fs_s))
    lines.append(_text_el(sx + 6, sy + 56, data["object_name"], fs_s))

    lines.append(_text_el(sx + 6, sy + 80, data["sheet_name"], fs_s))
    lines.append(_text_el(sx + 6, sy + 94, data["sheet_title"], fs_s))

    lines.append(_text_el(sx + 6, sy + 116, data["company"], fs_s))

    lines.append(_text_el(sx + 6, sy + 142, "ГИП: " + data["gip"], fs_s))
    lines.append(_text_el(sx + 160, sy + 142, "Исполн.: " + data["executor"], fs_s))
    lines.append(_text_el(sx + 300, sy + 142, "Н. контр.: " + data["inspector"], fs_s))
    lines.append(_text_el(x_mid + 6, sy + 142, "Стадия: " + data["stage"], fs_s))

    # Правая колонка (листы и формат)
    xc = x_right + (sx + w - x_right) / 2.0
    lines.append(_text_el(x_right + 4, y4 + 16, "Листов", fs_s))
    lines.append(_text_el(xc, y4 + 34, data["total_sheets"], 11, "middle"))
    lines.append(_text_el(x_right + 4, y_rsep + 16, "Лист", fs_s))
    lines.append(_text_el(xc, y_rsep + 32, data["sheet_num"], 11, "middle"))
    lines.append(_text_el(sx + w - 8, sy + 18, data["format"], fs_s, "end"))

    lines.append("</g>")
    return "\n".join(lines)


def _frame_layers(
    width: int,
    height: int,
    inner_left: float,
    inner_top: float,
    inner_right: float,
    inner_bottom: float,
    stamp_x: float,
    stamp_y: float,
    stamp_data: dict[str, str],
    content_svg: str,
) -> str:
    """Внешняя/внутренняя рамка, рабочая область с контентом, штамп."""
    outer = (
        '<rect x="5" y="5" width="{:.1f}" height="{:.1f}" fill="none" stroke="{}" '
        'stroke-width="{}" />'
    ).format(width - 10, height - 10, STROKE, SW)
    inner_w = inner_right - inner_left
    inner_h = inner_bottom - inner_top
    inner = (
        '<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}" fill="none" stroke="{}" '
        'stroke-width="1" />'
    ).format(inner_left, inner_top, inner_w, inner_h, STROKE)
    work = (
        '<g id="gost-working-area" transform="translate({:.1f},{:.1f})">'
        "{}"
        "</g>"
    ).format(inner_left, inner_top, content_svg)
    stamp = _stamp_block(stamp_x, stamp_y, stamp_data)
    return "\n".join([outer, inner, work, stamp])


def gost_frame_a3(content_svg: str = "", stamp_data: Mapping[str, Any] | None = None) -> str:
    """
    Полный SVG A3 (альбомная ориентация): 1190×842 px, ГОСТ-рамка и основная надпись.

    Поля: внешняя граница — отступ 5 px от края; внутренняя — 20 px слева (подшивка),
    5 px сверху, справа и снизу. Рабочая область: внутри внутренней рамки; контент
    группируется с началом в точке внутреннего левого верхнего угла.

    ``stamp_data`` — словарь полей основной надписи (см. ``_default_stamp_data``).
    """
    width, height = 1190, 842
    inner_left = 20.0
    inner_top = 5.0
    inner_right = width - 5.0
    inner_bottom = height - 5.0
    stamp_x = inner_right - STAMP_W
    stamp_y = inner_bottom - STAMP_H
    data = _merge_stamp(stamp_data)
    data["format"] = data.get("format") or "A3"
    body = _frame_layers(
        width,
        height,
        inner_left,
        inner_top,
        inner_right,
        inner_bottom,
        stamp_x,
        stamp_y,
        data,
        content_svg,
    )
    defs = (
        "<defs>"
        '<style type="text/css"><![CDATA['
        "text { font-family: Arial, sans-serif; }"
        "]]></style>"
        "</defs>"
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
        "{defs}{body}</svg>"
    ).format(w=width, h=height, defs=defs, body=body)


def gost_frame_a4(content_svg: str = "", stamp_data: Mapping[str, Any] | None = None) -> str:
    """
    Полный SVG A4 (книжная ориентация): 595×842 px, те же отступы и штамп.
    """
    width, height = 595, 842
    inner_left = 20.0
    inner_top = 5.0
    inner_right = width - 5.0
    inner_bottom = height - 5.0
    stamp_x = inner_right - STAMP_W
    stamp_y = inner_bottom - STAMP_H
    data = _merge_stamp(stamp_data)
    data["format"] = data.get("format") or "A4"
    body = _frame_layers(
        width,
        height,
        inner_left,
        inner_top,
        inner_right,
        inner_bottom,
        stamp_x,
        stamp_y,
        data,
        content_svg,
    )
    defs = (
        "<defs>"
        '<style type="text/css"><![CDATA['
        "text { font-family: Arial, sans-serif; }"
        "]]></style>"
        "</defs>"
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
        "{defs}{body}</svg>"
    ).format(w=width, h=height, defs=defs, body=body)
