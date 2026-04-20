# Plan: Финальный платёж и замечания РСО

**Created:** 2026-04-16
**Orchestration:** orch-2026-04-16-13-20-final-payment-rso
**Status:** 🟢 Ready
**Priority:** High

## Goal
Исправить post-delivery flow после отправки готового проекта: клиент должен по одной публичной ссылке либо оплатить остаток, либо загрузить скан сопроводительного письма, затем при необходимости загрузить замечания РСО, а система должна корректно напоминать об оплате через 15 дней и позволять инженеру повторно отправлять исправленный проект с тем же счётом на остаток.

## Recommendation
Рекомендуемый вариант: **не вводить новые `OrderStatus`**, оставить основной статус `awaiting_final_payment`, но расширить модель предметными артефактами и флагами:
- новая категория файла `RSO_REMARKS` для замечаний РСО;
- новая категория файла `FINAL_INVOICE` для сохранения счёта на остаток, чтобы повторно отправлять именно тот же документ;
- одно лёгкое поле-якорь времени `orders.rso_scan_received_at` для reminder через 15 дней;
- вычисляемые флаги/API-поля для UI: `has_rso_scan`, `has_rso_remarks`, `awaiting_rso_feedback`, `final_invoice_available`.

Это минимально достаточный вариант: стейт-машина не разрастается, а UX, напоминания и повторная отправка исправленного проекта становятся явными и воспроизводимыми.

## Architectural Options

### Option A: Новые статусы согласования
- Пример: `awaiting_rso_feedback`, `rso_remarks_received`.
- Плюсы: очень явная стейт-машина, проще читать статус в админке.
- Минусы: больше миграций (`order_status`), больше переходов, больше регрессионных рисков в `payment.html`, `admin.html`, `pipeline.py`, старых заявках и legacy-ветке.
- Вердикт: избыточно для текущего MVP.

### Option B: Сохранить `awaiting_final_payment` + добавить file categories и флаги
- Плюсы: минимальный объём изменений, не ломает текущий approve/payment flow, хорошо ложится на существующие `OrderFile`, `EmailLog`, `payment-page`.
- Минусы: часть подстадий будет отображаться как derived state, а не как отдельный status.
- Вердикт: **лучший вариант**.

### Option C: Вообще без новых полей, всё вычислять из `order_files` и `email_log`
- Плюсы: минимальная миграция.
- Минусы: хрупкие beat-запросы, сложнее повторная отправка "того же счёта", UI начинает дублировать бизнес-логику, audit trail хуже.
- Вердикт: допустимо только как временный hotfix, не рекомендовано.

## Scope And Files

### Core backend
- `backend/app/models/models.py`
- `backend/alembic/versions/YYYYMMDD_uute_final_payment_rso_feedback.py`
- `backend/app/schemas/schemas.py`
- `backend/app/api/landing.py`
- `backend/app/api/pipeline.py`
- `backend/app/services/tasks.py`
- `backend/app/services/email_service.py`
- `backend/app/core/celery_app.py`

### Templates and static UI
- `backend/templates/emails/project_delivery.html`
- `backend/templates/emails/final_payment_request.html`
- `backend/static/payment.html`
- `backend/static/admin.html`

### Docs
- `docs/project.md`
- `docs/changelog.md`
- `docs/tasktracker.md`

## Data Model Decisions

### Keep existing statuses
- Без новых `OrderStatus`.
- `advance_paid -> awaiting_final_payment -> completed` остаётся как есть.

### Add file categories
- `RSO_REMARKS`: файл с замечаниями РСО от клиента.
- `FINAL_INVOICE`: счёт на остаток, сохранённый в `OrderFile` для повторной отправки без регенерации "другого" документа.

### Add one order timestamp
- `rso_scan_received_at`: UTC-время первой/последней загрузки скана сопроводительного в РСО.

### Add response-level flags
- `has_rso_scan`
- `has_rso_remarks`
- `awaiting_rso_feedback`
- `final_invoice_available`

Флаги вычисляются в API по `OrderFile` и `Order.final_paid_at`; отдельные bool-колонки в БД не нужны.

## Target User Flow
1. `send_completed_project` отправляет проект, сопроводительное и **сохранённый** счёт на остаток, затем переводит `advance_paid -> awaiting_final_payment`.
2. На `payment.html` клиент сразу видит два сценария: `оплатить по счёту` или `загрузить скан сопроводительного`.
3. После `upload-rso-scan` страница явно подтверждает приём файла и переключается в режим "ожидаем оплату или замечания РСО".
4. Если клиент загружает замечания РСО, они сохраняются как `RSO_REMARKS`, инженер получает уведомление.
5. Инженер исправляет проект и повторно отправляет комплект: новый PDF проекта + обновлённое сопроводительное + **тот же** `FINAL_INVOICE`.
6. Через 15 дней после `rso_scan_received_at`, если остаток не подтверждён, уходит повторное письмо на оплату.
7. `confirm-final` остаётся финальной точкой закрытия заявки.

## Tasks Overview

### PAY-001: Модель данных и миграция
- **Priority:** Critical
- **Complexity:** Moderate
- **Dependencies:** None
- **Files:** `backend/app/models/models.py`, `backend/alembic/versions/...`
- **Work:**
  - Добавить `FileCategory.RSO_REMARKS`.
  - Добавить `FileCategory.FINAL_INVOICE`.
  - Добавить `Order.rso_scan_received_at`.
  - Обновить docstring/комментарии `OrderStatus.awaiting_final_payment`.
- **Acceptance criteria:**
  - Миграция создаёт новые значения enum `file_category`.
  - Миграция добавляет колонку `rso_scan_received_at`.
  - Нет изменений `order_status`, значит не трогаем `ALLOWED_TRANSITIONS`.

### PAY-002: Публичные API и схема payment page
- **Priority:** High
- **Complexity:** Moderate
- **Dependencies:** PAY-001
- **Files:** `backend/app/schemas/schemas.py`, `backend/app/api/landing.py`
- **Work:**
  - Расширить `PaymentPageInfo` и при необходимости `OrderResponse`.
  - В `GET /landing/orders/{id}/payment-page` отдавать derived flags и наличие `FINAL_INVOICE`.
  - Для `POST /landing/orders/{id}/upload-rso-scan`:
    - записывать `order.rso_scan_received_at`;
    - оставлять статус `awaiting_final_payment`;
    - возвращать тот же `FileResponse`.
  - Добавить `POST /landing/orders/{id}/upload-rso-remarks`.
- **Acceptance criteria:**
  - Клиент может загрузить замечания только в `awaiting_final_payment`.
  - API позволяет UI без дополнительных эвристик понять, что делать дальше.

### PAY-003: Celery и email-логика
- **Priority:** High
- **Complexity:** Complex
- **Dependencies:** PAY-001, PAY-002
- **Files:** `backend/app/services/tasks.py`, `backend/app/services/email_service.py`, `backend/templates/emails/project_delivery.html`, `backend/templates/emails/final_payment_request.html`, `backend/app/core/celery_app.py`
- **Work:**
  - Изменить `send_completed_project`:
    - сохранять счёт на остаток в `OrderFile(FINAL_INVOICE)`, если его ещё нет;
    - при повторной отправке брать последний `generated_project` и существующий `FINAL_INVOICE`.
  - Добавить задачу уведомления инженеру о `RSO_REMARKS`.
  - Добавить задачу/ветку повторной отправки исправленного проекта без смены статуса.
  - Добавить beat-задачу напоминания через 15 дней после `rso_scan_received_at`.
  - Скорректировать тексты писем:
    - CTA из письма с проектом ведёт на `payment/{id}`;
    - copy не обещает рабочую онлайн-карту, пока YooKassa не внедрена.
- **Acceptance criteria:**
  - Повторная отправка проекта не создаёт новый счёт на остаток.
  - Напоминание уходит только если есть `rso_scan_received_at` и нет `final_paid_at`.
  - Идемпотентность reminder решается через `EmailLog`.

### PAY-004: Payment page UX
- **Priority:** High
- **Complexity:** Moderate
- **Dependencies:** PAY-002, PAY-003
- **Files:** `backend/static/payment.html`
- **Work:**
  - В экране `awaiting_final_payment` показать два явных сценария:
    - оплатить по счёту;
    - загрузить скан сопроводительного.
  - После загрузки скана явно показывать success-state:
    - файл принят;
    - ожидаем замечания РСО или оплату;
    - появляется отдельный upload-блок для замечаний РСО.
  - Если `has_rso_remarks`, показывать подтверждение, что замечания получены и переданы инженеру.
  - Кнопку оплаты переименовать в формулировку без обещания онлайн-эквайринга, например `Открыть страницу оплаты / реквизитов`.
- **Acceptance criteria:**
  - После `upload-rso-scan` пользователь видит не просто banner, а устойчивый экран подтверждения.
  - Ссылка из письма с проектом открывает понятный экран и не упирается в "заглушку" онлайн-оплаты.

### PAY-005: Admin UI и ручные действия инженера
- **Priority:** High
- **Complexity:** Moderate
- **Dependencies:** PAY-002, PAY-003
- **Files:** `backend/static/admin.html`, `backend/app/api/pipeline.py`
- **Work:**
  - В `admin.html` добавить отображение:
    - `RSO_REMARKS`;
    - `rso_scan_received_at`;
    - derived state "ждём замечания/ждём оплату/замечания получены".
  - Добавить действие инженера `Отправить исправленный проект` для `awaiting_final_payment`, если есть `RSO_REMARKS`.
  - В `pipeline.py` добавить admin endpoint/действие на enqueue повторной отправки исправленного проекта.
- **Acceptance criteria:**
  - Инженер видит, что именно произошло после загрузки скана.
  - Исправленный проект можно отправить, не переводя заявку в другой статус и не ломая `confirm-final`.

### PAY-006: Документация и ручная проверка
- **Priority:** Medium
- **Complexity:** Simple
- **Dependencies:** PAY-001..PAY-005
- **Files:** `docs/project.md`, `docs/changelog.md`, `docs/tasktracker.md`
- **Work:**
  - Обновить архитектурное описание post-delivery flow.
  - Зафиксировать user-visible/API changes.
  - Добавить задачу в tasktracker.
  - Провести smoke-проверку сценариев вручную.
- **Acceptance criteria:**
  - Документация описывает новый post-delivery flow без противоречий.
  - Есть checklist ручной проверки.

## Execution Order
1. PAY-001
2. PAY-002
3. PAY-003
4. PAY-004 and PAY-005
5. PAY-006

PAY-004 и PAY-005 можно делать параллельно после стабилизации API/задач.

## Risks

### Enum migration
- Изменение `file_category` требует аккуратного Alembic-скрипта с `Enum(...).create(..., checkfirst=True)` или `ALTER TYPE ... ADD VALUE`, в зависимости от текущего шаблона миграций.
- Риск: на production БД автогенерация не создаст всё корректно.
- Митигация: вручную прописать upgrade/downgrade strategy и проверить на копии БД.

### YooKassa не внедрена
- Нельзя обещать реальную кнопку "Оплатить картой" в письмах и `payment.html`.
- Митигация: тексты CTA должны вести на страницу оплаты/реквизитов, а не обещать card checkout.

### Повторная отправка исправленного проекта
- Если не сохранять `FINAL_INVOICE`, "тот же счёт" будет трудно гарантировать.
- Митигация: хранить финальный счёт отдельным `OrderFile` и переиспользовать его.

### Смешение оплаты и замечаний в одном статусе
- Риск: UI станет неочевидным.
- Митигация: вынести derived flags в API и не дублировать эвристики в шаблоне.

## Manual Verification Checklist
- Открыть ссылку из `project_delivery` и убедиться, что `payment.html` показывает два сценария.
- Загрузить `rso_scan` и убедиться, что:
  - есть явное подтверждение на странице;
  - в админке видно, что согласование началось;
  - reminder через 15 дней становится кандидатом на отправку.
- Загрузить `RSO_REMARKS` и убедиться, что:
  - инженер получает уведомление;
  - в админке доступна повторная отправка исправленного проекта.
- Повторно отправить проект и убедиться, что клиент получает новый проект и тот же `FINAL_INVOICE`.
- Подтвердить остаток через `confirm-final` и убедиться, что заявка завершается как раньше.

## Plan Status
- [ ] PAY-001: Модель данных и миграция
- [ ] PAY-002: Публичные API и схема payment page
- [ ] PAY-003: Celery и email-логика
- [ ] PAY-004: Payment page UX
- [ ] PAY-005: Admin UI и ручные действия инженера
- [ ] PAY-006: Документация и ручная проверка
