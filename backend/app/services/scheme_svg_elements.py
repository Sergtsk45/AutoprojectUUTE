"""
@file: scheme_svg_elements.py
@description: Генератор SVG-фрагментов условных обозначений для инженерных схем теплоснабжения (УУТЭ).
@dependencies: нет (чистые строки SVG)
@created: 2026-04-20
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

# Общие стили по умолчанию
STROKE = "#000000"
FILL_NONE = "none"
STROKE_WIDTH = "1.5"
FONT_FAMILY = "Arial, sans-serif"
FONT_SIZE = "11"


def _xml_escape(text: str) -> str:
    """Экранирование текста для встраивания в SVG."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _group_open(x: float, y: float, rotate: int, pivot: tuple[float, float]) -> str:
    """Открывающий тег группы: translate + опционально rotate вокруг pivot (локальные координаты)."""
    px, py = pivot
    if rotate in (0, 360):
        return '<g transform="translate({:.2f},{:.2f})">'.format(x, y)
    return '<g transform="translate({:.2f},{:.2f}) rotate({} {:.2f} {:.2f})">'.format(
        x, y, rotate, px, py
    )


def _line_common() -> str:
    return 'stroke="{}" stroke-width="{}" fill="{}"'.format(STROKE, STROKE_WIDTH, FILL_NONE)


def _text_common() -> str:
    return 'fill="{}" font-family="{}" font-size="{}"'.format(STROKE, FONT_FAMILY, FONT_SIZE)


def pipe_horizontal(x: float, y: float, length: float, label: str | None = None) -> str:
    """
    Горизонтальный участок трубопровода со стрелкой направления потока по центру.

    Размер: линия длиной ``length`` px по оси X; стрелка ~12 px по оси X, ~8 px по Y.
    """
    mid = length / 2.0
    parts: list[str] = [
        _group_open(x, y, 0, (0.0, 0.0)),
        '<line x1="0" y1="0" x2="{:.2f}" y2="0" {} />'.format(length, _line_common()),
        '<polygon points="{:.1f},-4 {:.1f},4 {:.1f},0" fill="{}" stroke="none" />'.format(
            mid - 5, mid - 5, mid + 9, STROKE
        ),
    ]
    if label:
        parts.append(
            '<text x="{:.1f}" y="-8" text-anchor="middle" {}>{}</text>'.format(
                mid, _text_common(), _xml_escape(label)
            )
        )
    parts.append("</g>")
    return "".join(parts)


def pipe_vertical(x: float, y: float, length: float, label: str | None = None) -> str:
    """
    Вертикальный участок трубопровода со стрелкой направления потока (вниз) по центру.

    Размер: линия длиной ``length`` px по оси Y.
    """
    mid = length / 2.0
    parts: list[str] = [
        _group_open(x, y, 0, (0.0, 0.0)),
        '<line x1="0" y1="0" x2="0" y2="{:.2f}" {} />'.format(length, _line_common()),
        '<polygon points="-5,{:.1f} 5,{:.1f} 0,{:.1f}" fill="{}" stroke="none" />'.format(
            mid - 6, mid - 6, mid + 8, STROKE
        ),
    ]
    if label:
        parts.append(
            '<text x="-14" y="{:.1f}" text-anchor="end" dominant-baseline="middle" {}>{}</text>'.format(
                mid, _text_common(), _xml_escape(label)
            )
        )
    parts.append("</g>")
    return "".join(parts)


def gate_valve(x: float, y: float, rotate: int = 0) -> str:
    """
    Задвижка (запорная арматура): два треугольника остриями друг к другу.

    Размер: около 20×20 px.
    """
    parts = [
        _group_open(x, y, rotate, (10.0, 10.0)),
        '<polygon points="0,0 10,10 0,20" {} />'.format(_line_common()),
        '<polygon points="20,0 10,10 20,20" {} />'.format(_line_common()),
        "</g>",
    ]
    return "".join(parts)


def strainer(x: float, y: float, rotate: int = 0) -> str:
    """
    Фильтр (грязевик): ромб с перекрестием внутри.

    Размер: около 20×20 px.
    """
    parts = [
        _group_open(x, y, rotate, (10.0, 10.0)),
        '<polygon points="10,0 20,10 10,20 0,10" {} />'.format(_line_common()),
        '<line x1="0" y1="10" x2="20" y2="10" {} />'.format(_line_common()),
        '<line x1="10" y1="0" x2="10" y2="20" {} />'.format(_line_common()),
        "</g>",
    ]
    return "".join(parts)


def check_valve(x: float, y: float, rotate: int = 0) -> str:
    """
    Обратный клапан: треугольник и линия-упор.

    Размер: около 20×16 px.
    """
    parts = [
        _group_open(x, y, rotate, (10.0, 8.0)),
        '<polygon points="0,8 16,0 16,16" {} />'.format(_line_common()),
        '<line x1="18" y1="0" x2="18" y2="16" {} />'.format(_line_common()),
        "</g>",
    ]
    return "".join(parts)


def flow_meter(x: float, y: float, label: str = "G1", rotate: int = 0) -> str:
    """
    Расходомер: окружность с обозначением (G1, G2, …), подпись «Расходомер» справа.

    Размер: диаметр около 30 px; с подписью занимает ~75×32 px.
    """
    parts = [
        _group_open(x, y, rotate, (15.0, 15.0)),
        '<circle cx="15" cy="15" r="14.25" {} />'.format(_line_common()),
        '<text x="15" y="19" text-anchor="middle" {} font-weight="bold">{}</text>'.format(
            _text_common(), _xml_escape(label)
        ),
        '<text x="34" y="19" text-anchor="start" {}>Расходомер</text>'.format(_text_common()),
        "</g>",
    ]
    return "".join(parts)


def temp_sensor(x: float, y: float, label: str = "t1", rotate: int = 0) -> str:
    """
    Датчик температуры (термопреобразователь): кружок и выносная линия с подписью.

    Размер: условный датчик ~10 px; подпись справа.
    """
    parts = [
        _group_open(x, y, rotate, (5.0, 5.0)),
        '<line x1="10" y1="5" x2="22" y2="5" {} />'.format(_line_common()),
        '<circle cx="5" cy="5" r="4.5" {} />'.format(_line_common()),
        '<text x="24" y="9" text-anchor="start" {}>{}</text>'.format(
            _text_common(), _xml_escape(label)
        ),
        '<text x="24" y="22" text-anchor="start" {} font-size="9">Термопреобразователь</text>'.format(
            _text_common()
        ),
        "</g>",
    ]
    return "".join(parts)


def pressure_sensor(x: float, y: float, label: str = "P1", rotate: int = 0) -> str:
    """
    Датчик давления: кружок с крестом и подписью.

    Размер: условный датчик ~10 px; подпись справа.
    """
    parts = [
        _group_open(x, y, rotate, (5.0, 5.0)),
        '<line x1="10" y1="5" x2="22" y2="5" {} />'.format(_line_common()),
        '<circle cx="5" cy="5" r="4.5" {} />'.format(_line_common()),
        '<line x1="2.5" y1="5" x2="7.5" y2="5" {} stroke-width="1" />'.format(_line_common()),
        '<line x1="5" y1="2.5" x2="5" y2="7.5" {} stroke-width="1" />'.format(_line_common()),
        '<text x="24" y="9" text-anchor="start" {}>{}</text>'.format(
            _text_common(), _xml_escape(label)
        ),
        '<text x="24" y="22" text-anchor="start" {} font-size="9">Датчик давления</text>'.format(
            _text_common()
        ),
        "</g>",
    ]
    return "".join(parts)


def _heat_cell(
    cx: float, cy: float, w: float, h: float, txt: str, fs: str = "8", anchor: str = "middle"
) -> str:
    return (
        '<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}" {} stroke-width="0.8" />'
        '<text x="{:.1f}" y="{:.1f}" text-anchor="{}" dominant-baseline="middle" '
        'font-family="{}" font-size="{}" fill="{}">{}</text>'
    ).format(
        cx,
        cy,
        w,
        h,
        _line_common(),
        cx + w / 2.0,
        cy + h / 2.0 + 3,
        anchor,
        FONT_FAMILY,
        fs,
        STROKE,
        _xml_escape(txt),
    )


def heat_calculator(x: float, y: float, params: Mapping[str, Any] | None = None) -> str:
    """
    Условное обозначение тепловычислителя УУТЭ с таблицей параметров (пунктирная рамка).

    Размер: около 280×180 px.

    Ключи ``params`` (все необязательны, подставляются в ячейки):
    ``Qo``, ``Qgvs``, ``T``, ``Txv``, ``Mgvs``, ``tgvs``, ``tc``, ``M1``, ``t1o``, ``t2o``,
    ``Mc``, ``Rgvs``, ``Rc``, ``M2``, ``P1o``, ``P2o``.
    """
    p: dict[str, str] = {k: "" for k in (
        "Qo", "Qgvs", "T", "Txv",
        "Mgvs", "tgvs", "tc", "M1", "t1o", "t2o",
        "Mc", "Rgvs", "Rc", "M2", "P1o", "P2o",
    )}
    if params:
        for key, val in params.items():
            if key in p and val is not None:
                p[key] = str(val)

    w, h = 280.0, 180.0
    parts: list[str] = [
        _group_open(x, y, 0, (0.0, 0.0)),
        '<rect x="0" y="0" width="{:.0f}" height="{:.0f}" {} stroke-dasharray="4 3" />'.format(
            w, h, _line_common()
        ),
        '<text x="10" y="22" text-anchor="start" {} font-size="14" font-weight="bold">УУТЭ</text>'.format(
            _text_common()
        ),
        '<text x="10" y="42" text-anchor="start" {} font-size="10">Qo: {}</text>'.format(
            _text_common(), _xml_escape(p["Qo"])
        ),
        '<text x="100" y="42" text-anchor="start" {} font-size="10">Qгвс: {}</text>'.format(
            _text_common(), _xml_escape(p["Qgvs"])
        ),
        '<text x="190" y="42" text-anchor="start" {} font-size="10">T: {}</text>'.format(
            _text_common(), _xml_escape(p["T"])
        ),
        '<text x="10" y="58" text-anchor="start" {} font-size="10">txв: {}</text>'.format(
            _text_common(), _xml_escape(p["Txv"])
        ),
    ]

    # Таблица: заголовки
    row_h = 14.0
    col_x = [10.0, 58.0, 106.0, 154.0, 202.0, 250.0]
    headers1 = ["Мгвс", "tгвс", "tц", "M1", "t1о", "t2о"]
    y0 = 72.0
    for i, title in enumerate(headers1):
        parts.append(_heat_cell(col_x[i], y0, 46.0, row_h, title, "8", "middle"))
    # Строка значений 1
    y1 = y0 + row_h
    vals1 = [p["Mgvs"], p["tgvs"], p["tc"], p["M1"], p["t1o"], p["t2o"]]
    for i, val in enumerate(vals1):
        parts.append(_heat_cell(col_x[i], y1, 46.0, row_h, val or "—", "8", "middle"))
    # Заголовки 2
    y2 = y1 + row_h
    headers2 = ["Мц", "Ргвс", "Рц", "M2", "P1о", "P2о"]
    for i, title in enumerate(headers2):
        parts.append(_heat_cell(col_x[i], y2, 46.0, row_h, title, "8", "middle"))
    y3 = y2 + row_h
    vals2 = [p["Mc"], p["Rgvs"], p["Rc"], p["M2"], p["P1o"], p["P2o"]]
    for i, val in enumerate(vals2):
        parts.append(_heat_cell(col_x[i], y3, 46.0, row_h, val or "—", "8", "middle"))

    parts.append("</g>")
    return "".join(parts)


def heat_exchanger(x: float, y: float, rotate: int = 0) -> str:
    """
    Теплообменник (пластинчатый): прямоугольник с диагональными линиями, четыре отвода.

    Размер: около 40×60 px.
    """
    parts = [
        _group_open(x, y, rotate, (20.0, 30.0)),
        '<rect x="0" y="10" width="40" height="40" {} />'.format(_line_common()),
        '<line x1="5" y1="15" x2="35" y2="45" {} stroke-width="1" />'.format(_line_common()),
        '<line x1="8" y1="18" x2="32" y2="42" {} stroke-width="1" />'.format(_line_common()),
        '<line x1="11" y1="21" x2="29" y2="39" {} stroke-width="1" />'.format(_line_common()),
        '<line x1="0" y1="18" x2="-12" y2="18" {} />'.format(_line_common()),
        '<line x1="40" y1="22" x2="52" y2="22" {} />'.format(_line_common()),
        '<line x1="0" y1="42" x2="-12" y2="42" {} />'.format(_line_common()),
        '<line x1="40" y1="38" x2="52" y2="38" {} />'.format(_line_common()),
        '<line x1="20" y1="10" x2="20" y2="0" {} />'.format(_line_common()),
        '<line x1="20" y1="50" x2="20" y2="60" {} />'.format(_line_common()),
        "</g>",
    ]
    return "".join(parts)


def pump(x: float, y: float, rotate: int = 0) -> str:
    """
    Насос: окружность и треугольник направления потока.

    Размер: диаметр около 25 px.
    """
    parts = [
        _group_open(x, y, rotate, (12.5, 12.5)),
        '<circle cx="12.5" cy="12.5" r="12" {} />'.format(_line_common()),
        '<polygon points="7,12.5 17,7 17,18" fill="{}" stroke="{}" stroke-width="1" />'.format(
            STROKE, STROKE
        ),
        "</g>",
    ]
    return "".join(parts)


def valve_3way(x: float, y: float, rotate: int = 0) -> str:
    """
    Трёхходовой регулирующий клапан: два запорных символа и третий отвод с обозначением регулирования.

    Размер: около 25×25 px.
    """
    parts = [
        _group_open(x, y, rotate, (12.5, 12.5)),
        '<polygon points="2,2 12.5,12.5 2,23" {} />'.format(_line_common()),
        '<polygon points="23,2 12.5,12.5 23,23" {} />'.format(_line_common()),
        '<line x1="12.5" y1="12.5" x2="12.5" y2="0" {} />'.format(_line_common()),
        '<text x="12.5" y="10" text-anchor="middle" {} font-size="9">M</text>'.format(
            _text_common()
        ),
        "</g>",
    ]
    return "".join(parts)


def valve_2way(x: float, y: float, rotate: int = 0) -> str:
    """
    Двухходовой регулирующий клапан: два треугольника и символ регулирования.

    Размер: около 20×20 px.
    """
    parts = [
        _group_open(x, y, rotate, (10.0, 10.0)),
        '<polygon points="0,0 10,10 0,20" {} />'.format(_line_common()),
        '<polygon points="20,0 10,10 20,20" {} />'.format(_line_common()),
        '<text x="10" y="8" text-anchor="middle" {} font-size="9">M</text>'.format(_text_common()),
        "</g>",
    ]
    return "".join(parts)


def radiator(x: float, y: float) -> str:
    """
    Радиатор отопления: прямоугольник с вертикальными линиями, подпись «Отопление».

    Размер: около 40×30 px.
    """
    parts = [
        _group_open(x, y, 0, (0.0, 0.0)),
        '<rect x="0" y="0" width="40" height="22" {} />'.format(_line_common()),
        '<line x1="8" y1="4" x2="8" y2="18" {} stroke-width="1" />'.format(_line_common()),
        '<line x1="16" y1="4" x2="16" y2="18" {} stroke-width="1" />'.format(_line_common()),
        '<line x1="24" y1="4" x2="24" y2="18" {} stroke-width="1" />'.format(_line_common()),
        '<line x1="32" y1="4" x2="32" y2="18" {} stroke-width="1" />'.format(_line_common()),
        '<text x="20" y="30" text-anchor="middle" {} font-size="10">Отопление</text>'.format(
            _text_common()
        ),
        "</g>",
    ]
    return "".join(parts)


def flow_arrow(x: float, y: float, rotate: int = 0) -> str:
    """
    Стрелка направления потока (заливка).

    Размер: около 12×8 px.
    """
    parts = [
        _group_open(x, y, rotate, (6.0, 4.0)),
        '<polygon points="0,4 12,0 12,8" fill="{}" stroke="none" />'.format(STROKE),
        "</g>",
    ]
    return "".join(parts)


def text_label(
    x: float,
    y: float,
    text: str,
    font_size: int = 11,
    anchor: str = "start",
    bold: bool = False,
) -> str:
    """
    Текстовая подпись (элемент ``<text>``).
    """
    weight = ' font-weight="bold"' if bold else ""
    return (
        '<text x="{:.2f}" y="{:.2f}" text-anchor="{}" font-family="{}" font-size="{}" '
        'fill="{}"{}>{}</text>'
    ).format(
        x,
        y,
        anchor,
        FONT_FAMILY,
        font_size,
        STROKE,
        weight,
        _xml_escape(text),
    )


def svg_canvas(width: int = 1190, height: int = 842, content: str = "") -> str:
    """
    Полный корневой элемент SVG с ``viewBox`` и базовыми ``defs`` (стили линий).
    """
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
        "{defs}{content}</svg>"
    ).format(w=width, h=height, defs=defs, content=content)


def connection_line(points: Sequence[tuple[float, float]]) -> str:
    """
    Ломаная линия соединения между элементами (``<polyline>``).

    ``points`` — последовательность пар (x, y) в абсолютных координатах канвы.
    """
    if len(points) < 2:
        return ""
    pts = " ".join("{:.1f},{:.1f}".format(px, py) for px, py in points)
    return '<polyline points="{}" {}" />'.format(pts, _line_common())


def dashed_rect(x: float, y: float, w: float, h: float, label: str | None = None) -> str:
    """
    Прямоугольник с пунктирной границей (зона УУТЭ, ГВС и т.п.).

    Опциональная подпись — над верхней стороной.
    """
    parts: list[str] = [
        _group_open(x, y, 0, (0.0, 0.0)),
        '<rect x="0" y="0" width="{:.2f}" height="{:.2f}" {} stroke-dasharray="6 4" />'.format(
            w, h, _line_common()
        ),
    ]
    if label:
        parts.append(
            '<text x="{:.1f}" y="-6" text-anchor="middle" {}>{}</text>'.format(
                w / 2.0, _text_common(), _xml_escape(label)
            )
        )
    parts.append("</g>")
    return "".join(parts)
