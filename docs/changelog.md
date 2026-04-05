# Changelog

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
