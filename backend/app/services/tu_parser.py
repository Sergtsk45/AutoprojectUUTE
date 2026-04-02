"""Модуль 1 — Парсинг технических условий.

Пайплайн:
1. Извлечение данных из PDF:
   - Текстовый PDF → pymupdf → текст → LLM API (текстовый промпт)
   - Скан PDF → pymupdf → рендер страниц в PNG → LLM Vision API
2. Парсинг JSON-ответа в TUParsedData
3. Валидация: диапазоны, перекрёстные проверки
4. Возврат структурированных данных + список проблем

Зависимости:
    pip install pymupdf openai
"""

import base64
import json
import logging
import re
from pathlib import Path

import fitz  # pymupdf

from app.core.config import settings
from app.services.param_labels import CLIENT_DOCUMENT_PARAM_CODES
from app.services.tu_schema import TUParsedData, get_missing_fields

logger = logging.getLogger(__name__)

# Порог: если из PDF извлечено меньше этого кол-ва символов — считаем сканом
_MIN_TEXT_LENGTH = 200


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Работа с PDF
# ═══════════════════════════════════════════════════════════════════════════════


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Пытается извлечь текст из PDF через pymupdf.

    Returns:
        Текст или пустая строка, если PDF — скан.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF не найден: {path}")

    doc = fitz.open(str(path))
    pages_text = []

    for page_num, page in enumerate(doc, 1):
        text = page.get_text("text")
        if text.strip():
            pages_text.append(f"--- Страница {page_num} ---\n{text}")

    doc.close()
    return "\n\n".join(pages_text)


def render_pdf_pages_to_base64(pdf_path: str | Path, dpi: int = 200) -> list[str]:
    """Рендерит страницы PDF в PNG и возвращает base64-строки.

    Используется для сканов — отправляем изображения в LLM Vision.
    DPI=200 — баланс между качеством и размером (~300-500 КБ на страницу).
    """
    path = Path(pdf_path)
    doc = fitz.open(str(path))
    images = []

    zoom = dpi / 72  # 72 — стандартный DPI в PDF
    mat = fitz.Matrix(zoom, zoom)

    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        b64 = base64.standard_b64encode(png_bytes).decode("ascii")
        images.append(b64)

    doc.close()
    logger.info("Рендер PDF: %d страниц, DPI=%d", len(images), dpi)
    return images


def is_scanned_pdf(pdf_path: str | Path) -> bool:
    """Определяет, является ли PDF сканом (без текстового слоя)."""
    text = extract_text_from_pdf(pdf_path)
    return len(text.strip()) < _MIN_TEXT_LENGTH


# ═══════════════════════════════════════════════════════════════════════════════
# 2. LLM-извлечение параметров
# ═══════════════════════════════════════════════════════════════════════════════

EXTRACTION_PROMPT = """Ты — инженер-проектировщик узлов учёта тепловой энергии.

Тебе предоставлен текст технических условий (ТУ) на проектирование УУТЭ,
извлечённый из PDF-документа.

Извлеки ВСЕ параметры из текста и верни СТРОГО в формате JSON
(без markdown-обрамления, без пояснений — только JSON).

Структура JSON:

{
  "rso": {
    "rso_name": "наименование РСО",
    "rso_address": "адрес РСО",
    "rso_phone": "телефон",
    "rso_email": "email",
    "rso_website": "сайт"
  },
  "document": {
    "tu_number": "номер ТУ",
    "tu_date": "дата выдачи ДД.ММ.ГГГГ",
    "tu_valid_from": "действует с ДД.ММ.ГГГГ",
    "tu_valid_to": "действует по ДД.ММ.ГГГГ",
    "tu_response_to": "на заявку №... от ...",
    "signatory_name": "ФИО подписанта",
    "signatory_position": "должность подписанта"
  },
  "applicant": {
    "applicant_name": "наименование заявителя",
    "applicant_address": "почтовый адрес заявителя",
    "contact_person": "контактное лицо (ФИО)"
  },
  "object": {
    "object_type": "тип объекта (МКД / нежилое / промышленное)",
    "object_address": "адрес объекта теплоснабжения",
    "city": "город"
  },
  "heat_loads": {
    "total_load": числовое значение общей нагрузки в Гкал/ч,
    "heating_load": нагрузка на отопление в Гкал/ч или null,
    "ventilation_load": нагрузка на вентиляцию в Гкал/ч или null,
    "hot_water_load": нагрузка на ГВС в Гкал/ч или null
  },
  "pipeline": {
    "pipe_outer_diameter_mm": наружный диаметр в мм (число),
    "pipe_inner_diameter_mm": условный/внутренний диаметр в мм или null
  },
  "coolant": {
    "supply_temp": температура подачи °C (число),
    "return_temp": температура обратки °C (число),
    "temp_schedule": "температурный график, например 117.2/70",
    "heating_season": "отопительный сезон, например 2024/2025",
    "supply_pressure_kgcm2": давление в подающем кг/см² (число, положительное),
    "return_pressure_kgcm2": давление в обратном кг/см² (число, положительное)
  },
  "metering": {
    "meter_location": "место установки узла учёта",
    "heat_calculator_model": "модель тепловычислителя или null",
    "flowmeter_model": "модель расходомеров или null",
    "temp_sensor_model": "модель датчиков температуры или null",
    "pressure_sensor_model": "модель датчиков давления или null",
    "heat_meter_class": класс теплосчётчика (число) или null,
    "data_interface": "интерфейс передачи данных или null",
    "archive_capacity_hours": ёмкость часового архива (суток) или null,
    "archive_capacity_daily": ёмкость суточного архива (месяцев) или null,
    "archive_capacity_monthly": ёмкость месячного архива (лет) или null
  },
  "connection": {
    "connection_type": "зависимая" или "независимая" или "неизвестно",
    "system_type": "закрытая" или "открытая" или "неизвестно",
    "heating_system": "перечень систем: отопление, ГВС, вентиляция"
  },
  "additional": {
    "approval_organization": "организация для согласования проекта",
    "pre_survey_required": true/false,
    "gcs_module": true/false — требуется ли модуль ГСМ,
    "notes": ["доп. требование 1", "доп. требование 2"]
  },
  "parse_confidence": число от 0 до 1 — твоя уверенность в корректности извлечения,
  "warnings": ["предупреждение если что-то неоднозначно"]
}

ПРАВИЛА:
- Если параметр явно указан в тексте — извлеки его.
- Если параметр НЕ указан — поставь null. НЕ выдумывай!
- Давления всегда положительные числа (даже если в тексте "-8,0 кг/см²" — это 8.0).
- Температурный график: если написано "117,2/70" — supply_temp=117.2, return_temp=70.
- Десятичный разделитель в русских документах — запятая. Конвертируй в точку.
- В поле notes собери все значимые требования, не вошедшие в другие поля.
- parse_confidence: 0.9+ если текст ясный и все ключевые параметры найдены.
"""


def extract_params_with_llm(
    text: str | None = None,
    page_images_b64: list[str] | None = None,
) -> dict:
    """Отправляет ТУ в LLM через OpenRouter API, получает JSON с параметрами.

    Два режима:
    - text: для текстовых PDF (дешевле, быстрее)
    - page_images_b64: для сканов (Vision — LLM читает изображения)

    Returns:
        dict — сырой JSON от LLM.
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )

    # Собираем messages в формате OpenAI
    user_content = []

    if page_images_b64:
        # Vision-режим: отправляем изображения страниц
        user_content.append({
            "type": "text",
            "text": (
                "Ниже — изображения страниц PDF-документа "
                "с техническими условиями на проектирование УУТЭ. "
                "Прочитай текст со всех страниц и извлеки параметры "
                "согласно инструкции."
            ),
        })
        for img_b64 in page_images_b64:
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}",
                },
            })
        user_content.append({
            "type": "text",
            "text": "Извлеки ВСЕ параметры из этих страниц. Верни только JSON.",
        })
    elif text:
        # Текстовый режим
        user_content.append({
            "type": "text",
            "text": (
                f"Вот текст технических условий, извлечённый из PDF:\n\n"
                f"```\n{text}\n```\n\n"
                f"Извлеки параметры согласно инструкции."
            ),
        })
    else:
        raise ValueError("Нужен text или page_images_b64")

    messages = [
        {"role": "system", "content": EXTRACTION_PROMPT},
        {"role": "user", "content": user_content},
    ]

    response = client.chat.completions.create(
        model=settings.openrouter_model,
        messages=messages,
        max_tokens=4096,
        temperature=0.1,
        extra_headers={
            "HTTP-Referer": settings.app_base_url,
            "X-Title": "UUTE Project Parser",
        },
    )

    raw_response = response.choices[0].message.content.strip()
    logger.debug("LLM raw response (first 500 chars): %s", raw_response[:500])

    # Убираем возможные markdown-обрамления
    cleaned = raw_response
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("LLM вернул невалидный JSON: %s", e)
        logger.debug("Raw response: %s", raw_response)
        raise RuntimeError(f"LLM вернул невалидный JSON: {e}") from e

    return data


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Валидация и перекрёстные проверки
# ═══════════════════════════════════════════════════════════════════════════════


def validate_parsed_data(data: TUParsedData) -> list[str]:
    """Перекрёстные проверки извлечённых параметров.

    Returns:
        Список предупреждений (пустой = всё ок).
    """
    warnings = []
    hl = data.heat_loads
    cl = data.coolant
    pp = data.pipeline

    # 1. Сумма нагрузок ≈ общая
    if hl.total_load and hl.heating_load and hl.hot_water_load:
        component_sum = (
            (hl.heating_load or 0)
            + (hl.ventilation_load or 0)
            + (hl.hot_water_load or 0)
        )
        diff = abs(hl.total_load - component_sum)
        if diff > 0.01:
            warnings.append(
                f"Сумма нагрузок ({component_sum:.4f}) ≠ общая ({hl.total_load:.4f}), "
                f"разница {diff:.4f} Гкал/ч"
            )

    # 2. Температура подачи > обратки
    if cl.supply_temp and cl.return_temp:
        if cl.supply_temp <= cl.return_temp:
            warnings.append(
                f"Температура подачи ({cl.supply_temp}°C) ≤ обратки ({cl.return_temp}°C)"
            )

    # 3. Давление подачи > обратки (типично)
    if cl.supply_pressure_kgcm2 and cl.return_pressure_kgcm2:
        if cl.supply_pressure_kgcm2 < cl.return_pressure_kgcm2:
            warnings.append(
                f"Давление подачи ({cl.supply_pressure_kgcm2}) < обратки "
                f"({cl.return_pressure_kgcm2}) — проверьте"
            )

    # 4. Диаметр трубы в разумных пределах для нагрузки
    if pp.pipe_outer_diameter_mm and hl.total_load:
        if hl.total_load > 1.0 and pp.pipe_outer_diameter_mm < 50:
            warnings.append(
                f"Подозрительно малый диаметр ({pp.pipe_outer_diameter_mm} мм) "
                f"для нагрузки {hl.total_load} Гкал/ч"
            )

    # 5. Класс теплосчётчика
    if data.metering.heat_meter_class and data.metering.heat_meter_class > 2:
        warnings.append(
            f"Класс теплосчётчика ({data.metering.heat_meter_class}) > 2 — "
            "для коммерческого учёта обычно требуется не ниже 2"
        )

    return warnings


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Основная функция парсинга
# ═══════════════════════════════════════════════════════════════════════════════


def parse_tu_document(pdf_path: str | Path) -> TUParsedData:
    """Полный пайплайн парсинга ТУ.

    Автоматически определяет тип PDF:
    - Текстовый → извлекает текст → LLM API (текстовый промпт)
    - Скан → рендерит страницы → LLM Vision API

    Args:
        pdf_path: Путь к PDF-файлу с техническими условиями.

    Returns:
        TUParsedData — структурированные данные.
    """
    logger.info("Парсинг ТУ: %s", pdf_path)
    raw_text = ""

    # Шаг 1: определяем тип PDF и извлекаем данные
    text = extract_text_from_pdf(pdf_path)

    if len(text.strip()) >= _MIN_TEXT_LENGTH:
        # Текстовый PDF
        logger.info("Текстовый PDF, извлечено %d символов", len(text))
        raw_text = text
        llm_result = extract_params_with_llm(text=text)
    else:
        # Скан — используем Vision
        logger.info("Скан PDF — используем LLM Vision")
        page_images = render_pdf_pages_to_base64(pdf_path, dpi=200)
        raw_text = f"[СКАН: {len(page_images)} страниц, распознано через Vision]"
        llm_result = extract_params_with_llm(page_images_b64=page_images)

    # Шаг 2: Pydantic-валидация
    try:
        parsed = TUParsedData.model_validate(llm_result)
    except Exception as e:
        logger.error("Ошибка валидации данных от LLM: %s", e)
        parsed = TUParsedData(
            warnings=[f"Ошибка валидации LLM-ответа: {e}"],
            parse_confidence=0.1,
        )

    parsed.raw_text = raw_text[:10000]

    # Шаг 3: перекрёстные проверки
    cross_warnings = validate_parsed_data(parsed)
    parsed.warnings.extend(cross_warnings)

    logger.info(
        "Парсинг завершён: confidence=%.2f, warnings=%d, missing_required=%d",
        parsed.parse_confidence,
        len(parsed.warnings),
        len(get_missing_fields(parsed)),
    )

    return parsed


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Определение missing_params для оркестратора
# ═══════════════════════════════════════════════════════════════════════════════


def determine_missing_params(parsed: TUParsedData) -> list[str]:
    """Определяет, какие документы нужно запросить у клиента.

    На основании parsed данных + обязательных полей из схемы
    формирует список кодов для order.missing_params.

    Коды соответствуют param_labels.py и FileCategory для файлов.
    """
    return list(CLIENT_DOCUMENT_PARAM_CODES)
