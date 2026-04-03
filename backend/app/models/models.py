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

    new                  → клиент загрузил ТУ, заявка создана
    tu_parsing           → ТУ отправлены на парсинг (модуль 1)
    tu_parsed            → параметры извлечены, проверяется полнота
    waiting_client_info  → клиенту отправлен запрос на доп. информацию
    client_info_received → клиент прислал ответ, идёт анализ
    data_complete        → все данные собраны
    generating_project   → Excel заполнен, T-FLEX генерирует проект
    review               → проект готов, ждёт проверки инженером
    completed            → проект отправлен клиенту
    error                → ошибка на любом этапе
    """

    NEW = "new"
    TU_PARSING = "tu_parsing"
    TU_PARSED = "tu_parsed"
    WAITING_CLIENT_INFO = "waiting_client_info"
    CLIENT_INFO_RECEIVED = "client_info_received"
    DATA_COMPLETE = "data_complete"
    GENERATING_PROJECT = "generating_project"
    REVIEW = "review"
    COMPLETED = "completed"
    ERROR = "error"


# Разрешённые переходы между статусами
ALLOWED_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.NEW: [OrderStatus.TU_PARSING, OrderStatus.ERROR],
    OrderStatus.TU_PARSING: [OrderStatus.TU_PARSED, OrderStatus.ERROR],
    OrderStatus.TU_PARSED: [
        OrderStatus.WAITING_CLIENT_INFO,  # если данных не хватает
        OrderStatus.DATA_COMPLETE,        # если всё есть из ТУ
        OrderStatus.ERROR,
    ],
    OrderStatus.WAITING_CLIENT_INFO: [
        OrderStatus.CLIENT_INFO_RECEIVED,
        OrderStatus.ERROR,
    ],
    OrderStatus.CLIENT_INFO_RECEIVED: [
        OrderStatus.DATA_COMPLETE,        # всё получено
        OrderStatus.WAITING_CLIENT_INFO,  # нужно ещё
        OrderStatus.ERROR,
    ],
    OrderStatus.DATA_COMPLETE: [OrderStatus.GENERATING_PROJECT, OrderStatus.ERROR],
    OrderStatus.GENERATING_PROJECT: [OrderStatus.REVIEW, OrderStatus.ERROR],
    OrderStatus.REVIEW: [OrderStatus.COMPLETED, OrderStatus.GENERATING_PROJECT, OrderStatus.ERROR],
    OrderStatus.COMPLETED: [],
    OrderStatus.ERROR: [OrderStatus.NEW],  # перезапуск заявки
}


# ─── Тип заявки ──────────────────────────────────────────────────────────────

class OrderType(str, enum.Enum):
    EXPRESS = "express"  # Экспресс-проект (по ТУ)
    CUSTOM = "custom"    # Индивидуальный проект (опросный лист)


# ─── Типы файлов ─────────────────────────────────────────────────────────────

class FileCategory(str, enum.Enum):
    """Категории загружаемых файлов.

    Клиент: ТУ, акт разграничения, план подключения, план ТП, схема ТП.
    Служебные: сгенерированные артефакты и прочее.
    """

    TU = "tu"  # Технические условия (ТУ)
    BALANCE_ACT = "BALANCE_ACT"  # Акт разграничения балансовой принадлежности
    CONNECTION_PLAN = "CONNECTION_PLAN"  # План подключения к тепловой сети
    HEAT_POINT_PLAN = "heat_point_plan"  # План теплового пункта (УУТЭ, ШУ)
    HEAT_SCHEME = "heat_scheme"  # Принципиальная схема теплового пункта с УУТЭ
    GENERATED_EXCEL = "generated_excel"
    GENERATED_PROJECT = "generated_project"
    OTHER = "other"


# ─── Типы email ──────────────────────────────────────────────────────────────

class EmailType(str, enum.Enum):
    INFO_REQUEST = "info_request"      # Запрос доп. информации
    REMINDER = "reminder"              # Напоминание
    PROJECT_DELIVERY = "project_delivery"  # Отправка готового проекта
    ERROR_NOTIFICATION = "error_notification"  # Уведомление об ошибке
    SAMPLE_DELIVERY = "sample_delivery"        # Отправка образца проекта
    NEW_ORDER_NOTIFICATION = "new_order_notification"  # Уведомление инженеру о новой заявке
    PARTNERSHIP_REQUEST = "partnership_request"  # Запрос на партнёрство
    SURVEY_REMINDER = "survey_reminder"          # Напоминание заполнить опросный лист


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

    # Извлечённые параметры из ТУ (JSON)
    # Пример: {"heat_load_gvs": 0.15, "heat_load_ot": 0.45, "t_supply": 150, ...}
    parsed_params = Column(JSONB, nullable=True, default=dict)

    # Список параметров, которых не хватает (JSON-массив строк)
    # Пример: ["BALANCE_ACT", "heat_scheme"] — коды как в param_labels / FileCategory
    missing_params = Column(JSONB, nullable=True, default=list)

    # Тип заявки
    order_type = Column(
        Enum(OrderType, name="order_type"),
        nullable=False,
        default=OrderType.EXPRESS,
    )

    # Данные опросного листа (только для CUSTOM)
    survey_data = Column(JSONB, nullable=True, default=None)

    # Счётчик повторных запросов клиенту
    retry_count = Column(Integer, nullable=False, default=0)

    # Комментарий инженера (для этапа review)
    reviewer_comment = Column(Text, nullable=True)

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

    # Категория файла
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
