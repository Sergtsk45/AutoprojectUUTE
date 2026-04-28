"""Common helpers: sync session, requisites, file helpers (D1.b package split)."""

import logging
import shutil
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.repositories.order_jsonb import (
    get_company_requisites_dict,
    get_parsed_params,
)
from app.models.models import (
    EmailLog,
    FileCategory,
    Order,
    OrderFile,
    OrderStatus,
    EmailType,
)

logger = logging.getLogger(__name__)

# Задержка перед первой автоотправкой письма «запрос документов» (info_request), сек.
INFO_REQUEST_AUTO_DELAY_SECONDS = 24 * 60 * 60
FINAL_PAYMENT_REMINDER_DELAY_DAYS = 15


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
        raise ValueError(f"Недопустимый переход: {order.status.value} → {new_status.value}")
    order.status = new_status
    session.commit()


def _latest_order_file(order: Order, category: FileCategory) -> OrderFile | None:
    files = [f for f in order.files if f.category == category]
    if not files:
        return None
    return sorted(files, key=lambda file_obj: file_obj.created_at)[-1]


def _existing_order_file_path(order: Order, category: FileCategory) -> Path | None:
    existing_file = _latest_order_file(order, category)
    if existing_file is None:
        return None
    file_path = settings.upload_dir / existing_file.storage_path
    if not file_path.exists():
        logger.error(
            "_existing_order_file_path: файл %s для order=%s отсутствует на диске",
            existing_file.storage_path,
            order.id,
        )
        return None
    return file_path


def _store_generated_file(
    session: Session,
    order: Order,
    source_path: Path,
    category: FileCategory,
    prefix: str,
    content_type: str = ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
) -> Path:
    order_id_short = str(order.id)[:8]
    dest_dir = settings.upload_dir / str(order.id) / category.value
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / f"{prefix}_{order_id_short}{source_path.suffix}"
    shutil.copy2(str(source_path), str(dest_file))
    storage_path = f"{order.id}/{category.value}/{dest_file.name}"
    session.add(
        OrderFile(
            order_id=order.id,
            category=category,
            original_filename=dest_file.name,
            storage_path=storage_path,
            content_type=content_type,
            file_size=dest_file.stat().st_size,
        )
    )
    session.commit()
    session.refresh(order)
    return dest_file


def _normalize_client_requisites(raw: dict, fallback_name: str) -> dict:
    """Приводит JSON реквизитов к виду, ожидаемому generate_contract / generate_invoice."""

    def g(key: str, default: str = "—") -> str:
        v = raw.get(key)
        if v is None:
            return default
        s = str(v).strip()
        return s if s else default

    full_name = g("full_name", "") or fallback_name
    return {
        "full_name": full_name,
        "inn": g("inn", "—"),
        "kpp": g("kpp", "—") if raw.get("kpp") else "—",
        "ogrn": g("ogrn", "—") if raw.get("ogrn") else "—",
        "legal_address": g("legal_address", "—"),
        "bank_name": g("bank_name", "—"),
        "bik": g("bik", "—"),
        "corr_account": g("corr_account", "—"),
        "settlement_account": g("settlement_account", "—"),
        "director_name": g("director_name", "—"),
        "director_position": g("director_position", "Генеральный директор"),
        "email": raw.get("email"),
    }


def _ensure_final_invoice_attachment(
    session: Session,
    order: Order,
) -> tuple[Path | None, Path | None]:
    """Возвращает сохранённый счёт на остаток, при необходимости генерируя его один раз."""
    from app.services.contract_generator import generate_invoice

    existing_invoice_path = _existing_order_file_path(order, FileCategory.FINAL_INVOICE)
    if existing_invoice_path is not None:
        return existing_invoice_path, None
    if _latest_order_file(order, FileCategory.FINAL_INVOICE) is not None:
        return None, None

    can_generate_final_invoice = (
        order.payment_amount is not None
        and order.advance_amount is not None
        and order.payment_amount > order.advance_amount
    )
    if not can_generate_final_invoice:
        return None, None

    order_id_short = str(order.id)[:8]
    # `_normalize_client_requisites` работает на сыром dict — отдаём ей
    # валидированный dict (мусорные ключи отфильтрованы `extra='ignore'`).
    req = _normalize_client_requisites(
        get_company_requisites_dict(order),
        order.client_name,
    )
    temp_invoice_path = generate_invoice(
        order_id_short,
        order.contract_number or order_id_short,
        order.object_address or "—",
        order.payment_amount or 0,
        order.advance_amount or 0,
        req,
        is_advance=False,
    )
    if not temp_invoice_path or not temp_invoice_path.exists():
        return None, temp_invoice_path

    persisted_invoice_path = _store_generated_file(
        session=session,
        order=order,
        source_path=temp_invoice_path,
        category=FileCategory.FINAL_INVOICE,
        prefix="final_invoice",
    )
    return persisted_invoice_path, temp_invoice_path


def _ensure_completion_act_attachment(
    session: Session,
    order: Order,
) -> tuple[Path | None, Path | None]:
    """Возвращает акт выполненных работ, при необходимости генерируя его один раз.

    Returns:
        (persisted_path, temp_path) — temp_path удаляет вызывающий код.
    """
    from app.services.contract_generator import generate_completion_act

    existing_act_path = _existing_order_file_path(order, FileCategory.COMPLETION_ACT)
    if existing_act_path is not None:
        return existing_act_path, None
    if _latest_order_file(order, FileCategory.COMPLETION_ACT) is not None:
        return None, None

    if order.payment_amount is None:
        return None, None

    order_id_short = str(order.id)[:8]
    req = _normalize_client_requisites(
        get_company_requisites_dict(order),
        order.client_name,
    )
    temp_act_path = generate_completion_act(
        order_id_short,
        order.contract_number or order_id_short,
        order.object_address or "—",
        order.payment_amount,
        req,
    )
    if not temp_act_path or not temp_act_path.exists():
        return None, temp_act_path

    persisted_act_path = _store_generated_file(
        session=session,
        order=order,
        source_path=temp_act_path,
        category=FileCategory.COMPLETION_ACT,
        prefix="akt",
    )
    return persisted_act_path, temp_act_path


def _has_successful_final_payment_reminder(
    session: Session,
    order_id: uuid.UUID,
    reminder_kind: str,
) -> bool:
    return (
        session.execute(
            select(EmailLog.id)
            .where(
                EmailLog.order_id == order_id,
                EmailLog.email_type == EmailType.FINAL_PAYMENT_REQUEST,
                EmailLog.sent_at.isnot(None),
                EmailLog.body_text.contains(f"reminder_kind:{reminder_kind}"),
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def _collect_project_attachments(session: Session, order: Order) -> tuple[list[str], Path | None]:
    """Собирает PDF проекта и генерирует сопроводительное письмо в РСО.

    Returns:
        (attachment_paths, cover_letter_path)
        cover_letter_path может быть None если parsed_params пуст.
        Вызывающий код ОБЯЗАН удалить cover_letter_path после отправки.
    """
    from app.services.cover_letter import generate_cover_letter

    _ = session

    order_id_short = str(order.id)[:8]

    latest_project_path = _existing_order_file_path(order, FileCategory.GENERATED_PROJECT)
    attachment_paths = [str(latest_project_path)] if latest_project_path is not None else []

    if latest_project_path is None:
        logger.warning(
            "_collect_project_attachments: order=%s — нет актуального PDF проекта",
            order.id,
        )

    cover_letter_path: Path | None = None
    try:
        parsed = get_parsed_params(order)
        if parsed is not None:
            cover_letter_path = generate_cover_letter(
                parsed,
                order_id_short,
                client_email=order.client_email,
                admin_email=settings.admin_email,
            )
            attachment_paths.append(str(cover_letter_path))
            logger.info(
                "_collect_project_attachments: сопроводительное создано для order=%s: %s",
                order.id,
                cover_letter_path,
            )
    except Exception as e:
        logger.error(
            "_collect_project_attachments: ошибка сопроводительного для order=%s: %s",
            order.id,
            e,
            exc_info=True,
        )

    return attachment_paths, cover_letter_path


def _resolve_initial_payment_amount(order: Order) -> int:
    """Полная стоимость для старта оплаты: из заявки, из parsed_params.circuits или дефолт."""
    from app.models.models import OrderType

    if order.payment_amount is not None and order.payment_amount > 0:
        return order.payment_amount

    is_express = order.order_type == OrderType.EXPRESS
    price_map = {1: 11250, 2: 35000, 3: 50000} if is_express else {1: 22500, 2: 35000, 3: 50000}
    default = 11250 if is_express else 22500

    # `circuits` — исторический плоский ключ, не входит в `TUParsedData`,
    # поэтому читаем сырой dict напрямую (через accessor он был бы отфильтрован
    # `extra='ignore'` и терялся бы у express-заявок со старыми LLM-ответами).
    circuits: int | None = None
    raw = order.parsed_params
    if isinstance(raw, dict):
        v = raw.get("circuits")
        if isinstance(v, int):
            circuits = v
        elif isinstance(v, str) and v.strip().isdigit():
            circuits = int(v.strip())
    if circuits is not None:
        circuits = max(1, min(circuits, 3))
        return price_map.get(circuits, default)
    return default
