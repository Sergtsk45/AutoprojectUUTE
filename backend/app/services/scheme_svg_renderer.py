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
    
    Топология: базовая схема 1 + трёхходовой клапан перед G1 и насос на перемычке
    между подачей и обраткой (для регулирования температуры).
    """
    parts: list[str] = []

    # Координаты (как в схеме 1, но с вставкой клапана и перемычки)
    y_supply = 180
    y_return = 480
    x_start = 60
    x_gate1 = 150
    x_filter1 = 230
    x_sensor1 = 320
    x_valve3 = 420  # Трёхходовой клапан
    x_g1 = 520
    x_rad = 690
    x_g2 = 860
    x_sensor2 = 990
    x_filter2 = 1080
    x_gate2 = CANVAS_W - 60

    # Подающий трубопровод
    parts.append(text_label(x_start - 20, y_supply - 20, "Т1 (подача)", 10, anchor="end"))
    parts.append(pipe_horizontal(x_start, y_supply, x_gate1 - x_start))
    parts.append(gate_valve(x_gate1 - 10, y_supply - 10))
    parts.append(pipe_horizontal(x_gate1 + 20, y_supply, x_filter1 - x_gate1 - 20))
    parts.append(strainer(x_filter1 - 10, y_supply - 10))
    parts.append(pipe_horizontal(x_filter1 + 20, y_supply, x_sensor1 - x_filter1 - 20))

    # Датчики температуры и давления (подача)
    parts.append(temp_sensor(x_sensor1, y_supply - 40, params.t1_label or "t1"))
    parts.append(pressure_sensor(x_sensor1 + 60, y_supply - 40, params.p1_label or "P1"))
    parts.append(pipe_horizontal(x_sensor1, y_supply, x_valve3 - x_sensor1 - 30))

    # Трёхходовой клапан (регулирование температуры)
    parts.append(valve_3way(x_valve3 - 12, y_supply - 12))
    parts.append(text_label(x_valve3 + 20, y_supply - 30, "3-ход. клапан", 9))
    parts.append(pipe_horizontal(x_valve3 + 20, y_supply, x_g1 - x_valve3 - 50))

    # Перемычка с насосом (от клапана к обратке)
    y_bypass = (y_supply + y_return) / 2
    parts.append(pipe_vertical(x_valve3, y_supply + 10, y_bypass - y_supply - 40))
    parts.append(pump(x_valve3 - 12, y_bypass - 12, rotate=90))
    parts.append(text_label(x_valve3 + 25, y_bypass, "Насос", 9))
    parts.append(pipe_vertical(x_valve3, y_bypass + 15, y_return - y_bypass - 15))

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
    parts.append(text_label(CANVAS_W - 20, y_return + 30, "Т2 (обратка)", 10, anchor="end"))

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
    parts.append(dashed_rect(790, 590, 300, 200, "Зона УУТЭ"))

    # Подписи труб
    parts.append(text_label(400, y_supply - 40, "Подающий трубопровод", 11, anchor="middle", bold=True))
    parts.append(text_label(400, y_return + 60, "Обратный трубопровод", 11, anchor="middle", bold=True))

    return "".join(parts)


def render_scheme_04_dep_valve_gwp(params: SchemeParams) -> str:
    """
    Схема 4: зависимая с клапаном, насосом и ГВС.
    
    Топология: схема 3 (клапан + насос на перемычке) + блок ГВС (схема 2).
    """
    parts: list[str] = []

    # Координаты (базовые как в схеме 3)
    y_supply = 180
    y_return = 480
    x_start = 60
    x_gate1 = 150
    x_filter1 = 230
    x_sensor1 = 320
    x_valve3 = 420
    x_g1 = 520
    x_rad = 690
    x_g2 = 860
    x_sensor2 = 990
    x_filter2 = 1080
    x_gate2 = CANVAS_W - 60

    # Подающий трубопровод
    parts.append(text_label(x_start - 20, y_supply - 20, "Т1 (подача)", 10, anchor="end"))
    parts.append(pipe_horizontal(x_start, y_supply, x_gate1 - x_start))
    parts.append(gate_valve(x_gate1 - 10, y_supply - 10))
    parts.append(pipe_horizontal(x_gate1 + 20, y_supply, x_filter1 - x_gate1 - 20))
    parts.append(strainer(x_filter1 - 10, y_supply - 10))
    parts.append(pipe_horizontal(x_filter1 + 20, y_supply, x_sensor1 - x_filter1 - 20))

    # Датчики температуры и давления (подача)
    parts.append(temp_sensor(x_sensor1, y_supply - 40, params.t1_label or "t1"))
    parts.append(pressure_sensor(x_sensor1 + 60, y_supply - 40, params.p1_label or "P1"))
    parts.append(pipe_horizontal(x_sensor1, y_supply, x_valve3 - x_sensor1 - 30))

    # Трёхходовой клапан
    parts.append(valve_3way(x_valve3 - 12, y_supply - 12))
    parts.append(text_label(x_valve3 + 20, y_supply - 30, "3-ход. клапан", 9))
    parts.append(pipe_horizontal(x_valve3 + 20, y_supply, x_g1 - x_valve3 - 50))

    # Перемычка с насосом
    y_bypass = (y_supply + y_return) / 2
    parts.append(pipe_vertical(x_valve3, y_supply + 10, y_bypass - y_supply - 40))
    parts.append(pump(x_valve3 - 12, y_bypass - 12, rotate=90))
    parts.append(text_label(x_valve3 + 25, y_bypass, "Насос", 9))
    parts.append(pipe_vertical(x_valve3, y_bypass + 15, y_return - y_bypass - 15))

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
    parts.append(text_label(CANVAS_W - 20, y_return + 30, "Т2 (обратка)", 10, anchor="end"))

    # === БЛОК ГВС (как в схеме 2, но смещён левее из-за клапана) ===
    gwp_x = 560
    gwp_y_top = 250
    gwp_y_bot = 380

    # Врезка в подающий трубопровод для ступени 2
    parts.append(pipe_vertical(gwp_x, y_supply, gwp_y_top - y_supply))
    parts.append(text_label(gwp_x + 15, y_supply + 30, "→ ГВС-2", 9))

    # Теплообменник ступени 2
    parts.append(heat_exchanger(gwp_x + 80, gwp_y_top - 30, rotate=90))
    parts.append(text_label(gwp_x + 120, gwp_y_top - 40, "Подогр. 2 ст.", 9))

    # Врезка в обратный трубопровод для ступени 1
    parts.append(pipe_vertical(gwp_x + 20, y_return, gwp_y_bot - y_return))
    parts.append(text_label(gwp_x + 35, y_return - 30, "→ ГВС-1", 9))

    # Теплообменник ступени 1
    parts.append(heat_exchanger(gwp_x + 100, gwp_y_bot - 30, rotate=90))
    parts.append(text_label(gwp_x + 140, gwp_y_bot - 40, "Подогр. 1 ст.", 9))

    # Насос ГВС
    parts.append(pump(gwp_x + 180, gwp_y_top + 20, rotate=90))
    parts.append(text_label(gwp_x + 210, gwp_y_top + 30, "Насос ГВС", 9))

    # Расходомер G3
    parts.append(flow_meter(gwp_x + 240, gwp_y_top + 45, params.g3_label or "G3"))

    # Холодная вода
    parts.append(pipe_vertical(gwp_x + 280, gwp_y_bot + 40, 60))
    parts.append(text_label(gwp_x + 290, gwp_y_bot + 110, "ХВС", 9))

    # Горячая вода
    parts.append(pipe_vertical(gwp_x + 280, gwp_y_top - 80, -40))
    parts.append(text_label(gwp_x + 290, gwp_y_top - 90, "ГВС", 9, bold=True))

    # Соединительные линии
    parts.append(connection_line([
        (gwp_x + 110, gwp_y_bot),
        (gwp_x + 110, gwp_y_bot - 50),
        (gwp_x + 90, gwp_y_bot - 50),
        (gwp_x + 90, gwp_y_top + 30)
    ]))

    # Возврат в обратку
    parts.append(pipe_horizontal(gwp_x + 100, gwp_y_top, -60))
    parts.append(pipe_vertical(gwp_x + 40, gwp_y_top, y_return - gwp_y_top - 20))
    parts.append(connection_line([(gwp_x + 40, y_return - 20), (gwp_x + 40, y_return)]))

    # Рамка зоны ГВС
    parts.append(dashed_rect(gwp_x - 20, gwp_y_top - 100, 340, 280, "Зона ГВС"))

    # Тепловычислитель УУТЭ
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
    parts.append(dashed_rect(50, 590, 300, 200, "Зона УУТЭ"))

    # Подписи труб
    parts.append(text_label(400, y_supply - 40, "Подающий трубопровод", 11, anchor="middle", bold=True))
    parts.append(text_label(400, y_return + 60, "Обратный трубопровод", 11, anchor="middle", bold=True))

    return "".join(parts)


def render_scheme_05_dep_valve_gwp_vent(params: SchemeParams) -> str:
    """
    Схема 5: зависимая с клапаном, насосом, ГВС и вентиляцией.
    
    Топология: схема 4 + параллельная ветка вентиляции (отдельная врезка от подачи/обратки).
    """
    parts: list[str] = []

    # Координаты (как схема 4, но с дополнительной веткой вентиляции)
    y_supply = 150
    y_return = 480
    x_start = 60
    x_gate1 = 150
    x_filter1 = 230
    x_sensor1 = 320
    x_valve3 = 420
    x_g1 = 520
    x_rad = 690
    x_g2 = 860
    x_sensor2 = 990
    x_filter2 = 1080
    x_gate2 = CANVAS_W - 60

    # Подающий трубопровод
    parts.append(text_label(x_start - 20, y_supply - 20, "Т1 (подача)", 10, anchor="end"))
    parts.append(pipe_horizontal(x_start, y_supply, x_gate1 - x_start))
    parts.append(gate_valve(x_gate1 - 10, y_supply - 10))
    parts.append(pipe_horizontal(x_gate1 + 20, y_supply, x_filter1 - x_gate1 - 20))
    parts.append(strainer(x_filter1 - 10, y_supply - 10))
    parts.append(pipe_horizontal(x_filter1 + 20, y_supply, x_sensor1 - x_filter1 - 20))

    # Датчики температуры и давления (подача)
    parts.append(temp_sensor(x_sensor1, y_supply - 40, params.t1_label or "t1"))
    parts.append(pressure_sensor(x_sensor1 + 60, y_supply - 40, params.p1_label or "P1"))
    parts.append(pipe_horizontal(x_sensor1, y_supply, x_valve3 - x_sensor1 - 30))

    # Трёхходовой клапан
    parts.append(valve_3way(x_valve3 - 12, y_supply - 12))
    parts.append(text_label(x_valve3 + 20, y_supply - 30, "3-ход. клапан", 9))
    parts.append(pipe_horizontal(x_valve3 + 20, y_supply, x_g1 - x_valve3 - 50))

    # Перемычка с насосом
    y_bypass = (y_supply + y_return) / 2 + 30
    parts.append(pipe_vertical(x_valve3, y_supply + 10, y_bypass - y_supply - 40))
    parts.append(pump(x_valve3 - 12, y_bypass - 12, rotate=90))
    parts.append(text_label(x_valve3 + 25, y_bypass, "Насос", 9))
    parts.append(pipe_vertical(x_valve3, y_bypass + 15, y_return - y_bypass - 15))

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
    parts.append(text_label(CANVAS_W - 20, y_return + 30, "Т2 (обратка)", 10, anchor="end"))

    # === БЛОК ГВС ===
    gwp_x = 560
    gwp_y_top = 220
    gwp_y_bot = 350

    parts.append(pipe_vertical(gwp_x, y_supply, gwp_y_top - y_supply))
    parts.append(text_label(gwp_x + 15, y_supply + 30, "→ ГВС-2", 9))
    parts.append(heat_exchanger(gwp_x + 80, gwp_y_top - 30, rotate=90))
    parts.append(text_label(gwp_x + 120, gwp_y_top - 40, "Подогр. 2 ст.", 9))

    parts.append(pipe_vertical(gwp_x + 20, y_return, gwp_y_bot - y_return))
    parts.append(text_label(gwp_x + 35, y_return - 30, "→ ГВС-1", 9))
    parts.append(heat_exchanger(gwp_x + 100, gwp_y_bot - 30, rotate=90))
    parts.append(text_label(gwp_x + 140, gwp_y_bot - 40, "Подогр. 1 ст.", 9))

    parts.append(pump(gwp_x + 180, gwp_y_top + 20, rotate=90))
    parts.append(text_label(gwp_x + 210, gwp_y_top + 30, "Насос ГВС", 9))
    parts.append(flow_meter(gwp_x + 240, gwp_y_top + 45, params.g3_label or "G3"))

    parts.append(pipe_vertical(gwp_x + 280, gwp_y_bot + 40, 60))
    parts.append(text_label(gwp_x + 290, gwp_y_bot + 110, "ХВС", 9))
    parts.append(pipe_vertical(gwp_x + 280, gwp_y_top - 80, -40))
    parts.append(text_label(gwp_x + 290, gwp_y_top - 90, "ГВС", 9, bold=True))

    parts.append(connection_line([
        (gwp_x + 110, gwp_y_bot),
        (gwp_x + 110, gwp_y_bot - 50),
        (gwp_x + 90, gwp_y_bot - 50),
        (gwp_x + 90, gwp_y_top + 30)
    ]))

    parts.append(pipe_horizontal(gwp_x + 100, gwp_y_top, -60))
    parts.append(pipe_vertical(gwp_x + 40, gwp_y_top, y_return - gwp_y_top - 20))
    parts.append(connection_line([(gwp_x + 40, y_return - 20), (gwp_x + 40, y_return)]))

    parts.append(dashed_rect(gwp_x - 20, gwp_y_top - 100, 340, 280, "Зона ГВС"))

    # === БЛОК ВЕНТИЛЯЦИИ (параллельная ветка, сверху) ===
    vent_x = 200
    vent_y = 50

    # Врезка от подачи к вентиляции
    parts.append(pipe_vertical(vent_x, y_supply, -(y_supply - vent_y - 40)))
    parts.append(text_label(vent_x + 15, vent_y + 60, "→ Вент.", 9))

    # Теплообменник вентиляции
    parts.append(heat_exchanger(vent_x + 60, vent_y, rotate=0))
    parts.append(text_label(vent_x + 110, vent_y + 10, "Подогр. вент.", 9))

    # Насос вентиляции
    parts.append(pump(vent_x + 140, vent_y + 10, rotate=0))

    # Возврат в обратку
    parts.append(pipe_horizontal(vent_x + 160, vent_y + 12, 60))
    parts.append(pipe_vertical(vent_x + 220, vent_y + 12, y_return - vent_y - 12))
    parts.append(text_label(vent_x + 230, vent_y + 80, "→ Т2", 9))

    # Рамка зоны вентиляции
    parts.append(dashed_rect(vent_x - 20, vent_y - 20, 260, 80, "Зона вентиляции"))

    # Тепловычислитель УУТЭ
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
    parts.append(dashed_rect(50, 590, 300, 200, "Зона УУТЭ"))

    # Подписи труб
    parts.append(text_label(400, y_supply - 40, "Подающий трубопровод", 11, anchor="middle", bold=True))
    parts.append(text_label(400, y_return + 60, "Обратный трубопровод", 11, anchor="middle", bold=True))

    return "".join(parts)


def render_scheme_06_indep(params: SchemeParams) -> str:
    """
    Схема 6: независимая с 2-ходовым клапаном, насосом и подпиткой G3.
    
    Топология: два контура (сетевой и внутренний) соединены теплообменником.
    Сетевой контур: подача → задвижка → фильтр → t1/P1 → G1 → теплообменник → G2 → t2/P2 → фильтр → задвижка → обратка.
    Внутренний контур: насос → 2-ходовой клапан → теплообменник → радиатор → подпитка G3 → насос.
    """
    parts: list[str] = []

    # Координаты сетевого контура (верхний)
    y_net_supply = 150
    y_net_return = 350
    x_start = 60
    x_gate1 = 150
    x_filter1 = 230
    x_sensor1 = 320
    x_g1 = 450
    x_hex_net = 600  # Теплообменник (сетевая сторона)
    x_g2 = 750
    x_sensor2 = 880
    x_filter2 = 970
    x_gate2 = CANVAS_W - 60

    # Сетевой контур: подача
    parts.append(text_label(x_start - 20, y_net_supply - 20, "Т1 (сеть, подача)", 10, anchor="end"))
    parts.append(pipe_horizontal(x_start, y_net_supply, x_gate1 - x_start))
    parts.append(gate_valve(x_gate1 - 10, y_net_supply - 10))
    parts.append(pipe_horizontal(x_gate1 + 20, y_net_supply, x_filter1 - x_gate1 - 20))
    parts.append(strainer(x_filter1 - 10, y_net_supply - 10))
    parts.append(pipe_horizontal(x_filter1 + 20, y_net_supply, x_sensor1 - x_filter1 - 20))

    parts.append(temp_sensor(x_sensor1, y_net_supply - 40, params.t1_label or "t1"))
    parts.append(pressure_sensor(x_sensor1 + 60, y_net_supply - 40, params.p1_label or "P1"))
    parts.append(pipe_horizontal(x_sensor1, y_net_supply, x_g1 - x_sensor1 - 30))

    parts.append(flow_meter(x_g1 - 15, y_net_supply - 15, params.g1_label or "G1"))
    parts.append(pipe_horizontal(x_g1 + 30, y_net_supply, x_hex_net - x_g1 - 50))

    # Теплообменник (вертикальный, соединяет сетевой и внутренний контуры)
    parts.append(heat_exchanger(x_hex_net - 20, y_net_supply + 20, rotate=90))
    parts.append(text_label(x_hex_net + 40, (y_net_supply + y_net_return) / 2, "Теплообм.", 9))

    # Сетевой контур: обратка
    parts.append(pipe_horizontal(x_hex_net, y_net_return, x_g2 - x_hex_net - 30))
    parts.append(flow_meter(x_g2 - 15, y_net_return - 15, params.g2_label or "G2"))
    parts.append(pipe_horizontal(x_g2 + 30, y_net_return, x_sensor2 - x_g2 - 90))

    parts.append(temp_sensor(x_sensor2, y_net_return + 40, params.t2_label or "t2"))
    parts.append(pressure_sensor(x_sensor2 + 60, y_net_return + 40, params.p2_label or "P2"))
    parts.append(pipe_horizontal(x_sensor2, y_net_return, x_filter2 - x_sensor2 - 20))

    parts.append(strainer(x_filter2 - 10, y_net_return - 10))
    parts.append(pipe_horizontal(x_filter2 + 20, y_net_return, x_gate2 - x_filter2 - 30))
    parts.append(gate_valve(x_gate2 - 10, y_net_return - 10))
    parts.append(pipe_horizontal(x_gate2 + 20, y_net_return, CANVAS_W - x_gate2 - 20))
    parts.append(text_label(CANVAS_W - 20, y_net_return + 30, "Т2 (сеть, обратка)", 10, anchor="end"))

    # Рамка сетевого контура
    parts.append(dashed_rect(50, y_net_supply - 60, CANVAS_W - 100, 280, "Сетевой контур"))

    # === ВНУТРЕННИЙ КОНТУР (потребитель) ===
    y_int_supply = 450
    y_int_return = 650
    x_pump = 200
    x_valve2 = 300
    x_hex_int = x_hex_net  # Теплообменник (внутренняя сторона)
    x_rad = 750

    # Насос внутреннего контура
    parts.append(pump(x_pump - 12, y_int_supply - 12, rotate=0))
    parts.append(text_label(x_pump + 20, y_int_supply - 25, "Насос ВК", 9))
    parts.append(pipe_horizontal(x_pump + 15, y_int_supply, x_valve2 - x_pump - 30))

    # 2-ходовой клапан
    parts.append(valve_2way(x_valve2 - 10, y_int_supply - 10, rotate=0))
    parts.append(text_label(x_valve2 + 20, y_int_supply - 25, "2-ход. клапан", 9))
    parts.append(pipe_horizontal(x_valve2 + 20, y_int_supply, x_hex_int - x_valve2 - 40))

    # Теплообменник (внутренняя сторона подачи)
    parts.append(pipe_vertical(x_hex_int, y_net_return + 60, y_int_supply - y_net_return - 60))
    parts.append(pipe_horizontal(x_hex_int, y_int_supply, x_rad - x_hex_int - 50))

    # Радиатор
    parts.append(pipe_vertical(x_rad, y_int_supply, y_int_return - y_int_supply - 60))
    parts.append(radiator(x_rad - 20, y_int_return - 60))
    parts.append(pipe_vertical(x_rad, y_int_return - 30, 30))

    # Обратка внутреннего контура + подпитка G3
    parts.append(pipe_horizontal(x_rad, y_int_return, -(x_rad - x_pump - 30)))

    # Подпитка G3 (врезка в обратку перед насосом)
    x_g3 = x_pump - 60
    parts.append(pipe_vertical(x_g3, y_int_return - 80, 80))
    parts.append(flow_meter(x_g3 - 15, y_int_return - 80 - 15, params.g3_label or "G3"))
    parts.append(text_label(x_g3 - 50, y_int_return - 80, "Подпитка", 9))
    parts.append(pipe_vertical(x_g3, y_int_return, 40))
    parts.append(text_label(x_g3 + 15, y_int_return + 50, "← Подп.", 9))

    # Возврат в насос
    parts.append(pipe_horizontal(x_pump - 30, y_int_return, -30))
    parts.append(pipe_vertical(x_pump - 30, y_int_return, -(y_int_return - y_int_supply)))
    parts.append(pipe_horizontal(x_pump - 30, y_int_supply, 30))

    # Рамка внутреннего контура
    parts.append(dashed_rect(50, y_int_supply - 60, CANVAS_W - 100, 280, "Внутренний контур"))

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
    parts.append(heat_calculator(60, 720, calc_params))
    parts.append(dashed_rect(50, 710, 300, 200, "Зона УУТЭ"))

    # Подписи контуров
    parts.append(text_label(400, y_net_supply - 80, "Сетевой контур", 11, anchor="middle", bold=True))
    parts.append(text_label(400, y_int_supply - 80, "Внутренний контур (потребитель)", 11, anchor="middle", bold=True))

    return "".join(parts)


def render_scheme_07_indep_gwp(params: SchemeParams) -> str:
    """
    Схема 7: независимая с ГВС.
    
    Топология: схема 6 (независимая с 2-ходовым клапаном) + блок ГВС (врезка из сетевого контура).
    """
    # Базовая независимая схема (копия схемы 6, но с немного изменёнными координатами для ГВС)
    parts: list[str] = []

    y_net_supply = 120
    y_net_return = 320
    x_start = 60
    x_gate1 = 150
    x_filter1 = 230
    x_sensor1 = 320
    x_g1 = 450
    x_hex_net = 580
    x_g2 = 730
    x_sensor2 = 860
    x_filter2 = 950
    x_gate2 = CANVAS_W - 60

    # Сетевой контур: подача
    parts.append(text_label(x_start - 20, y_net_supply - 20, "Т1 (сеть, подача)", 10, anchor="end"))
    parts.append(pipe_horizontal(x_start, y_net_supply, x_gate1 - x_start))
    parts.append(gate_valve(x_gate1 - 10, y_net_supply - 10))
    parts.append(pipe_horizontal(x_gate1 + 20, y_net_supply, x_filter1 - x_gate1 - 20))
    parts.append(strainer(x_filter1 - 10, y_net_supply - 10))
    parts.append(pipe_horizontal(x_filter1 + 20, y_net_supply, x_sensor1 - x_filter1 - 20))

    parts.append(temp_sensor(x_sensor1, y_net_supply - 40, params.t1_label or "t1"))
    parts.append(pressure_sensor(x_sensor1 + 60, y_net_supply - 40, params.p1_label or "P1"))
    parts.append(pipe_horizontal(x_sensor1, y_net_supply, x_g1 - x_sensor1 - 30))

    parts.append(flow_meter(x_g1 - 15, y_net_supply - 15, params.g1_label or "G1"))
    parts.append(pipe_horizontal(x_g1 + 30, y_net_supply, x_hex_net - x_g1 - 50))

    # Теплообменник
    parts.append(heat_exchanger(x_hex_net - 20, y_net_supply + 20, rotate=90))
    parts.append(text_label(x_hex_net + 40, (y_net_supply + y_net_return) / 2, "Теплообм.", 9))

    # Сетевой контур: обратка
    parts.append(pipe_horizontal(x_hex_net, y_net_return, x_g2 - x_hex_net - 30))
    parts.append(flow_meter(x_g2 - 15, y_net_return - 15, params.g2_label or "G2"))
    parts.append(pipe_horizontal(x_g2 + 30, y_net_return, x_sensor2 - x_g2 - 90))

    parts.append(temp_sensor(x_sensor2, y_net_return + 40, params.t2_label or "t2"))
    parts.append(pressure_sensor(x_sensor2 + 60, y_net_return + 40, params.p2_label or "P2"))
    parts.append(pipe_horizontal(x_sensor2, y_net_return, x_filter2 - x_sensor2 - 20))

    parts.append(strainer(x_filter2 - 10, y_net_return - 10))
    parts.append(pipe_horizontal(x_filter2 + 20, y_net_return, x_gate2 - x_filter2 - 30))
    parts.append(gate_valve(x_gate2 - 10, y_net_return - 10))
    parts.append(pipe_horizontal(x_gate2 + 20, y_net_return, CANVAS_W - x_gate2 - 20))
    parts.append(text_label(CANVAS_W - 20, y_net_return + 30, "Т2 (сеть, обратка)", 10, anchor="end"))

    parts.append(dashed_rect(50, y_net_supply - 40, CANVAS_W - 100, 250, "Сетевой контур"))

    # Внутренний контур
    y_int_supply = 390
    y_int_return = 550
    x_pump = 180
    x_valve2 = 280
    x_hex_int = x_hex_net
    x_rad = 730

    parts.append(pump(x_pump - 12, y_int_supply - 12, rotate=0))
    parts.append(text_label(x_pump + 20, y_int_supply - 25, "Насос ВК", 9))
    parts.append(pipe_horizontal(x_pump + 15, y_int_supply, x_valve2 - x_pump - 30))

    parts.append(valve_2way(x_valve2 - 10, y_int_supply - 10, rotate=0))
    parts.append(text_label(x_valve2 + 20, y_int_supply - 25, "2-ход. клапан", 9))
    parts.append(pipe_horizontal(x_valve2 + 20, y_int_supply, x_hex_int - x_valve2 - 40))

    parts.append(pipe_vertical(x_hex_int, y_net_return + 60, y_int_supply - y_net_return - 60))
    parts.append(pipe_horizontal(x_hex_int, y_int_supply, x_rad - x_hex_int - 50))

    parts.append(pipe_vertical(x_rad, y_int_supply, y_int_return - y_int_supply - 40))
    parts.append(radiator(x_rad - 20, y_int_return - 40))
    parts.append(pipe_vertical(x_rad, y_int_return - 20, 20))

    parts.append(pipe_horizontal(x_rad, y_int_return, -(x_rad - x_pump - 30)))

    # Подпитка G3
    x_g3 = x_pump - 60
    parts.append(pipe_vertical(x_g3, y_int_return - 60, 60))
    parts.append(flow_meter(x_g3 - 15, y_int_return - 60 - 15, params.g3_label or "G3"))
    parts.append(text_label(x_g3 - 50, y_int_return - 60, "Подпитка", 9))
    parts.append(pipe_vertical(x_g3, y_int_return, 30))

    parts.append(pipe_horizontal(x_pump - 30, y_int_return, -30))
    parts.append(pipe_vertical(x_pump - 30, y_int_return, -(y_int_return - y_int_supply)))
    parts.append(pipe_horizontal(x_pump - 30, y_int_supply, 30))

    parts.append(dashed_rect(50, y_int_supply - 40, CANVAS_W - 100, 220, "Внутренний контур"))

    # === БЛОК ГВС (врезка из сетевого контура) ===
    gwp_x = 750
    gwp_y_top = 200
    gwp_y_bot = 300

    parts.append(pipe_vertical(gwp_x, y_net_supply, gwp_y_top - y_net_supply))
    parts.append(text_label(gwp_x + 15, y_net_supply + 25, "→ ГВС-2", 9))
    parts.append(heat_exchanger(gwp_x + 50, gwp_y_top - 30, rotate=90))
    parts.append(text_label(gwp_x + 90, gwp_y_top - 40, "Подогр. 2 ст.", 9))

    parts.append(pipe_vertical(gwp_x + 20, y_net_return, gwp_y_bot - y_net_return))
    parts.append(text_label(gwp_x + 35, y_net_return - 25, "→ ГВС-1", 9))
    parts.append(heat_exchanger(gwp_x + 70, gwp_y_bot - 30, rotate=90))
    parts.append(text_label(gwp_x + 110, gwp_y_bot - 40, "Подогр. 1 ст.", 9))

    parts.append(pump(gwp_x + 150, gwp_y_top + 15, rotate=90))
    parts.append(text_label(gwp_x + 180, gwp_y_top + 25, "Насос ГВС", 9))
    parts.append(flow_meter(gwp_x + 210, gwp_y_top + 40, "G_гвс"))

    parts.append(pipe_vertical(gwp_x + 250, gwp_y_bot + 30, 50))
    parts.append(text_label(gwp_x + 260, gwp_y_bot + 90, "ХВС", 9))
    parts.append(pipe_vertical(gwp_x + 250, gwp_y_top - 70, -40))
    parts.append(text_label(gwp_x + 260, gwp_y_top - 80, "ГВС", 9, bold=True))

    parts.append(connection_line([
        (gwp_x + 80, gwp_y_bot),
        (gwp_x + 80, gwp_y_bot - 40),
        (gwp_x + 60, gwp_y_bot - 40),
        (gwp_x + 60, gwp_y_top + 25)
    ]))

    parts.append(pipe_horizontal(gwp_x + 70, gwp_y_top, -50))
    parts.append(pipe_vertical(gwp_x + 20, gwp_y_top, y_net_return - gwp_y_top - 20))
    parts.append(connection_line([(gwp_x + 20, y_net_return - 20), (gwp_x + 20, y_net_return)]))

    parts.append(dashed_rect(gwp_x - 20, gwp_y_top - 90, 300, 240, "Зона ГВС"))

    # Тепловычислитель УУТЭ
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
    parts.append(heat_calculator(60, 620, calc_params))
    parts.append(dashed_rect(50, 610, 300, 200, "Зона УУТЭ"))

    # Подписи контуров
    parts.append(text_label(400, y_net_supply - 60, "Сетевой контур", 11, anchor="middle", bold=True))
    parts.append(text_label(400, y_int_supply - 60, "Внутренний контур (потребитель)", 11, anchor="middle", bold=True))

    return "".join(parts)


def render_scheme_08_indep_gwp_vent(params: SchemeParams) -> str:
    """
    Схема 8: независимая с ГВС и вентиляцией.
    
    Топология: схема 7 (независимая с ГВС) + параллельная ветка вентиляции из сетевого контура.
    """
    parts: list[str] = []

    y_net_supply = 100
    y_net_return = 300
    x_start = 60
    x_gate1 = 150
    x_filter1 = 230
    x_sensor1 = 320
    x_g1 = 450
    x_hex_net = 580
    x_g2 = 730
    x_sensor2 = 860
    x_filter2 = 950
    x_gate2 = CANVAS_W - 60

    # Сетевой контур: подача
    parts.append(text_label(x_start - 20, y_net_supply - 20, "Т1 (сеть)", 10, anchor="end"))
    parts.append(pipe_horizontal(x_start, y_net_supply, x_gate1 - x_start))
    parts.append(gate_valve(x_gate1 - 10, y_net_supply - 10))
    parts.append(pipe_horizontal(x_gate1 + 20, y_net_supply, x_filter1 - x_gate1 - 20))
    parts.append(strainer(x_filter1 - 10, y_net_supply - 10))
    parts.append(pipe_horizontal(x_filter1 + 20, y_net_supply, x_sensor1 - x_filter1 - 20))

    parts.append(temp_sensor(x_sensor1, y_net_supply - 40, params.t1_label or "t1"))
    parts.append(pressure_sensor(x_sensor1 + 60, y_net_supply - 40, params.p1_label or "P1"))
    parts.append(pipe_horizontal(x_sensor1, y_net_supply, x_g1 - x_sensor1 - 30))

    parts.append(flow_meter(x_g1 - 15, y_net_supply - 15, params.g1_label or "G1"))
    parts.append(pipe_horizontal(x_g1 + 30, y_net_supply, x_hex_net - x_g1 - 50))

    # Теплообменник
    parts.append(heat_exchanger(x_hex_net - 20, y_net_supply + 20, rotate=90))
    parts.append(text_label(x_hex_net + 40, (y_net_supply + y_net_return) / 2, "Теплообм.", 9))

    # Сетевой контур: обратка
    parts.append(pipe_horizontal(x_hex_net, y_net_return, x_g2 - x_hex_net - 30))
    parts.append(flow_meter(x_g2 - 15, y_net_return - 15, params.g2_label or "G2"))
    parts.append(pipe_horizontal(x_g2 + 30, y_net_return, x_sensor2 - x_g2 - 90))

    parts.append(temp_sensor(x_sensor2, y_net_return + 40, params.t2_label or "t2"))
    parts.append(pressure_sensor(x_sensor2 + 60, y_net_return + 40, params.p2_label or "P2"))
    parts.append(pipe_horizontal(x_sensor2, y_net_return, x_filter2 - x_sensor2 - 20))

    parts.append(strainer(x_filter2 - 10, y_net_return - 10))
    parts.append(pipe_horizontal(x_filter2 + 20, y_net_return, x_gate2 - x_filter2 - 30))
    parts.append(gate_valve(x_gate2 - 10, y_net_return - 10))
    parts.append(pipe_horizontal(x_gate2 + 20, y_net_return, CANVAS_W - x_gate2 - 20))
    parts.append(text_label(CANVAS_W - 20, y_net_return + 30, "Т2 (сеть)", 10, anchor="end"))

    parts.append(dashed_rect(50, y_net_supply - 40, CANVAS_W - 100, 260, "Сетевой контур"))

    # Внутренний контур
    y_int_supply = 370
    y_int_return = 520
    x_pump = 180
    x_valve2 = 280
    x_hex_int = x_hex_net
    x_rad = 730

    parts.append(pump(x_pump - 12, y_int_supply - 12, rotate=0))
    parts.append(text_label(x_pump + 20, y_int_supply - 25, "Насос ВК", 9))
    parts.append(pipe_horizontal(x_pump + 15, y_int_supply, x_valve2 - x_pump - 30))

    parts.append(valve_2way(x_valve2 - 10, y_int_supply - 10, rotate=0))
    parts.append(text_label(x_valve2 + 20, y_int_supply - 25, "2-ход. клапан", 9))
    parts.append(pipe_horizontal(x_valve2 + 20, y_int_supply, x_hex_int - x_valve2 - 40))

    parts.append(pipe_vertical(x_hex_int, y_net_return + 60, y_int_supply - y_net_return - 60))
    parts.append(pipe_horizontal(x_hex_int, y_int_supply, x_rad - x_hex_int - 50))

    parts.append(pipe_vertical(x_rad, y_int_supply, y_int_return - y_int_supply - 35))
    parts.append(radiator(x_rad - 20, y_int_return - 35))
    parts.append(pipe_vertical(x_rad, y_int_return - 15, 15))

    parts.append(pipe_horizontal(x_rad, y_int_return, -(x_rad - x_pump - 30)))

    # Подпитка G3
    x_g3 = x_pump - 60
    parts.append(pipe_vertical(x_g3, y_int_return - 50, 50))
    parts.append(flow_meter(x_g3 - 15, y_int_return - 50 - 15, params.g3_label or "G3"))
    parts.append(text_label(x_g3 - 50, y_int_return - 50, "Подпитка", 9))
    parts.append(pipe_vertical(x_g3, y_int_return, 25))

    parts.append(pipe_horizontal(x_pump - 30, y_int_return, -30))
    parts.append(pipe_vertical(x_pump - 30, y_int_return, -(y_int_return - y_int_supply)))
    parts.append(pipe_horizontal(x_pump - 30, y_int_supply, 30))

    parts.append(dashed_rect(50, y_int_supply - 40, CANVAS_W - 100, 200, "Внутренний контур"))

    # === БЛОК ГВС ===
    gwp_x = 750
    gwp_y_top = 180
    gwp_y_bot = 280

    parts.append(pipe_vertical(gwp_x, y_net_supply, gwp_y_top - y_net_supply))
    parts.append(text_label(gwp_x + 15, y_net_supply + 20, "→ ГВС-2", 9))
    parts.append(heat_exchanger(gwp_x + 50, gwp_y_top - 30, rotate=90))
    parts.append(text_label(gwp_x + 90, gwp_y_top - 40, "Подогр. 2 ст.", 9))

    parts.append(pipe_vertical(gwp_x + 20, y_net_return, gwp_y_bot - y_net_return))
    parts.append(text_label(gwp_x + 35, y_net_return - 25, "→ ГВС-1", 9))
    parts.append(heat_exchanger(gwp_x + 70, gwp_y_bot - 30, rotate=90))
    parts.append(text_label(gwp_x + 110, gwp_y_bot - 40, "Подогр. 1 ст.", 9))

    parts.append(pump(gwp_x + 150, gwp_y_top + 15, rotate=90))
    parts.append(text_label(gwp_x + 180, gwp_y_top + 25, "Насос ГВС", 9))
    parts.append(flow_meter(gwp_x + 210, gwp_y_top + 40, "G_гвс"))

    parts.append(pipe_vertical(gwp_x + 250, gwp_y_bot + 25, 45))
    parts.append(text_label(gwp_x + 260, gwp_y_bot + 80, "ХВС", 9))
    parts.append(pipe_vertical(gwp_x + 250, gwp_y_top - 70, -35))
    parts.append(text_label(gwp_x + 260, gwp_y_top - 75, "ГВС", 9, bold=True))

    parts.append(connection_line([
        (gwp_x + 80, gwp_y_bot),
        (gwp_x + 80, gwp_y_bot - 35),
        (gwp_x + 60, gwp_y_bot - 35),
        (gwp_x + 60, gwp_y_top + 25)
    ]))

    parts.append(pipe_horizontal(gwp_x + 70, gwp_y_top, -50))
    parts.append(pipe_vertical(gwp_x + 20, gwp_y_top, y_net_return - gwp_y_top - 20))
    parts.append(connection_line([(gwp_x + 20, y_net_return - 20), (gwp_x + 20, y_net_return)]))

    parts.append(dashed_rect(gwp_x - 20, gwp_y_top - 85, 300, 220, "Зона ГВС"))

    # === БЛОК ВЕНТИЛЯЦИИ ===
    vent_x = 200
    vent_y = 30

    parts.append(pipe_vertical(vent_x, y_net_supply, -(y_net_supply - vent_y - 30)))
    parts.append(text_label(vent_x + 15, vent_y + 50, "→ Вент.", 9))

    parts.append(heat_exchanger(vent_x + 50, vent_y, rotate=0))
    parts.append(text_label(vent_x + 100, vent_y + 10, "Подогр. вент.", 9))

    parts.append(pump(vent_x + 130, vent_y + 10, rotate=0))

    parts.append(pipe_horizontal(vent_x + 150, vent_y + 12, 50))
    parts.append(pipe_vertical(vent_x + 200, vent_y + 12, y_net_return - vent_y - 12))
    parts.append(text_label(vent_x + 210, vent_y + 70, "→ Т2", 9))

    parts.append(dashed_rect(vent_x - 20, vent_y - 20, 240, 70, "Зона вентиляции"))

    # Тепловычислитель УУТЭ
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
    parts.append(heat_calculator(60, 590, calc_params))
    parts.append(dashed_rect(50, 580, 300, 200, "Зона УУТЭ"))

    # Подписи контуров
    parts.append(text_label(400, y_net_supply - 60, "Сетевой контур", 11, anchor="middle", bold=True))
    parts.append(text_label(400, y_int_supply - 60, "Внутренний контур", 11, anchor="middle", bold=True))

    return "".join(parts)
