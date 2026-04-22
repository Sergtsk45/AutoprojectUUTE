"""Contract, advance, pay, company card (payment) (D1.b)."""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from app.core.celery_app import celery_app
from app.core.config import settings
from app.repositories.order_jsonb import (
    get_company_requisites_dict,
    get_parsed_params,
    set_company_requisites,
)
from app.models.models import FileCategory, Order, OrderFile, OrderStatus, PaymentMethod

from . import client_response
from ._common import (
    SyncSession,
    _existing_order_file_path,
    _get_order,
    _latest_order_file,
    _normalize_client_requisites,
    _resolve_initial_payment_amount,
    _transition,
)

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.services.tasks.process_card_and_contract",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def process_card_and_contract(self, order_id: str):
    """CLIENT_INFO_RECEIVED → CONTRACT_SENT: парсинг реквизитов, генерация и отправка договора/счёта."""
    from datetime import datetime, timezone

    from app.services.company_parser import parse_company_card
    from app.services.contract_generator import (
        generate_contract,
        generate_contract_number,
        generate_invoice,
    )
    from app.services.email_service import send_contract_delivery_to_client

    oid = uuid.UUID(order_id)
    order_id_short = order_id[:8]
    logger.info("process_card_and_contract: order=%s", oid)

    contract_path: Path | None = None
    invoice_path: Path | None = None

    try:
        with SyncSession() as session:
            order = _get_order(session, oid)
            if order is None:
                return

            if order.status == OrderStatus.CONTRACT_SENT:
                logger.info("process_card_and_contract: order=%s уже в contract_sent", oid)
                return

            if order.status != OrderStatus.CLIENT_INFO_RECEIVED:
                logger.warning(
                    "process_card_and_contract: order=%s статус %s, пропускаем",
                    oid,
                    order.status.value,
                )
                return

            card_files = sorted(
                [f for f in order.files if f.category == FileCategory.COMPANY_CARD],
                key=lambda f: f.created_at,
            )
            if not card_files:
                order.waiting_client_info_at = datetime.now(timezone.utc)
                session.commit()
                _transition(session, order, OrderStatus.WAITING_CLIENT_INFO)
                logger.warning(
                    "process_card_and_contract: нет company_card, order=%s → waiting_client_info",
                    oid,
                )
                return

            card_file = card_files[-1]
            card_path = settings.upload_dir / card_file.storage_path
            if not card_path.exists():
                raise FileNotFoundError(f"Файл карточки не найден: {card_path}")

            requisites = parse_company_card(str(card_path))
            set_company_requisites(order, requisites)
            order.payment_amount = _resolve_initial_payment_amount(order)
            order.advance_amount = order.payment_amount // 2
            if not order.contract_number:
                order.contract_number = generate_contract_number(str(order.id))
            session.commit()

            contract_existing = sorted(
                [f for f in order.files if f.category == FileCategory.CONTRACT],
                key=lambda f: f.created_at,
            )
            invoice_existing = sorted(
                [f for f in order.files if f.category == FileCategory.INVOICE],
                key=lambda f: f.created_at,
            )

            attachment_paths: list[str] = []
            if contract_existing and invoice_existing:
                existing_contract = settings.upload_dir / contract_existing[-1].storage_path
                existing_invoice = settings.upload_dir / invoice_existing[-1].storage_path
                if existing_contract.exists() and existing_invoice.exists():
                    attachment_paths = [str(existing_contract), str(existing_invoice)]

            if not attachment_paths:
                req = _normalize_client_requisites(
                    get_company_requisites_dict(order), order.client_name
                )
                tu_path = _existing_order_file_path(order, FileCategory.TU)
                parsed_model = get_parsed_params(order)
                doc_info = (
                    parsed_model.document.model_dump(mode="json")
                    if parsed_model is not None
                    else {}
                )
                rso_info = (
                    parsed_model.rso.model_dump(mode="json") if parsed_model is not None else {}
                )
                contract_path = generate_contract(
                    order_id_short,
                    order.contract_number or order_id_short,
                    order.object_address or "—",
                    order.client_name,
                    order.payment_amount or 0,
                    order.advance_amount or 0,
                    req,
                    client_email=order.client_email,
                    tu_file_path=tu_path,
                    rso_name=rso_info.get("rso_name"),
                    tu_number=doc_info.get("tu_number"),
                    tu_date=doc_info.get("tu_date"),
                    tu_valid_to=doc_info.get("tu_valid_to"),
                )
                invoice_path = generate_invoice(
                    order_id_short,
                    order.contract_number or order_id_short,
                    order.object_address or "—",
                    order.payment_amount or 0,
                    order.advance_amount or 0,
                    req,
                    is_advance=True,
                )

                doc_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                for src_path, category, prefix in (
                    (contract_path, FileCategory.CONTRACT, "contract"),
                    (invoice_path, FileCategory.INVOICE, "invoice"),
                ):
                    dest_dir = settings.upload_dir / str(oid) / category.value
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_file = dest_dir / f"{prefix}_{order_id_short}.docx"
                    shutil.copy2(str(src_path), str(dest_file))
                    storage_path = f"{oid}/{category.value}/{dest_file.name}"
                    session.add(
                        OrderFile(
                            order_id=oid,
                            category=category,
                            original_filename=dest_file.name,
                            storage_path=storage_path,
                            content_type=doc_mime,
                            file_size=dest_file.stat().st_size,
                        )
                    )
                    attachment_paths.append(str(dest_file))
                session.commit()

            sent = send_contract_delivery_to_client(
                session,
                order,
                attachment_paths=attachment_paths,
            )
            if not sent:
                raise RuntimeError("Не удалось отправить письмо с договором клиенту")

            _transition(session, order, OrderStatus.CONTRACT_SENT)
            client_response.notify_engineer_client_documents_received.delay(order_id)
            logger.info("process_card_and_contract: order=%s → contract_sent", oid)
    except Exception as exc:
        logger.exception("process_card_and_contract: ошибка order=%s: %s", oid, exc)
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error("process_card_and_contract: исчерпаны попытки для order=%s", oid)
    finally:
        for p in (contract_path, invoice_path):
            if p is not None:
                try:
                    p.unlink(missing_ok=True)
                except OSError as err:
                    logger.warning("Не удалось удалить временный файл %s: %s", p, err)


@celery_app.task(
    name="app.services.tasks.fill_excel",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
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


@celery_app.task(
    name="app.services.tasks.generate_project",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
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


@celery_app.task(
    name="app.services.tasks.initiate_payment_flow",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def initiate_payment_flow(self, order_id: str):
    """REVIEW → AWAITING_CONTRACT: инженер одобрил, начинаем оплату."""
    from app.services.contract_generator import generate_contract_number
    from app.services.email_service import send_project_ready_payment

    oid = uuid.UUID(order_id)
    logger.info("initiate_payment_flow: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return

        if order.status != OrderStatus.REVIEW:
            logger.warning(
                "initiate_payment_flow: order=%s в статусе %s, пропускаем",
                oid,
                order.status.value,
            )
            return

        order.payment_amount = _resolve_initial_payment_amount(order)
        order.advance_amount = order.payment_amount // 2

        if not order.contract_number:
            order.contract_number = generate_contract_number(str(order.id))

        session.commit()

        _transition(session, order, OrderStatus.AWAITING_CONTRACT)

        success = send_project_ready_payment(session, order)
        if not success:
            logger.error(
                "initiate_payment_flow: не удалось отправить email для order=%s",
                oid,
            )

    logger.info("initiate_payment_flow: завершено, order=%s → awaiting_contract", oid)


@celery_app.task(
    name="app.services.tasks.process_advance_payment",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def process_advance_payment(self, order_id: str):
    """CONTRACT_SENT → ADVANCE_PAID: аванс подтверждён, проект отправляется отдельно."""
    from datetime import datetime, timezone

    oid = uuid.UUID(order_id)
    logger.info("process_advance_payment: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return

        if order.status == OrderStatus.CONTRACT_SENT:
            if order.advance_paid_at is None:
                order.advance_paid_at = datetime.now(timezone.utc)
                session.commit()
            _transition(session, order, OrderStatus.ADVANCE_PAID)
            logger.info("process_advance_payment: order=%s → advance_paid", oid)
            return

        if order.status == OrderStatus.ADVANCE_PAID:
            logger.info("process_advance_payment: order=%s уже в advance_paid", oid)
            return

        logger.warning(
            "process_advance_payment: order=%s статус %s, пропускаем",
            oid,
            order.status.value,
        )


@celery_app.task(
    name="app.services.tasks.process_final_payment",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def process_final_payment(self, order_id: str):
    """AWAITING_FINAL_PAYMENT → COMPLETED: финальная оплата подтверждена инженером."""
    from datetime import datetime, timezone

    from app.services.email_service import send_final_payment_received

    oid = uuid.UUID(order_id)
    logger.info("process_final_payment: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return

        if order.status not in (
            OrderStatus.AWAITING_FINAL_PAYMENT,
            OrderStatus.RSO_REMARKS_RECEIVED,
        ):
            logger.warning(
                "process_final_payment: order=%s статус %s, пропускаем",
                oid,
                order.status.value,
            )
            return

        order.final_paid_at = datetime.now(timezone.utc)
        session.commit()

        success = send_final_payment_received(session, order)
        if not success:
            logger.warning("process_final_payment: email не отправлен для order=%s", oid)

        _transition(session, order, OrderStatus.COMPLETED)

    logger.info("process_final_payment: order=%s → completed", oid)


@celery_app.task(
    name="app.services.tasks.parse_company_card_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
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
        card_files = [f for f in order.files if f.category.value == "company_card"]
        if not card_files:
            logger.error("parse_company_card_task: нет файла company_card для order=%s", oid)
            return

        card_file = sorted(card_files, key=lambda f: f.created_at)[-1]
        file_path = settings.upload_dir / card_file.storage_path

        if not file_path.exists():
            logger.error("parse_company_card_task: файл не найден на диске: %s", file_path)
            return

        try:
            requisites = parse_company_card(str(file_path))
        except Exception as e:
            logger.exception("parse_company_card_task: ошибка парсинга: order=%s, error=%s", oid, e)
            # Сохраняем маркер ошибки для отображения на странице. Это не
            # `CompanyRequisites` — отдельный формат `{"error": "..."}`;
            # фронт проверяет `company_requisites.error` перед рендерингом.
            order.company_requisites = {
                "error": str(e),
                "parse_confidence": 0.0,
            }
            session.commit()
            raise self.retry(exc=e)

        set_company_requisites(order, requisites)
        session.commit()

        logger.info(
            "parse_company_card_task: реквизиты извлечены: order=%s, inn=%s, "
            "confidence=%.2f, warnings=%d",
            oid,
            (requisites.inn[:4] + "...") if requisites.inn else "N/A",
            requisites.parse_confidence,
            len(requisites.warnings),
        )


@celery_app.task(
    name="app.services.tasks.process_company_card_and_send_contract",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def process_company_card_and_send_contract(self, order_id: str):
    """AWAITING_CONTRACT → CONTRACT_SENT: реквизиты есть — договор, счёт, письмо, файлы в БД."""

    from app.services.contract_generator import (
        generate_contract,
        generate_contract_number,
        generate_invoice,
    )
    from app.services.email_service import send_contract_delivery_to_client

    oid = uuid.UUID(order_id)
    order_id_short = order_id[:8]
    logger.info("process_company_card_and_send_contract: order=%s", oid)

    contract_path: Path | None = None
    invoice_path: Path | None = None

    try:
        with SyncSession() as session:
            order = _get_order(session, oid)
            if order is None:
                logger.error("process_company_card_and_send_contract: заявка не найдена: %s", oid)
                return

            if order.status != OrderStatus.AWAITING_CONTRACT:
                logger.warning(
                    "process_company_card_and_send_contract: пропуск, статус %s",
                    order.status.value,
                )
                return

            if order.payment_method != PaymentMethod.BANK_TRANSFER:
                logger.info("process_company_card_and_send_contract: не bank_transfer — пропуск")
                return

            # Маркер ошибки парсинга (`{"error": "..."}`) — не реквизиты, а флаг
            # неудачного OCR; читаем сырой dict напрямую, чтобы отличить этот случай
            # от валидных данных.
            raw_req = order.company_requisites
            if not raw_req or not isinstance(raw_req, dict) or raw_req.get("error"):
                logger.error(
                    "process_company_card_and_send_contract: нет валидных реквизитов %s",
                    oid,
                )
                return

            if order.payment_amount is None or order.advance_amount is None:
                logger.error(
                    "process_company_card_and_send_contract: не заданы суммы order=%s",
                    oid,
                )
                return

            contract_number = order.contract_number or generate_contract_number(str(order.id))
            req = _normalize_client_requisites(
                get_company_requisites_dict(order), order.client_name
            )

            contract_existing = sorted(
                [f for f in order.files if f.category == FileCategory.CONTRACT],
                key=lambda f: f.created_at,
            )
            invoice_existing = sorted(
                [f for f in order.files if f.category == FileCategory.INVOICE],
                key=lambda f: f.created_at,
            )
            if contract_existing and invoice_existing:
                p_c = settings.upload_dir / contract_existing[-1].storage_path
                p_i = settings.upload_dir / invoice_existing[-1].storage_path
                if p_c.exists() and p_i.exists():
                    ok = send_contract_delivery_to_client(
                        session,
                        order,
                        [str(p_c), str(p_i)],
                    )
                    if ok:
                        _transition(session, order, OrderStatus.CONTRACT_SENT)
                        logger.info(
                            "process_company_card_and_send_contract: повторная отправка ok order=%s",
                            oid,
                        )
                    else:
                        try:
                            self.retry()
                        except self.MaxRetriesExceededError:
                            logger.error(
                                "process_company_card_and_send_contract: исчерпаны попытки order=%s",
                                oid,
                            )
                    return

            tu_path = _existing_order_file_path(order, FileCategory.TU)
            parsed_model = get_parsed_params(order)
            doc_info = (
                parsed_model.document.model_dump(mode="json") if parsed_model is not None else {}
            )
            rso_info = parsed_model.rso.model_dump(mode="json") if parsed_model is not None else {}
            contract_path = generate_contract(
                order_id_short,
                contract_number,
                order.object_address or "—",
                order.client_name,
                order.payment_amount,
                order.advance_amount,
                req,
                client_email=order.client_email,
                tu_file_path=tu_path,
                rso_name=rso_info.get("rso_name"),
                tu_number=doc_info.get("tu_number"),
                tu_date=doc_info.get("tu_date"),
                tu_valid_to=doc_info.get("tu_valid_to"),
            )
            invoice_path = generate_invoice(
                order_id_short,
                contract_number,
                order.object_address or "—",
                order.payment_amount,
                order.advance_amount,
                req,
                is_advance=True,
            )

            doc_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            for src_path, category, prefix in (
                (contract_path, FileCategory.CONTRACT, "contract"),
                (invoice_path, FileCategory.INVOICE, "invoice"),
            ):
                dest_dir = settings.upload_dir / str(oid) / category.value
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = dest_dir / f"{prefix}_{order_id_short}.docx"
                shutil.copy2(str(src_path), str(dest_file))
                storage_path = f"{oid}/{category.value}/{dest_file.name}"
                session.add(
                    OrderFile(
                        order_id=oid,
                        category=category,
                        original_filename=dest_file.name,
                        storage_path=storage_path,
                        content_type=doc_mime,
                        file_size=dest_file.stat().st_size,
                    )
                )

            order.contract_number = contract_number
            session.commit()

            ok = send_contract_delivery_to_client(
                session,
                order,
                [str(contract_path), str(invoice_path)],
            )
            if ok:
                _transition(session, order, OrderStatus.CONTRACT_SENT)
                logger.info("process_company_card_and_send_contract: готово order=%s", oid)
            else:
                try:
                    self.retry()
                except self.MaxRetriesExceededError:
                    logger.error(
                        "process_company_card_and_send_contract: исчерпаны попытки order=%s",
                        oid,
                    )
    except Exception as e:
        logger.exception("process_company_card_and_send_contract: ошибка order=%s: %s", oid, e)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(
                "process_company_card_and_send_contract: исчерпаны попытки order=%s",
                oid,
            )
    finally:
        for p in (contract_path, invoice_path):
            if p is not None:
                try:
                    p.unlink(missing_ok=True)
                except OSError as err:
                    logger.warning("Не удалось удалить временный файл %s: %s", p, err)
