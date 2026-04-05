"""Celery-задачи — оркестратор стейт-машины заявок.

Каждая задача:
1. Загружает заявку из БД
2. Проверяет допустимость перехода
3. Выполняет работу
4. Обновляет статус
5. Ставит в очередь следующую задачу

Запуск воркера:
    celery -A app.core.celery_app worker -l info -Q default
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.param_labels import compute_client_document_missing
from app.models.models import (
    ALLOWED_TRANSITIONS,
    Order,
    OrderStatus,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Утилиты для синхронного доступа к БД из Celery
# ═══════════════════════════════════════════════════════════════════════════════
# Celery-воркеры — синхронные. Используем отдельный sync-движок.
# Ленивая инициализация: движок создаётся при первом вызове,
# а не при импорте модуля (FastAPI не нуждается в psycopg2).

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_sync_engine = None
_SyncSessionFactory = None


def _get_sync_session() -> Session:
    global _sync_engine, _SyncSessionFactory
    if _SyncSessionFactory is None:
        _sync_url = settings.database_url.replace("+asyncpg", "")
        _sync_engine = create_engine(_sync_url)
        _SyncSessionFactory = sessionmaker(_sync_engine)
    return _SyncSessionFactory()


class _SyncSessionContextManager:
    """Drop-in replacement for `with SyncSession() as session:`."""
    def __enter__(self) -> Session:
        self._session = _get_sync_session()
        return self._session
    def __exit__(self, *exc):
        self._session.close()


SyncSession = _SyncSessionContextManager


def _get_order(session: Session, order_id: uuid.UUID) -> Order | None:
    stmt = (
        select(Order)
        .options(selectinload(Order.files), selectinload(Order.emails))
        .where(Order.id == order_id)
    )
    return session.execute(stmt).scalar_one_or_none()


def _transition(session: Session, order: Order, new_status: OrderStatus) -> None:
    if not order.can_transition_to(new_status):
        raise ValueError(
            f"Недопустимый переход: {order.status.value} → {new_status.value}"
        )
    order.status = new_status
    session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Задачи по шагам пайплайна
# ═══════════════════════════════════════════════════════════════════════════════


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def start_tu_parsing(self, order_id: str):
    """NEW → TU_PARSING → TU_PARSED: Парсинг технических условий.

    Находит PDF с ТУ в файлах заявки, запускает парсер (модуль 1):
    - Текстовый PDF → pymupdf → LLM API
    - Скан PDF → pymupdf render → LLM Vision API
    Сохраняет извлечённые параметры в order.parsed_params.
    """
    from app.services.tu_parser import parse_tu_document, determine_missing_params

    oid = uuid.UUID(order_id)
    logger.info("start_tu_parsing: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            logger.error("Заявка %s не найдена", oid)
            return

        _transition(session, order, OrderStatus.TU_PARSING)

        # Ищем файл ТУ
        tu_files = [f for f in order.files if f.category.value == "tu"]
        if not tu_files:
            order.status = OrderStatus.ERROR
            session.commit()
            logger.error("Нет файла ТУ для order=%s", oid)
            return

        pdf_path = settings.upload_dir / tu_files[0].storage_path

        try:
            # Парсинг
            parsed = parse_tu_document(pdf_path)

            # Сохраняем в БД
            order.parsed_params = parsed.model_dump(
                exclude={"raw_text"},  # raw_text большой, не храним в JSONB
                mode="json",
            )
            order.missing_params = determine_missing_params(parsed)

            _transition(session, order, OrderStatus.TU_PARSED)
            logger.info(
                "Парсинг завершён: order=%s, confidence=%.2f, missing=%s",
                oid, parsed.parse_confidence, order.missing_params,
            )

        except Exception as e:
            logger.error("Ошибка парсинга ТУ для order=%s: %s", oid, e, exc_info=True)
            order.status = OrderStatus.ERROR
            session.commit()
            try:
                self.retry(exc=e)
            except self.MaxRetriesExceededError:
                logger.error("Исчерпаны попытки парсинга для order=%s", oid)
            return

    # Следующий шаг
    check_data_completeness.delay(order_id)


@celery_app.task(bind=True)
def check_data_completeness(self, order_id: str):
    """TU_PARSED / CLIENT_INFO_RECEIVED → DATA_COMPLETE или WAITING_CLIENT_INFO.

    Если missing_params пуст — данные полные, двигаем дальше.
    Если нет — отправляем запрос клиенту.
    """
    oid = uuid.UUID(order_id)
    logger.info("check_data_completeness: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return

        missing = order.missing_params or []

        if len(missing) == 0:
            _transition(session, order, OrderStatus.DATA_COMPLETE)
            logger.info("Все данные собраны для order=%s", oid)
            fill_excel.delay(order_id)
        else:
            _transition(session, order, OrderStatus.WAITING_CLIENT_INFO)
            logger.info(
                "Не хватает данных для order=%s: %s", oid, missing
            )
            send_info_request_email.delay(order_id)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def send_info_request_email(self, order_id: str):
    """Отправка письма клиенту с запросом недостающей информации.

    Рендерит шаблон info_request.html с перечнем недостающих документов,
    прикладывает образцы и отправляет через SMTP.
    """
    from app.services.email_service import send_info_request

    oid = uuid.UUID(order_id)
    logger.info("send_info_request_email: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return

        success = send_info_request(session, order)

        if success:
            order.retry_count += 1
            session.commit()
            logger.info(
                "Письмо с запросом отправлено на %s (попытка %d)",
                order.client_email, order.retry_count,
            )
        else:
            logger.error(
                "Не удалось отправить письмо на %s", order.client_email
            )
            try:
                self.retry()
            except self.MaxRetriesExceededError:
                logger.error(
                    "Исчерпаны попытки отправки email для order=%s", oid
                )


@celery_app.task(bind=True)
def process_client_response(self, order_id: str):
    """CLIENT_INFO_RECEIVED: Обработка ответа клиента.

    Вызывается после того, как клиент загрузил файлы
    через страницу upload-page.
    """
    oid = uuid.UUID(order_id)
    logger.info("process_client_response: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return

        uploaded_categories = {f.category.value for f in order.files}
        order.missing_params = compute_client_document_missing(uploaded_categories)
        session.commit()

    # Повторная проверка полноты
    check_data_completeness.delay(order_id)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def fill_excel(self, order_id: str):
    """DATA_COMPLETE → GENERATING_PROJECT: Заполнение Excel-шаблона.

    Заглушка — модуль 3 будет реализован позже.
    """
    oid = uuid.UUID(order_id)
    logger.info("fill_excel: order=%s (ЗАГЛУШКА)", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return

        # TODO: модуль 3
        # - Загрузить Excel-шаблон
        # - Заполнить ячейки из order.parsed_params
        # - Пересчитать формулы (LibreOffice headless)
        # - Сохранить файл, создать запись OrderFile

        _transition(session, order, OrderStatus.GENERATING_PROJECT)

    generate_project.delay(order_id)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def generate_project(self, order_id: str):
    """GENERATING_PROJECT → REVIEW: Генерация проекта в T-FLEX.

    Заглушка — модуль 4 будет реализован позже.
    """
    oid = uuid.UUID(order_id)
    logger.info("generate_project: order=%s (ЗАГЛУШКА)", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return

        # TODO: модуль 4
        # - Передать Excel в T-FLEX через COM API
        # - Дождаться перестроения модели
        # - Экспорт PDF
        # - Сохранить файл, создать запись OrderFile

        _transition(session, order, OrderStatus.REVIEW)

    logger.info("Проект готов к проверке: order=%s", oid)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def send_completed_project(self, order_id: str):
    """REVIEW → COMPLETED: Отправка готового проекта клиенту.

    Находит сгенерированный PDF проекта в файлах заявки,
    отправляет клиенту письмом с вложением.
    """
    from app.services.email_service import send_project

    oid = uuid.UUID(order_id)
    logger.info("send_completed_project: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return

        # Собираем PDF-файлы проекта для вложения
        project_files = [
            f for f in order.files
            if f.category.value == "generated_project"
        ]
        attachment_paths = [
            str(settings.upload_dir / f.storage_path)
            for f in project_files
            if (settings.upload_dir / f.storage_path).exists()
        ]

        success = send_project(
            session, order,
            attachment_paths=attachment_paths,
        )

        if success:
            _transition(session, order, OrderStatus.COMPLETED)
            logger.info("Проект отправлен клиенту: order=%s", oid)
        else:
            logger.error("Не удалось отправить проект для order=%s", oid)
            try:
                self.retry()
            except self.MaxRetriesExceededError:
                logger.error(
                    "Исчерпаны попытки отправки проекта для order=%s", oid
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Периодические задачи
# ═══════════════════════════════════════════════════════════════════════════════


@celery_app.task
def send_reminders():
    """Периодическая задача: напоминания клиентам, не приславшим документы.

    Запускается по расписанию (Celery Beat).
    Ищет заявки в статусе WAITING_CLIENT_INFO, где последнее письмо
    было отправлено более 3 дней назад, и retry_count < max_retry_count.
    """
    from datetime import datetime, timedelta, timezone
    from app.services.email_service import send_reminder

    logger.info("send_reminders: проверка заявок, ожидающих ответа клиента")

    with SyncSession() as session:
        stmt = (
            select(Order)
            .where(Order.status == OrderStatus.WAITING_CLIENT_INFO)
            .where(Order.retry_count < settings.max_retry_count)
        )
        orders = list(session.execute(stmt).scalars().all())

        cutoff = datetime.now(timezone.utc) - timedelta(days=3)
        sent_count = 0

        for order in orders:
            # Проверяем дату последнего письма
            last_email = max(
                (e.created_at for e in order.emails if e.email_type.value == "info_request"),
                default=None,
            )

            if last_email is not None and last_email.replace(tzinfo=timezone.utc) > cutoff:
                continue  # Ещё не прошло 3 дня

            success = send_reminder(session, order)
            if success:
                order.retry_count += 1
                session.commit()
                sent_count += 1
                logger.info(
                    "Напоминание отправлено: order=%s, попытка %d",
                    order.id, order.retry_count,
                )

        logger.info("send_reminders: отправлено %d напоминаний", sent_count)
