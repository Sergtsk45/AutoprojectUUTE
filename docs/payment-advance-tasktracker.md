# Фича: Единая авансовая модель оплаты 50/50

> После ревью инженера клиент получает уведомление «Проект готов», загружает карточку предприятия, получает договор и счёт на аванс 50%. После оплаты аванса — проект отправляется клиенту. После согласования в РСО (скан с входящим номером) или оплаты остатка 50% — заявка завершена.

---

## Архитектура: расширение стейт-машины

### Текущая финальная часть
```
review → completed
```

### Новая финальная часть
```
review → awaiting_contract → contract_sent → advance_paid → awaiting_final_payment → completed
```

### Описание новых статусов

| Статус | Что происходит | Кто действует |
|--------|---------------|---------------|
| `awaiting_contract` | Инженер одобрил. Клиенту ушло письмо «Проект готов, загрузите реквизиты» | Клиент |
| `contract_sent` | Реквизиты распарсены. Договор + счёт на 50% отправлены | Клиент |
| `advance_paid` | Аванс получен. Проект + сопроводительное в РСО отправлены | Клиент (сдаёт в РСО) |
| `awaiting_final_payment` | Ожидание скана РСО или оплаты оставшихся 50% | Клиент / Инженер |

---

## Задача 1: Модель данных — статусы, enum'ы, поля оплаты в Order
- **Статус**: В работе
- **Приоритет**: Критический (блокирует все остальные задачи)
- **Описание**: 4 новых значения `OrderStatus`, новый enum `PaymentMethod`, 4 значения `FileCategory`, 5 значений `EmailType`, 7 полей оплаты в модели `Order`, обновление `ALLOWED_TRANSITIONS`, расширение Pydantic-схем. Миграция Alembic.
- **Шаги выполнения**:
  - [x] В `OrderStatus` добавить `AWAITING_CONTRACT`, `CONTRACT_SENT`, `ADVANCE_PAID`, `AWAITING_FINAL_PAYMENT` (между `REVIEW` и `COMPLETED`)
  - [x] Создать enum `PaymentMethod` (`bank_transfer`, `online_card`) с `values_callable=_enum_db_values`
  - [x] В `FileCategory` добавить `COMPANY_CARD`, `CONTRACT`, `INVOICE`, `RSO_SCAN`
  - [x] В `EmailType` добавить `PROJECT_READY_PAYMENT`, `CONTRACT_DELIVERY`, `ADVANCE_RECEIVED`, `FINAL_PAYMENT_REQUEST`, `FINAL_PAYMENT_RECEIVED`
  - [x] В модель `Order` добавить 7 полей: `payment_method`, `payment_amount`, `advance_amount`, `advance_paid_at`, `final_paid_at`, `company_requisites` (JSONB), `contract_number`
  - [x] Обновить `ALLOWED_TRANSITIONS`: `review → awaiting_contract`, далее по цепочке; каждый новый статус → `COMPLETED` (override) и `ERROR`
  - [x] В `__init__.py` добавить `PaymentMethod` в экспорт
  - [x] В `OrderResponse` и `OrderListItem` добавить поля оплаты
  - [ ] Миграция Alembic: `ALTER TYPE ADD VALUE` для существующих enum, `CREATE TYPE` для `payment_method`, `add_column` для 7 полей
  - [x] В `.env.example` добавить переменные `COMPANY_*` (реквизиты) и `YOOKASSA_*` (заглушки) — сделано в задаче 3
- **Файлы**: `backend/app/models/models.py`, `backend/app/models/__init__.py`, `backend/app/schemas/schemas.py`, `backend/app/core/config.py`, `backend/.env.example`, миграция Alembic
- **Зависимости**: нет — это фундамент

---

## Задача 2: Парсинг карточки предприятия (LLM)
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: Pydantic-модель `CompanyRequisites` (15 полей: ИНН, КПП, ОГРН, р/с, БИК и т.д.), LLM-промпт для извлечения реквизитов из PDF/изображения, пост-валидация длин (ИНН 10/12, БИК 9, счета 20), Celery-задача `parse_company_card_task`.
- **Шаги выполнения**:
  - [x] Создать `backend/app/services/company_parser.py`
  - [x] Модель `CompanyRequisites` (full_name, inn, kpp, ogrn, legal_address, bank_name, bik, corr_account, settlement_account, director_name, director_position, phone, email, parse_confidence, warnings)
  - [x] `COMPANY_EXTRACTION_PROMPT` — системный промпт для LLM (роль бухгалтера, JSON-формат)
  - [x] `parse_company_card(file_path)` — определение типа файла (PDF текст / скан / изображение), вызов LLM, Pydantic-валидация
  - [x] `_extract_with_llm(text=..., page_images_b64=...)` — по аналогии с `tu_parser.extract_params_with_llm`
  - [x] `_validate_requisites(r)` — проверка длин ИНН, КПП, БИК, счетов; нормализация (только цифры)
  - [x] Импорт `extract_text_from_pdf`, `render_pdf_pages_to_base64` из `tu_parser` (не дублировать)
  - [x] В `tasks.py` добавить `parse_company_card_task` — находит файл `COMPANY_CARD`, вызывает парсер, сохраняет результат в `order.company_requisites`
- **Файлы**: новый `backend/app/services/company_parser.py`, `backend/app/services/tasks.py`
- **Зависимости**: Задача 1 (FileCategory.COMPANY_CARD)

---

## Задача 3: Генерация договора и счёта (DOCX)
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: Генератор DOCX через `python-docx` (уже в зависимостях) для договора на проектирование УУТЭ с условием оплаты 50/50 и счёта на аванс. Реквизиты исполнителя из `settings.company_*`, заказчика из `order.company_requisites`.
- **Шаги выполнения**:
  - [x] В `config.py` → `Settings` добавить 10 полей `company_*` (full_name, inn, ogrn, address, bank_name, bik, corr_account, settlement_account, director_name, director_position)
  - [x] Создать `backend/app/services/contract_generator.py`
  - [x] `generate_contract_number(order_id)` → формат `UUTE-YYYYMMDD-xxxx`
  - [x] `generate_contract(order_id_short, contract_number, object_address, payment_amount, advance_amount, client_requisites)` → Path к DOCX (предмет, стоимость, условия 50/50, сроки, реквизиты сторон, подписи)
  - [x] `generate_invoice(order_id_short, contract_number, object_address, payment_amount, advance_amount, client_requisites, is_advance)` → Path к DOCX (счёт на аванс или остаток)
  - [x] Обе функции возвращают Path к временному файлу (tempfile), как в `cover_letter.py`
- **Файлы**: новый `backend/app/services/contract_generator.py`, `backend/app/core/config.py`
- **Зависимости**: Задача 1 (поля payment_amount, advance_amount, contract_number)

---

## Задача 4: Страница оплаты (payment.html) + публичные API
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: Публичная HTML-страница `/payment/{order_id}` (аналог `upload.html`, ванильный JS). 7 экранов по статусу: загрузка карточки → парсинг (polling) → подтверждение реквизитов + выбор метода → договор отправлен → аванс получен + загрузка скана РСО → ожидание остатка → завершено. 4 публичных API-эндпоинта в `landing.py`.
- **Шаги выполнения**:
  - [x] В `main.py` добавить роут `GET /payment/{order_id}` → `FileResponse(payment.html)` (перед catch-all SPA)
  - [x] В `schemas.py` создать `PaymentPageInfo` (поля: order_id, client_name, client_email, object_address, order_status, order_type, payment_method, payment_amount, advance_amount, company_requisites, contract_number, files_uploaded — без отдельных requisites_ready/requisites_error, готовность по `company_requisites`)
  - [x] `GET /landing/orders/{id}/payment-page` → `PaymentPageInfo` (публичный)
  - [x] `POST /landing/orders/{id}/upload-company-card` → загрузка файла + запуск `parse_company_card_task.delay()` (статус: `awaiting_contract`)
  - [x] `POST /landing/orders/{id}/select-payment-method` → сохранение метода, для `bank_transfer` запуск `process_company_card_and_send_contract.delay()`, для `online_card` заглушка (ответ 200, без YooKassa)
  - [x] `POST /landing/orders/{id}/upload-rso-scan` → загрузка скана + `notify_engineer_rso_scan_received.delay()` (статусы: `advance_paid`, `awaiting_final_payment`)
  - [x] Создать `backend/static/payment.html`: экраны по статусам, drag-and-drop + XHR с прогрессом, polling парсинга и смены статуса, таблица реквизитов, выбор метода оплаты, загрузка скана РСО, лимит 25 МБ
  - [x] CSS: базовые стили по образцу `upload.html` + блоки оплаты, `.requisites-table`, `.spinner`
- **Файлы**: новый `backend/static/payment.html`, `backend/app/api/landing.py`, `backend/app/main.py`, `backend/app/schemas/schemas.py`
- **Зависимости**: Задача 1 (статусы, enum'ы), Задача 2 (parse_company_card_task)

---

## Задача 5: Интеграция YooKassa (онлайн-оплата)
- **Статус**: Не начата
- **Приоритет**: Средний (безнал работает без неё)
- **Описание**: SDK `yookassa`, создание платежа (аванс и остаток), webhook `/api/v1/webhooks/yookassa` для автоматического подтверждения. После успешного аванса — `advance_paid`, после остатка — `completed`.
- **Шаги выполнения**:
  - [ ] В `config.py` добавить `yookassa_shop_id`, `yookassa_secret_key`
  - [ ] В `requirements.txt` добавить `yookassa==3.4.0`
  - [ ] Создать `backend/app/services/payment_service.py`: `create_payment(order_id, amount, description, return_url)`, `verify_payment(payment_id)`
  - [ ] Создать `backend/app/api/webhooks.py`: `POST /webhooks/yookassa` — валидация события, извлечение order_id из metadata, определение тип оплаты по статусу заявки, запуск соответствующей Celery-задачи
  - [ ] Подключить роутер в `main.py`
  - [ ] В `payment.html` активировать кнопку «Оплата картой» (убрать disabled/заглушку)
  - [ ] В `landing.py` → `select-payment-method` для `online_card`: создание платежа, возврат `confirmation_url`
- **Файлы**: новый `backend/app/services/payment_service.py`, новый `backend/app/api/webhooks.py`, `backend/app/main.py`, `backend/requirements.txt`
- **Зависимости**: Задача 1, Задача 4

---

## Задача 6: Email-шаблоны (5 новых писем)
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: 5 Jinja2-шаблонов (наследуют `base.html`), 5 render-функций и 5 send-функций в `email_service.py`. Стиль: `.list-block`, `.btn-center`, `.note` — как в существующих шаблонах.
- **Шаги выполнения**:
  - [x] `project_ready_payment.html` — «Проект готов, загрузите реквизиты» (кнопка → `/payment/{id}`, суммы, условия)
  - [x] `contract_delivery.html` — «Договор и счёт на аванс» (номер договора, сумма, реквизиты для оплаты из `settings.company_*`, вложения)
  - [x] `advance_received.html` — «Аванс получен, вот проект» (состав проекта, инструкция по РСО, просьба прислать скан или оплатить остаток, вложения)
  - [x] `final_payment_request.html` — «Напоминание: остаток оплаты» (сумма, договор, кнопка)
  - [x] `final_payment_received.html` — «Оплата завершена, спасибо» (итого, кнопка на сайт)
  - [x] В `email_service.py`: 5 пар `render_*` + `send_*` по паттерну существующих (render → tuple[str, str, list[str]], send → bool + `_log_email`)
  - [x] `render_contract_delivery` и `render_advance_received` принимают `attachment_paths`
  - [x] Все `payment_url` = `settings.app_base_url + "/payment/" + str(order.id)`
- **Файлы**: 5 новых HTML в `backend/templates/emails/`, `backend/app/services/email_service.py`
- **Зависимости**: Задача 1 (EmailType)

---

## Задача 7: Celery-задачи оркестрации оплаты
- **Статус**: В работе
- **Приоритет**: Высокий
- **Описание**: 4 Celery-задачи — полный пайплайн от «инженер одобрил» до «оплата завершена». Переиспользует логику сборки вложений из `send_completed_project` (PDF проекта + сопроводительное в РСО). Вспомогательная функция `_resolve_price` для определения суммы заявки.
- **Шаги выполнения**:
  - [ ] `initiate_payment_flow`: `REVIEW → AWAITING_CONTRACT` — расчёт `payment_amount` / `advance_amount`, генерация `contract_number`, отправка `send_project_ready_payment`
  - [ ] `_resolve_price(order)` — определение цены (из `order.payment_amount` или дефолт 22500)
  - [x] `process_company_card_and_send_contract`: `AWAITING_CONTRACT → CONTRACT_SENT` — генерация DOCX договора и счёта, сохранение как `OrderFile` (CONTRACT, INVOICE), отправка `send_contract_delivery_to_client` с вложениями, удаление временных файлов (триггер с `payment.html` / `select-payment-method`, не с approve)
  - [ ] `send_project_after_advance`: `CONTRACT_SENT → ADVANCE_PAID → AWAITING_FINAL_PAYMENT` — фиксация `advance_paid_at`, сборка PDF проекта + сопроводительного (как `send_completed_project`), отправка `send_advance_received` с вложениями
  - [ ] `process_final_payment`: `AWAITING_FINAL_PAYMENT → COMPLETED` — фиксация `final_paid_at`, отправка `send_final_payment_received`
  - [ ] `send_completed_project` НЕ менять — остаётся для ручного override инженером
  - [ ] Все задачи: `bind=True`, `max_retries=2`, проверка текущего статуса (идемпотентность), lazy-импорты
- **Файлы**: `backend/app/services/tasks.py`
- **Зависимости**: Задачи 2 (парсер), 3 (генератор DOCX), 6 (email)

---

## Задача 8: Переработка approve + управление оплатой в админке
- **Статус**: Не начата
- **Приоритет**: Высокий
- **Описание**: Кнопка «Одобрить» вызывает `initiate_payment_flow` вместо `send_completed_project`. Два новых эндпоинта: `confirm-advance` и `confirm-final`. В `admin.html`: 4 новых статуса в степпере, карточка «Оплата» с реквизитами и кнопками подтверждения.
- **Шаги выполнения**:
  - [ ] В `pipeline.py` → `approve_project`: заменить `send_completed_project.delay()` на `initiate_payment_flow.delay()`
  - [ ] Новый `POST /pipeline/{id}/confirm-advance` (admin key) — для безнала инженер подтверждает аванс → `send_project_after_advance.delay()`
  - [ ] Новый `POST /pipeline/{id}/confirm-final` (admin key) — инженер подтверждает остаток → `process_final_payment.delay()`
  - [ ] В `admin.html` → `STATUS_LABELS` и `STATUS_COLORS`: добавить 4 новых статуса
  - [ ] В `admin.html` → `STATUS_ORDER`: вставить 4 статуса между `review` и `completed`
  - [ ] В `admin.html` → `renderOrder()`: карточка `paymentCard` — метод оплаты, суммы, даты, реквизиты клиента, ссылка на `/payment/{id}`
  - [ ] Кнопки по статусам: `contract_sent` → «Аванс получен», `awaiting_final_payment` → «Остаток получен»
  - [ ] Блокировка кнопок на время запроса (как `approveProject`)
- **Файлы**: `backend/app/api/pipeline.py`, `backend/static/admin.html`
- **Зависимости**: Задача 7 (Celery-задачи)

---

## Задача 9: Авто-напоминания об оплате (Celery Beat)
- **Статус**: Не начата
- **Приоритет**: Низкий
- **Описание**: Периодическая задача `send_payment_reminders` — ежедневно 10:00 МСК. Напоминание для `contract_sent` (> 5 дней) и `awaiting_final_payment` (> 7 дней). Максимум 3 напоминания, не чаще 1 раза в 7 дней. Идемпотентность через `email_log`.
- **Шаги выполнения**:
  - [ ] Новая задача `send_payment_reminders()` в `tasks.py`
  - [ ] Поиск заявок `contract_sent` где с момента отправки договора > 5 дней
  - [ ] Поиск заявок `awaiting_final_payment` где с момента отправки проекта > 7 дней
  - [ ] Отправка `send_final_payment_request` (если ещё не отправляли или прошло > 7 дней с последнего)
  - [ ] Ограничение: максимум 3 `FINAL_PAYMENT_REQUEST` на заявку
  - [ ] В `celery_app.py` → `beat_schedule` добавить `send-payment-reminders` (crontab hour=10, minute=0)
- **Файлы**: `backend/app/services/tasks.py`, `backend/app/core/celery_app.py`
- **Зависимости**: Задачи 1, 6, 7

---

## Задача 10: Обновить лендинг — единые цены, упоминание аванса
- **Статус**: Не начата
- **Приоритет**: Средний
- **Описание**: Убрать скидку 50% для экспресса. Обе карточки показывают одну цену. Добавить упоминание «Оплата: аванс 50% + 50% после согласования в РСО». Экспресс доступен для 1–3 контуров.
- **Шаги выполнения**:
  - [ ] `CalculatorSection.tsx`: убрать `discountPrice`, зачёркнутую цену, бейдж «Популярный выбор»
  - [ ] Обе карточки показывают `price` (одинаковая цена)
  - [ ] Под ценой: «Оплата: 50% аванс + 50% после согласования в РСО»
  - [ ] Убрать ограничение `circuits === 1` для экспресса
  - [ ] `EmailModal.tsx`: в success-экране добавить «После проверки проекта вам будет отправлен договор с условиями оплаты»
  - [ ] `npm run build` + `docker restart uute-backend`
- **Файлы**: `frontend/src/components/CalculatorSection.tsx`, `frontend/src/components/EmailModal.tsx`
- **Зависимости**: Задача 1

---

## Задача 11: Обновить changelog и документацию
- **Статус**: В работе
- **Приоритет**: Низкий
- **Описание**: Зафиксировать изменения.
- **Шаги выполнения**:
  - [x] Запись в `docs/changelog.md` (страница оплаты / API — 2026-04-15)
  - [x] Обновить `docs/tasktracker.md` — задача «Публичная страница оплаты /payment/{id}»
  - [ ] Обновить `docs/project.md` — новые статусы, стейт-машина, страница `/payment`, реквизиты
  - [ ] Обновить `CLAUDE.md` — новые переменные `.env`, роуты, модели
- **Файлы**: `docs/changelog.md`, `docs/tasktracker.md`, `docs/project.md`, `CLAUDE.md`
- **Зависимости**: Задачи 1–10

---

## Новые переменные .env

```
# Реквизиты компании (для генерации договора и счёта)
COMPANY_FULL_NAME=ИП Иванов Иван Иванович
COMPANY_INN=
COMPANY_OGRN=
COMPANY_ADDRESS=
COMPANY_BANK_NAME=
COMPANY_BIK=
COMPANY_CORR_ACCOUNT=
COMPANY_SETTLEMENT_ACCOUNT=
COMPANY_DIRECTOR_NAME=
COMPANY_DIRECTOR_POSITION=Индивидуальный предприниматель

# YooKassa (заполнить при реализации задачи 5)
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
```

---

## Порядок выполнения

```
Задача 1  (модель данных)       ████████░░░░░░░░░░░░  блокирует всё
Задача 2  (парсинг карточки)    ░░░░░░░░████░░░░░░░░  параллельно с 3, 4, 6
Задача 3  (договор DOCX)        ░░░░░░░░████░░░░░░░░  параллельно с 2, 4, 6
Задача 4  (payment.html + API)  ████████████████████  завершена
Задача 6  (email-шаблоны)       ░░░░░░░░████░░░░░░░░  параллельно с 2, 3, 4
Задача 7  (Celery оркестрация)  ░░░░░░░░████░░░░░░░░  после 2, 3, 6 (частично)
Задача 8  (approve + админка)   ░░░░░░░░░░░░░░░░████  после 7
Задача 5  (YooKassa)            ░░░░░░░░░░░░░░░░░░██  можно отложить
Задача 9  (авто-напоминания)    ░░░░░░░░░░░░░░░░░░██  после 7
Задача 10 (лендинг)             ░░░░░░░░░░░░░░░░░░██  после 1
Задача 11 (docs)                ░░░░░░░░░░░░░░░░░░░█  последняя
                                ──────────────────────
                                Оценка: ~4-5 дней
```

**Критический путь**: 1 → {2, 3, 6} → 7 → 8

**MVP без онлайн-оплаты**: задачи 1–4, 6–8 (безнал работает, YooKassa добавляется позже)
