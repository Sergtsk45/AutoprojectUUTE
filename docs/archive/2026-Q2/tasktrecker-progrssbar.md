# План: отложенный запрос клиенту, одноразовые кнопки, письмо инженеру, прогресс загрузки

> **Статус реализации (2026-04-07): выполнено.** Детали — [`docs/changelog.md`](changelog.md) от 2026-04-07, [`docs/project.md`](project.md) (разделы «Админка», «Письма и Celery»).

> Связанный контекст в коде: `check_data_completeness` + `send_info_request_email` ([`backend/app/services/tasks.py`](../backend/app/services/tasks.py)), `process_due_info_requests` (Beat), `send_reminders`, админка [`backend/static/admin.html`](../backend/static/admin.html), лог писем `EmailLog` / `EmailType` в [`backend/app/models/models.py`](../backend/app/models/models.py).

---

## Эпик A: Запрос клиенту через 24 ч после парсинга ТУ

### A1. Модель данных и миграция (при необходимости)
- [x] Момент готовности к авто-запросу: переход в `waiting_client_info` в `check_data_completeness`; метка UTC — `Order.waiting_client_info_at`.
- [x] Миграция Alembic + поле в API ответа заявки (флаги отправок, не сам таймер).
- [x] Вариант: явное поле `waiting_client_info_at` (UTC).

### A2. Убрать мгновенную отправку, ввести отложенную (Celery)
- [x] В `check_data_completeness`: без немедленного `send_info_request_email.delay`.
- [x] Периодическая задача Beat `process_due_info_requests` (каждые 15 мин): заявки в `WAITING_CLIENT_INFO`, `waiting_client_info_at + 24h` истекло, нет успешного `info_request`.
- [x] В `send_info_request_email`: статус, дубликат по логу, проверка 24 ч; явные записи в лог при пропуске.

### A3. Ручная отправка инженером «до 24 ч»
- [x] Эндпоинт [`emails.py`](../backend/app/api/emails.py); после ручной отправки авто-задача идемпотентна.
- [x] `retry_count` и `EmailLog` как при успешной отправке (существующая логика).

### A4. Согласование с текущим `send_reminders` (Beat)
- [x] Напоминание только при успешном `info_request`, не раньше 3 суток с `sent_at` последнего успешного `info_request`; не более одного успешного `reminder`.
- [x] Обновлены `docs/project.md` и changelog.

---

## Эпик B: Кнопки в админке — одноразовые

### B1. «Отправить запрос клиенту»
- [x] После успешной отправки кнопка `disabled` (флаг `info_request_sent` в `GET /orders/{id}`).
- [x] Источник истины: `email_log` с успешным `info_request` (`sent_at`).

### B2. «Отправить напоминание»
- [x] После одной успешной отправки `reminder` — кнопка неактивна (`reminder_sent`); неактивна, пока не было `info_request`.
- [x] Согласованность с cron: проверка по логу.
- [x] Бэкенд: повтор — **409** с `detail`.

---

## Эпик C: Письмо инженеру после загрузки файлов клиентом

### C1. Триггер
- [x] После `POST .../client-upload-done` + Celery `notify_engineer_client_documents_received`.

### C2. Реализация
- [x] Тип `EmailType.CLIENT_DOCUMENTS_RECEIVED`, шаблон Jinja2, `email_service`, идемпотентность по `EmailLog`.

### C3. Документация и конфиг
- [x] Новых переменных в `config` не требуется; changelog обновлён.

---

## Эпик D: Прогресс-бар загрузки готового проекта (админка)

### D1. UI
- [x] Для `generated_project`: XHR + `upload.onprogress`, элемент `<progress>`.

### D2. UX
- [x] Состояния 0–100 %, ошибка, сброс; кнопка загрузки блокируется на время запроса.

### D3. Проверка
- [ ] Ручная проверка на большом PDF на стенде (выполнить при деплое).

---

## Критерии готовности (acceptance)

- [x] Письмо с запросом документов не сразу после парсинга, а не раньше чем через 24 ч с `waiting_client_info_at` (или ручная отправка раньше).
- [x] Ручная отправка блокирует дубликат авто-задачи.
- [x] Кнопки запроса и напоминания одноразовые; согласованность с периодикой.
- [x] После «Готово» у клиента — письмо инженеру (один раз на заявку по логу).
- [x] Прогресс при загрузке PDF проекта в админке.

---

## Зависимости и риски

- **Celery Beat / timezone:** `enable_utc=True`, расписание в МСК для суточных задач; `waiting_client_info_at` в UTC.
- **Дубли писем:** проверки по `EmailLog` в авто-задаче и в `POST /emails/.../send`.
- **Обратная совместимость:** backfill в миграции для уже висящих в `WAITING_CLIENT_INFO`.
- **Метка enum в PostgreSQL:** в миграции — `CLIENT_DOCUMENTS_RECEIVED` (имя члена Python/SQLAlchemy для `email_type`). При отличии в вашей БД — сверка через `\dT+ email_type` в psql.
