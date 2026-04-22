"""API-эндпоинты для форм лендинга.

Публичные (без авторизации) — вызываются фронтендом.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.models import FileCategory, OrderStatus, OrderType, PaymentMethod
from app.post_project_state import derive_post_project_flags
from app.repositories.order_jsonb import (
    get_company_requisites_dict,
    get_parsed_params_dict,
    get_survey_data_dict,
    set_survey_data,
)
from app.schemas.jsonb import SurveyData
from app.services.param_labels import CLIENT_DOCUMENT_PARAM_CODES
from app.services import OrderService
from app.services.email_service import send_kp_request_notification
from app.services.tasks import notify_engineer_new_order, start_tu_parsing
from app.schemas import (
    FileResponse,
    OrderCreate,
    PaymentPageInfo,
    PipelineResponse,
    UploadPageInfo,
)
from pydantic import ValidationError

router = APIRouter(prefix="/landing", tags=["landing"])
logger = logging.getLogger(__name__)

# Статусы, в которых клиент может сохранить опрос по публичной ссылке (UUID).
_SURVEY_SAVE_ALLOWED: frozenset[OrderStatus] = frozenset(
    {
        OrderStatus.TU_PARSED,
        OrderStatus.WAITING_CLIENT_INFO,
        OrderStatus.CLIENT_INFO_RECEIVED,
        OrderStatus.DATA_COMPLETE,
        OrderStatus.GENERATING_PROJECT,
    }
)

_MAX_TU_SIZE = 20 * 1024 * 1024  # 20 МБ — максимальный размер файла ТУ
_MAX_SIGNED_CONTRACT_SIZE = 25 * 1024 * 1024  # 25 МБ
_SIGNED_CONTRACT_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
_SIGNED_CONTRACT_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


# ── Schemas ──────────────────────────────────────────────────────────────────


class SampleRequest(BaseModel):
    email: EmailStr


class OrderRequest(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=255)
    client_email: EmailStr
    client_phone: str | None = Field(None, max_length=50)
    client_organization: str | None = Field(None, max_length=255)
    object_address: str | None = None
    object_city: str = Field(..., min_length=2, max_length=255)
    circuits: int | None = Field(None, ge=1, le=10)
    price: int | None = None
    order_type: str = Field("express", pattern="^(express|custom)$")


class OrderCreatedResponse(BaseModel):
    order_id: str
    upload_url: str
    message: str


class PartnershipRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    company: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=50)


# Справочная схема для документации — в эндпоинте используются Form() параметры напрямую
class KpRequest(BaseModel):
    organization: str = Field(..., min_length=2, max_length=255)
    responsible_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=5, max_length=50)
    email: EmailStr


class SimpleResponse(BaseModel):
    success: bool
    message: str


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/sample-request", response_model=SimpleResponse)
async def request_sample(data: SampleRequest):
    """Сценарий A: Клиент запросил образец проекта.

    Отправляет PDF-образец на email (если файл есть),
    или просто подтверждение.
    """
    from app.services.email_service import send_sample_delivery

    # D4: SMTP выносим из event loop. Результат не влияет на UX (success=True всегда).
    await asyncio.to_thread(send_sample_delivery, data.email)

    return SimpleResponse(
        success=True,  # Всегда true для UX — даже если SMTP упал, не пугаем клиента
        message="Образец отправлен на вашу почту",
    )


@router.post("/order", response_model=OrderCreatedResponse, status_code=201)
async def create_order_from_landing(
    data: OrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Сценарий B: Клиент заказывает проект.

    Создаёт заявку в БД, уведомляет инженера (Celery, best-effort),
    возвращает ссылку на upload-страницу.
    """
    svc = OrderService(db)
    order_data = OrderCreate(
        client_name=data.client_name,
        client_email=data.client_email,
        client_phone=data.client_phone,
        client_organization=data.client_organization,
        object_address=data.object_address,
        object_city=data.object_city,
        order_type=data.order_type,
    )
    order = await svc.create_order(order_data)

    # D4: раньше уведомление шло через синхронную сессию прямо в async-роутере и
    # блокировало event loop. Теперь — best-effort через Celery.
    # Исключения при enqueue глушим: отсутствие уведомления не должно ломать создание заявки.
    try:
        notify_engineer_new_order.delay(
            str(order.id),
            circuits=data.circuits,
            price=data.price,
            order_type=data.order_type,
        )
    except Exception:
        logger.exception(
            "notify_engineer_new_order enqueue failed for order %s; продолжаем без уведомления",
            order.id,
        )

    upload_url = f"{settings.app_base_url}/upload/{order.id}"

    return OrderCreatedResponse(
        order_id=str(order.id),
        upload_url=upload_url,
        message="Заявка создана",
    )


@router.post("/partnership", response_model=SimpleResponse)
async def partnership_request(data: PartnershipRequest):
    """Сценарий C: Запрос на партнёрство.

    Пересылает данные на почту инженера.
    """
    from app.services.email_service import send_partnership_request

    # D4: SMTP вне event loop. Возвращаем success=True при любом исходе
    # (поведение совпадает с прежним — в роутере результат send_partnership_request не проверялся).
    await asyncio.to_thread(
        send_partnership_request,
        contact_name=data.name,
        company=data.company,
        contact_email=data.email,
        contact_phone=data.phone,
    )

    return SimpleResponse(
        success=True,
        message="Заявка на партнёрство отправлена",
    )


@router.post("/kp-request", response_model=SimpleResponse)
async def kp_request(
    organization: str = Form(..., min_length=2, max_length=255),
    responsible_name: str = Form(..., min_length=2, max_length=255),
    phone: str = Form(..., min_length=5, max_length=50),
    email: EmailStr = Form(...),
    tu_file: UploadFile = File(...),
):
    """Сценарий D: Запрос коммерческого предложения.

    Принимает контактные данные и файл ТУ, отправляет письмо инженеру.
    Заявка в БД не создаётся.
    """
    tu_bytes = await tu_file.read(_MAX_TU_SIZE + 1)
    if len(tu_bytes) > _MAX_TU_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой (максимум 20 МБ)")

    tu_filename = tu_file.filename or "tu.pdf"

    # D4: SMTP + attachment до 20 МБ — inline (нельзя гонять через Redis), но out-of-loop.
    ok = await asyncio.to_thread(
        send_kp_request_notification,
        organization=organization,
        responsible_name=responsible_name,
        phone=phone,
        email=email,
        tu_filename=tu_filename,
        tu_bytes=tu_bytes,
    )
    if not ok:
        raise HTTPException(
            status_code=500, detail="Не удалось отправить запрос. Попробуйте позже."
        )

    return SimpleResponse(
        success=True,
        message="Запрос КП принят. Мы свяжемся с вами в ближайшее время.",
    )


# ── Клиентская страница загрузки (публичная) ─────────────────────────────────


@router.get("/orders/{order_id}/upload-page", response_model=UploadPageInfo)
async def get_upload_page_info(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Информация для клиентской страницы загрузки файлов.

    Клиент получает ссылку в письме:
    https://yourdomain.ru/upload/<order_id>
    """
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    files = await svc.get_files_by_order(order_id)

    await svc.fix_legacy_client_document_params(order)

    if order.status in (
        OrderStatus.WAITING_CLIENT_INFO,
        OrderStatus.CLIENT_INFO_RECEIVED,
    ):
        missing = list(CLIENT_DOCUMENT_PARAM_CODES)
    else:
        missing = order.missing_params or []

    # Для custom-заказов отдаём клиенту валидированные parsed_params / survey_data.
    # На невалидных исторических записях accessor вернёт `{}` (+ WARNING в лог) —
    # фронт отобразит пустой опрос вместо падения страницы.
    parsed_params: dict | None = None
    survey_data: dict | None = None
    if order.order_type == OrderType.CUSTOM:
        validated_parsed = get_parsed_params_dict(order)
        if validated_parsed:
            parsed_params = validated_parsed
        if order.survey_data is not None:
            survey_data = get_survey_data_dict(order)

    return UploadPageInfo(
        order_id=order.id,
        client_name=order.client_name,
        order_status=order.status.value,
        order_type=order.order_type.value,
        contract_number=order.contract_number,
        payment_amount=order.payment_amount,
        advance_amount=order.advance_amount,
        company_requisites=_company_requisites_for_response(order),
        missing_params=missing,
        files_uploaded=files,
        parsed_params=parsed_params,
        survey_data=survey_data,
    )


def _company_requisites_for_response(order) -> dict | None:
    """Готовит `company_requisites` для публичных DTO.

    Специальный случай: записи-маркеры вида `{"error": "..."}` пропускаются «как есть»
    (фронт показывает ошибку распознавания). Нормальные реквизиты — проходят через
    Pydantic-валидацию (`extra='ignore'` чистит мусорные ключи).
    """
    raw = order.company_requisites
    if not raw:
        return None
    if isinstance(raw, dict) and raw.get("error"):
        return raw
    validated = get_company_requisites_dict(order)
    return validated or None


@router.post(
    "/orders/{order_id}/upload-tu",
    response_model=FileResponse,
    status_code=201,
)
async def client_upload_tu(
    order_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Публичная загрузка ТУ для новой заявки (страница upload.html).

    Принимает только категорию TU; заявка должна быть в статусе ``new``.
    """
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status != OrderStatus.NEW:
        raise HTTPException(
            status_code=400,
            detail="Загрузка технических условий доступна только для новой заявки",
        )

    try:
        order_file = await svc.upload_file(order_id, FileCategory.TU, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return order_file


@router.post("/orders/{order_id}/submit", response_model=PipelineResponse)
async def client_submit_new_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Публичный запуск парсинга ТУ после загрузки файла (страница upload.html).

    Те же проверки, что у ``POST /pipeline/{id}/start``, без админского ключа.
    """
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status != OrderStatus.NEW:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя запустить обработку: текущий статус {order.status.value}",
        )

    tu_files = await svc.get_files_by_order(order_id, category=FileCategory.TU)
    if not tu_files:
        raise HTTPException(
            status_code=400,
            detail="Сначала загрузите файл технических условий",
        )

    task = start_tu_parsing.delay(str(order_id))

    return PipelineResponse(
        message="Обработка запущена",
        order_id=order_id,
        task_id=task.id,
    )


@router.post("/orders/{order_id}/survey", response_model=SimpleResponse)
async def save_survey(
    order_id: uuid.UUID,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """Публичное сохранение данных опросного листа (только для custom-заказов)."""
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.order_type != OrderType.CUSTOM:
        raise HTTPException(
            status_code=400,
            detail="Опросный лист не требуется для экспресс-заказа",
        )

    if order.status not in _SURVEY_SAVE_ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"Сохранение опроса недоступно в статусе «{order.status.value}»",
        )

    # Валидируем тело запроса через Pydantic — неизвестные ключи молча отбрасываем
    # (`extra='ignore'` в `SurveyData`), но типы и диапазоны проверяем строго.
    # Невалидный запрос → 422 с понятным сообщением для фронта.
    try:
        survey = SurveyData.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Некорректные данные опроса: {exc.errors()}",
        ) from exc

    set_survey_data(order, survey)
    db.add(order)
    await db.commit()

    return SimpleResponse(success=True, message="Опросный лист сохранён")


# ── Страница оплаты (публичная) ───────────────────────────────────────────────


class PaymentMethodRequest(BaseModel):
    payment_method: str = Field(..., pattern="^(bank_transfer|online_card)$")


@router.get("/orders/{order_id}/payment-page", response_model=PaymentPageInfo)
async def get_payment_page_info(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Информация для страницы оплаты клиентом."""
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    all_files = await svc.get_files_by_order(order_id)
    payment_categories = {
        FileCategory.COMPANY_CARD.value,
        FileCategory.CONTRACT.value,
        FileCategory.INVOICE.value,
        FileCategory.FINAL_INVOICE.value,
        FileCategory.RSO_SCAN.value,
        FileCategory.RSO_REMARKS.value,
    }
    payment_files = [f for f in all_files if f.category.value in payment_categories]
    post_project_flags = derive_post_project_flags(
        all_files,
        order.final_paid_at,
        order.status,
    )

    return PaymentPageInfo(
        order_id=order.id,
        client_name=order.client_name,
        client_email=order.client_email,
        object_address=order.object_address,
        order_status=order.status.value,
        order_type=order.order_type.value if order.order_type else None,
        payment_method=order.payment_method.value if order.payment_method else None,
        payment_amount=order.payment_amount,
        advance_amount=order.advance_amount,
        company_requisites=_company_requisites_for_response(order),
        payment_requisites={
            "company_full_name": settings.company_full_name,
            "company_inn": settings.company_inn,
            "company_settlement_account": settings.company_settlement_account,
            "company_bank_name": settings.company_bank_name,
            "company_bik": settings.company_bik,
            "company_corr_account": settings.company_corr_account,
        },
        contract_number=order.contract_number,
        rso_scan_received_at=order.rso_scan_received_at,
        **post_project_flags,
        files_uploaded=payment_files,
    )


@router.post(
    "/orders/{order_id}/upload-company-card",
    response_model=FileResponse,
    status_code=201,
)
async def client_upload_company_card(
    order_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Загрузка карточки предприятия клиентом (страница payment.html).

    Принимает PDF, DOC, DOCX, JPG, PNG. Запускает парсинг реквизитов.
    """
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status != OrderStatus.AWAITING_CONTRACT:
        raise HTTPException(
            status_code=400,
            detail="Загрузка карточки доступна только на этапе оформления договора",
        )

    try:
        order_file = await svc.upload_file(order_id, FileCategory.COMPANY_CARD, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    from app.services.tasks import parse_company_card_task

    parse_company_card_task.delay(str(order_id))

    return order_file


@router.post("/orders/{order_id}/select-payment-method", response_model=SimpleResponse)
async def select_payment_method(
    order_id: uuid.UUID,
    data: PaymentMethodRequest,
    db: AsyncSession = Depends(get_db),
):
    """Клиент выбрал метод оплаты.

    Для bank_transfer: сохраняет метод, запускает генерацию договора и счёта.
    Для online_card: сохраняет метод, создаёт платёж в YooKassa.
    """
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status != OrderStatus.AWAITING_CONTRACT:
        raise HTTPException(
            status_code=400,
            detail="Выбор метода оплаты доступен только на этапе оформления",
        )

    if not order.company_requisites or order.company_requisites.get("error"):
        raise HTTPException(
            status_code=400,
            detail="Сначала загрузите карточку предприятия",
        )

    order.payment_method = PaymentMethod(data.payment_method)
    await db.commit()

    if data.payment_method == "bank_transfer":
        from app.services.tasks import process_company_card_and_send_contract

        process_company_card_and_send_contract.delay(str(order_id))
        return SimpleResponse(
            success=True,
            message="Договор и счёт будут отправлены на email",
        )

    return SimpleResponse(
        success=True,
        message="Онлайн-эквайринг пока не подключён. Мы свяжемся с вами для согласования альтернативного способа оплаты.",
    )


@router.post(
    "/orders/{order_id}/upload-rso-scan",
    response_model=FileResponse,
    status_code=201,
)
async def client_upload_rso_scan(
    order_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Загрузка скана письма с входящим номером РСО."""
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status not in (
        OrderStatus.ADVANCE_PAID,
        OrderStatus.AWAITING_FINAL_PAYMENT,
    ):
        raise HTTPException(
            status_code=400,
            detail="Загрузка скана доступна только после получения проекта",
        )

    try:
        order_file = await svc.upload_file(order_id, FileCategory.RSO_SCAN, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if order.rso_scan_received_at is None:
        order.rso_scan_received_at = datetime.now(timezone.utc)
    if order.status == OrderStatus.ADVANCE_PAID:
        order.status = OrderStatus.AWAITING_FINAL_PAYMENT
    db.add(order)
    await db.commit()

    from app.services.tasks import (
        notify_client_after_rso_scan,
        notify_engineer_rso_scan_received,
    )

    notify_engineer_rso_scan_received.delay(str(order_id))
    notify_client_after_rso_scan.delay(str(order_id))

    return order_file


@router.post(
    "/orders/{order_id}/upload-rso-remarks",
    response_model=FileResponse,
    status_code=201,
)
async def client_upload_rso_remarks(
    order_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Загрузка замечаний РСО после получения проекта."""
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status not in (
        OrderStatus.AWAITING_FINAL_PAYMENT,
        OrderStatus.RSO_REMARKS_RECEIVED,
    ):
        raise HTTPException(
            status_code=400,
            detail="Загрузка замечаний РСО доступна только после отправки проекта",
        )

    has_rso_scan = any(
        existing_file.category == FileCategory.RSO_SCAN for existing_file in (order.files or [])
    )
    if order.rso_scan_received_at is None and not has_rso_scan:
        raise HTTPException(
            status_code=409,
            detail="Сначала загрузите скан сопроводительного письма с входящим номером РСО",
        )

    try:
        order_file = await svc.upload_file(order_id, FileCategory.RSO_REMARKS, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    order.status = OrderStatus.RSO_REMARKS_RECEIVED
    db.add(order)
    await db.commit()

    from app.services.tasks import notify_engineer_rso_remarks_received

    notify_engineer_rso_remarks_received.delay(str(order_id))
    return order_file


@router.post(
    "/orders/{order_id}/upload-signed-contract",
    response_model=FileResponse,
    status_code=201,
)
async def client_upload_signed_contract(
    order_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Публичная загрузка подписанного договора клиентом."""
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status != OrderStatus.CONTRACT_SENT:
        raise HTTPException(
            status_code=400,
            detail="Загрузка подписанного договора доступна только в статусе contract_sent",
        )

    try:
        existing_signed = await svc.get_files_by_order(
            order_id, category=FileCategory.SIGNED_CONTRACT
        )
    except SQLAlchemyError as exc:
        logger.exception(
            "upload-signed-contract: DB error while checking existing file, order=%s: %s",
            order_id,
            exc,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Сервис обновляется: не удалось проверить загрузку подписанного договора. "
                "Повторите попытку через 1-2 минуты."
            ),
        ) from exc
    if existing_signed:
        raise HTTPException(
            status_code=409,
            detail="Подписанный договор уже загружен",
        )

    filename = (file.filename or "").lower()
    has_allowed_extension = any(
        filename.endswith(ext) for ext in _SIGNED_CONTRACT_ALLOWED_EXTENSIONS
    )
    if not has_allowed_extension:
        raise HTTPException(
            status_code=400,
            detail="Разрешены только PDF, JPG и PNG файлы",
        )
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in _SIGNED_CONTRACT_ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Недопустимый MIME-тип файла",
        )

    content = await file.read(_MAX_SIGNED_CONTRACT_SIZE + 1)
    if len(content) > _MAX_SIGNED_CONTRACT_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Файл слишком большой (максимум 25 МБ)",
        )
    await file.seek(0)

    try:
        order_file = await svc.upload_file(order_id, FileCategory.SIGNED_CONTRACT, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SQLAlchemyError as exc:
        logger.exception(
            "upload-signed-contract: DB error while saving file, order=%s: %s",
            order_id,
            exc,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Не удалось сохранить подписанный договор. "
                "Возможно, база данных ещё не обновлена. Повторите попытку позже."
            ),
        ) from exc

    from app.services.tasks import notify_engineer_signed_contract

    try:
        notify_engineer_signed_contract.delay(str(order_id))
    except Exception as exc:  # noqa: BLE001
        # Загрузка не должна падать, если очередь временно недоступна.
        logger.exception(
            "upload-signed-contract: failed to enqueue engineer notification, order=%s: %s",
            order_id,
            exc,
        )
    return order_file
