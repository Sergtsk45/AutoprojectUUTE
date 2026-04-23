"""
@file: app/schemas/jsonb/company.py
@description: Pydantic-модель для `Order.company_requisites` — реквизиты заказчика,
    извлекаемые из «Карточки предприятия». Исторически жила в
    `services/company_parser.py`; теперь здесь, в `services/company_parser.py`
    оставлен обратно-совместимый реэкспорт.
@dependencies: pydantic v2.
@created: 2026-04-21 (перенос из services/company_parser.py)
"""

from pydantic import BaseModel, ConfigDict, Field


class CompanyRequisites(BaseModel):
    """Реквизиты организации, извлечённые из карточки предприятия.

    Хранится в `Order.company_requisites` (JSONB) вместе с метаданными парсинга
    (`parse_confidence`, `warnings`). `extra='ignore'` — чтобы старые записи с
    дополнительными ключами (от предыдущих версий промпта) не ломали чтение.
    """

    model_config = ConfigDict(extra="ignore")

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


class CompanyRequisitesError(BaseModel):
    """Маркер неудачного парсинга «Карточки предприятия».

    Попадает в `Order.company_requisites` (JSONB) когда парсер не смог извлечь
    реквизиты (PDF нечитаем, сканирование низкого качества и т.п.). Фронт
    админки (`admin.html`) и страница оплаты (`payment.html`) распознают этот
    маркер по полю `error` и показывают баннер «Ошибка распознавания».

    Выделен в отдельную схему (фаза B1.c, 2026-04-22), чтобы типизация
    `OrderResponse.company_requisites` была точной: либо валидные
    `CompanyRequisites`, либо этот маркер, либо `None`.
    """

    model_config = ConfigDict(extra="ignore")

    error: str = Field(..., description="Сообщение об ошибке парсинга")
