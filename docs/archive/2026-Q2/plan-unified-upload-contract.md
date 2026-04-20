# План: Объединённый запрос документов + реквизитов, договор до проекта

> **Суть изменения:** После парсинга ТУ клиенту одновременно запрашиваются технические документы И карточка предприятия (реквизиты). Реквизиты парсятся, формируется договор + счёт и отправляется клиенту. Клиент подписывает, загружает скан. После оплаты аванса инженер готовит проект (≤3 дня) и отправляет с сопроводительным письмом.

---

## Новая стейт-машина (основной путь)

```
new → tu_parsing → tu_parsed
  → waiting_client_info          ← ВСЕГДА (тех. документы + карточка предприятия)
  → client_info_received         ← парсинг реквизитов → генерация договора → отправка
  → contract_sent                ← ожидание: скан подписанного договора + оплата аванса
  → advance_paid                 ← аванс подтверждён → проект готовится (SLA ≤3 дня)
  → awaiting_final_payment       ← проект отправлен, ожидание остатка / скана РСО
  → completed
```

### Что изменилось по сравнению с текущим потоком

| Этап | Было | Стало |
|------|------|-------|
| После ТУ, если всё есть | `→ data_complete` | `→ waiting_client_info` (всегда, нужна карточка) |
| Запрос документов | Только тех. документы | Тех. документы + карточка предприятия |
| Карточка предприятия | На отдельной странице `/payment/{id}` после approve | На странице `/upload/{id}` вместе с документами |
| Генерация договора | После approve инженером | Сразу после получения карточки от клиента |
| Подписание договора | Не было (оплата без подписания) | Клиент загружает скан подписанного договора |
| Approve инженера | Запускал платёжный флоу | Не нужен для договора (договор идёт автоматически) |
| Оплата аванса | Блокировала отправку проекта | Блокирует отправку проекта (без изменений) |
| `data_complete` → `review` | Основной путь | Выведены из основного потока (совместимость) |
| `awaiting_contract` | Ожидание карточки на `/payment` | Не используется в новом потоке |

### Статусы, выведенные из основного потока

`data_complete`, `generating_project`, `review`, `awaiting_contract` — **остаются в enum** для обратной совместимости со старыми заявками, но новые заявки их не проходят. Переходы в `ALLOWED_TRANSITIONS` для них сохраняются.

---

## Задачи

### Задача 1: Модель данных — FileCategory + ALLOWED_TRANSITIONS
- **Приоритет**: Критический (блокирует всё)
- **Оценка**: 1 час

**Шаги:**
1. В `FileCategory` добавить `SIGNED_CONTRACT = "signed_contract"` — скан подписанного договора
2. В `ALLOWED_TRANSITIONS` добавить:
   - `client_info_received → contract_sent` (новый прямой путь)
   - `contract_sent → advance_paid` (уже есть)
3. В `EmailType` добавить `SIGNED_CONTRACT_NOTIFICATION = "signed_contract_notification"` — уведомление инженеру
4. Миграция Alembic: `ALTER TYPE file_category ADD VALUE 'SIGNED_CONTRACT'`, `ALTER TYPE email_type ADD VALUE 'SIGNED_CONTRACT_NOTIFICATION'`

**Файлы:**
- `backend/app/models/models.py`
- `backend/alembic/versions/` (новая миграция)

---

### Задача 2: param_labels — company_card в обязательных документах
- **Приоритет**: Критический
- **Оценка**: 30 минут

**Шаги:**
1. Добавить `"company_card"` в `CLIENT_DOCUMENT_PARAM_CODES`
2. Добавить запись в `MISSING_PARAM_LABELS`:
   ```python
   "company_card": {
       "label": "Карточка предприятия (реквизиты организации)",
       "hint": "PDF или фото с ИНН, КПП, расчётным счётом, БИК и адресом",
   },
   ```
3. `compute_client_document_missing` автоматически подхватит company_card

**Файлы:**
- `backend/app/services/param_labels.py`

---

### Задача 3: check_data_completeness — всегда переходить в WAITING_CLIENT_INFO
- **Приоритет**: Критический
- **Оценка**: 30 минут

**Суть:** Сейчас если `missing_params` пуст → `DATA_COMPLETE`. Теперь company_card всегда в `missing_params` (из задачи 2), поэтому после ТУ-парсинга заявка ВСЕГДА пойдёт в `WAITING_CLIENT_INFO`. Но добавляем явную страховку: если вдруг `missing_params` пуст (все файлы уже загружены), всё равно идём в `WAITING_CLIENT_INFO`.

**Шаги:**
1. В `check_data_completeness`: после пересчёта missing, принудительно добавлять `company_card` если файл COMPANY_CARD ещё не загружен
2. Всегда переходить в `WAITING_CLIENT_INFO` (убрать ветку `→ DATA_COMPLETE` из этой задачи — прямой путь через data_complete больше не используется для новых заявок)
3. Корректировка: если статус уже `CLIENT_INFO_RECEIVED` (повторный вызов) — не переводить обратно

**Файлы:**
- `backend/app/services/tasks.py` (`check_data_completeness`)

---

### Задача 4: process_client_response — цепочка «парсинг → договор → отправка»
- **Приоритет**: Критический
- **Оценка**: 2-3 часа

**Суть:** После `client-upload-done` вместо повторной проверки полноты данных запускаем:
1. Парсинг карточки предприятия (если загружена)
2. Генерация договора + счёта
3. Отправка email клиенту
4. Переход `CLIENT_INFO_RECEIVED → CONTRACT_SENT`
5. Уведомление инженера о полученных тех. документах

**Шаги:**
1. Рефакторить `process_client_response`:
   - Убрать вызов `check_data_completeness.delay()` в конце
   - Проверить наличие файла `COMPANY_CARD`
   - Если нет → вернуть в `WAITING_CLIENT_INFO` (клиент не загрузил карточку)
   - Если есть → вызвать `process_card_and_contract.delay(order_id)` — новая цепочка
2. Новая Celery-задача `process_card_and_contract(order_id)`:
   - Парсинг карточки (переиспользовать `parse_company_card` из `company_parser.py`)
   - Расчёт сумм (`_resolve_initial_payment_amount`)
   - Генерация `contract_number`
   - Генерация DOCX договора + счёта (переиспользовать `generate_contract`, `generate_invoice`)
   - Сохранение файлов в `UPLOAD_DIR` и создание `OrderFile` записей
   - Отправка email `contract_delivery` клиенту (с ссылкой на `/upload/{id}` для скана)
   - Переход `CLIENT_INFO_RECEIVED → CONTRACT_SENT`
   - Уведомление инженера `notify_engineer_client_documents_received`
3. По сути это объединение логики из текущих `parse_company_card_task` + `process_company_card_and_send_contract` + `initiate_payment_flow` в одну цепочку

**Файлы:**
- `backend/app/services/tasks.py`

---

### Задача 5: info_request email — добавить запрос карточки
- **Приоритет**: Высокий
- **Оценка**: 30 минут

**Шаги:**
1. В шаблоне `info_request.html`: company_card автоматически попадёт в `missing_items` (из задачи 2)
2. Проверить, что текст «Карточка предприятия» выглядит уместно среди тех. документов
3. Опционально: визуально выделить «Карточка предприятия» как отдельный блок в письме (отдельный заголовок или разделитель), чтобы клиент понимал разницу

**Файлы:**
- `backend/templates/emails/info_request.html` (опционально)
- Основная работа уже сделана в задаче 2

---

### Задача 6: contract_delivery email — ссылка на загрузку скана
- **Приоритет**: Высокий
- **Оценка**: 1 час

**Шаги:**
1. В шаблоне `contract_delivery.html`:
   - Убрать текст про «оплатить аванс в течение 5 рабочих дней, проект автоматически отправлен»
   - Добавить блок: «Подпишите договор и загрузите скан подписанного экземпляра»
   - Кнопка: «Загрузить подписанный договор» → `{{ upload_url }}`
   - Текст: «После получения подписанного договора и оплаты аванса проект будет подготовлен в течение 3 рабочих дней»
   - Сохранить блок с реквизитами для оплаты (аванс всё ещё нужен)
2. В `render_contract_delivery`: передавать `upload_url` (`/upload/{order.id}`) в контекст шаблона

**Файлы:**
- `backend/templates/emails/contract_delivery.html`
- `backend/app/services/email_service.py` (`render_contract_delivery`)

---

### Задача 7: upload.html — карточка предприятия + скан подписанного договора
- **Приоритет**: Высокий
- **Оценка**: 3-4 часа

**Суть:** Страница `/upload/{id}` получает два новых экрана:

**A) Статус `waiting_client_info` — добавить company_card в загрузку:**
1. Company_card уже будет в `missing_params` (задача 2)
2. В JS-справочнике `CATEGORY_META` добавить `company_card: { label: '...', hint: '...' }`
3. Валидация: кнопка «Всё загружено» недоступна, если company_card не загружена
4. Визуально: карточка предприятия показывается отдельным блоком под тех. документами

**B) Статус `contract_sent` — загрузка подписанного договора:**
1. Новый экран (аналог экрана `new` для ТУ, но для скана):
   - Заголовок: «Подпишите договор и загрузите скан»
   - Информация: номер договора, сумма, реквизиты для оплаты
   - Drop-zone для загрузки скана подписанного договора
   - Endpoint: `POST /api/v1/landing/orders/{id}/upload-signed-contract`
   - После загрузки: сообщение «Спасибо! Ваш договор принят. Проект будет подготовлен в течение 3 рабочих дней после подтверждения оплаты аванса.»
2. API `GET /landing/orders/{id}/upload-page` расширить:
   - Возвращать `contract_number`, `payment_amount`, `advance_amount`, `company_requisites` когда статус `contract_sent`

**Файлы:**
- `backend/static/upload.html`
- `backend/app/api/landing.py` (`get_upload_page_info`)
- `backend/app/schemas/schemas.py` (`UploadPageInfo` — добавить поля оплаты)

---

### Задача 8: Публичный API — загрузка подписанного скана
- **Приоритет**: Высокий
- **Оценка**: 1 час

**Шаги:**
1. Новый эндпоинт `POST /api/v1/landing/orders/{id}/upload-signed-contract`:
   - Доступен в статусе `contract_sent`
   - Принимает файл (PDF, JPG, PNG), лимит 25 МБ
   - Сохраняет как `FileCategory.SIGNED_CONTRACT`
   - Отправляет уведомление инженеру (email: «Клиент загрузил подписанный договор — заявка №XXX»)
   - Возвращает `FileResponse`
2. Уведомление инженеру: новая функция `send_signed_contract_notification` в `email_service.py` (аналог `notify_engineer_rso_scan_received`)
3. Celery-задача `notify_engineer_signed_contract(order_id)`:
   - HTML-письмо с ссылкой на админку
   - Логирование как `EmailType.SIGNED_CONTRACT_NOTIFICATION`

**Файлы:**
- `backend/app/api/landing.py`
- `backend/app/services/email_service.py`
- `backend/app/services/tasks.py`

---

### Задача 9: Админка — обновление под новый поток
- **Приоритет**: Высокий
- **Оценка**: 2-3 часа

**Шаги:**
1. **Степпер** (`STATUS_ORDER`, `STATUS_LABELS`):
   - Основной поток: `new → tu_parsing → tu_parsed → waiting_client_info → client_info_received → contract_sent → advance_paid → awaiting_final_payment → completed`
   - Убрать `data_complete`, `generating_project`, `review`, `awaiting_contract` из основного степпера (оставить метки для обратной совместимости)
2. **Карточка заявки**:
   - В статусе `contract_sent`: показывать блок «Ожидание подписанного договора»
     - Индикатор: скан загружен / не загружен (проверка файла `SIGNED_CONTRACT`)
     - Индикатор: аванс оплачен / не оплачен
     - Кнопка «Подтвердить аванс» (существующий `confirm-advance`)
   - В статусе `advance_paid`:
     - Текст: «Проект в работе. Срок: 3 рабочих дня»
     - Кнопка «Отправить проект» → `send_completed_project.delay()` → `COMPLETED`
   - Блок с загруженными файлами: показывать `SIGNED_CONTRACT`, `COMPANY_CARD` наравне с тех. документами
3. **Кнопка «Одобрить»** (`approve`):
   - Переназначить: доступна в статусе `advance_paid` (вместо `review`)
   - Действие: `send_completed_project.delay()` — отправка проекта клиенту
   - Проверка: файл `GENERATED_PROJECT` загружен

**Файлы:**
- `backend/static/admin.html`
- `backend/app/api/pipeline.py` (`approve_project` — рефакторинг)

---

### Задача 10: pipeline.py — рефакторинг approve и confirm
- **Приоритет**: Высокий
- **Оценка**: 1-2 часа

**Шаги:**
1. `approve_project`:
   - Доступен в статусе `advance_paid` (инженер готов отправить проект)
   - Проверяет наличие `GENERATED_PROJECT`
   - Вызывает `send_completed_project.delay()` → `COMPLETED`
2. `confirm-advance`:
   - Оставить как есть (из `contract_sent` → `advance_paid`)
   - Задача `process_advance_payment`: убрать автоматическую отправку проекта
   - Только перевод статуса: `CONTRACT_SENT → ADVANCE_PAID` + запись `advance_paid_at`
   - Проект отправляется отдельно через `approve` после подготовки
3. `confirm-final`:
   - Оставить как есть (`awaiting_final_payment → completed`)

**Файлы:**
- `backend/app/api/pipeline.py`
- `backend/app/services/tasks.py` (`process_advance_payment` — упростить)

---

### Задача 11: Документация и changelog
- **Приоритет**: Низкий
- **Оценка**: 1 час

**Шаги:**
1. Обновить `docs/changelog.md` — запись о перестройке пайплайна
2. Обновить `docs/tasktracker.md`
3. Обновить `docs/project.md` — новая стейт-машина
4. Обновить `CLAUDE.md` — описание нового потока

**Файлы:**
- `docs/changelog.md`, `docs/tasktracker.md`, `docs/project.md`, `CLAUDE.md`

---

## Порядок выполнения и зависимости

```
Задача 1  (модель данных)            ████░░░░░░░░░░░░░░░░  блокирует всё
Задача 2  (param_labels)             ░░░░██░░░░░░░░░░░░░░  после 1
Задача 3  (check_data_completeness)  ░░░░██░░░░░░░░░░░░░░  после 2
Задача 4  (process → договор)        ░░░░░░████████░░░░░░  после 1, 2 (основная работа)
Задача 5  (info_request email)       ░░░░░░██░░░░░░░░░░░░  после 2
Задача 6  (contract email)           ░░░░░░██░░░░░░░░░░░░  параллельно с 4
Задача 7  (upload.html)              ░░░░░░░░████████░░░░  после 4, 8
Задача 8  (API signed contract)      ░░░░░░░░████░░░░░░░░  после 1
Задача 9  (admin.html)               ░░░░░░░░░░░░████░░░░  после 4, 10
Задача 10 (pipeline.py рефакторинг)  ░░░░░░░░░░░░██░░░░░░  после 4
Задача 11 (docs)                     ░░░░░░░░░░░░░░░░░░██  последняя
                                     ──────────────────────
                                     Оценка: ~3-4 дня
```

**Критический путь**: 1 → 2 → 4 → 7

---

## Переиспользуемый код (не пишем заново)

| Компонент | Источник | Что берём |
|-----------|----------|-----------|
| Парсинг карточки | `company_parser.py` | `parse_company_card()` — без изменений |
| Генерация DOCX | `contract_generator.py` | `generate_contract()`, `generate_invoice()` — без изменений |
| Нормализация реквизитов | `tasks.py` | `_normalize_client_requisites()` — без изменений |
| Расчёт суммы | `tasks.py` | `_resolve_initial_payment_amount()` — без изменений |
| Email отправка | `email_service.py` | `send_contract_delivery_to_client()` — без изменений |
| Отправка проекта | `tasks.py` | `send_completed_project` — без изменений |
| Сопроводительное письмо | `cover_letter.py` | `generate_cover_letter()` — без изменений |

---

## Обратная совместимость

- Старые заявки в статусах `awaiting_contract`, `data_complete`, `generating_project`, `review` продолжают работать через старые переходы (ALLOWED_TRANSITIONS не удаляются)
- `payment.html` остаётся (для старых заявок, если есть)
- Enum-значения не удаляются из PostgreSQL

---

## Что НЕ меняется

- Создание заявки на лендинге (`POST /landing/order`)
- Загрузка ТУ и парсинг (`upload-tu`, `submit`, `start_tu_parsing`)
- Логика парсинга ТУ (`tu_parser.py`)
- Генерация сопроводительного письма
- Отправка проекта с вложениями
- Финальная оплата и скан РСО (`confirm-final`, `process_final_payment`)
- Автонапоминания (`send_reminders`, Celery Beat)
- YooKassa (не реализовано, план не меняется)
