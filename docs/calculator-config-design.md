# Дизайн: Настроечная БД вычислителя в админке (мультиприборность)

**Дата:** 2026-04-12
**Статус:** Проект
**Основание:** ПП РФ №1034 п.44(е) — проект УУТЭ обязан содержать настроечную БД

---

## Контекст

Клиент в опросном листе выбирает производителя (Эско 3Э / Теплоком / Логика).
Этот выбор определяет какой **тепловычислитель** используется в проекте:

| Производитель в опроснике | Тепловычислитель | Конфигуратор |
|---|---|---|
| `esko` — Эско 3Э | **ЭСКО-Терра М** | ПО «ЭСКО Конфигуратор» |
| `teplokom` — Теплоком (ТВ7) | **ТВ7** (Термотроник) | ПО «ТВ7 Конфигуратор» |
| `logika` — Логика (СПТ) | **СПТ-941.20** | ПО «КОНФИГУРАТОР» (НПФ Логика) |

Инженер в админке видит **сворачиваемую таблицу настроечных параметров**, предзаполненную из ТУ + опросного листа. Недостающее запрашивается у клиента или заполняется вручную. На выходе — PDF-лист для вложения в проект.

---

## Маппинг: производитель → шаблон

```
survey.manufacturer  →  calculator_type  →  template JSON
─────────────────────────────────────────────────────────
"esko"               →  "esko_terra"     →  esko_terra.json
"teplokom"            →  "tv7"            →  tv7.json
"logika"              →  "spt941"         →  spt941.json
"pulsar"              →  null (пока)      →  нет шаблона
"other"               →  null             →  ручной режим
```

Если шаблон = null, блок настроечной БД в админке показывает:
> «Для данного вычислителя шаблон ещё не создан. Настроечную БД необходимо оформить вручную.»

---

## Архитектура

### 1. JSON-шаблоны (`backend/calculator_templates/`)

Каждый файл описывает **полный** перечень настроечных параметров прибора по его РЭ. Структура единая для всех приборов:

```json
{
  "calculator_id": "tv7",
  "calculator_name": "ТВ7 (Термотроник)",
  "re_version": "РЭПР.407290.007 РЭ ред. 2.06",
  "has_dual_db": true,

  "groups": [
    {
      "id": "system",
      "title": "Системные параметры",
      "description": "Общие для БД1 и БД2",
      "params": [
        {
          "id": "EI",
          "label": "ЕИ",
          "full_label": "Единицы измерений Q и Р",
          "type": "select",
          "options": [
            {"value": "0", "text": "Гкал и кгс/см²"},
            {"value": "1", "text": "ГДж и МПа"},
            {"value": "2", "text": "MWh и Bar"}
          ],
          "default": "0",
          "source": "default",
          "auto_rule": null,
          "required": true,
          "re_reference": "п.2.6, стр.14"
        },
        {
          "id": "PI",
          "label": "ПИ",
          "full_label": "Период измерений",
          "type": "select",
          "options": [
            {"value": "0", "text": "600 с"},
            {"value": "1", "text": "60 с"},
            {"value": "2", "text": "6 с"}
          ],
          "default": "0",
          "source": "default",
          "required": true
        },
        {
          "id": "TV_COUNT",
          "label": "ТВ",
          "full_label": "Количество тепловых вводов",
          "type": "select",
          "options": [
            {"value": "0", "text": "только ТВ1"},
            {"value": "1", "text": "ТВ1 и ТВ2"}
          ],
          "default": null,
          "source": "auto",
          "auto_rule": "derive_tv_count",
          "required": true
        },
        {
          "id": "tx",
          "label": "tх",
          "full_label": "Договорная температура холодной воды, °C",
          "type": "number",
          "min": 0, "max": 99.9, "step": 0.1,
          "default": null,
          "source": "client",
          "required": true,
          "hint": "Из договора теплоснабжения. Обычно зима=5, лето=15"
        },
        {
          "id": "Px",
          "label": "Рх",
          "full_label": "Договорное давление холодной воды, кгс/см²",
          "type": "number",
          "min": 0, "max": 17, "step": 0.1,
          "default": null,
          "source": "client",
          "required": false
        },
        {
          "id": "HT",
          "label": "ХТ",
          "full_label": "Характеристика термопреобразователей",
          "type": "select",
          "options": [
            {"value": "0", "text": "100П (W100=1,391)"},
            {"value": "1", "text": "Pt100 (W100=1,385)"},
            {"value": "2", "text": "100М (W100=1,428)"},
            {"value": "3", "text": "500П"},
            {"value": "4", "text": "Pt500"}
          ],
          "default": null,
          "source": "engineer",
          "auto_rule": "derive_from_tu_sensors",
          "required": true,
          "hint": "По паспорту датчика. КТСН-Н → 100П"
        }
      ]
    },
    {
      "id": "tv1_general",
      "title": "Общие параметры ТВ1",
      "description": "Определяют алгоритм расчёта тепловой энергии",
      "params": [
        {
          "id": "SI",
          "label": "СИ",
          "full_label": "Схема измерений",
          "type": "select",
          "options": [
            {"value": "1", "text": "СИ=1: закрытая, 2 ВС (подающий+обратный)"},
            {"value": "2", "text": "СИ=2: закрытая, 1 ВС в подающем"},
            {"value": "3", "text": "СИ=3: закрытая, 1 ВС в обратном"},
            {"value": "4", "text": "СИ=4: открытая, 3 ВС (подающий+обратный+подпитка)"},
            {"value": "5", "text": "СИ=5: открытая, 2 ВС (подающий+подпитка)"},
            {"value": "6", "text": "СИ=6: открытая, 2 ВС (обратный+подпитка)"}
          ],
          "default": null,
          "source": "auto",
          "auto_rule": "derive_si_from_system",
          "required": true
        },
        {
          "id": "FT",
          "label": "ФТ",
          "full_label": "Формула расчёта тепла",
          "type": "select",
          "options": [
            {"value": "0", "text": "Q = M1·(h1-h2)"},
            {"value": "1", "text": "Q = M2·(h1-h2)"},
            {"value": "2", "text": "Q = M1·h1 - M2·h2 + (M1-M2)·hх"}
          ],
          "default": null,
          "source": "auto",
          "auto_rule": "derive_ft_from_si",
          "required": true
        },
        {
          "id": "SE",
          "label": "СЕ",
          "full_label": "Сезонность",
          "type": "select",
          "options": [
            {"value": "0", "text": "Круглогодично"},
            {"value": "1", "text": "Только зимний сезон"},
            {"value": "2", "text": "Только летний сезон"}
          ],
          "default": null,
          "source": "client",
          "required": true,
          "hint": "Из договора с РСО"
        },
        {
          "id": "KT",
          "label": "КТ",
          "full_label": "Контроль часового тепла",
          "type": "select",
          "options": [
            {"value": "0", "text": "Нет контроля"},
            {"value": "1", "text": "Усечение"},
            {"value": "2", "text": "Пропуск"}
          ],
          "default": "0",
          "source": "engineer",
          "required": true,
          "hint": "Согласовать с РСО"
        },
        {
          "id": "KM",
          "label": "КМ",
          "full_label": "Контроль баланса масс",
          "type": "select",
          "options": [
            {"value": "0", "text": "Нет контроля"},
            {"value": "1", "text": "По часу"},
            {"value": "2", "text": "Текущий"}
          ],
          "default": "0",
          "source": "engineer",
          "required": true
        },
        {
          "id": "KT3",
          "label": "КТ3",
          "full_label": "Назначение трубопровода Тр3",
          "type": "select",
          "options": [
            {"value": "0", "text": "Не используется"},
            {"value": "1", "text": "Учёт объёма воды (ХВС/питьевая)"},
            {"value": "2", "text": "Измерение температуры"},
            {"value": "3", "text": "Расчёт тепла (ГВС/подпитка)"}
          ],
          "default": null,
          "source": "auto",
          "auto_rule": "derive_kt3_from_system",
          "required": true
        }
      ]
    },
    {
      "id": "tv1_tr1",
      "title": "Тр1 — подающий трубопровод (ТВ1)",
      "repeat_for": ["tv1_tr2", "tv1_tr3"],
      "params": [
        {
          "id": "KY_1",
          "label": "Ку",
          "full_label": "Вес импульса расходомера, л/имп",
          "type": "number",
          "min": 0.0001, "max": 10000,
          "default": null,
          "source": "engineer",
          "required": true,
          "hint": "Из паспорта выбранного расходомера"
        },
        {
          "id": "GV_1",
          "label": "Gв",
          "full_label": "Верхний предел диапазона расхода, м³/ч",
          "type": "number",
          "default": null,
          "source": "engineer",
          "required": true,
          "hint": "Из паспорта расходомера (Qmax)"
        },
        {
          "id": "GN_1",
          "label": "Gн",
          "full_label": "Нижний предел диапазона расхода, м³/ч",
          "type": "number",
          "default": null,
          "source": "engineer",
          "required": true,
          "hint": "Из паспорта расходомера (Qmin)"
        },
        {
          "id": "GDOG_1",
          "label": "Gдог",
          "full_label": "Договорной расход, м³/ч",
          "type": "number",
          "default": null,
          "source": "auto",
          "auto_rule": "calculate_gdog_from_load",
          "required": true,
          "hint": "G = Q×1000 / (t1-t2)"
        },
        {
          "id": "PDOG_1",
          "label": "Рдог",
          "full_label": "Договорное давление, кгс/см²",
          "type": "number",
          "default": null,
          "source": "auto",
          "auto_rule": "tu.coolant.supply_pressure_kgcm2",
          "required": true
        },
        {
          "id": "TDOG_1",
          "label": "tдог",
          "full_label": "Договорная температура, °C",
          "type": "number",
          "default": null,
          "source": "auto",
          "auto_rule": "tu.coolant.supply_temp",
          "required": true
        },
        {
          "id": "PV_1",
          "label": "Рв",
          "full_label": "Верхний предел датчика давления, кгс/см²",
          "type": "number",
          "min": 1, "max": 25,
          "default": null,
          "source": "engineer",
          "required": true,
          "hint": "Из паспорта ПД"
        },
        {
          "id": "PD_USE_1",
          "label": "ДД",
          "full_label": "Использование датчика давления",
          "type": "select",
          "options": [
            {"value": "0", "text": "Нет — расчёт по Рдог"},
            {"value": "1", "text": "Есть, используется"},
            {"value": "2", "text": "Есть, не используется"}
          ],
          "default": null,
          "source": "engineer",
          "required": true
        }
      ]
    }
  ],

  "auto_rules": {
    "derive_tv_count": {
      "description": "Если система открытая И есть ГВС → ТВ=1 (два ввода), иначе ТВ=0",
      "inputs": ["tu.connection.system_type", "tu.heat_loads.hot_water_load"]
    },
    "derive_si_from_system": {
      "description": "закрытая → СИ=1; открытая → СИ=4",
      "inputs": ["tu.connection.system_type"]
    },
    "derive_ft_from_si": {
      "description": "СИ=1,2,3 → ФТ=0; СИ=4,5,6 → ФТ=2",
      "inputs": ["SI"]
    },
    "derive_kt3_from_system": {
      "description": "открытая с ГВС → КТ3=3; закрытая без ГВС → КТ3=0",
      "inputs": ["tu.connection.system_type", "tu.heat_loads.hot_water_load"]
    },
    "derive_from_tu_sensors": {
      "description": "КТСН-Н → 100П (0); КТПТР → Pt100 (1)",
      "inputs": ["tu.metering.temp_sensor_model"]
    },
    "calculate_gdog_from_load": {
      "description": "Gдог = Q_total × 1000 / (t_supply - t_return)",
      "inputs": ["tu.heat_loads.total_load", "tu.coolant.supply_temp", "tu.coolant.return_temp"]
    }
  }
}
```

### Различия между шаблонами приборов

| Аспект | ТВ7 | СПТ-941.20 | ЭСКО-Терра М |
|---|---|---|---|
| Баз данных | 2 (БД1, БД2) | 1 | 1 |
| Тепловых вводов макс | 2 (ТВ1, ТВ2) | 1 (3 трубопровода) | 2 |
| Трубопроводов макс | 3 на ТВ | 3 | 6 |
| Датчиков давления | 0–6 (зависит от модели) | 3 | до 6 |
| Схем измерений | 6 (СИ=1..6) | 12 (СИ=0..11) | По конфигурации |
| Обозначения параметров | ЕИ, ПИ, СИ, ФТ... | ЕИ, ПЕ, СИ, ФТ... | Свои обозначения |
| Конфигуратор производителя | ТВ7 Конфигуратор (.xls) | КОНФИГУРАТОР + ПРОЛОГ | ЭСКО Конфигуратор |

### 2. Модель в БД

```python
class CalculatorConfig(Base):
    __tablename__ = "calculator_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), unique=True
    )
    calculator_type: Mapped[str]          # "tv7" | "spt941" | "esko_terra"
    config_data: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # {"EI": "0", "PI": "0", "tx": 5.0, ...}

    status: Mapped[str] = mapped_column(
        default="draft"
    )  # draft → filling → complete → exported

    # Трекинг заполненности
    total_params: Mapped[int] = mapped_column(default=0)
    filled_params: Mapped[int] = mapped_column(default=0)
    missing_required: Mapped[list] = mapped_column(
        JSONB, default=list
    )  # ["tx", "KY_1", ...]

    # Что запрошено у клиента
    client_requested_params: Mapped[list] = mapped_column(
        JSONB, default=list
    )  # ["tx", "SE"]
    client_response_data: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )

    # Мета
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    exported_at: Mapped[datetime | None]

    order: Mapped["Order"] = relationship(
        back_populates="calculator_config"
    )
```

### 3. API-эндпоинты

```
GET    /admin/orders/{id}/calc-config
       → Текущая конфигурация + шаблон + источники значений

POST   /admin/orders/{id}/calc-config/init
       body: { calculator_type: "tv7" }  (или авто из survey)
       → Создать, автозаполнить из ТУ + опросника

PATCH  /admin/orders/{id}/calc-config
       body: { params: { "tx": 5.0, "KY_1": 10 } }
       → Инженер обновляет параметры

POST   /admin/orders/{id}/calc-config/request-client
       body: { params: ["tx", "SE"], message: "..." }
       → Email клиенту с конкретными вопросами

POST   /admin/orders/{id}/calc-config/export-pdf
       → Сгенерировать PDF настроечной БД
```

### 4. Сервис автозаполнения

```python
# services/calculator_config_service.py

MANUFACTURER_TO_CALCULATOR = {
    "esko": "esko_terra",
    "teplokom": "tv7",
    "logika": "spt941",
}

def init_config(order) -> CalculatorConfig:
    """Создаёт конфигурацию по выбранному производителю."""
    manufacturer = order.survey_data.get("manufacturer")
    calc_type = MANUFACTURER_TO_CALCULATOR.get(manufacturer)

    if not calc_type:
        raise ValueError(f"Нет шаблона для {manufacturer}")

    template = load_template(calc_type)
    config_data = auto_fill(template, order.parsed_tu, order.survey_data)

    return CalculatorConfig(
        order_id=order.id,
        calculator_type=calc_type,
        config_data=config_data,
        ...
    )

def auto_fill(template, parsed_tu, survey_data) -> dict:
    """Автозаполнение по правилам шаблона."""
    result = {}

    for group in template["groups"]:
        for param in group["params"]:
            pid = param["id"]
            value = None

            # 1. Значение по умолчанию
            if param.get("default") is not None:
                value = param["default"]

            # 2. Авто-правило
            rule = param.get("auto_rule")
            if rule:
                value = execute_auto_rule(
                    rule, parsed_tu, survey_data, result
                ) or value

            if value is not None:
                result[pid] = value

    return result

def execute_auto_rule(rule_name, tu, survey, current):
    """Выполняет правило автозаполнения."""

    # Прямой маппинг из ТУ
    if rule_name.startswith("tu."):
        return get_nested(tu, rule_name[3:])

    # Расчёт Gдог
    if rule_name == "calculate_gdog_from_load":
        Q = get_nested(tu, "heat_loads.total_load")
        t1 = get_nested(tu, "coolant.supply_temp")
        t2 = get_nested(tu, "coolant.return_temp")
        if Q and t1 and t2 and (t1 - t2) > 0:
            return round(Q * 1000 / (t1 - t2), 2)

    # Схема измерений из типа системы
    if rule_name == "derive_si_from_system":
        sys_type = get_nested(tu, "connection.system_type") or ""
        if "закрытая" in sys_type:
            return "1"
        elif "открытая" in sys_type:
            return "4"

    # ... другие правила
    return None
```

### 5. UI в admin.html — сворачиваемая таблица

```
┌─────────────────────────────────────────────────────────────┐
│ ▼ Настроечная БД: ТВ7 (Термотроник)         14/28 ████░░░░ │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Легенда: 🟢 из ТУ  🔵 по умолч.  🟡 запрос  ⬜ инженер   │
│                                                             │
│  ┌─ Системные параметры ──────────────────────────────────┐ │
│  │ Обозн. │ Параметр                   │ Значение     │ ● │ │
│  │ ЕИ     │ Единицы Q и Р              │ Гкал,кгс/см² │ 🔵│ │
│  │ ПИ     │ Период измерений           │ 600 с        │ 🔵│ │
│  │ ТВ     │ Кол-во тепловых вводов     │ только ТВ1   │ 🟢│ │
│  │ tх     │ Договорная t ХВС, °C       │ [____]       │ 🟡│ │
│  │ Рх     │ Договорное Р ХВС, кгс/см²  │ [____]       │ 🟡│ │
│  │ ХТ     │ Характеристика ТС          │ 100П         │ 🟢│ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Общие параметры ТВ1 ─────────────────────────────────┐ │
│  │ СИ     │ Схема измерений            │ 1 (закр,2ВС) │ 🟢│ │
│  │ ФТ     │ Формула расчёта            │ Q=M1(h1-h2)  │ 🟢│ │
│  │ СЕ     │ Сезонность                 │ [____]       │ 🟡│ │
│  │ КТ     │ Контроль тепла             │ [Нет контр▾] │ ⬜│ │
│  │ КМ     │ Контроль масс              │ [Нет контр▾] │ ⬜│ │
│  │ КТ3    │ Назначение Тр3             │ Не использ.  │ 🟢│ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Тр1 — подающий (ТВ1) ────────────────────────────────┐ │
│  │ Ку     │ Вес импульса, л/имп        │ [____]       │ ⬜│ │
│  │ Gв     │ Верхний предел, м³/ч       │ [____]       │ ⬜│ │
│  │ Gн     │ Нижний предел, м³/ч        │ [____]       │ ⬜│ │
│  │ Gдог   │ Договорной расход, м³/ч    │ 7.14         │ 🟢│ │
│  │ Рдог   │ Договорное давление        │ 6.6          │ 🟢│ │
│  │ tдог   │ Договорная температура     │ 117.2        │ 🟢│ │
│  │ Рв     │ Верх.пред.ПД, кгс/см²     │ [____]       │ ⬜│ │
│  │ ДД     │ Использование ПД           │ [___▾]       │ ⬜│ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Тр2 — обратный (ТВ1) ────────────────────────────────┐ │
│  │ ...аналогично, Рдог=5.8, tдог=70...                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ⚠ Не заполнено обязательных: tх, Ку(Тр1), Gв(Тр1),     │
│    Gн(Тр1), Рв(Тр1), ДД(Тр1), Ку(Тр2)...                │
│                                                             │
│  [📧 Запросить у клиента (tх, СЕ)]  [💾 Сохранить]  [📄 PDF] │
└─────────────────────────────────────────────────────────────┘
```

### 6. Генерация PDF — формат «Приложение Г»

PDF повторяет табличный формат из РЭ прибора.
Для ТВ7 — формат «Приложения Г» (ред. 2.06):

```
┌──────────────────────────────────────────────────────┐
│         НАСТРОЕЧНАЯ БАЗА ДАННЫХ                      │
│    Тепловычислитель ТВ7 (Термотроник)                │
│    Зав. № ________                                   │
│                                                      │
│    Объект: МКД, ул. Текстильная, д.33/1              │
│    Заявитель: ООО «С-Холдинг»                        │
│    ТУ № 230-07.2/2006 от 28.07.2025                  │
├──────────────────────────────────────────────────────┤
│ Обозн. │ Параметр                │  БД1    │  БД2   │
├────────┼────────────────────────-─┼─────────┼────────┤
│        │ СИСТЕМНЫЕ ПАРАМЕТРЫ     │         │        │
│ ЕИ     │ Единицы измерений       │  0      │  0     │
│ ПИ     │ Период измерений, с     │  600    │  600   │
│ ТВ     │ Кол-во тепловых вводов  │  0      │  0     │
│ tх     │ Догов.t ХВС, °C         │  5.0    │  15.0  │
│ ХТ     │ Характеристика ТС       │  100П   │  100П  │
│        │                         │         │        │
│        │ ОБЩИЕ ПАРАМЕТРЫ ТВ1     │         │        │
│ СИ     │ Схема измерений         │  1      │  1     │
│ ФТ     │ Формула расчёта тепла   │  0      │  0     │
│ ...    │ ...                     │  ...    │  ...   │
│        │                         │         │        │
│        │ ТР1 — ПОДАЮЩИЙ          │         │        │
│ Ку     │ Вес импульса, л/имп     │  10     │  10    │
│ Gдог   │ Договорной расход, м³/ч │  7.14   │  7.14  │
│ Рдог   │ Договорное давление     │  6.6    │  6.6   │
│ tдог   │ Договорная t, °C        │  117.2  │  117.2 │
│ ...    │ ...                     │  ...    │  ...   │
├──────────────────────────────────────────────────────┤
│ Контрольная сумма БД1: ________                      │
│ Контрольная сумма БД2: ________                      │
│                                                      │
│ Составил: _________________ / _________              │
│ Дата: ______________                                 │
└──────────────────────────────────────────────────────┘
```

Для СПТ-941.20 формат другой — параметры нумеруются (000, 001, ...).
Для ЭСКО-Терра — свой формат с группировкой по магистралям.

---

## Механизм запроса у клиента

### Сценарий

1. Инженер видит 🟡-параметры (tх, СЕ)
2. Жмёт «Запросить у клиента» → выбирает какие параметры запросить
3. Бэкенд отправляет email клиенту с конкретными вопросами:

> Для завершения проектирования УУТЭ нам необходимы:
> - **Договорная температура холодной воды** (обычно 5°C зимой, 15°C летом — уточните в договоре с РСО)
> - **Сезонность учёта** (круглогодичный или только отопительный сезон)

4. Клиент на upload-странице видит мини-форму с этими вопросами
5. Ответ клиента сохраняется → автоматически подтягивается в конфигурацию
6. Инженер получает уведомление

### Затрагиваемые файлы

- `upload.html` — новый блок `#calcParamsRequestCard`
- `email_service.py` — новый тип `CALC_PARAMS_REQUEST`
- `landing.py` — эндпоинт `POST /landing/orders/{id}/calc-params`

---

## Порядок реализации

```
Задача 1: JSON-шаблоны (tv7, spt941, esko_terra)     ~4-6 часов
Задача 2: Модель + миграция CalculatorConfig           ~1 час
Задача 3: Сервис автозаполнения                        ~3-4 часа
Задача 4: API-эндпоинты (CRUD + PDF)                   ~2-3 часа
Задача 5: UI в admin.html (таблица)                    ~4-5 часов
Задача 6: Генератор PDF (по формату каждого прибора)   ~3-4 часа
Задача 7: Запрос у клиента (email + upload)            ~2-3 часа
Задача 8: Docs + changelog                             ~30 мин
────────────────────────────────────────────────────────
Итого: ~3-4 дня
```

**Критический путь:** 1 → 2 → 3 → 4 → 5 → 6
**Параллельно:** Задача 7 (после задачи 4)

---

## Затрагиваемые файлы

### Новые файлы
- `backend/calculator_templates/tv7.json`
- `backend/calculator_templates/spt941.json`
- `backend/calculator_templates/esko_terra.json`
- `backend/app/services/calculator_config_service.py`
- `backend/app/api/calculator_config.py`
- `backend/templates/emails/calc_params_request.html`

### Изменяемые файлы
- `backend/app/models/models.py` — модель CalculatorConfig
- `backend/static/admin.html` — UI таблицы
- `backend/static/upload.html` — мини-форма для ответа клиента
- `backend/app/api/admin.py` — подключение роутера
- `backend/app/api/landing.py` — эндпоинт ответа клиента

### Бэкенд не трогаем
- `tu_parser.py` — уже парсит нужные данные
- `tu_schema.py` — схема данных уже содержит все нужные поля
