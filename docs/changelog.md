# Changelog

## [2026-04-20] — SVG: схема 2 (зависимая с ГВС) и fix text_label

### Добавлено
- В [`backend/app/services/scheme_svg_renderer.py`](../backend/app/services/scheme_svg_renderer.py): реализация схемы 2 (`render_scheme_02_dep_simple_gwp`) — базовая схема + блок ГВС (двухступенчатый подогреватель с теплообменниками 1-й и 2-й ступени, врезки в подачу/обратку, насос ГВС, расходомер G3, подписи ХВС/ГВС, зона ГВС с пунктирной рамкой).

### Исправлено
- В [`backend/app/services/scheme_svg_elements.py`](../backend/app/services/scheme_svg_elements.py): функция `text_label()` — исправлен return (многострочный литерал требует явных скобок), теперь текстовые подписи корректно генерируются.

### Изменено
- В [`docs/scheme-generator-roadmap.md`](scheme-generator-roadmap.md): схема 2 завершена ✅.

## [2026-04-20] — SVG: рендерер схем УУТЭ — эталонная схема 1

### Добавлено
- Файл [`backend/app/services/scheme_svg_renderer.py`](../backend/app/services/scheme_svg_renderer.py): модуль компоновки полных схем, диспетчер `render_scheme()` и реализация эталонной схемы 1 (`render_scheme_01_dep_simple`) — зависимая без клапана (топология: подача/обратка, задвижки, фильтры, датчики t/P, расходомеры G1/G2, радиатор, УУТЭ с таблицей).

### Изменено
- В [`docs/scheme-generator-roadmap.md`](scheme-generator-roadmap.md): задача 3 в работе, подзадача 3.1 завершена.

## [2026-04-20] — SVG: библиотека условных обозначений и ГОСТ-рамка для схем УУТЭ

### Добавлено
- Файл [`backend/app/services/scheme_svg_elements.py`](../backend/app/services/scheme_svg_elements.py): генераторы SVG-фрагментов (трубопроводы, арматура, датчики, расходомеры, теплообменник, насос, радиатор, тепловычислитель с таблицей, вспомогательные `svg_canvas`, `connection_line`, `dashed_rect`).
- Файл [`backend/app/services/scheme_gost_frame.py`](../backend/app/services/scheme_gost_frame.py): `gost_frame_a3` и `gost_frame_a4` с рамкой по полям и основной надписью.

### Изменено
- В [`docs/project.md`](project.md): кратко описаны новые модули SVG.

## [2026-04-19] — Принципиальные схемы ИТП: Pydantic-конфиг и сервис маппинга

### Добавлено
- Файл [`backend/app/schemas/scheme.py`](../backend/app/schemas/scheme.py): перечисление `SchemeType` (8 типовых конфигураций), `SchemeConfig` с валидацией сочетаний признаков (`model_validator`), `SchemeParams`, модели запроса/ответа для превью SVG и справочника шаблонов для UI.
- Файл [`backend/app/services/scheme_service.py`](../backend/app/services/scheme_service.py): словари `SCHEME_MAP` и `SCHEME_LABELS`, функции `resolve_scheme_type`, `get_available_templates`, `extract_scheme_params_from_parsed` (вложенный формат `TUParsedData` и плоские legacy-ключи).

## [2026-04-19] — Договор DOCX: новый шаблон и компактная вёрстка

### Изменено
- В [`backend/app/services/contract_generator.py`](../backend/app/services/contract_generator.py): текст договора и приложений синхронизирован с шаблоном [`docs/kontrakt_ukute_template (2).md`](kontrakt_ukute_template%20(2).md), включая обновлённые формулировки разделов 4–14 и приложений 1–3.
- В [`backend/app/services/contract_generator.py`](../backend/app/services/contract_generator.py): для договора задан компактный формат документа — базовый шрифт `10 pt`, нулевые интервалы до/после абзацев и минимальный межстрочный интервал, чтобы уменьшить объём DOCX и приблизить вёрстку к образцу.

## [2026-04-19] — Договор DOCX: вставка страниц ТУ и лимит размера

### Добавлено
- В [`backend/app/services/contract_generator.py`](../backend/app/services/contract_generator.py): генерация договора по полному шаблону (разделы 1–15, приложения 1–3); вложение страниц PDF категории `tu` в Приложение №2 как PNG (PyMuPDF); автоматическое снижение DPI (150 → 120 → 100) до укладывания в ~25 МБ; при превышении лимита даже на минимальном DPI — договор без встроенных страниц ТУ и запись ERROR в лог.
- Зависимость `PyMuPDF==1.24.10` в [`backend/requirements.txt`](../backend/requirements.txt).

### Изменено
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): при вызовах `generate_contract` передаются путь к последнему файлу ТУ и поля `parsed_params` (`rso.rso_name`, `document.tu_*`).

## [2026-04-16] — Fix: backfill статуса замечаний РСО для исторических заявок

### Исправлено
- В [`backend/alembic/versions/20260416_uute_rso_remarks_status.py`](../backend/alembic/versions/20260416_uute_rso_remarks_status.py): исходная миграция `RSO_REMARKS_RECEIVED` усилена guard-условием `o.final_paid_at IS NULL`, при этом сохранены `autocommit_block()` для enum PostgreSQL и безопасная хронологическая логика `latest_remarks_at >= latest_project_at`, чтобы backfill не возвращал уже обработанные замечания после более нового `GENERATED_PROJECT`.
- В [`backend/tests/test_rso_status_migration.py`](../backend/tests/test_rso_status_migration.py): усилен регрессионный тест миграции, который теперь фиксирует `autocommit_block()`, `RSO_REMARKS_RECEIVED`, `o.final_paid_at IS NULL` и наличие безопасной хронологии по `latest_remarks_at` / `latest_project_at`.

## [2026-04-16] — Fix: race-condition сворачивания настроечной БД

### Исправлено
- В [`backend/static/admin.html`](../backend/static/admin.html): `loadCalcConfig(orderId)` больше не вызывает `applyCalcConfigDetailsState(orderId)` на poll-обновлениях той же заявки; восстановление open/close состояния теперь происходит только при смене заявки, чтобы асинхронный `fetch` не переоткрывал панель, которую инженер только что закрыл.
- В [`backend/tests/test_admin_post_project_actions.py`](../backend/tests/test_admin_post_project_actions.py): добавлен регрессионный тест на защиту `loadCalcConfig` от принудительного восстановления `details.open` при поллинге той же заявки.

## [2026-04-16] — Fix: действия инженера при замечаниях РСО

### Исправлено
- В [`backend/static/admin.html`](../backend/static/admin.html): post-project действия инженера больше не зависят только от точного статуса `rso_remarks_received`; если у заявки активны derived-флаги замечаний РСО (`has_rso_remarks`), админка по-прежнему показывает кнопки `Отправить исправленный проект` и `Остаток получен`.
- В [`backend/tests/test_admin_post_project_actions.py`](../backend/tests/test_admin_post_project_actions.py): добавлен регрессионный тест на fallback показа действий инженера по derived-флагу замечаний РСО.

## [2026-04-16] — Fix: UX настроечной БД в админке

### Изменено
- В [`backend/static/admin.html`](../backend/static/admin.html): блок «Настроечная БД вычислителя» теперь остаётся свёрнутым при первом открытии конкретной заявки и сохраняет ручное раскрытие/сворачивание инженера для этой заявки в рамках текущей сессии админки.
- В [`backend/static/admin.html`](../backend/static/admin.html): после успешного сохранения настроечной БД кнопка `Сохранить` принудительно возвращается в disabled-состояние и снова активируется только после следующего изменения полей.
- В [`docs/project.md`](project.md): уточнено фактическое поведение карточки настроечной БД в админке.

## [2026-04-16] — Fix: письмо инженеру после загрузки и парсинга ТУ

### Добавлено
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): новая Celery-задача `notify_engineer_tu_parsed`, которая ставится в очередь из `check_data_completeness` сразу после перехода заявки в `waiting_client_info`.
- В [`backend/templates/emails/tu_parsed_notification.html`](../backend/templates/emails/tu_parsed_notification.html): отдельный шаблон письма инженеру о том, что клиент загрузил ТУ и парсинг завершён.
- В [`backend/alembic/versions/20260416_uute_tu_parsed_notification_enum.py`](../backend/alembic/versions/20260416_uute_tu_parsed_notification_enum.py): миграция enum-значения `TU_PARSED_NOTIFICATION` для PostgreSQL-типа `email_type`.
- В [`backend/tests/test_tu_parsed_engineer_notification.py`](../backend/tests/test_tu_parsed_engineer_notification.py): регрессионный тест на постановку инженерского уведомления после `check_data_completeness`.

### Изменено
- В [`backend/app/models/models.py`](../backend/app/models/models.py): `EmailType` расширен значением `tu_parsed_notification` для отдельного логирования события после парсинга ТУ.
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): добавлены `render_tu_parsed_notification` и `send_tu_parsed_notification` с текстом о статусе `waiting_client_info`, списке недостающих документов и ссылке на админку.
- В [`docs/project.md`](project.md): актуализировано описание email/Celery-цепочки после загрузки и парсинга ТУ.

## [2026-04-16] — Fix: безопасная enum-миграция статуса замечаний РСО

### Исправлено
- В [`backend/alembic/versions/20260416_uute_rso_remarks_status.py`](../backend/alembic/versions/20260416_uute_rso_remarks_status.py): `ALTER TYPE ... ADD VALUE` вынесен в `autocommit_block`, чтобы PostgreSQL успевал закоммитить новый enum перед `UPDATE orders`.
- В [`backend/alembic/README.md`](../backend/alembic/README.md): добавлено правило для всех будущих enum-миграций PostgreSQL через `op.get_context().autocommit_block()`.

## [2026-04-16] — Post-project flow: отдельный статус замечаний РСО

### Добавлено
- В [`backend/app/models/models.py`](../backend/app/models/models.py): новый статус заявки `rso_remarks_received` для явного возврата post-project заявки инженеру после замечаний РСО.
- В [`backend/alembic/versions/20260416_uute_rso_remarks_status.py`](../backend/alembic/versions/20260416_uute_rso_remarks_status.py): миграция enum-значения `RSO_REMARKS_RECEIVED` для PostgreSQL-типа `order_status` и backfill уже открытых замечаний РСО.
- В [`backend/app/post_project_state.py`](../backend/app/post_project_state.py): вынесен helper вычисления post-project флагов по статусу и хронологии файлов.

### Изменено
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): `upload-rso-remarks` теперь переводит заявку в `rso_remarks_received`.
- В [`backend/app/api/pipeline.py`](../backend/app/api/pipeline.py) и [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): повторная отправка исправленного проекта доступна из `rso_remarks_received` и после успеха возвращает заявку в `awaiting_final_payment`; подтверждение финальной оплаты теперь не блокируется новым статусом.
- В [`backend/app/schemas/schemas.py`](../backend/app/schemas/schemas.py): derived-флаги post-project flow теперь учитывают реальный статус заявки и не залипают на старых файлах замечаний после повторной отправки.
- В [`backend/static/admin.html`](../backend/static/admin.html) и [`backend/static/payment.html`](../backend/static/payment.html): добавлено отображение нового статуса и синхронизирован UX после загрузки замечаний РСО.

## [2026-04-16] — Post-project flow: финальный счёт и замечания РСО

### Добавлено
- В [`backend/app/models/models.py`](../backend/app/models/models.py): новые категории файлов `final_invoice` и `rso_remarks`, а также поле `rso_scan_received_at` в `Order`.
- В [`backend/alembic/versions/20260416_uute_final_payment_rso_feedback.py`](../backend/alembic/versions/20260416_uute_final_payment_rso_feedback.py): миграция enum-значений `FINAL_INVOICE` / `RSO_REMARKS` и колонки `orders.rso_scan_received_at`.
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): публичный `POST /landing/orders/{id}/upload-rso-remarks`, derived-флаги payment-page (`has_rso_scan`, `has_rso_remarks`, `awaiting_rso_feedback`, `final_invoice_available`) и реквизиты для оплаты по счёту.
- В [`backend/app/api/pipeline.py`](../backend/app/api/pipeline.py): admin endpoint `POST /pipeline/{id}/resend-corrected-project` для повторной отправки исправленного проекта клиенту.
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): задачи `notify_engineer_rso_remarks_received`, `resend_corrected_project`, ежедневная beat-задача reminder спустя 15 дней после `rso_scan_received_at`.

### Изменено
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): `send_completed_project` теперь сохраняет счёт на остаток как `OrderFile(final_invoice)` и при повторных отправках переиспользует уже сохранённый документ вместо генерации нового.
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): добавлена отдельная ветка повторной отправки исправленного проекта; письма `project_delivery` и `final_payment_request` больше не обещают онлайн-эквайринг и ведут на рабочий экран оплаты по счёту / загрузки замечаний РСО.
- В [`backend/static/payment.html`](../backend/static/payment.html): переработан сценарий `awaiting_final_payment` для варианта A — выбор между загрузкой скана РСО и оплатой по счёту, устойчивое подтверждение приёма скана, upload замечаний РСО, показ реквизитов и статуса счёта.
- В [`backend/static/admin.html`](../backend/static/admin.html): добавлены отображение `rso_scan_received_at`, файла `rso_remarks`, derived state post-project flow и действие «Отправить исправленный проект».
- В [`backend/app/schemas/schemas.py`](../backend/app/schemas/schemas.py): расширены `PaymentPageInfo` и `OrderResponse` вычисляемыми post-project флагами.

## [2026-04-16] — Доработки UI и email/payment flow

### Изменено
- В [`backend/static/admin.html`](../backend/static/admin.html): в блоке «Настроечная БД вычислителя» кнопка «Сохранить» теперь неактивна без pending-изменений, блокируется на время `PATCH` и снова активируется только после новых правок полей.
- В [`backend/static/admin.html`](../backend/static/admin.html): блок «Настроечная БД вычислителя» сделан сворачиваемым и по умолчанию отображается в свернутом состоянии; группы параметров внутри блока также свёрнуты по умолчанию.
- В [`backend/templates/emails/info_request.html`](../backend/templates/emails/info_request.html): письмо «Запрос документов» дополнено этапом предварительных расчётов (диаметр расходомера, суточные/месячные расходы) и обновлённой формулировкой продолжения.
- В [`backend/static/upload.html`](../backend/static/upload.html): в сценарии `contract_sent` после успешной загрузки `signed_contract` добавлена кнопка «Вернуться на сайт».
- В [`backend/templates/emails/project_delivery.html`](../backend/templates/emails/project_delivery.html): в письмо «Проект готов» добавлена кнопка для загрузки скана сопроводительного письма (`/payment/{id}`).
- В [`backend/templates/emails/final_payment_request.html`](../backend/templates/emails/final_payment_request.html): добавлен сценарий письма после загрузки скана сопроводительного в РСО (15/5 рабочих дней с ссылкой на ПП РФ №1034 п.51/п.50 и CTA «Загрузить замечания от РСО»).

### Добавлено
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): после `upload-rso-scan` добавлена задача `notify_client_after_rso_scan` с отправкой клиенту письма о следующих шагах согласования.
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): `send_completed_project` формирует и прикладывает счёт на остаток по договору (`generate_invoice(..., is_advance=False)`) вместе с проектом и сопроводительным письмом.

### Исправлено
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): добавлен cleanup временного файла счёта на остаток после отправки письма с готовым проектом.
- В [`backend/static/payment.html`](../backend/static/payment.html): для статуса `awaiting_final_payment` возвращён экран загрузки скана РСО, если скан ещё не загружен; экран «Ожидание подтверждения» показывается только после фактической загрузки `rso_scan`.

## [2026-04-16] — Fix: upload-signed-contract HTTP 500

### Исправлено
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): `POST /landing/orders/{id}/upload-signed-contract` теперь обрабатывает ошибки БД при проверке/сохранении файла как контролируемый `503` с понятным сообщением вместо `500`.
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): сбой постановки Celery-уведомления инженеру (`notify_engineer_signed_contract.delay`) больше не ломает успешную загрузку файла клиентом.

## [2026-04-16] — Unified upload + contract flow (frontend/admin/API)

### Добавлено
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): публичный `POST /landing/orders/{id}/upload-signed-contract` (только `contract_sent`, лимит 25 МБ, PDF/JPG/JPEG/PNG, уведомление инженеру).
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): новая Celery-цепочка `process_card_and_contract`, уведомление `notify_engineer_signed_contract`, упрощённый `process_advance_payment` (только `contract_sent → advance_paid`).
- В [`backend/alembic/versions/20260416_uute_signed_contract_enums.py`](../backend/alembic/versions/20260416_uute_signed_contract_enums.py): миграция enum-значений `SIGNED_CONTRACT` и `SIGNED_CONTRACT_NOTIFICATION`.
- В [`backend/static/upload.html`](../backend/static/upload.html): отдельный сценарий `contract_sent` с карточкой «Подпишите договор и загрузите скан», отображением `contract_number` / `payment_amount` / `advance_amount`, отдельным dropzone и загрузкой в `POST /api/v1/landing/orders/{id}/upload-signed-contract` (форматы: PDF/JPG/JPEG/PNG).
- В [`backend/static/admin.html`](../backend/static/admin.html): индикатор наличия файла `signed_contract` в действиях для статуса `contract_sent`; в селект категорий добавлены `company_card`, `contract`, `invoice`, `signed_contract`, `rso_scan`.

### Изменено
- В [`backend/app/models/models.py`](../backend/app/models/models.py): расширены `FileCategory`/`EmailType`, обновлены переходы стейт-машины для нового шага `client_info_received → contract_sent`.
- В [`backend/app/services/param_labels.py`](../backend/app/services/param_labels.py): `company_card` добавлен в обязательные клиентские документы и подписи.
- В [`backend/app/api/pipeline.py`](../backend/app/api/pipeline.py): `approve` для нового потока отправляет проект из `advance_paid`, `confirm-advance` требует загруженный подписанный договор; legacy-ветка `review` сохранена.
- В [`backend/app/services/order_service.py`](../backend/app/services/order_service.py): защита от path traversal при сохранении имени загружаемого файла.
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): `contract_delivery` обновлён под загрузку подписанного договора, добавлено письмо инженеру `SIGNED_CONTRACT_NOTIFICATION`.
- В [`backend/app/schemas/schemas.py`](../backend/app/schemas/schemas.py): `UploadPageInfo` расширен контрактными полями (`contract_number`, суммы, реквизиты).
- В [`backend/static/upload.html`](../backend/static/upload.html): в `PARAM_LABELS` добавлен `company_card`; для `waiting_client_info`/`client_info_received` карточка `company_card` выделяется отдельным визуальным блоком рядом с техдокументами.
- В [`backend/static/admin.html`](../backend/static/admin.html): основной stepper приведён к новому потоку `new → tu_parsing → tu_parsed → waiting_client_info → client_info_received → contract_sent → advance_paid → awaiting_final_payment → completed`; legacy-статусы сохранены в совместимых словарях.
- В [`backend/static/admin.html`](../backend/static/admin.html): кнопка approve перенесена на `advance_paid` для основного потока (legacy `review` сохранён), обновлены текст/подтверждение/успешное сообщение; polling после approve ждёт выход из исходного статуса.

## [2026-04-16] — Калькулятор: обновление цен

### Изменено
- В [`frontend/src/components/CalculatorSection.tsx`](../frontend/src/components/CalculatorSection.tsx): базовые цены «Индивидуальный» — 1 контур 22 500 руб., 2 контура 35 000 руб., 3 контура 50 000 руб.; тариф «Экспресс» (ЭСКО, 1 контур) — 11 250 руб.

## [2026-04-15] — Approve → оплата; админка: оплата и подтверждения

### Добавлено
- В [`backend/app/api/pipeline.py`](../backend/app/api/pipeline.py): `POST .../confirm-advance`, `POST .../confirm-final` (admin key) — запуск `process_advance_payment` / `process_final_payment`
- В [`backend/static/admin.html`](../backend/static/admin.html): статусы оплаты в степпере и легенде, карточка «Оплата», кнопки подтверждения аванса и остатка, `startPaymentFlowPoll`, подписи типов писем оплаты

### Изменено
- В [`backend/app/api/pipeline.py`](../backend/app/api/pipeline.py): `approve_project` ставит в очередь `initiate_payment_flow` вместо `send_completed_project`
- В [`backend/static/admin.html`](../backend/static/admin.html): текст подтверждения одобрения и опрос после approve (ожидание ухода из `review`)

## [2026-04-15] — Celery: оркестрация авансовой оплаты

### Добавлено
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): `_collect_project_attachments`, `_resolve_initial_payment_amount`; задачи `initiate_payment_flow`, `process_advance_payment`, `process_final_payment`

### Изменено
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): `send_completed_project` собирает вложения через `_collect_project_attachments`; `process_company_card_and_send_contract` — сохранение договора/счёта в БД и на диск до отправки письма, повторная отправка при уже сохранённых файлах, `max_retries=2` / `delay=60`

## [2026-04-15] — Письма по авансовой оплате (шаблоны + send/render)

### Добавлено
- В [`backend/templates/emails/`](../backend/templates/emails/): `project_ready_payment.html`, `contract_delivery.html`, `advance_received.html`, `final_payment_request.html`, `final_payment_received.html` (наследуют `base.html`, суммы и кнопки на `/payment/{id}`)
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): хелперы `_format_rub`, `_final_amount_rub`, `_contract_number_display`, `_executor_bank_context`; пары `render_*` / `send_*` для `PROJECT_READY_PAYMENT`, `CONTRACT_DELIVERY`, `ADVANCE_RECEIVED`, `FINAL_PAYMENT_REQUEST`, `FINAL_PAYMENT_RECEIVED`

### Изменено
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): `send_contract_delivery_to_client` использует шаблон `contract_delivery.html` вместо inline HTML

## [2026-04-15] — Публичная страница оплаты /payment/{id}

### Добавлено
- В [`backend/static/payment.html`](../backend/static/payment.html): клиентская страница оплаты (экраны по статусу, drag-and-drop с прогрессом, polling парсинга реквизитов и смены статуса)
- В [`backend/app/main.py`](../backend/app/main.py): маршрут `GET /payment/{order_id}` → `payment.html`
- В [`backend/app/schemas/schemas.py`](../backend/app/schemas/schemas.py): схема `PaymentPageInfo`
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): публичные эндпоинты `GET .../payment-page`, `POST .../upload-company-card`, `POST .../select-payment-method`, `POST .../upload-rso-scan`
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): `send_contract_delivery_to_client` — письмо с договором и счётом
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): `process_company_card_and_send_contract`, `notify_engineer_rso_scan_received`

## [2026-04-14] — Калькулятор: тариф «Индивидуальный»

### Изменено
- В [`frontend/src/components/CalculatorSection.tsx`](../frontend/src/components/CalculatorSection.tsx): цены варианта «Индивидуальный» — 1 контур 30 000 ₽, 2 контура 45 000 ₽, 3 контура 60 000 ₽ (в заявку уходит выбранная сумма)

## [2026-04-14] — Калькулятор: тариф «Экспресс» 20 000 ₽

### Изменено
- В [`frontend/src/components/CalculatorSection.tsx`](../frontend/src/components/CalculatorSection.tsx): для варианта «Экспресс» (1 контур) отображается и в заявку уходит фиксированная цена 20 000 ₽ вместо 50% от базового тарифа контура
- В [`frontend/src/components/FAQSection.tsx`](../frontend/src/components/FAQSection.tsx): убрана отдельная строка про цену со скидкой в ответе о стоимости (актуальная цена экспресса — в калькуляторе)

## [2026-04-14] — Модальное окно "Запросить КП" (Шаг 2)

### Добавлено
- В [`frontend/src/components/KpRequestModal.tsx`](../frontend/src/components/KpRequestModal.tsx): модальный компонент с 5 обязательными полями (организация, ФИО, телефон, email, файл ТУ), FormData-отправка, состояния submitting/success/error
- В [`frontend/src/api.ts`](../frontend/src/api.ts): функция `sendKpRequest(formData: FormData)` для отправки multipart/form-data
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): эндпоинт `POST /api/v1/landing/kp-request` с валидацией EmailStr, ограничением 20 МБ, проверкой результата отправки
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): функция `send_kp_request_notification` — письмо инженеру с файлом ТУ во вложении, HTML-экранирование пользовательских полей, Reply-To header

### Изменено
- В [`frontend/src/components/ProcessSection.tsx`](../frontend/src/components/ProcessSection.tsx): кнопка "Запросить КП" в шаге 2 теперь открывает модальное окно (вместо ссылки на `#calculator`)

## [2026-04-14] — Настроечная БД Эско-Терра в express-пайплайне

### Добавлено
- В [`backend/app/services/calculator_config_service.py`](../backend/app/services/calculator_config_service.py): константа `ESKO_MARKERS`, функция `resolve_calculator_type_for_express(order)` — автоопределение Эско-Терра по `parsed_params.metering.heat_calculator_model`; синхронная `init_config_sync(order, session)` для Celery-задач
- В [`backend/app/api/calculator_config.py`](../backend/app/api/calculator_config.py): ветка для express-заявок в `GET /calc-config` (через `resolve_calculator_type_for_express`); guard в `POST /calc-config/init` — для express разрешён только `esko_terra`; новое поле `esko_detected` в ответе GET для express
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): автоинициализация настроечной БД после парсинга ТУ для express-заявок — если Эско-Терра обнаружена, конфиг создаётся автоматически; ошибка не прерывает пайплайн
- В [`backend/static/admin.html`](../backend/static/admin.html): карточка настроечной БД показывается и для express-заявок; статус `not_supported_for_express` отображает предупреждение + кнопку «Инициализировать как Эско 3Э»; добавлена функция `initCalcConfigExpress`

## [2026-04-12] — Настроечная БД вычислителя (мультиприборность)

### Добавлено
- В [`backend/calculator_templates/`](../backend/calculator_templates/): JSON-шаблоны настроечных параметров для ТВ7 (29 параметров, `has_dual_db: true`), СПТ-941.20 (25 параметров), ЭСКО-Терра М (22 параметра); каждый параметр содержит `source` (auto/default/engineer/client), `auto_rule` и метаданные для UI
- В [`backend/app/models/models.py`](../backend/app/models/models.py): модель `CalculatorConfig` с полями `calculator_type`, `config_data` (JSONB), `status`, `total_params`, `filled_params`, `missing_required`, `client_requested_params`; relationship в `Order`
- В [`backend/alembic/versions/20260412_uute_add_calculator_configs.py`](../backend/alembic/versions/20260412_uute_add_calculator_configs.py): миграция создания таблицы `calculator_configs`
- В [`backend/app/services/calculator_config_service.py`](../backend/app/services/calculator_config_service.py): сервис автозаполнения — маппинг `manufacturer→calculator_type`, 8 авто-правил (расчёт Gдог, вывод SI/FT/HT, маппинг давлений и температур из ТУ), функции `init_config`, `update_params`, `export_pdf` (PyMuPDF)
- В [`backend/app/api/calculator_config.py`](../backend/app/api/calculator_config.py): CRUD-эндпоинты `GET/POST(init)/PATCH/POST(export-pdf)` для `/api/v1/admin/orders/{order_id}/calc-config`
- В [`backend/app/main.py`](../backend/app/main.py): подключён `calculator_config_router`
- В [`backend/static/admin.html`](../backend/static/admin.html): сворачиваемая карточка `calcConfigCard` с прогресс-баром заполненности, легендой цветов источников, таблицами параметров по группам, inline-редактированием (инженер/клиент), кнопками «Инициализировать», «Сохранить», «Экспорт PDF»; блок показывается только для `custom`-заказов

## [2026-04-11] — Лэндинг: реквизиты только в подвале

### Изменено
- В [`frontend/src/components/PartnerFormSection.tsx`](../frontend/src/components/PartnerFormSection.tsx): из блока «Свяжитесь с нами» убран подзаголовок «Реквизиты»; ИНН, счета и банк остаются только в подвале.

## [2026-04-11] — Лэндинг: единые контакты и реквизиты в подвале и в «Свяжитесь с нами»

### Изменено
- В [`frontend/src/components/PartnerFormSection.tsx`](../frontend/src/components/PartnerFormSection.tsx): блок «Свяжитесь с нами» использует те же адрес, телефон и email, что и подвал (ранее были заглушки).
- В [`frontend/src/components/Footer.tsx`](../frontend/src/components/Footer.tsx): контакты и реквизиты берутся из общего модуля.

### Добавлено
- [`frontend/src/constants/siteLegal.ts`](../frontend/src/constants/siteLegal.ts): `SITE_CONTACT`, `SITE_REQUISITES` — единый источник для лэндинга.

## [2026-04-11] — Исправлено: PDF с лендинга в production открывался как повреждённый

### Исправлено
- В [`backend/app/main.py`](../backend/app/main.py): маршрут SPA сначала отдаёт реальный файл из `frontend-dist` по пути запроса (например `/downloads/opros_list_form.pdf`), иначе — `index.html`. Ранее catch-all всегда возвращал HTML, и скачанный «PDF» был невалидным.

## [2026-04-11] — Поле «Город объекта»

### Добавлено
- В [`backend/app/models/models.py`](../backend/app/models/models.py): колонка `object_city TEXT` в таблице `orders`
- В [`backend/alembic/versions/`](../backend/alembic/versions/): миграция `20260411_uute_add_object_city`
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): обязательное поле `object_city` в `OrderRequest`
- В [`frontend/src/components/EmailModal.tsx`](../frontend/src/components/EmailModal.tsx): поле «Город объекта *» в форме заказа
- В [`backend/static/upload.html`](../backend/static/upload.html): поле «Город объекта *» в опросном листе (группа «1. Объект»), предзаполнение из `parsed_params.object.city`
- В [`backend/static/admin.html`](../backend/static/admin.html): столбец «Город» в списке заявок, строка в карточке, строка в сравнительной таблице

### Изменено
- В [`backend/app/schemas/schemas.py`](../backend/app/schemas/schemas.py): поле `object_city` в `OrderCreate`, `OrderResponse`, `OrderListItem`
- В [`backend/app/services/order_service.py`](../backend/app/services/order_service.py): передача `object_city` при создании заявки
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): автозаполнение `order.object_city` из `parsed.object.city` после парсинга ТУ

## [2026-04-11] — Скачивание опросного листа (PDF) с лендинга

### Добавлено
- Статический файл [`frontend/public/downloads/opros_list_form.pdf`](../frontend/public/downloads/opros_list_form.pdf): копия [`docs/opros_list_form.pdf`](opros_list_form.pdf) для раздачи Vite/production.

### Изменено
- В [`frontend/src/components/ProcessSection.tsx`](../frontend/src/components/ProcessSection.tsx): ссылки «Скачать опросный лист» (шаг 1 и блок под `#questionnaire`) ведут на `/downloads/opros_list_form.pdf` с атрибутом `download`.

## [2026-04-11] — Excel-совместимый шаблон опросного листа для клиента

### Добавлено
- В [`docs/templates/client-survey-excel/uute_client_survey_sheet1.csv`](templates/client-survey-excel/uute_client_survey_sheet1.csv): основной CSV-лист для отправки клиенту с полями из текущего парсинга ТУ и действующего опросного листа.
- В [`docs/templates/client-survey-excel/uute_client_survey_sheet2_mapping.csv`](templates/client-survey-excel/uute_client_survey_sheet2_mapping.csv): технический CSV-лист соответствия между кодами полей, `survey_data` и `parsed_params`.
- В [`docs/templates/client-survey-excel/README.md`](templates/client-survey-excel/README.md): описание структуры шаблона и порядка переноса двух CSV в единый `.xlsx`.


## [2026-04-11] — Custom: заполненные поля опросного листа только для чтения при повторном открытии

### Изменено
- В [`backend/static/upload.html`](../backend/static/upload.html): добавлена функция `lockFilledSurveyFields(surveyData)` — после предзаполнения формы из сохранённого `survey_data` каждое поле с непустым значением помечается как только для чтения (`readonly` для `input`/`textarea`, `pointer-events: none` для `select`). Пустые поля остаются редактируемыми. Применяется при вызове `prefillSurveyFromSaved` — то есть когда клиент открывает страницу по ссылке из письма (статусы `waiting_client_info` и другие `CUSTOM_EDITABLE_STATUSES`) и опрос уже был заполнен при создании заявки.

## [2026-04-10] — Custom: необязательные документы, подсказка, свёртка опроса в админке

### Изменено
- В [`backend/static/upload.html`](../backend/static/upload.html): для custom-заявок в статусах `WAITING_CLIENT_INFO` и смежных кнопка «Всё загружено — отправить» теперь разблокируется как только сохранён опросный лист — загрузка всех дополнительных документов **необязательна**.
- В [`backend/static/upload.html`](../backend/static/upload.html): если опрос сохранён, но не все документы загружены — показывается жёлтая подсказка «Вы можете отправить заявку сейчас — инженер свяжется с вами для уточнения деталей».
- В [`backend/static/upload.html`](../backend/static/upload.html): баннер после сохранения опроса обновлён — отражает опциональность загрузки документов.
- В [`backend/static/admin.html`](../backend/static/admin.html): карточка «Опросный лист» стала **сворачиваемой** — по клику на заголовок «Данные опросного листа ▶» через `<details>/<summary>` (по умолчанию развёрнута).

## [2026-04-10] — Письмо «Проект готов»: убран пункт про скан после согласования

### Изменено
- В [`backend/templates/emails/project_delivery.html`](../backend/templates/emails/project_delivery.html): из блока «Дальнейшие действия» удалён пункт о присылании скана письма с входящим номером РСО после согласования.

## [2026-04-09] — UX custom: опросный лист над документами, свёртка, звёздочки, секции в админке

### Изменено
- В [`backend/static/upload.html`](../backend/static/upload.html): **опросный лист перемещён** над блоками «Необходимые документы» и «Загрузка файлов» (для custom-заявок).
- В [`backend/static/upload.html`](../backend/static/upload.html): на начальном экране (`status=new`) опросный лист показывается **свёрнутым** (заголовок-аккордеон с ▼); клик раскрывает/скрывает. После парсинга ТУ раскрывается автоматически.
- В [`backend/static/upload.html`](../backend/static/upload.html): обязательные поля опросного листа (все без пометки «(необяз.)») **отмечены красной звёздочкой `*`** в лейбле.
- В [`backend/static/admin.html`](../backend/static/admin.html): «Опросный лист» в карточке custom-заявки теперь отображается **в секциях** (🏢 Объект / ⚡ Теплоснабжение / 🔥 Тепловые нагрузки / 🔧 Трубопроводы / 📊 Приборы учёта / ➕ Дополнительно) в том же стиле, что «Результат парсинга ТУ» для экспресс. Порядок строк фиксирован, пустые секции не отображаются.

## [2026-04-09] — UX: ошибки опроса inline, поле ВРУ, приветствие экспресс, кнопка «Одобрить»

### Изменено
- В [`backend/static/upload.html`](../backend/static/upload.html): ошибки валидации при нажатии «Сохранить опросный лист» (не указан производитель, не заполнено расстояние) теперь появляются **inline под кнопкой**, а не в баннере вверху страницы.
- В [`backend/static/upload.html`](../backend/static/upload.html): поле «Расстояние до ВРУ» переименовано в **«Расстояние до ВРУ или щита собственных нужд ТП, м»** и стало обязательным (убрана пометка «необяз.»).
- В [`backend/static/upload.html`](../backend/static/upload.html): для **экспресс-заявки** после отправки документов клиентом приветственный текст обновляется на «Спасибо! Документы загружены, ждите готовый проект или запрос на уточнения» — срабатывает и при первой отправке, и при повторном открытии страницы.
- В [`backend/static/admin.html`](../backend/static/admin.html): `runAction()` теперь **блокирует все кнопки действий** на время API-запроса; при ошибке — разблокирует; при успехе — `loadOrder` перестраивает страницу через 1.2 сек.
- В [`backend/static/admin.html`](../backend/static/admin.html): под блоком загрузки файлов добавлена подсказка инженеру: порядок действий (выбрать файл → Загрузить → Одобрить и отправить клиенту).
- В [`backend/static/admin.html`](../backend/static/admin.html): метка поля `distance_to_vru` в словаре `param_labels` обновлена до «Расстояние до ВРУ или щита собственных нужд ТП, м».

---

## [2026-04-09] — Письмо «Проект готов»: формулировка про оплату и скан

### Изменено
- В [`backend/templates/emails/project_delivery.html`](../backend/templates/emails/project_delivery.html): блок про оплату — срок **пять рабочих дней** на присылание скана сопроводительного письма **или** оплату за выполненную работу (вместо прежних «2 рабочих дней» и приоритета оплаты).

---

## [2026-04-08] — Админка: polling для статуса tu_parsing

### Исправлено
- В [`backend/static/admin.html`](../backend/static/admin.html): после клика «Запустить парсинг ТУ» страница больше не показывает «Нет доступных действий» и не требует ручного обновления; добавлен polling каждые 5 секунд (максимум 60 попыток, 5 минут) при статусе `tu_parsing`; показывается спиннер «Выполняется анализ ТУ…»; при завершении парсинга — автоматическое обновление заявки и уведомление «Анализ завершён!»; при ошибке или таймауте — соответствующее уведомление.

---

## [2026-04-08] — Страница загрузки custom: опрос и кнопка «Всё загружено»

### Изменено
- В [`backend/static/upload.html`](../backend/static/upload.html): для индивидуальной заявки после парсинга ТУ кнопка «Всё загружено — отправить» активна только после **сохранения опросного листа** и загрузки всех файлов из чеклиста; подсказка в `title`; после сохранения опроса — бейдж «Опросный лист заполнен», баннер на 12 с, прокрутка к блоку опроса; при уже сохранённом `survey_data` при открытии страницы сразу показывается бейдж без кнопки сохранения; разбор `detail` ошибок API (массивы FastAPI).

---

## [2026-04-08] — Таймер 24 ч для авто-запроса документов (info_request)

### Добавлено
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): при переходе в `waiting_client_info` постановка `send_info_request_email` в очередь Celery с задержкой 24 часа (`INFO_REQUEST_AUTO_DELAY_SECONDS`); периодическая `process_due_info_requests` остаётся резервом.
- В [`backend/app/schemas/schemas.py`](../backend/app/schemas/schemas.py): в `OrderResponse` поле `info_request_earliest_auto_at` (UTC), в [`build_order_response`](../backend/app/schemas/schemas.py) — расчёт `waiting_client_info_at + 24 ч`, пока `info_request` ещё не отправляли.

### Изменено
- В [`backend/static/admin.html`](../backend/static/admin.html): подсказка с датой/временем автоотправки (МСК) в статусе ожидания клиента, если запрос ещё не уходил; кнопка «Отправить запрос клиенту» по-прежнему неактивна после успешной отправки (`info_request_sent`).

---

## [2026-04-08] — Сопроводительное письмо: e-mail заказчика и инженера для замечаний

### Изменено
- В [`backend/app/services/cover_letter.py`](../backend/app/services/cover_letter.py): вместо контактного лица из ТУ в абзаце про замечания подставляются e-mail заказчика (`orders.client_email`) и e-mail инженера (`ADMIN_EMAIL` из настроек); сигнатура `generate_cover_letter(..., client_email=..., admin_email=...)`.
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): `send_completed_project` передаёт эти адреса в генератор DOCX.

---

## [2026-04-07] — Сопроводительное письмо в РСО при отправке проекта

### Добавлено
- В [`backend/app/services/cover_letter.py`](../backend/app/services/cover_letter.py): генератор DOCX сопроводительного письма в РСО из данных `TUParsedData` (applicant.*, rso.*, document.*, object.*).
- В [`backend/requirements.txt`](../backend/requirements.txt): зависимость `python-docx==1.1.2`.

### Изменено
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): `send_completed_project` — генерирует DOCX сопроводительного письма и прикладывает его к email вместе с PDF проекта; временный файл удаляется после отправки.
- В [`backend/templates/emails/project_delivery.html`](../backend/templates/emails/project_delivery.html): обновлён текст письма — добавлена инструкция по сопроводительному письму и требование оплаты в течение 2 рабочих дней или скана с входящим номером РСО.

---

## [2026-04-07] — Отложенный info_request (24 ч), одноразовые письма, уведомление инженеру, прогресс загрузки PDF

### Добавлено
- В [`backend/app/models/models.py`](../backend/app/models/models.py): поле `orders.waiting_client_info_at` (UTC); значение `EmailType.CLIENT_DOCUMENTS_RECEIVED`.
- Миграция [`backend/alembic/versions/20260407_uute_waiting_client_info_email_enum.py`](../backend/alembic/versions/20260407_uute_waiting_client_info_email_enum.py): колонка + значение `email_type` в PostgreSQL (`CLIENT_DOCUMENTS_RECEIVED`, как имя члена enum в SQLAlchemy); backfill для текущих `WAITING_CLIENT_INFO`.
- Задачи Celery [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): `process_due_info_requests` (Beat раз в 15 мин), `notify_engineer_client_documents_received`; логика `send_reminders` и `send_info_request_email` с идемпотентностью по `email_log`.
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): `has_successful_email`, `send_client_documents_received_notification`, шаблон [`backend/templates/emails/client_documents_received.html`](../backend/templates/emails/client_documents_received.html).
- В ответе заявки [`backend/app/schemas/schemas.py`](../backend/app/schemas/schemas.py): `info_request_sent`, `reminder_sent` (сборка через `build_order_response` в [`backend/app/api/orders.py`](../backend/app/api/orders.py)).

### Изменено
- [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): при неполных данных после парсинга не вызывается немедленная отправка `info_request`.
- [`backend/app/api/emails.py`](../backend/app/api/emails.py): повтор `info_request` / `reminder` — **409** с текстом в `detail`.
- [`backend/app/api/pipeline.py`](../backend/app/api/pipeline.py): после `client-upload-done` — постановка уведомления инженеру в очередь.
- [`backend/static/admin.html`](../backend/static/admin.html): блокировка кнопок запроса/напоминания по флагам API; прогресс загрузки для `generated_project` через XHR.

## [2026-04-06] — Одобрение проекта только при загруженном PDF

### Изменено
- В [`backend/app/api/pipeline.py`](../backend/app/api/pipeline.py): `POST /pipeline/{id}/approve` перед постановкой `send_completed_project` в очередь проверяет наличие файла категории `generated_project`; при отсутствии — **422** и текст с подсказкой загрузить PDF.

### Добавлено
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): предупреждение в лог, если у заявки нет путей вложений при отправке (страховка при рассинхроне БД и диска).
- В [`backend/static/admin.html`](../backend/static/admin.html): кнопка «Одобрить и отправить клиенту» неактивна, пока нет файла «Готовый проект»; подсказка в `title` и в блоке действий.

## [2026-04-05] — Письмо «Проект готов»: имя вложения RFC 5987, без ссылки на admin API

### Исправлено
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): для вложений в `_build_message` заголовок `Content-Disposition` задаётся через `add_header(..., filename=...)`, чтобы не-ASCII имена файлов кодировались по RFC 2231/5987 (`filename*=utf-8''...`), а не «голой» строкой в кавычках.
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): в `send_completed_project` убрана ссылка «Скачать проект» на `GET /api/v1/orders/{id}/files` (требует `X-Admin-Key`); клиенту остаётся только вложение в письме.

## [2026-04-05] — Письмо «Проект готов»: одно вложение вместо дубля

### Исправлено
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): в `send_project` убрано повторное объединение `attachments + attachment_paths` — список путей уже возвращается из `render_project_delivery` и совпадает с аргументом вызова. Раньше файл прикреплялся дважды (удвоенный размер письма), из‑за чего SMTP мог принимать сообщение, а доставка до клиента не происходила.

## [2026-04-05] — file_category: персистить имена членов Enum (TU, …)

### Исправлено
- В [`backend/app/models/models.py`](../backend/app/models/models.py): у `OrderFile.category` убран `values_callable` — в PostgreSQL метки `file_category` совпадают с именами членов Python (`TU`, `BALANCE_ACT`, …), а не с `.value` (`tu`, …). Устраняет `invalid input value for enum file_category: "tu"`.
- Там же: у `EmailLog.email_type` убран `values_callable` (в БД — имена членов, как для `order_status` / `file_category`); `values_callable` остаётся только у `order_type`.

## [2026-04-05] — Enum: order_status без values_callable

### Исправлено
- В [`backend/app/models/models.py`](../backend/app/models/models.py): у колонки `status` убран `values_callable` — в PostgreSQL тип `order_status` хранит метки как имена членов (`NEW`, `TU_PARSING`, …), а не строки `.value` (`new`, …). Для `order_type`, `file_category`, `email_type` `values_callable` оставлен: там метки в БД совпадают с `Enum.value` (`express`, `tu`, `info_request`, …).

## [2026-04-05] — SQLAlchemy enum: передача значений в PostgreSQL

### Исправлено
- В [`backend/app/models/models.py`](../backend/app/models/models.py): для колонок `order_status`, `order_type`, `file_category`, `email_type` задан общий `values_callable`, чтобы в БД уходили строки `Enum.value` (как в типах PostgreSQL), а не имена членов Python (`EXPRESS`, `NEW` и т.д.). Устраняет ошибку `invalid input value for enum order_type: "EXPRESS"` при создании заявки с сайта.

## [2026-04-05] — Ссылка из письма «Новая заявка» в админку

### Исправлено
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): кнопка «Открыть заявку» ведёт на `/admin?order=<uuid>` вместо JSON API `GET /api/v1/orders/{id}` — браузер при обычном переходе по ссылке не отправляет заголовок `X-Admin-Key`, поэтому раньше отображался JSON с текстом «Неверный API-ключ».
- В [`backend/static/admin.html`](../backend/static/admin.html): чтение параметра `order` из URL, открытие карточки заявки после входа, если ключ ещё не сохранён в `sessionStorage` (ссылка из письма).

## [2026-04-05] — Восстановление кириллицы в админ-панели (admin.html)

### Исправлено
- В [`backend/static/admin.html`](../backend/static/admin.html): восстановлены все строки интерфейса и комментариев в UTF-8 (после коммита `ec45248` в репозитории оказались `?` вместо русского текста). Сохранена актуальная логика: `order_type`, опросный лист, `BALANCE_ACT`/`CONNECTION_PLAN` в загрузке, колонка «Тип заявки», подпись `survey_reminder` в логе писем, эмодзи в секциях парсера ТУ.

## [2026-04-05] — Кнопка «Вернуться на сайт» на странице загрузки

### Добавлено
- В [`backend/static/upload.html`](../backend/static/upload.html): стиль `.btn-secondary`, фокус `:focus-visible` для `.btn`; ссылка «Вернуться на сайт» (`href="/"`) в карточке «Все документы получены»; после успешного сохранения опросного листа — тот же блок `#surveyBackActions` (скрывается при ошибке сохранения).

## [2026-04-05] — Upload-page: parsed_params и survey_data для custom

### Добавлено
- В [`backend/app/schemas/schemas.py`](../backend/app/schemas/schemas.py): поля `parsed_params: dict | None = None` и `survey_data: dict | None = None` в `UploadPageInfo`.
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): в `get_upload_page_info` всегда передаётся `order_type`; для заявок `custom` в ответ включаются непустой `parsed_params` и `survey_data` (если в БД не `null`); для `express` оба поля `null`.
- В [`backend/static/upload.html`](../backend/static/upload.html): для custom + новая заявка после `/submit` — карточка ожидания парсинга `#parsingCard`, опрос `GET .../upload-page` каждые 5 с (до 5 мин), затем `prefillSurvey` + показ `#surveyCard`; при `order_status === tu_parsing` при открытии страницы — тот же polling; express и сценарий `waiting_client_info` без изменений; `prefillSurvey` маппит вложенную структуру парсера ТУ в поля опросника.
- В [`backend/static/upload.html`](../backend/static/upload.html): задача «умный опрос» — `PARAM_TO_SURVEY`, `getNestedValue`, `hydrateSurveyFromOrder` (приоритет сохранённого `survey_data`), классы `.prefilled` / `.needs-input`, бейджи «из ТУ», блок «Уверенность анализа» и список `warnings`.
- В [`backend/static/upload.html`](../backend/static/upload.html): инициализация custom по `order_status` — `initCustomOrderUi`, overlay заблокированного опроса при `new`, polling при `tu_parsing`, `prefillSurveyFromSaved` / ТУ при редактируемых статусах, догрузка файлов через `showUploadAlongsideSurveyIfNeeded`; `showCompleted` скрывает опрос и парсинг; `error` — баннер и загрузка.

### Изменено (ревью умного опроса, задача 5)
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): `POST /landing/orders/{id}/survey` принимает сохранение только в статусах `tu_parsed`, `waiting_client_info`, `client_info_received`, `data_complete`, `generating_project` (не в `new`, `review`, `completed` и т.д.).
- В [`backend/static/upload.html`](../backend/static/upload.html): `clearSurveyDecorations` вызывает `hideSurveyMeta`; вынесено `applyParsedParamsToSurvey` (prefill + мета парсера).

## [2026-04-04] — Опросный лист для custom-заказов (Задача 4)

### Добавлено
- В [`backend/app/schemas/schemas.py`](../backend/app/schemas/schemas.py): поле `order_type: str | None = None` в `UploadPageInfo`.
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): `order_type` передаётся в ответе `get_upload_page_info`; новый публичный эндпоинт `POST /landing/orders/{order_id}/survey` — принимает произвольный JSON, проверяет `order_type == CUSTOM`, сохраняет в `order.survey_data`, возвращает `SimpleResponse`.
- В [`backend/static/upload.html`](../backend/static/upload.html): блок `#surveyCard` с интерактивной формой опросного листа (6 групп полей: объект, теплоснабжение, нагрузки, трубопроводы, приборы учёта, дополнительно); показывается только при `order_type === 'custom'`; при сабмите отправляет JSON на `POST /api/v1/landing/orders/{id}/survey`; после успеха показывает зелёный бейдж.

## [2026-04-03] — Сегментация клиентов: экспресс / индивидуальный проект

### Добавлено
- В [`backend/app/models/models.py`](../backend/app/models/models.py): enum `OrderType` (`express`, `custom`); поля `order_type` (default=`EXPRESS`) и `survey_data` (JSONB) в модели `Order`.
- В [`backend/app/schemas/schemas.py`](../backend/app/schemas/schemas.py): `order_type` в `OrderCreate`, `OrderResponse`, `OrderListItem`; `survey_data` в `OrderResponse`.
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): `OrderRequest` принимает `order_type` (default `"express"`, паттерн `^(express|custom)$`); при custom-заказе отправляется `survey_reminder`.
- В [`backend/app/services/order_service.py`](../backend/app/services/order_service.py): `create_order` сохраняет `order_type` в модель.
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): `send_new_order_notification` принимает `order_type_label`; новая функция `send_survey_reminder`.
- В [`backend/app/models/models.py`](../backend/app/models/models.py): `EmailType.SURVEY_REMINDER`.
- Шаблон [`backend/templates/emails/survey_reminder.html`](../backend/templates/emails/survey_reminder.html): письмо клиенту с кнопкой на upload-страницу.
- В [`backend/static/admin.html`](../backend/static/admin.html): колонка «Тип» в таблице заявок; бейджи `orderTypeBadge`; блок «Опросный лист» (`renderSurveyData`) с 25 русскими подписями ключей.
- В [`frontend/src/components/CalculatorSection.tsx`](../frontend/src/components/CalculatorSection.tsx): две карточки вместо одной кнопки — «Экспресс» (−50%, зелёная) и «Индивидуальный» (полная цена).
- В [`frontend/src/components/EmailModal.tsx`](../frontend/src/components/EmailModal.tsx): prop `orderType`, передаётся в API; разный success-текст для custom.
- В [`frontend/src/api.ts`](../frontend/src/api.ts): поле `order_type?` в `OrderRequest`.

### Примечание
Миграция Alembic (колонки `order_type`, `survey_data` в таблице `orders`) создаётся на сервере отдельно перед деплоем.

## [2026-04-03] — Админ API: ключ в query `_k`

### Добавлено
- В [`backend/app/core/auth.py`](../backend/app/core/auth.py): `verify_admin_key` принимает query-параметр `_k` как запасной способ передачи ключа (если нет заголовка `X-Admin-Key`).

## [2026-04-03] — Enum `file_category`: BALANCE_ACT и CONNECTION_PLAN

### Изменено
- PostgreSQL: `ALTER TYPE file_category RENAME VALUE` для `balance_act` → `BALANCE_ACT`, `connection_plan` → `CONNECTION_PLAN` (миграция Alembic `20260403_fc_upper`, `down_revision`: `20260402_uute_fc`).
- `FileCategory`, `CLIENT_DOCUMENT_PARAM_CODES`, `param_labels`, `admin.html`, `upload.html`: те же строковые значения, что и метки enum в БД.
- `orders.missing_params`: пересборка массива с заменой старых кодов на новые.

## [2026-04-03] — Главная: React SPA из `frontend-dist`

### Добавлено
- В [`backend/app/main.py`](../backend/app/main.py): `FRONTEND_DIR = /app/frontend-dist`, монтирование `/assets` из Vite-сборки (если каталог есть), catch-all `GET /{full_path:path}` в конце приложения — отдаёт `index.html` для клиентского роутинга.

### Исправлено
- Корень сайта и прочие не-API пути больше не отвечают `{"detail":"Not Found"}` при смонтированном в Docker `./frontend/dist` (см. `docker-compose.prod.yml`).

## [2026-04-03] — Админка: таблица извлечённых параметров ТУ

### Добавлено
- В [`backend/static/admin.html`](../backend/static/admin.html) свёрнутый блок «Извлечённые параметры» (`<details>`) с таблицами по разделам (документ, нагрузки, теплоноситель, трубопровод, подключение, учёт); стили `.parsed-params-details`, `.parsed-params-table`, плейсхолдер «—» для пустых значений.
- Fallback отображения для устаревшего плоского формата `parsed_params`, если нет вложенной структуры `TUParsedData`.

### Изменено
- Карточка «Результат парсинга ТУ» всегда показывается при просмотре заявки; при пустом `parsed_params` — сообщение «Парсинг не выполнен» вместо скрытия карточки.
- Список недостающих данных экранируется при выводе (`esc`).

## [2026-04-02] — Парсер ТУ: system_type для ответов LLM

### Добавлено
- `SYSTEM_TYPE_ALLOWED` в `tu_schema.py`; расширен `Literal` для `connection.system_type` (двух-/четырёхтрубные варианты).
- `SYSTEM_TYPE_MAP`, `_normalize_system_type_raw`, `_apply_system_type_normalization` в `tu_parser.py` — нормализация до `model_validate`.

### Изменено
- `EXTRACTION_PROMPT`: явный перечень допустимых `system_type` и правило для «двухтрубная» → `закрытая_двухтрубная`.

## [2026-04-02] — Ровно 4 документа в missing_params и подписи

### Добавлено
- `CLIENT_DOCUMENT_PARAM_CODES`, `compute_client_document_missing()`, `client_document_list_needs_migration()` в `param_labels.py`.
- `OrderService.fix_legacy_client_document_params()`: при открытии upload-page, если в БД устаревшие/чужие коды (`floor_plan`, `connection_scheme`, `system_type` и т.д.), заменяет `missing_params` на полный канонический список из четырёх.
- Для `waiting_client_info` / `client_info_received` ответ `upload-page` всегда отдаёт в `missing_params` четыре канонических кода (чеклист и подписи), а факт «что ещё не прислали» для пайплайна хранится в БД после «Готово».

### Изменено
- `process_client_response` (Celery): `missing_params` = `compute_client_document_missing(uploaded)` вместо фильтрации устаревшего списка.
- Уточнены человекочитаемые названия четырёх документов в `param_labels`, `upload.html`, админке.

## [2026-04-02] — Категории файлов УУТЭ (FileCategory)

### Добавлено
- Значения `balance_act`, `connection_plan` в enum файлов; первая миграция Alembic `20260402_uute_file_category` (PostgreSQL): добавление значений в `file_category`, перенос `floor_plan` → `other`, нормализация `missing_params` (`floor_plan` → `balance_act`, удаление `connection_scheme` / `system_type`).
- Файл `docs/project.md` с описанием категорий файлов.

### Изменено
- `FileCategory`: вместо `floor_plan` — набор из четырёх категорий проектной документации клиента (`balance_act`, `connection_plan`, `heat_point_plan`, `heat_scheme`).
- `param_labels.py`, `tu_parser.determine_missing_params`, `upload.html` (`PARAM_LABELS`), админка (`uploadCategory`, подписи в списке файлов).
- Из автоматического `missing_params` после парсинга ТУ убраны `heat_load_details`, `connection_scheme`, `system_type` (коды вне нового enum ломали загрузку с 422).
- Образцы в `SAMPLE_DOCUMENTS` переименованы по новым кодам (файлы в `templates/samples/` при необходимости положить вручную).

## [2026-04-02] — Публичные upload-tu и submit для новой заявки

### Добавлено
- `POST /api/v1/landing/orders/{id}/upload-tu` — загрузка ТУ без `X-Admin-Key` (только статус `new`, категория TU на сервере).
- `POST /api/v1/landing/orders/{id}/submit` — запуск парсинга ТУ без ключа (те же проверки, что у `POST /pipeline/{id}/start`).
- Схема `PipelineResponse` в `app.schemas` (общая для пайплайна и лендинга).

### Изменено
- `upload.html`: для новой заявки используются пути `landing/.../upload-tu` и `landing/.../submit`; на этапе `new` разрешена только загрузка с типом «Технические условия».

## [2026-04-02] — Страница загрузки: новые заявки и waiting_client_info

### Добавлено
- Поле `order_status` в ответе `GET /api/v1/landing/orders/{id}/upload-page` и в схеме `UploadPageInfo` для выбора сценария на клиенте.

### Изменено
- `upload.html`: для статуса `new` отдельные публичные эндпоинты лендинга; для `waiting_client_info` — `client-upload` / `client-upload-done`.
- Для новых заявок в списке типов документа по умолчанию выбраны «Технические условия» (`tu`).
