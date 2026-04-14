"""Парсер карточки предприятия.

Извлекает реквизиты юрлица / ИП из PDF (текстового или скана) и изображений
через LLM (OpenRouter). Аналог tu_parser.py.

Пайплайн:
1. Определение типа файла (PDF текст / PDF скан / JPG / PNG)
2. Извлечение контента (текст или base64-изображения)
3. LLM-вызов через OpenRouter → JSON
4. Pydantic-валидация → CompanyRequisites
5. Пост-валидация: проверка длин реквизитов

Зависимости:
    pip install pymupdf openai pydantic
"""

import base64
import json
import logging
import re
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.tu_parser import (
    extract_text_from_pdf,
    render_pdf_pages_to_base64,
)

logger = logging.getLogger(__name__)

# Порог для определения PDF-скана — как в tu_parser
_MIN_TEXT_LENGTH = 200


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Pydantic-модель реквизитов
# ═══════════════════════════════════════════════════════════════════════════════


class CompanyRequisites(BaseModel):
    """Реквизиты организации, извлечённые из карточки предприятия."""

    full_name: str = Field("", description="Полное наименование с ОПФ (ООО «Теплосеть»)")
    short_name: str | None = Field(None, description="Краткое наименование")
    inn: str = Field("", description="ИНН (10 цифр юрлицо, 12 цифр ИП)")
    kpp: str | None = Field(None, description="КПП (9 цифр, только юрлица)")
    ogrn: str | None = Field(None, description="ОГРН (13 цифр) или ОГРНИП (15 цифр)")
    legal_address: str = Field("", description="Юридический адрес")
    actual_address: str | None = Field(None, description="Фактический адрес (если отличается)")
    bank_name: str = Field("", description="Наименование банка")
    bik: str = Field("", description="БИК (9 цифр)")
    corr_account: str = Field("", description="Корреспондентский счёт (20 цифр)")
    settlement_account: str = Field("", description="Расчётный счёт (20 цифр)")
    director_name: str = Field("", description="ФИО руководителя полностью")
    director_position: str = Field(
        "Генеральный директор",
        description="Должность (Генеральный директор / Директор / ИП)",
    )
    phone: str | None = Field(None, description="Телефон")
    email: str | None = Field(None, description="Email")
    parse_confidence: float = Field(0.0, ge=0, le=1, description="Уверенность парсера")
    warnings: list[str] = Field(default_factory=list, description="Предупреждения парсера")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. LLM-промпт
# ═══════════════════════════════════════════════════════════════════════════════

COMPANY_EXTRACTION_PROMPT = """Ты — опытный бухгалтер. Тебе предоставлен документ
«Карточка предприятия» (или «Реквизиты организации», или «Карточка контрагента»).

Извлеки ВСЕ реквизиты и верни СТРОГО в формате JSON.
Без markdown-обрамления, без пояснений — только JSON.

Формат ответа:
{
  "full_name": "Полное наименование с организационно-правовой формой",
  "short_name": "Краткое наименование или null",
  "inn": "ИНН (только цифры, без пробелов)",
  "kpp": "КПП (только цифры) или null для ИП",
  "ogrn": "ОГРН или ОГРНИП (только цифры) или null",
  "legal_address": "Юридический адрес полностью",
  "actual_address": "Фактический адрес или null если совпадает с юридическим",
  "bank_name": "Полное наименование банка",
  "bik": "БИК банка (9 цифр)",
  "corr_account": "Корреспондентский счёт (20 цифр)",
  "settlement_account": "Расчётный счёт (20 цифр)",
  "director_name": "ФИО руководителя полностью (Иванов Иван Иванович)",
  "director_position": "Должность (Генеральный директор / Директор / Индивидуальный предприниматель)",
  "phone": "Телефон или null",
  "email": "Email или null",
  "parse_confidence": 0.95
}

Правила:
- ИНН, КПП, ОГРН, БИК, расчётный и корр. счёт — ТОЛЬКО цифры, без пробелов и дефисов.
- Если поле не найдено в документе — укажи null (не пустую строку).
- Если документ содержит реквизиты нескольких организаций — извлеки реквизиты ПЕРВОЙ (основной).
- Если это ИП — КПП будет null, в director_position укажи "Индивидуальный предприниматель".
- parse_confidence: 0.0-1.0, оцени насколько уверенно удалось извлечь данные.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 3. LLM-вызов
# ═══════════════════════════════════════════════════════════════════════════════


def _extract_with_llm(
    *,
    text: str | None = None,
    page_images_b64: list[str] | None = None,
    media_type: str = "image/png",
) -> dict:
    """Отправляет данные в LLM и возвращает JSON-словарь.

    Аналог extract_params_with_llm из tu_parser.py.

    Args:
        text: Текст карточки для текстового режима.
        page_images_b64: Список base64-изображений для Vision-режима.
        media_type: MIME-тип изображений.

    Returns:
        dict — сырой JSON от LLM.
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )

    user_content: list[dict] = []

    if page_images_b64:
        user_content.append({
            "type": "text",
            "text": (
                "Ниже — изображения документа «Карточка предприятия». "
                "Прочитай текст и извлеки реквизиты согласно инструкции."
            ),
        })
        for b64 in page_images_b64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{b64}"},
            })
        user_content.append({
            "type": "text",
            "text": "Извлеки реквизиты из этого документа. Верни только JSON.",
        })
    elif text:
        user_content.append({
            "type": "text",
            "text": (
                f"Вот текст карточки предприятия:\n\n"
                f"```\n{text}\n```\n\n"
                f"Извлеки реквизиты согласно инструкции."
            ),
        })
    else:
        raise ValueError("Нужен text или page_images_b64")

    messages = [
        {"role": "system", "content": COMPANY_EXTRACTION_PROMPT},
        {"role": "user", "content": user_content},
    ]

    response = client.chat.completions.create(
        model=settings.openrouter_model,
        messages=messages,
        max_tokens=2048,
        temperature=0.1,
        extra_headers={
            "HTTP-Referer": settings.app_base_url,
            "X-Title": "UUTE Company Card Parser",
        },
    )

    raw = response.choices[0].message.content.strip()
    logger.debug("LLM raw (500): %s", raw[:500])

    # Убираем markdown-обрамление (```json ... ```)
    cleaned = raw
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("LLM вернул невалидный JSON: %s", e)
        logger.debug("Raw response: %s", raw)
        raise RuntimeError(f"LLM вернул невалидный JSON: {e}") from e

    return data


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Пост-валидация реквизитов
# ═══════════════════════════════════════════════════════════════════════════════

# Ожидаемые длины числовых реквизитов
_DIGITS_ONLY = re.compile(r"\D")

_FIELD_LENGTHS: dict[str, tuple[int, ...]] = {
    "inn": (10, 12),         # юрлицо / ИП
    "kpp": (9,),
    "bik": (9,),
    "corr_account": (20,),
    "settlement_account": (20,),
}

_OGRN_LENGTHS = (13, 15)     # ОГРН / ОГРНИП


def _only_digits(value: str) -> str:
    """Оставляет только цифры в строке."""
    return _DIGITS_ONLY.sub("", value)


def _validate_requisites(r: CompanyRequisites) -> list[str]:
    """Проверяет длины числовых реквизитов.

    Нормализует поля (удаляет нецифровые символы) и возвращает
    список предупреждений при несовпадении ожидаемых длин.
    """
    warnings: list[str] = []

    # Нормализация и проверка фиксированных полей
    for field, expected_lengths in _FIELD_LENGTHS.items():
        raw = getattr(r, field) or ""
        normalized = _only_digits(raw)
        setattr(r, field, normalized)

        if not normalized:
            continue
        if len(normalized) not in expected_lengths:
            labels = " или ".join(str(n) for n in expected_lengths)
            warnings.append(
                f"{field.upper()}: ожидалось {labels} цифр, получено {len(normalized)} "
                f"(«{normalized}»)"
            )

    # КПП: нормализация (может быть None у ИП)
    if r.kpp is not None:
        r.kpp = _only_digits(r.kpp) or None

    # ОГРН / ОГРНИП
    if r.ogrn:
        normalized_ogrn = _only_digits(r.ogrn)
        r.ogrn = normalized_ogrn or None
        if normalized_ogrn and len(normalized_ogrn) not in _OGRN_LENGTHS:
            warnings.append(
                f"ОГРН: ожидалось 13 или 15 цифр, получено {len(normalized_ogrn)} "
                f"(«{normalized_ogrn}»)"
            )

    return warnings


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Основная функция парсинга
# ═══════════════════════════════════════════════════════════════════════════════


def parse_company_card(file_path: str | Path) -> CompanyRequisites:
    """Полный пайплайн парсинга карточки предприятия.

    Автоматически определяет тип файла:
    - PDF с текстом → извлекает текст → LLM (текстовый промпт)
    - PDF-скан → рендер страниц → LLM Vision
    - Изображение (JPG/PNG/WEBP) → LLM Vision напрямую

    Args:
        file_path: Путь к файлу карточки предприятия.

    Returns:
        CompanyRequisites — структурированные реквизиты.

    Raises:
        ValueError: Неподдерживаемый формат файла.
        RuntimeError: LLM вернул невалидный JSON.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    logger.info("Парсинг карточки предприятия: %s", path.name)

    if suffix in (".jpg", ".jpeg", ".png", ".webp"):
        # Изображение — сразу Vision
        with open(path, "rb") as f:
            b64 = base64.standard_b64encode(f.read()).decode("ascii")
        media_type = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
        llm_result = _extract_with_llm(page_images_b64=[b64], media_type=media_type)

    elif suffix == ".pdf":
        text = extract_text_from_pdf(path)
        if len(text.strip()) >= _MIN_TEXT_LENGTH:
            logger.info("Текстовый PDF, %d символов", len(text))
            llm_result = _extract_with_llm(text=text)
        else:
            logger.info("Скан PDF — Vision")
            page_images = render_pdf_pages_to_base64(path, dpi=200)
            llm_result = _extract_with_llm(page_images_b64=page_images)

    else:
        raise ValueError(f"Неподдерживаемый формат файла: {suffix}")

    # Pydantic-валидация
    try:
        requisites = CompanyRequisites.model_validate(llm_result)
    except Exception as e:
        logger.error("Ошибка валидации ответа LLM: %s", e)
        requisites = CompanyRequisites(
            warnings=[f"Ошибка валидации: {e}"],
            parse_confidence=0.1,
        )

    # Пост-валидация: проверка и нормализация числовых реквизитов
    extra_warnings = _validate_requisites(requisites)
    requisites.warnings.extend(extra_warnings)

    logger.info(
        "Парсинг карточки завершён: confidence=%.2f, warnings=%d, inn=%s",
        requisites.parse_confidence,
        len(requisites.warnings),
        (requisites.inn[:4] + "...") if requisites.inn else "N/A",
    )

    return requisites
