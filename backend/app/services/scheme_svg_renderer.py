"""
@file: scheme_svg_renderer.py
@description: Рендер полных принципиальных схем УУТЭ из библиотеки элементов.
              8 типовых конфигураций (зависимая/независимая, с/без клапана, ГВС, вентиляция).
@dependencies: scheme_svg_elements, scheme_service (SchemeParams)
@created: 2026-04-20
"""

from __future__ import annotations

from typing import Any, Mapping

from app.schemas.scheme import SchemeParams, SchemeType
from app.services.scheme_svg_elements import (
    check_valve,
    connection_line,
    dashed_rect,
    flow_meter,
    gate_valve,
    heat_calculator,
    heat_exchanger,
    pipe_horizontal,
    pipe_vertical,
    pressure_sensor,
    pump,
    radiator,
    strainer,
    temp_sensor,
    text_label,
    valve_2way,
    valve_3way,
)

# Размер рабочей области для A3 (внутри ГОСТ-рамки): ~1150×820 px
CANVAS_W = 1150
CANVAS_H = 820


def render_scheme(scheme_type: SchemeType, params: SchemeParams) -> str:
    """
    Диспетчер: подбор функции рендера по типу схемы.

    Возвращает SVG-контент (без корневого <svg> и ГОСТ-рамки) — только группы элементов.
    """
    renderers = {
        SchemeType.DEP_SIMPLE: render_scheme_01_dep_simple,
        SchemeType.DEP_SIMPLE_GWP: render_scheme_02_dep_simple_gwp,
        SchemeType.DEP_VALVE: render_scheme_03_dep_valve,
        SchemeType.DEP_VALVE_GWP: render_scheme_04_dep_valve_gwp,
        SchemeType.DEP_VALVE_GWP_VENT: render_scheme_05_dep_valve_gwp_vent,
        SchemeType.INDEP: render_scheme_06_indep,
        SchemeType.INDEP_GWP: render_scheme_07_indep_gwp,
        SchemeType.INDEP_GWP_VENT: render_scheme_08_indep_gwp_vent,
    }
    fn = renderers.get(scheme_type)
    if not fn:
        raise ValueError(f"Неизвестный тип схемы: {scheme_type}")
    return fn(params)


def render_scheme_01_dep_simple(params: SchemeParams) -> str:
    """
    Схема 1: зависимая без клапана, без ГВС, без вентиляции.

    Топология:
    - Подающий трубопровод (верх): сеть → задвижка → фильтр → t1, P1 → G1 → радиатор
    - Обратный трубопровод (низ): радиатор → G2 → t2, P2 → фильтр → задвижка → сеть
    - УУТЭ (тепловычислитель) — внизу справа
    """
    parts: list[str] = []

    # Координаты магистральных линий
    y_supply = 180  # Подача
    y_return = 480  # Обратка
    x_start = 60
    x_gate1 = 150
    x_filter1 = 230
    x_sensor1 = 320
    x_g1 = 450
    x_rad = 620
    x_g2 = 790
    x_sensor2 = 920
    x_filter2 = 1010
    x_gate2 = 1090

    # Подающий трубопровод
    parts.append(text_label(x_start - 20, y_supply - 20, "Т1 (подача)", 10, "end"))
    parts.append(pipe_horizontal(x_start, y_supply, x_gate1 - x_start))
    parts.append(gate_valve(x_gate1 - 10, y_supply - 10))
    parts.append(pipe_horizontal(x_gate1 + 20, y_supply, x_filter1 - x_gate1 - 20))
    parts.append(strainer(x_filter1 - 10, y_supply - 10))
    parts.append(pipe_horizontal(x_filter1 + 20, y_supply, x_sensor1 - x_filter1 - 20))

    # Датчики температуры и давления (подача)
    parts.append(temp_sensor(x_sensor1, y_supply - 40, params.t1_label or "t1"))
    parts.append(pressure_sensor(x_sensor1 + 60, y_supply - 40, params.p1_label or "P1"))
    parts.append(pipe_horizontal(x_sensor1, y_supply, x_g1 - x_sensor1 - 30))

    # Расходомер G1
    parts.append(flow_meter(x_g1 - 15, y_supply - 15, params.g1_label or "G1"))
    parts.append(pipe_horizontal(x_g1 + 30, y_supply, x_rad - x_g1 - 80))

    # Вертикаль к радиатору
    parts.append(pipe_vertical(x_rad, y_supply, y_return - y_supply - 60))
    parts.append(radiator(x_rad - 20, y_return - 60))

    # Обратный трубопровод
    parts.append(pipe_vertical(x_rad, y_return - 30, 30))
    parts.append(pipe_horizontal(x_rad, y_return, x_g2 - x_rad - 30))
    parts.append(flow_meter(x_g2 - 15, y_return - 15, params.g2_label or "G2"))
    parts.append(pipe_horizontal(x_g2 + 30, y_return, x_sensor2 - x_g2 - 90))

    # Датчики температуры и давления (обратка)
    parts.append(temp_sensor(x_sensor2, y_return + 40, params.t2_label or "t2"))
    parts.append(pressure_sensor(x_sensor2 + 60, y_return + 40, params.p2_label or "P2"))
    parts.append(pipe_horizontal(x_sensor2, y_return, x_filter2 - x_sensor2 - 20))

    parts.append(strainer(x_filter2 - 10, y_return - 10))
    parts.append(pipe_horizontal(x_filter2 + 20, y_return, x_gate2 - x_filter2 - 30))
    parts.append(gate_valve(x_gate2 - 10, y_return - 10))
    parts.append(pipe_horizontal(x_gate2 + 20, y_return, CANVAS_W - x_gate2 - 20))
    parts.append(text_label(CANVAS_W - 20, y_return + 30, "Т2 (обратка)", 10, "end"))

    # Тепловычислитель УУТЭ
    calc_params = {
        "Qo": params.q_heat or "",
        "Qgvs": "",
        "T": "",
        "Txv": "",
        "Mgvs": "",
        "tgvs": "",
        "tc": "",
        "M1": params.m1 or "",
        "t1o": params.t1 or "",
        "t2o": params.t2 or "",
        "Mc": "",
        "Rgvs": "",
        "Rc": "",
        "M2": params.m2 or "",
        "P1o": params.p1 or "",
        "P2o": params.p2 or "",
    }
    parts.append(heat_calculator(800, 600, calc_params))

    # Соединительные линии от датчиков к УУТЭ (пунктир)
    parts.append(
        dashed_rect(790, 590, 300, 200, "Зона УУТЭ")
    )

    # Подписи труб
    parts.append(text_label(400, y_supply - 40, "Подающий трубопровод", 11, "middle", bold=True))
    parts.append(text_label(400, y_return + 60, "Обратный трубопровод", 11, "middle", bold=True))

    return "".join(parts)


def render_scheme_02_dep_simple_gwp(params: SchemeParams) -> str:
    """
    Схема 2: зависимая без клапана, с ГВС (двухступенчатый подогреватель).
    
    Топология: базовая схема 1 + блок ГВС справа.
    ГВС: две ступени подогревателя (от обратки и от подачи), циркуляционный насос,
    расходомер G3, датчики температуры ГВС.
    """
    parts: list[str] = []

    # Координаты магистральных линий (как в схеме 1)
    y_supply = 180
    y_return = 480
    x_start = 60
    x_gate1 = 150
    x_filter1 = 230
    x_sensor1 = 320
    x_g1 = 450
    x_rad = 620
    x_g2 = 790
    x_sensor2 = 920
    x_filter2 = 1010
    x_gate2 = 1090

    # Подающий трубопровод
    parts.append(text_label(x_start - 20, y_supply - 20, "Т1 (подача)", 10, "end"))
    parts.append(pipe_horizontal(x_start, y_supply, x_gate1 - x_start))
    parts.append(gate_valve(x_gate1 - 10, y_supply - 10))
    parts.append(pipe_horizontal(x_gate1 + 20, y_supply, x_filter1 - x_gate1 - 20))
    parts.append(strainer(x_filter1 - 10, y_supply - 10))
    parts.append(pipe_horizontal(x_filter1 + 20, y_supply, x_sensor1 - x_filter1 - 20))

    # Датчики температуры и давления (подача)
    parts.append(temp_sensor(x_sensor1, y_supply - 40, params.t1_label or "t1"))
    parts.append(pressure_sensor(x_sensor1 + 60, y_supply - 40, params.p1_label or "P1"))
    parts.append(pipe_horizontal(x_sensor1, y_supply, x_g1 - x_sensor1 - 30))

    # Расходомер G1
    parts.append(flow_meter(x_g1 - 15, y_supply - 15, params.g1_label or "G1"))
    parts.append(pipe_horizontal(x_g1 + 30, y_supply, x_rad - x_g1 - 80))

    # Вертикаль к радиатору
    parts.append(pipe_vertical(x_rad, y_supply, y_return - y_supply - 60))
    parts.append(radiator(x_rad - 20, y_return - 60))

    # Обратный трубопровод
    parts.append(pipe_vertical(x_rad, y_return - 30, 30))
    parts.append(pipe_horizontal(x_rad, y_return, x_g2 - x_rad - 30))
    parts.append(flow_meter(x_g2 - 15, y_return - 15, params.g2_label or "G2"))
    parts.append(pipe_horizontal(x_g2 + 30, y_return, x_sensor2 - x_g2 - 90))

    # Датчики температуры и давления (обратка)
    parts.append(temp_sensor(x_sensor2, y_return + 40, params.t2_label or "t2"))
    parts.append(pressure_sensor(x_sensor2 + 60, y_return + 40, params.p2_label or "P2"))
    parts.append(pipe_horizontal(x_sensor2, y_return, x_filter2 - x_sensor2 - 20))

    parts.append(strainer(x_filter2 - 10, y_return - 10))
    parts.append(pipe_horizontal(x_filter2 + 20, y_return, x_gate2 - x_filter2 - 30))
    parts.append(gate_valve(x_gate2 - 10, y_return - 10))
    parts.append(pipe_horizontal(x_gate2 + 20, y_return, CANVAS_W - x_gate2 - 20))
    parts.append(text_label(CANVAS_W - 20, y_return + 30, "Т2 (обратка)", 10, "end"))

    # === БЛОК ГВС (справа от основной схемы) ===
    gwp_x = 720
    gwp_y_top = 250  # Ступень 2 (от подачи)
    gwp_y_bot = 380  # Ступень 1 (от обратки)

    # Врезка в подающий трубопровод для ступени 2 (сверху)
    parts.append(pipe_vertical(gwp_x, y_supply, gwp_y_top - y_supply))
    parts.append(text_label(gwp_x + 15, y_supply + 30, "→ ГВС-2", 9))

    # Теплообменник ступени 2 (от подачи)
    parts.append(heat_exchanger(gwp_x + 80, gwp_y_top - 30, rotate=90))
    parts.append(text_label(gwp_x + 120, gwp_y_top - 40, "Подогр. 2 ст.", 9))

    # Врезка в обратный трубопровод для ступени 1 (снизу)
    parts.append(pipe_vertical(gwp_x + 20, y_return, gwp_y_bot - y_return))
    parts.append(text_label(gwp_x + 35, y_return - 30, "→ ГВС-1", 9))

    # Теплообменник ступени 1 (от обратки)
    parts.append(heat_exchanger(gwp_x + 100, gwp_y_bot - 30, rotate=90))
    parts.append(text_label(gwp_x + 140, gwp_y_bot - 40, "Подогр. 1 ст.", 9))

    # Циркуляционный насос ГВС
    parts.append(pump(gwp_x + 180, gwp_y_top + 20, rotate=90))
    parts.append(text_label(gwp_x + 210, gwp_y_top + 30, "Насос ГВС", 9))

    # Расходомер G3 для ГВС
    parts.append(flow_meter(gwp_x + 240, gwp_y_top + 45, params.g3_label or "G3"))

    # Холодная вода (вход снизу)
    parts.append(pipe_vertical(gwp_x + 280, gwp_y_bot + 40, 60))
    parts.append(text_label(gwp_x + 290, gwp_y_bot + 110, "ХВС", 9))

    # Горячая вода (выход сверху)
    parts.append(pipe_vertical(gwp_x + 280, gwp_y_top - 80, -40))
    parts.append(text_label(gwp_x + 290, gwp_y_top - 90, "ГВС", 9, bold=True))

    # Соединительные линии между ступенями
    parts.append(connection_line([
        (gwp_x + 110, gwp_y_bot),
        (gwp_x + 110, gwp_y_bot - 50),
        (gwp_x + 90, gwp_y_bot - 50),
        (gwp_x + 90, gwp_y_top + 30)
    ]))

    # Возврат в обратку (после ступени 2)
    parts.append(pipe_horizontal(gwp_x + 100, gwp_y_top, -60))
    parts.append(pipe_vertical(gwp_x + 40, gwp_y_top, y_return - gwp_y_top - 20))
    parts.append(connection_line([(gwp_x + 40, y_return - 20), (gwp_x + 40, y_return)]))

    # Рамка зоны ГВС
    parts.append(dashed_rect(gwp_x - 20, gwp_y_top - 100, 340, 280, "Зона ГВС"))

    # Тепловычислитель УУТЭ (под схемой)
    calc_params = {
        "Qo": params.q_heat or "",
        "Qgvs": params.q_gwp or "",
        "T": "",
        "Txv": "",
        "Mgvs": "",
        "tgvs": "",
        "tc": "",
        "M1": params.m1 or "",
        "t1o": params.t1 or "",
        "t2o": params.t2 or "",
        "Mc": "",
        "Rgvs": "",
        "Rc": "",
        "M2": params.m2 or "",
        "P1o": params.p1 or "",
        "P2o": params.p2 or "",
    }
    parts.append(heat_calculator(60, 600, calc_params))

    # Зона УУТЭ
    parts.append(dashed_rect(50, 590, 300, 200, "Зона УУТЭ"))

    # Подписи труб
    parts.append(text_label(400, y_supply - 40, "Подающий трубопровод", 11, "middle", bold=True))
    parts.append(text_label(400, y_return + 60, "Обратный трубопровод", 11, "middle", bold=True))

    return "".join(parts)


def render_scheme_03_dep_valve(params: SchemeParams) -> str:
    """
    Схема 3: зависимая с 3-ходовым клапаном и насосом на перемычке.
    """
    # TODO
    return render_scheme_01_dep_simple(params) + text_label(100, 100, "TODO: + клапан/насос", 14, bold=True)


def render_scheme_04_dep_valve_gwp(params: SchemeParams) -> str:
    """
    Схема 4: зависимая с клапаном, насосом и ГВС.
    """
    # TODO
    return render_scheme_01_dep_simple(params) + text_label(100, 100, "TODO: + клапан/ГВС", 14, bold=True)


def render_scheme_05_dep_valve_gwp_vent(params: SchemeParams) -> str:
    """
    Схема 5: зависимая с клапаном, насосом, ГВС и вентиляцией.
    """
    # TODO
    return render_scheme_01_dep_simple(params) + text_label(100, 100, "TODO: + ГВС/вент", 14, bold=True)


def render_scheme_06_indep(params: SchemeParams) -> str:
    """
    Схема 6: независимая с 2-ходовым клапаном, насосом и подпиткой G3.
    """
    # TODO
    return text_label(100, 100, "TODO: независимая схема", 14, bold=True)


def render_scheme_07_indep_gwp(params: SchemeParams) -> str:
    """
    Схема 7: независимая с ГВС.
    """
    # TODO
    return text_label(100, 100, "TODO: независимая + ГВС", 14, bold=True)


def render_scheme_08_indep_gwp_vent(params: SchemeParams) -> str:
    """
    Схема 8: независимая с ГВС и вентиляцией.
    """
    # TODO
    return text_label(100, 100, "TODO: независимая + ГВС/вент", 14, bold=True)
