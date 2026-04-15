"""Эндпоинты для запуска пайплайна и обработки действий клиента."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_admin_key
from app.core.database import get_db
from app.models import OrderStatus, FileCategory, OrderType
from app.schemas import FileResponse, PipelineResponse
from app.services import OrderService
from app.services.param_labels import CLIENT_DOCUMENT_PARAM_CODES
from app.services.tasks import (
    start_tu_parsing,
    process_client_response,
    initiate_payment_flow,
    process_advance_payment,
    process_final_payment,
    notify_engineer_client_documents_received,
)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def get_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(db)


# ── Запуск обработки заявки ──────────────────────────────────────────────────


@router.post("/{order_id}/start", response_model=PipelineResponse)
async def start_pipeline(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_service),
    _key: str = Depends(verify_admin_key),
):
    """Запустить обработку заявки (после загрузки ТУ).

    Вызывается лендингом после того, как клиент:
    1. Заполнил форму → POST /api/v1/orders
    2. Загрузил ТУ → POST /api/v1/orders/{id}/files?category=tu
    3. Нажал «Отправить» → POST /api/v1/pipeline/{id}/start
    """
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status != OrderStatus.NEW:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя запустить пайплайн: текущий статус {order.status.value}",
        )

    # Проверяем, что ТУ загружены
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


# ── Загрузка файлов клиентом (страница upload-page) ─────────────────────────


@router.post("/{order_id}/client-upload", response_model=FileResponse, status_code=201)
async def client_upload_file(
    order_id: uuid.UUID,
    category: FileCategory = Query(..., description="Категория файла"),
    file: UploadFile = File(...),
    svc: OrderService = Depends(get_service),
):
    """Загрузка файла клиентом через страницу upload-page.

    Отличие от /orders/{id}/files: после загрузки проверяет,
    нужно ли ещё что-то, и обновляет стейт-машину.
    """
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status != OrderStatus.WAITING_CLIENT_INFO:
        raise HTTPException(
            status_code=400,
            detail="Заявка не ожидает загрузки файлов от клиента",
        )

    order_file = await svc.upload_file(order_id, category, file)
    return order_file


@router.post("/{order_id}/client-upload-done", response_model=PipelineResponse)
async def client_upload_done(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_service),
):
    """Клиент завершил загрузку файлов.

    Кнопка «Готово» на странице upload-page.
    Запускает проверку полноты данных.
    """
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status != OrderStatus.WAITING_CLIENT_INFO:
        raise HTTPException(
            status_code=400,
            detail="Заявка не ожидает данных от клиента",
        )

    # Переводим в промежуточный статус
    order.status = OrderStatus.CLIENT_INFO_RECEIVED
    db = svc.db
    await db.commit()

    task = process_client_response.delay(str(order_id))

    # Уведомляем инженера о полученных документах.
    # Экспресс: уведомляем при любых загруженных файлах.
    # Custom: только если загружены документы из обязательного списка
    #   (BALANCE_ACT, CONNECTION_PLAN, heat_point_plan, heat_scheme);
    #   если загружены только ТУ — инженер не получает письмо и сам
    #   инициирует запрос с образцами.
    all_files = await svc.get_files_by_order(order_id)
    uploaded_categories = {f.category.value for f in all_files}
    if order.order_type == OrderType.EXPRESS:
        should_notify = len(uploaded_categories) > 0
    else:
        should_notify = any(c in uploaded_categories for c in CLIENT_DOCUMENT_PARAM_CODES)
    if should_notify:
        notify_engineer_client_documents_received.delay(str(order_id))

    return PipelineResponse(
        message="Файлы приняты, идёт проверка",
        order_id=order_id,
        task_id=task.id,
    )


# ── Одобрение проекта инженером ──────────────────────────────────────────────


@router.post("/{order_id}/approve", response_model=PipelineResponse)
async def approve_project(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_service),
    _key: str = Depends(verify_admin_key),
):
    """Инженер одобрил проект — запуск оплаты (уведомление клиенту, статус awaiting_contract).

    Доступно на любом статусе, кроме new, tu_parsing и completed.
    Требуется загруженный PDF проекта (generated_project) для последующей отправки после аванса.
    """
    _APPROVE_BLOCKED = {OrderStatus.NEW, OrderStatus.TU_PARSING, OrderStatus.COMPLETED}

    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status in _APPROVE_BLOCKED:
        raise HTTPException(
            status_code=400,
            detail=f"Одобрение недоступно в статусе «{order.status.value}»",
        )

    project_files = await svc.get_files_by_order(
        order_id, category=FileCategory.GENERATED_PROJECT
    )
    if not project_files:
        raise HTTPException(
            status_code=422,
            detail=(
                "Невозможно отправить проект клиенту: файл проекта не загружен. "
                "Загрузите PDF через «Прикрепить файл» (категория «Готовый проект») и повторите."
            ),
        )

    task = initiate_payment_flow.delay(str(order_id))

    return PipelineResponse(
        message="Проект одобрен, клиенту отправлено уведомление об оплате",
        order_id=order_id,
        task_id=task.id,
    )


@router.post("/{order_id}/confirm-advance", response_model=PipelineResponse)
async def confirm_advance_payment(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_service),
    _key: str = Depends(verify_admin_key),
):
    """Инженер подтверждает получение аванса (безналичная оплата).

    Доступно только в статусе contract_sent.
    Запускает process_advance_payment — отправка проекта клиенту.
    """
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status != OrderStatus.CONTRACT_SENT:
        raise HTTPException(
            status_code=400,
            detail=f"Подтверждение аванса недоступно в статусе «{order.status.value}»",
        )

    task = process_advance_payment.delay(str(order_id))

    return PipelineResponse(
        message="Аванс подтверждён, проект отправляется клиенту",
        order_id=order_id,
        task_id=task.id,
    )


@router.post("/{order_id}/confirm-final", response_model=PipelineResponse)
async def confirm_final_payment(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_service),
    _key: str = Depends(verify_admin_key),
):
    """Инженер подтверждает получение остатка оплаты.

    Доступно только в статусе awaiting_final_payment.
    Переводит заявку в completed.
    """
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status != OrderStatus.AWAITING_FINAL_PAYMENT:
        raise HTTPException(
            status_code=400,
            detail=f"Подтверждение остатка недоступно в статусе «{order.status.value}»",
        )

    task = process_final_payment.delay(str(order_id))

    return PipelineResponse(
        message="Оплата подтверждена, заявка завершается",
        order_id=order_id,
        task_id=task.id,
    )
