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
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _group_open(x: float, y: float, rotate: int, pivot: tuple[float, float]) -> str:
    """Открывающий тег группы: translate + опционально rotate вокруг pivot (локальные координаты)."""
    px, py = pivot
    if rotate in (0, 360):
        return f'<g transform="translate({x:.2f},{y:.2f})">'
    return f'<g transform="translate({x:.2f},{y:.2f}) rotate({rotate} {px:.2f} {py:.2f})">'


def _line_common() -> str:
    return f'stroke="{STROKE}" stroke-width="{STROKE_WIDTH}" fill="{FILL_NONE}"'


def _text_common() -> str:
    return f'fill="{STROKE}" font-family="{FONT_FAMILY}" font-size="{FONT_SIZE}"'


def pipe_horizontal(x: float, y: float, length: float, label: str | None = None) -> str:
    """
    Горизонтальный участок трубопровода со стрелкой направления потока по центру.

    Размер: линия длиной ``length`` px по оси X; стрелка ~12 px по оси X, ~8 px по Y.
    """
    mid = length / 2.0
    parts: list[str] = [
        _group_open(x, y, 0, (0.0, 0.0)),
        f'<line x1="0" y1="0" x2="{length:.2f}" y2="0" {_line_common()} />',
        f'<polygon points="{mid - 5:.1f},-4 {mid - 5:.1f},4 {mid + 9:.1f},0" fill="{STROKE}" stroke="none" />',
    ]
    if label:
        parts.append(
            f'<text x="{mid:.1f}" y="-8" text-anchor="middle" {_text_common()}>{_xml_escape(label)}</text>'
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
        f'<line x1="0" y1="0" x2="0" y2="{length:.2f}" {_line_common()} />',
        f'<polygon points="-5,{mid - 6:.1f} 5,{mid - 6:.1f} 0,{mid + 8:.1f}" fill="{STROKE}" stroke="none" />',
    ]
    if label:
        parts.append(
            f'<text x="-14" y="{mid:.1f}" text-anchor="end" dominant-baseline="middle" {_text_common()}>{_xml_escape(label)}</text>'
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
        f'<polygon points="0,0 10,10 0,20" {_line_common()} />',
        f'<polygon points="20,0 10,10 20,20" {_line_common()} />',
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
        f'<polygon points="10,0 20,10 10,20 0,10" {_line_common()} />',
        f'<line x1="0" y1="10" x2="20" y2="10" {_line_common()} />',
        f'<line x1="10" y1="0" x2="10" y2="20" {_line_common()} />',
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
        f'<polygon points="0,8 16,0 16,16" {_line_common()} />',
        f'<line x1="18" y1="0" x2="18" y2="16" {_line_common()} />',
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
        f'<circle cx="15" cy="15" r="14.25" {_line_common()} />',
        f'<text x="15" y="19" text-anchor="middle" {_text_common()} font-weight="bold">{_xml_escape(label)}</text>',
        f'<text x="34" y="19" text-anchor="start" {_text_common()}>Расходомер</text>',
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
        f'<line x1="10" y1="5" x2="22" y2="5" {_line_common()} />',
        f'<circle cx="5" cy="5" r="4.5" {_line_common()} />',
        f'<text x="24" y="9" text-anchor="start" {_text_common()}>{_xml_escape(label)}</text>',
        f'<text x="24" y="22" text-anchor="start" {_text_common()} font-size="9">Термопреобразователь</text>',
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
        f'<line x1="10" y1="5" x2="22" y2="5" {_line_common()} />',
        f'<circle cx="5" cy="5" r="4.5" {_line_common()} />',
        f'<line x1="2.5" y1="5" x2="7.5" y2="5" {_line_common()} stroke-width="1" />',
        f'<line x1="5" y1="2.5" x2="5" y2="7.5" {_line_common()} stroke-width="1" />',
        f'<text x="24" y="9" text-anchor="start" {_text_common()}>{_xml_escape(label)}</text>',
        f'<text x="24" y="22" text-anchor="start" {_text_common()} font-size="9">Датчик давления</text>',
        "</g>",
    ]
    return "".join(parts)


def _heat_cell(
    cx: float, cy: float, w: float, h: float, txt: str, fs: str = "8", anchor: str = "middle"
) -> str:
    return (
        f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{w:.1f}" height="{h:.1f}" {_line_common()} stroke-width="0.8" />'
        f'<text x="{cx + w / 2.0:.1f}" y="{cy + h / 2.0 + 3:.1f}" text-anchor="{anchor}" dominant-baseline="middle" '
        f'font-family="{FONT_FAMILY}" font-size="{fs}" fill="{STROKE}">{_xml_escape(txt)}</text>'
    )


def heat_calculator(x: float, y: float, params: Mapping[str, Any] | None = None) -> str:
    """
    Условное обозначение тепловычислителя УУТЭ с таблицей параметров (пунктирная рамка).

    Размер: около 280×180 px.

    Ключи ``params`` (все необязательны, подставляются в ячейки):
    ``Qo``, ``Qgvs``, ``T``, ``Txv``, ``Mgvs``, ``tgvs``, ``tc``, ``M1``, ``t1o``, ``t2o``,
    ``Mc``, ``Rgvs``, ``Rc``, ``M2``, ``P1o``, ``P2o``.
    """
    p: dict[str, str] = {
        k: ""
        for k in (
            "Qo",
            "Qgvs",
            "T",
            "Txv",
            "Mgvs",
            "tgvs",
            "tc",
            "M1",
            "t1o",
            "t2o",
            "Mc",
            "Rgvs",
            "Rc",
            "M2",
            "P1o",
            "P2o",
        )
    }
    if params:
        for key, val in params.items():
            if key in p and val is not None:
                p[key] = str(val)

    w, h = 280.0, 180.0
    parts: list[str] = [
        _group_open(x, y, 0, (0.0, 0.0)),
        f'<rect x="0" y="0" width="{w:.0f}" height="{h:.0f}" {_line_common()} stroke-dasharray="4 3" />',
        f'<text x="10" y="22" text-anchor="start" {_text_common()} font-size="14" font-weight="bold">УУТЭ</text>',
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
        f'<rect x="0" y="10" width="40" height="40" {_line_common()} />',
        f'<line x1="5" y1="15" x2="35" y2="45" {_line_common()} stroke-width="1" />',
        f'<line x1="8" y1="18" x2="32" y2="42" {_line_common()} stroke-width="1" />',
        f'<line x1="11" y1="21" x2="29" y2="39" {_line_common()} stroke-width="1" />',
        f'<line x1="0" y1="18" x2="-12" y2="18" {_line_common()} />',
        f'<line x1="40" y1="22" x2="52" y2="22" {_line_common()} />',
        f'<line x1="0" y1="42" x2="-12" y2="42" {_line_common()} />',
        f'<line x1="40" y1="38" x2="52" y2="38" {_line_common()} />',
        f'<line x1="20" y1="10" x2="20" y2="0" {_line_common()} />',
        f'<line x1="20" y1="50" x2="20" y2="60" {_line_common()} />',
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
        f'<circle cx="12.5" cy="12.5" r="12" {_line_common()} />',
        f'<polygon points="7,12.5 17,7 17,18" fill="{STROKE}" stroke="{STROKE}" stroke-width="1" />',
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
        f'<polygon points="2,2 12.5,12.5 2,23" {_line_common()} />',
        f'<polygon points="23,2 12.5,12.5 23,23" {_line_common()} />',
        f'<line x1="12.5" y1="12.5" x2="12.5" y2="0" {_line_common()} />',
        f'<text x="12.5" y="10" text-anchor="middle" {_text_common()} font-size="9">M</text>',
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
        f'<polygon points="0,0 10,10 0,20" {_line_common()} />',
        f'<polygon points="20,0 10,10 20,20" {_line_common()} />',
        f'<text x="10" y="8" text-anchor="middle" {_text_common()} font-size="9">M</text>',
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
        f'<rect x="0" y="0" width="40" height="22" {_line_common()} />',
        f'<line x1="8" y1="4" x2="8" y2="18" {_line_common()} stroke-width="1" />',
        f'<line x1="16" y1="4" x2="16" y2="18" {_line_common()} stroke-width="1" />',
        f'<line x1="24" y1="4" x2="24" y2="18" {_line_common()} stroke-width="1" />',
        f'<line x1="32" y1="4" x2="32" y2="18" {_line_common()} stroke-width="1" />',
        f'<text x="20" y="30" text-anchor="middle" {_text_common()} font-size="10">Отопление</text>',
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
        f'<polygon points="0,4 12,0 12,8" fill="{STROKE}" stroke="none" />',
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
        f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" font-family="{FONT_FAMILY}" font-size="{font_size}" '
        f'fill="{STROKE}"{weight}>{_xml_escape(text)}</text>'
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
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f"{defs}{content}</svg>"
    )


def connection_line(points: Sequence[tuple[float, float]]) -> str:
    """
    Ломаная линия соединения между элементами (``<polyline>``).

    ``points`` — последовательность пар (x, y) в абсолютных координатах канвы.
    """
    if len(points) < 2:
        return ""
    pts = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
    return f'<polyline points="{pts}" {_line_common()}" />'


def dashed_rect(x: float, y: float, w: float, h: float, label: str | None = None) -> str:
    """
    Прямоугольник с пунктирной границей (зона УУТЭ, ГВС и т.п.).

    Опциональная подпись — над верхней стороной.
    """
    parts: list[str] = [
        _group_open(x, y, 0, (0.0, 0.0)),
        f'<rect x="0" y="0" width="{w:.2f}" height="{h:.2f}" {_line_common()} stroke-dasharray="6 4" />',
    ]
    if label:
        parts.append(
            f'<text x="{w / 2.0:.1f}" y="-6" text-anchor="middle" {_text_common()}>{_xml_escape(label)}</text>'
        )
    parts.append("</g>")
    return "".join(parts)
