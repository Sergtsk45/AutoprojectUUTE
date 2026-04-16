import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# ─── Статусы заявки (стейт-машина) ───────────────────────────────────────────

class OrderStatus(str, enum.Enum):
    """Конечный автомат заявки.

    new                    → клиент загрузил ТУ, заявка создана
    tu_parsing             → ТУ отправлены на парсинг (модуль 1)
    tu_parsed              → параметры извлечены, проверяется полнота
    waiting_client_info    → клиенту отправлен запрос на доп. информацию
    client_info_received   → клиент прислал ответ, идёт анализ
    data_complete          → все данные собраны
    generating_project     → Excel заполнен, T-FLEX генерирует проект
    review                 → проект готов, ждёт проверки инженером
    awaiting_contract      → инженер одобрил, ждём реквизиты от клиента
    contract_sent          → договор и счёт на 50% отправлены, ждём аванс
    advance_paid           → аванс получен, проект отправлен клиенту
    awaiting_final_payment → ждём скан РСО, замечания или оплату остатка 50%
    rso_remarks_received   → получены замечания РСО, проект возвращён инженеру
    completed              → проект отправлен клиенту
    error                  → ошибка на любом этапе
    """

    NEW = "new"
    TU_PARSING = "tu_parsing"
    TU_PARSED = "tu_parsed"
    WAITING_CLIENT_INFO = "waiting_client_info"
    CLIENT_INFO_RECEIVED = "client_info_received"
    DATA_COMPLETE = "data_complete"
    GENERATING_PROJECT = "generating_project"
    REVIEW = "review"
    AWAITING_CONTRACT = "awaiting_contract"
    CONTRACT_SENT = "contract_sent"
    ADVANCE_PAID = "advance_paid"
    AWAITING_FINAL_PAYMENT = "awaiting_final_payment"
    RSO_REMARKS_RECEIVED = "rso_remarks_received"
    COMPLETED = "completed"
    ERROR = "error"


# Разрешённые переходы между статусами
ALLOWED_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.NEW: [OrderStatus.TU_PARSING, OrderStatus.ERROR],
    OrderStatus.TU_PARSING: [OrderStatus.TU_PARSED, OrderStatus.ERROR],
    OrderStatus.TU_PARSED: [
        OrderStatus.WAITING_CLIENT_INFO,  # если данных не хватает
        OrderStatus.DATA_COMPLETE,        # если всё есть из ТУ
        OrderStatus.COMPLETED,            # инженер одобрил вручную
        OrderStatus.ERROR,
    ],
    OrderStatus.WAITING_CLIENT_INFO: [
        OrderStatus.CLIENT_INFO_RECEIVED,
        OrderStatus.COMPLETED,            # инженер одобрил вручную
        OrderStatus.ERROR,
    ],
    OrderStatus.CLIENT_INFO_RECEIVED: [
        OrderStatus.CONTRACT_SENT,       # новый основной путь: договор отправлен
        OrderStatus.DATA_COMPLETE,        # всё получено
        OrderStatus.WAITING_CLIENT_INFO,  # нужно ещё
        OrderStatus.COMPLETED,            # инженер одобрил вручную
        OrderStatus.ERROR,
    ],
    OrderStatus.DATA_COMPLETE: [OrderStatus.GENERATING_PROJECT, OrderStatus.COMPLETED, OrderStatus.ERROR],
    OrderStatus.GENERATING_PROJECT: [OrderStatus.REVIEW, OrderStatus.COMPLETED, OrderStatus.ERROR],
    OrderStatus.REVIEW: [
        OrderStatus.AWAITING_CONTRACT,     # основной путь: запуск оплаты
        OrderStatus.COMPLETED,             # ручной override инженером
        OrderStatus.GENERATING_PROJECT,    # возврат на перегенерацию
        OrderStatus.ERROR,
    ],
    OrderStatus.AWAITING_CONTRACT: [
        OrderStatus.CONTRACT_SENT,         # реквизиты получены, договор отправлен
        OrderStatus.COMPLETED,             # override
        OrderStatus.ERROR,
    ],
    OrderStatus.CONTRACT_SENT: [
        OrderStatus.ADVANCE_PAID,          # аванс получен
        OrderStatus.AWAITING_CONTRACT,     # клиент обновил реквизиты — пересоздать договор
        OrderStatus.COMPLETED,             # override
        OrderStatus.ERROR,
    ],
    OrderStatus.ADVANCE_PAID: [
        OrderStatus.AWAITING_FINAL_PAYMENT,  # проект отправлен, ждём остаток
        OrderStatus.COMPLETED,               # override (инженер решил закрыть)
        OrderStatus.ERROR,
    ],
    OrderStatus.AWAITING_FINAL_PAYMENT: [
        OrderStatus.RSO_REMARKS_RECEIVED,   # клиент загрузил замечания РСО
        OrderStatus.COMPLETED,             # остаток получен или скан загружен
        OrderStatus.ERROR,
    ],
    OrderStatus.RSO_REMARKS_RECEIVED: [
        OrderStatus.AWAITING_FINAL_PAYMENT,  # исправленный проект повторно отправлен клиенту
        OrderStatus.COMPLETED,               # ручной override
        OrderStatus.ERROR,
    ],
    OrderStatus.COMPLETED: [],
    OrderStatus.ERROR: [OrderStatus.NEW],  # перезапуск заявки
}


# ─── Метод оплаты ────────────────────────────────────────────────────────────

class PaymentMethod(str, enum.Enum):
    BANK_TRANSFER = "bank_transfer"  # Безналичная оплата (юрлица, ИП)
    ONLINE_CARD = "online_card"      # Онлайн картой (YooKassa)


# ─── Тип заявки ──────────────────────────────────────────────────────────────

class OrderType(str, enum.Enum):
    EXPRESS = "express"  # Экспресс-проект (по ТУ)
    CUSTOM = "custom"    # Индивидуальный проект (опросный лист)


# ─── Типы файлов ─────────────────────────────────────────────────────────────

class FileCategory(str, enum.Enum):
    """Категории загружаемых файлов.

    В PostgreSQL тип file_category — метки как имена членов (TU, HEAT_SCHEME, …).
    Значения .value — для API, query-параметров и сегментов пути в хранилище.
    """

    TU = "tu"  # Технические условия (ТУ)
    BALANCE_ACT = "BALANCE_ACT"  # Акт разграничения балансовой принадлежности
    CONNECTION_PLAN = "CONNECTION_PLAN"  # План подключения к тепловой сети
    HEAT_POINT_PLAN = "heat_point_plan"  # План теплового пункта (УУТЭ, ШУ)
    HEAT_SCHEME = "heat_scheme"  # Принципиальная схема теплового пункта с УУТЭ
    GENERATED_EXCEL = "generated_excel"
    GENERATED_PROJECT = "generated_project"
    OTHER = "other"
    COMPANY_CARD = "company_card"      # Карточка предприятия (загружает клиент)
    SIGNED_CONTRACT = "signed_contract"  # Скан подписанного договора от клиента
    CONTRACT = "contract"              # Сгенерированный договор (DOCX)
    INVOICE = "invoice"                # Счёт на оплату (DOCX)
    FINAL_INVOICE = "final_invoice"    # Счёт на остаток по договору (DOCX)
    RSO_SCAN = "rso_scan"              # Скан письма с входящим номером РСО
    RSO_REMARKS = "rso_remarks"        # Замечания РСО по согласованию проекта


# ─── Типы email ──────────────────────────────────────────────────────────────

class EmailType(str, enum.Enum):
    INFO_REQUEST = "info_request"      # Запрос доп. информации
    REMINDER = "reminder"              # Напоминание
    PROJECT_DELIVERY = "project_delivery"  # Отправка готового проекта
    ERROR_NOTIFICATION = "error_notification"  # Уведомление об ошибке
    SAMPLE_DELIVERY = "sample_delivery"        # Отправка образца проекта
    NEW_ORDER_NOTIFICATION = "new_order_notification"  # Уведомление инженеру о новой заявке
    CLIENT_DOCUMENTS_RECEIVED = "client_documents_received"  # Клиент нажал «Готово» на загрузке
    PARTNERSHIP_REQUEST = "partnership_request"  # Запрос на партнёрство
    SURVEY_REMINDER = "survey_reminder"          # Напоминание заполнить опросный лист
    PROJECT_READY_PAYMENT = "project_ready_payment"          # Проект готов, ожидается оплата
    CONTRACT_DELIVERY = "contract_delivery"                  # Договор и счёт отправлены клиенту
    SIGNED_CONTRACT_NOTIFICATION = "signed_contract_notification"  # Уведомление инженеру о подписанном договоре
    ADVANCE_RECEIVED = "advance_received"                    # Аванс получен, проект отправлен
    FINAL_PAYMENT_REQUEST = "final_payment_request"          # Запрос финального платежа / скана РСО
    FINAL_PAYMENT_RECEIVED = "final_payment_received"        # Финальный платёж получен


def _enum_db_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Только для order_type: в БД метки lowercase (express, custom) = member.value.

    Остальные enum в этом файле: в PostgreSQL метки совпадают с именами членов Python
    (order_status, file_category, email_type) — SQLAlchemy персистит имена без callable.
    """
    return [m.value for m in enum_cls]


# ═══════════════════════════════════════════════════════════════════════════════
# МОДЕЛИ
# ═══════════════════════════════════════════════════════════════════════════════


class Order(Base):
    """Заявка на проектирование УУТЭ."""

    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(
        Enum(OrderStatus, name="order_status"),
        nullable=False,
        default=OrderStatus.NEW,
        index=True,
    )

    # Контактные данные клиента
    client_name = Column(String(255), nullable=False)
    client_email = Column(String(255), nullable=False, index=True)
    client_phone = Column(String(50), nullable=True)
    client_organization = Column(String(255), nullable=True)

    # Адрес объекта
    object_address = Column(Text, nullable=True)

    # Город объекта
    object_city = Column(Text, nullable=True)

    # Извлечённые параметры из ТУ (JSON)
    # Пример: {"heat_load_gvs": 0.15, "heat_load_ot": 0.45, "t_supply": 150, ...}
    parsed_params = Column(JSONB, nullable=True, default=dict)

    # Список параметров, которых не хватает (JSON-массив строк)
    # Пример: ["BALANCE_ACT", "heat_scheme"] — коды как в param_labels / FileCategory
    missing_params = Column(JSONB, nullable=True, default=list)

    # Тип заявки
    order_type = Column(
        Enum(OrderType, name="order_type", values_callable=_enum_db_values),
        nullable=False,
        default=OrderType.EXPRESS,
        server_default="express",
    )

    # Данные опросного листа (только для CUSTOM)
    survey_data = Column(JSONB, nullable=True)

    # Счётчик повторных запросов клиенту
    retry_count = Column(Integer, nullable=False, default=0)

    # Момент (UTC) перехода в waiting_client_info — не раньше чем через 24 ч шлём первый info_request
    waiting_client_info_at = Column(DateTime(timezone=True), nullable=True)

    # Комментарий инженера (для этапа review)
    reviewer_comment = Column(Text, nullable=True)

    # ── Оплата ────────────────────────────────────────────
    payment_method = Column(
        Enum(PaymentMethod, name="payment_method",
             values_callable=_enum_db_values),
        nullable=True,
    )
    payment_amount = Column(Integer, nullable=True)
    advance_amount = Column(Integer, nullable=True)
    advance_paid_at = Column(DateTime(timezone=True), nullable=True)
    final_paid_at = Column(DateTime(timezone=True), nullable=True)
    rso_scan_received_at = Column(DateTime(timezone=True), nullable=True)
    company_requisites = Column(JSONB, nullable=True)
    contract_number = Column(String(100), nullable=True)

    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Связи
    files = relationship("OrderFile", back_populates="order", cascade="all, delete-orphan")
    emails = relationship("EmailLog", back_populates="order", cascade="all, delete-orphan")
    calculator_config = relationship("CalculatorConfig", back_populates="order", uselist=False)

    def can_transition_to(self, new_status: OrderStatus) -> bool:
        """Проверяет, допустим ли переход в новый статус."""
        return new_status in ALLOWED_TRANSITIONS.get(self.status, [])


class OrderFile(Base):
    """Файл, привязанный к заявке."""

    __tablename__ = "order_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Категория файла (в БД — UPPER_CASE имена членов: TU, BALANCE_ACT, …)
    category = Column(Enum(FileCategory, name="file_category"), nullable=False)

    # Исходное имя файла от клиента
    original_filename = Column(String(500), nullable=False)

    # Путь к файлу в хранилище (относительно UPLOAD_DIR)
    storage_path = Column(String(1000), nullable=False, unique=True)

    # MIME-тип
    content_type = Column(String(100), nullable=True)

    # Размер в байтах
    file_size = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связи
    order = relationship("Order", back_populates="files")


class EmailLog(Base):
    """Лог отправленных писем."""

    __tablename__ = "email_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email_type = Column(Enum(EmailType, name="email_type"), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body_text = Column(Text, nullable=True)

    # Статус отправки
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связи
    order = relationship("Order", back_populates="emails")


class CalculatorConfig(Base):
    """Настроечная база данных вычислителя теплоэнергии."""

    __tablename__ = "calculator_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    calculator_type = Column(String(50), nullable=False)   # "tv7" | "spt941" | "esko_terra"
    config_data = Column(JSONB, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default="draft")  # draft | complete
    total_params = Column(Integer, nullable=False, default=0)
    filled_params = Column(Integer, nullable=False, default=0)
    missing_required = Column(JSONB, nullable=False, default=list)
    client_requested_params = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    exported_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", back_populates="calculator_config")
