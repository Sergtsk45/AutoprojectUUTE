# Changelog

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
