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
    EmailType,
)

logger = logging.getLogger(__name__)

# Задержка перед первой автоотправкой письма «запрос документов» (info_request), сек.
INFO_REQUEST_AUTO_DELAY_SECONDS = 24 * 60 * 60


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

            # Если город ещё не указан клиентом — взять из ТУ
            if not order.object_city and parsed.object.city:
                order.object_city = parsed.object.city

            _transition(session, order, OrderStatus.TU_PARSED)
            logger.info(
                "Парсинг завершён: order=%s, confidence=%.2f, missing=%s",
                oid, parsed.parse_confidence, order.missing_params,
            )

            # Автоинициализация настроечной БД для express-заявок с Эско-Терра
            from app.models.models import OrderType
            if order.order_type == OrderType.EXPRESS:
                try:
                    from app.services.calculator_config_service import (
                        resolve_calculator_type_for_express,
                        init_config_sync,
                    )
                    calc_type = resolve_calculator_type_for_express(order)
                    if calc_type:
                        init_config_sync(order, session)
                        logger.info(
                            "Авто-инициализация настроечной БД (%s) для order=%s",
                            calc_type, oid,
                        )
                    else:
                        logger.info(
                            "Express order=%s: Эско-Терра не обнаружена в ТУ, "
                            "инициализация настроечной БД пропущена",
                            oid,
                        )
                except Exception as init_err:
                    logger.warning(
                        "Авто-инициализация настроечной БД не удалась для order=%s: %s",
                        oid, init_err,
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
    Если нет — переход в WAITING_CLIENT_INFO; первый info_request уходит не раньше чем через 24 ч:
    отложенная задача Celery (таймер) + резерв — process_due_info_requests в Beat.
    Раньше 24 ч инженер может отправить запрос вручную из админки.
    """
    from datetime import datetime, timezone

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
            order.waiting_client_info_at = datetime.now(timezone.utc)
            _transition(session, order, OrderStatus.WAITING_CLIENT_INFO)
            logger.info(
                "Не хватает данных для order=%s: %s; запланирован info_request через 24 ч",
                oid,
                missing,
            )
            send_info_request_email.apply_async(
                args=[order_id],
                countdown=INFO_REQUEST_AUTO_DELAY_SECONDS,
            )
            logger.info(
                "check_data_completeness: send_info_request_email с задержкой %s с, order=%s",
                INFO_REQUEST_AUTO_DELAY_SECONDS,
                oid,
            )


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def send_info_request_email(self, order_id: str):
    """Отправка письма клиенту с запросом недостающей информации.

    Вызывается:
    - по таймеру: apply_async(..., countdown=INFO_REQUEST_AUTO_DELAY_SECONDS) из check_data_completeness;
    - резервно: process_due_info_requests (Beat), если отложенная задача не отработала.

    Идемпотентна: не шлёт дубликат при ручной отправке инженером ранее.
    """
    from datetime import datetime, timedelta, timezone

    from app.services.email_service import has_successful_email, send_info_request

    oid = uuid.UUID(order_id)
    logger.info("send_info_request_email: order=%s", oid)

    with SyncSession() as session:
        # SELECT FOR UPDATE блокирует строку на уровне БД: если несколько воркеров
        # стартуют одновременно, второй воркер ждёт снятия блокировки первым.
        # После разблокировки has_successful_email уже видит запись в EmailLog
        # от первого воркера и пропускает повторную отправку.
        # Блокировка удерживается до session.commit() в конце функции.
        order = session.execute(
            select(Order)
            .options(selectinload(Order.files), selectinload(Order.emails))
            .where(Order.id == oid)
            .with_for_update()
        ).scalar_one_or_none()

        if order is None:
            return

        if order.status != OrderStatus.WAITING_CLIENT_INFO:
            logger.info(
                "send_info_request_email: пропуск order=%s — статус %s",
                oid,
                order.status,
            )
            return

        if has_successful_email(session, oid, EmailType.INFO_REQUEST):
            logger.info(
                "send_info_request_email: пропуск order=%s — запрос уже отправлялся",
                oid,
            )
            return

        if order.waiting_client_info_at is None:
            logger.info(
                "send_info_request_email: пропуск order=%s — нет waiting_client_info_at",
                oid,
            )
            return

        due = order.waiting_client_info_at + timedelta(hours=24)
        if datetime.now(timezone.utc) < due:
            logger.info(
                "send_info_request_email: пропуск order=%s — ещё не наступил срок (%s)",
                oid,
                due.isoformat(),
            )
            return

        success = send_info_request(session, order)

        if success:
            order.retry_count += 1
            session.commit()
            logger.info(
                "Письмо с запросом отправлено на %s (попытка %d)",
                order.client_email,
                order.retry_count,
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


@celery_app.task
def process_due_info_requests():
    """Периодически: заявки в WAITING_CLIENT_INFO старше 24 ч без успешного info_request."""
    from datetime import datetime, timedelta, timezone

    from app.services.email_service import has_successful_email

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    orders: list[Order] = []
    queued = 0

    with SyncSession() as session:
        stmt = (
            select(Order)
            .options(selectinload(Order.emails))
            .where(Order.status == OrderStatus.WAITING_CLIENT_INFO)
            .where(Order.waiting_client_info_at.isnot(None))
            .where(Order.waiting_client_info_at <= cutoff)
        )
        orders = list(session.execute(stmt).scalars().all())
        queued = 0
        for order in orders:
            if has_successful_email(session, order.id, EmailType.INFO_REQUEST):
                continue
            logger.info(
                "process_due_info_requests: очередь info_request для order=%s",
                order.id,
            )
            send_info_request_email.delay(str(order.id))
            queued += 1

    logger.info(
        "process_due_info_requests: кандидатов %d, поставлено в очередь %d",
        len(orders),
        queued,
    )


@celery_app.task
def notify_engineer_client_documents_received(order_id: str):
    """Уведомляет инженера каждый раз, когда клиент отправляет документы."""
    from app.services.email_service import send_client_documents_received_notification

    oid = uuid.UUID(order_id)
    logger.info("notify_engineer_client_documents_received: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return
        send_client_documents_received_notification(session, order)


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
    генерирует DOCX сопроводительного письма в РСО,
    отправляет клиенту письмом с вложениями.
    """
    from app.services.email_service import send_project
    from app.services.cover_letter import generate_cover_letter
    from app.services.tu_schema import TUParsedData

    oid = uuid.UUID(order_id)
    order_id_short = order_id[:8]
    logger.info("send_completed_project: order=%s", oid)

    cover_letter_path = None

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

        if not attachment_paths:
            logger.warning(
                "send_completed_project: order=%s — нет вложений (записи generated_project в БД: %s, "
                "файлы на диске отсутствуют или пути неверны)",
                oid,
                len(project_files),
            )

        # Генерируем сопроводительное письмо из parsed_params
        try:
            if order.parsed_params:
                parsed = TUParsedData.model_validate(order.parsed_params)
                cover_letter_path = generate_cover_letter(
                    parsed,
                    order_id_short,
                    client_email=order.client_email,
                    admin_email=settings.admin_email,
                )
                attachment_paths.append(str(cover_letter_path))
                logger.info(
                    "send_completed_project: сопроводительное письмо создано: %s",
                    cover_letter_path,
                )
            else:
                logger.warning(
                    "send_completed_project: order=%s — parsed_params пуст, "
                    "сопроводительное письмо не создано",
                    oid,
                )
        except Exception as e:
            logger.error(
                "send_completed_project: ошибка генерации сопроводительного письма "
                "для order=%s: %s",
                oid,
                e,
                exc_info=True,
            )
            # Degraded mode: отправляем без docx

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

    # Удаляем временный файл вне сессии (независимо от успеха/неуспеха)
    if cover_letter_path and cover_letter_path.exists():
        try:
            cover_letter_path.unlink()
        except OSError as e:
            logger.warning("Не удалось удалить временный файл %s: %s", cover_letter_path, e)


# ═══════════════════════════════════════════════════════════════════════════════
# Задачи платёжного флоу
# ═══════════════════════════════════════════════════════════════════════════════


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def parse_company_card_task(self, order_id: str):
    """Парсинг карточки предприятия — извлечение реквизитов.

    Вызывается после загрузки клиентом файла категории COMPANY_CARD
    на странице /payment/{order_id}.
    Результат сохраняется в order.company_requisites (JSONB).
    Статус НЕ меняет — это делает вызывающий код (эндпоинт).
    """
    from app.services.company_parser import parse_company_card

    oid = uuid.UUID(order_id)
    logger.info("parse_company_card_task: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            logger.error("parse_company_card_task: заявка не найдена: %s", oid)
            return

        # Найти файл карточки предприятия (берём последний загруженный)
        card_files = [
            f for f in order.files
            if f.category.value == "company_card"
        ]
        if not card_files:
            logger.error(
                "parse_company_card_task: нет файла company_card для order=%s", oid
            )
            return

        card_file = sorted(card_files, key=lambda f: f.created_at)[-1]
        file_path = settings.upload_dir / card_file.storage_path

        if not file_path.exists():
            logger.error(
                "parse_company_card_task: файл не найден на диске: %s", file_path
            )
            return

        try:
            requisites = parse_company_card(str(file_path))
        except Exception as e:
            logger.exception(
                "parse_company_card_task: ошибка парсинга: order=%s, error=%s", oid, e
            )
            # Сохраняем ошибку для отображения на странице
            order.company_requisites = {
                "error": str(e),
                "parse_confidence": 0.0,
            }
            session.commit()
            raise self.retry(exc=e)

        order.company_requisites = requisites.model_dump(mode="json")
        session.commit()

        logger.info(
            "parse_company_card_task: реквизиты извлечены: order=%s, inn=%s, "
            "confidence=%.2f, warnings=%d",
            oid,
            (requisites.inn[:4] + "...") if requisites.inn else "N/A",
            requisites.parse_confidence,
            len(requisites.warnings),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Периодические задачи
# ═══════════════════════════════════════════════════════════════════════════════


@celery_app.task
def send_reminders():
    """Периодическая задача: одно напоминание клиенту после успешного info_request.

    Условия: WAITING_CLIENT_INFO, уже был успешный info_request, успешного reminder ещё не было,
    с момента последнего успешного info_request прошло не менее 3 суток, retry_count < max_retry_count.
    """
    from datetime import datetime, timedelta, timezone

    from app.services.email_service import has_successful_email, send_reminder

    logger.info("send_reminders: проверка заявок, ожидающих ответа клиента")

    with SyncSession() as session:
        stmt = (
            select(Order)
            .options(selectinload(Order.emails))
            .where(Order.status == OrderStatus.WAITING_CLIENT_INFO)
            .where(Order.retry_count < settings.max_retry_count)
        )
        orders = list(session.execute(stmt).scalars().all())

        cutoff = datetime.now(timezone.utc) - timedelta(days=3)
        sent_count = 0

        for order in orders:
            if not has_successful_email(session, order.id, EmailType.INFO_REQUEST):
                continue
            if has_successful_email(session, order.id, EmailType.REMINDER):
                logger.debug(
                    "send_reminders: пропуск order=%s — напоминание уже отправлялось",
                    order.id,
                )
                continue

            last_info = max(
                (
                    e.sent_at
                    for e in order.emails
                    if e.email_type == EmailType.INFO_REQUEST and e.sent_at is not None
                ),
                default=None,
            )
            if last_info is None:
                continue
            last_info_utc = last_info.replace(tzinfo=timezone.utc)
            if last_info_utc > cutoff:
                continue

            success = send_reminder(session, order)
            if success:
                order.retry_count += 1
                session.commit()
                sent_count += 1
                logger.info(
                    "Напоминание отправлено: order=%s, попытка %d",
                    order.id,
                    order.retry_count,
                )

        logger.info("send_reminders: отправлено %d напоминаний", sent_count)
