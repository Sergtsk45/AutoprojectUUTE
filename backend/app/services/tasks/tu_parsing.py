"""Парсинг ТУ, check_data (D1.b)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.models import FileCategory, Order, OrderStatus
from app.services.param_labels import compute_client_document_missing

from . import client_response
from ._common import (
    INFO_REQUEST_AUTO_DELAY_SECONDS,
    SyncSession,
    _get_order,
    _transition,
)

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.services.tasks.start_tu_parsing",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
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

            # Сохраняем в БД. Ручной `model_dump(exclude={"raw_text"})` —
            # raw_text большой (несколько страниц PDF), в JSONB не храним;
            # accessor `set_parsed_params` дампит без исключений, поэтому здесь
            # сохраняем напрямую.
            order.parsed_params = parsed.model_dump(
                exclude={"raw_text"},
                mode="json",
            )
            order.missing_params = determine_missing_params(parsed)

            # Если город ещё не указан клиентом — взять из ТУ
            if not order.object_city and parsed.object.city:
                order.object_city = parsed.object.city

            _transition(session, order, OrderStatus.TU_PARSED)
            logger.info(
                "Парсинг завершён: order=%s, confidence=%.2f, missing=%s",
                oid,
                parsed.parse_confidence,
                order.missing_params,
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
                            calc_type,
                            oid,
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
                        oid,
                        init_err,
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


@celery_app.task(name="app.services.tasks.check_data_completeness", bind=True)
def check_data_completeness(self, order_id: str):
    """TU_PARSED / CLIENT_INFO_RECEIVED: пересчёт missing и переход в WAITING_CLIENT_INFO.

    Для новых заявок всегда используем путь через WAITING_CLIENT_INFO.
    Если задача вызвана повторно в CLIENT_INFO_RECEIVED, обратный переход не делаем.
    """
    from datetime import datetime, timezone

    oid = uuid.UUID(order_id)
    logger.info("check_data_completeness: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return

        uploaded_categories = {f.category.value for f in order.files}
        missing = compute_client_document_missing(
            uploaded_categories, order.survey_data
        )
        if (
            FileCategory.COMPANY_CARD.value not in uploaded_categories
            and FileCategory.COMPANY_CARD.value not in missing
        ):
            missing.append(FileCategory.COMPANY_CARD.value)
        order.missing_params = missing
        session.commit()

        if order.status == OrderStatus.CLIENT_INFO_RECEIVED:
            logger.info(
                "check_data_completeness: order=%s уже в client_info_received, обратный переход не выполняем",
                oid,
            )
            return

        order.waiting_client_info_at = datetime.now(timezone.utc)
        session.commit()
        if order.status != OrderStatus.WAITING_CLIENT_INFO:
            _transition(session, order, OrderStatus.WAITING_CLIENT_INFO)
        logger.info(
            "check_data_completeness: order=%s → waiting_client_info, missing=%s",
            oid,
            missing,
        )
        client_response.send_info_request_email.apply_async(
            args=[order_id],
            countdown=INFO_REQUEST_AUTO_DELAY_SECONDS,
        )
        client_response.notify_engineer_tu_parsed.delay(order_id)
        logger.info(
            "check_data_completeness: send_info_request_email с задержкой %s с, order=%s",
            INFO_REQUEST_AUTO_DELAY_SECONDS,
            oid,
        )
        logger.info(
            "check_data_completeness: notify_engineer_tu_parsed поставлена в очередь, order=%s",
            oid,
        )
