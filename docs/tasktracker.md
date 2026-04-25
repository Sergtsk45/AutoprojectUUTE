# Task tracker

> **Долговой backlog:** оперативный реестр незакрытых хвостов и отложенных
> задач — в [`docs/backlog.md`](backlog.md). Этот файл — хронология
> **выполненных/активных** задач; всё, что остаётся «на потом» после
> закрытия задачи, — переносим в backlog с ID `BL-XXX` и ссылкой.

## Задача: DXF-шаблон первой принципиальной схемы
- **Статус**: Завершена
- **Описание**: Для первой конфигурации `SchemeType.DEP_SIMPLE` добавлен DXF-шаблонный renderer, который превращает исходник DXF в SVG-фрагмент и передаёт его в существующую цепочку ГОСТ-рамки и PDF. Остальные 7 схем пока используют legacy programmatic renderer до подготовки исходников DXF/SVG.
- **Шаги выполнения**:
  - [x] Добавлен renderer `scheme_template_renderer.py` для `DEP_SIMPLE`.
  - [x] Подключён fallback: если DXF-шаблон недоступен или тип схемы не поддержан, используется старый renderer из `scheme_svg_renderer.py`.
  - [x] Добавлена runtime-копия шаблона `backend/templates/schemes/dxf/1_2_dep_simple.dxf`.
  - [x] Добавлены и обновлены тесты шаблонного рендера и интеграции.
  - [x] Исправлен тёмный фон `ezdxf` в SVG/PDF: фон отключён, графика принудительно рендерится чёрной.
  - [x] Выполнены финальные проверки Task 3.
- **Зависимости**: `ezdxf`, существующая цепочка `gost_frame_a3` / WeasyPrint PDF.

## Задача: Исправить скачивание PDF принципиальной схемы на `/upload`
- **Статус**: Завершена
- **Описание**: После генерации PDF схемы клиентская ссылка «Скачать PDF» указывала на несуществующий публичный маршрут `/api/v1/orders/{order_id}/files/{file_id}/download`, из-за чего браузер переходил обратно на сайт вместо скачивания файла. Добавлен публичный endpoint скачивания только для файлов категории `heat_scheme`, а фронт переключён на новый URL в пространстве `/api/v1/schemes/...`.
- **Шаги выполнения**:
  - [x] Прослежен фронтенд-флоу `scheme.js`: `POST /schemes/{order_id}/generate` → установка `href` для download-link.
  - [x] Подтверждена причина: публичного `/api/v1/orders/.../download` нет; существующий `/api/v1/admin/files/{file_id}/download` защищён admin-key.
  - [x] Добавлен regression-test на публичное скачивание с проверкой `FileResponse`.
  - [x] Добавлен `GET /api/v1/schemes/{order_id}/files/{file_id}/download` с фильтром по `order_id`, `file_id` и `FileCategory.HEAT_SCHEME`.
  - [x] `backend/static/js/upload/scheme.js` переключён на новый публичный маршрут.
- **Зависимости**: модуль конфигуратора схем (`scheme.js`) и API `scheme_generator.py`.

## Задача: Фаза C1+C2 — удаление legacy-статусов OrderStatus (2026-04-22)
- **Статус**: Завершена (частичный scope)
- **Описание**: Roadmap-фаза C предполагала удаление 4 legacy-статусов (`data_complete`, `generating_project`, `review`, `awaiting_contract`). По итогам разведки удалено только 3 — `AWAITING_CONTRACT` остался, так как активно используется в `payment.html`-ветке оплаты (bank_transfer + YooKassa-заглушка). C1 и C2 слиты в один PR, как предлагал roadmap §13.1.
- **Scope**:
  - **Удалено**: `data_complete`, `generating_project`, `review` из enum `OrderStatus` + соответствующие ключи/значения в `ALLOWED_TRANSITIONS`.
  - **Удалено**: 3 Celery-task-заглушки (`fill_excel`, `generate_project`, `initiate_payment_flow`) — были `TODO`-stubs без логики, в современный флоу никогда не попадали.
  - **Удалено**: legacy-ветка `REVIEW → initiate_payment_flow` в `pipeline.py:approve_project` и `REVIEW → COMPLETED` в `post_project_flow.py:send_completed_project`.
  - **Сохранено**: `AWAITING_CONTRACT` и task `process_company_card_and_send_contract` (используются в payment.html-ветке).
- **Маппинг данных**: `data_complete | generating_project | review → client_info_received` (безопасный «карантин» — из `CLIENT_INFO_RECEIVED` инженер вручную переведёт заявку дальше; см. `ALLOWED_TRANSITIONS[CLIENT_INFO_RECEIVED]`). На момент миграции прод-данных в legacy нет.
- **Шаги выполнения**:
  - [x] Ветка `refactor/audit-c1-c2-drop-legacy-statuses` от актуального `main`
  - [x] Alembic-миграция `20260422_uute_drop_legacy_order_statuses.py`: `UPDATE orders SET status='client_info_received' WHERE status IN (legacy)` + пересоздание типа `order_status` без 3 значений
  - [x] `models.py`: удалены 3 enum-значения, пересобран docstring, упрощён `ALLOWED_TRANSITIONS` (добавлен ручной переход `CLIENT_INFO_RECEIVED → AWAITING_CONTRACT` как замена удалённому `initiate_payment_flow`)
  - [x] `landing.py`: `_SURVEY_SAVE_ALLOWED` — убраны `DATA_COMPLETE`, `GENERATING_PROJECT`
  - [x] `contract_flow.py`: удалены 3 Celery-task (`fill_excel`, `generate_project`, `initiate_payment_flow`)
  - [x] `tasks/__init__.py`: убраны импорты/экспорты
  - [x] `pipeline.py:approve_project`: удалена legacy-ветка `REVIEW → initiate_payment_flow.delay()`, импорт `initiate_payment_flow` убран
  - [x] `post_project_flow.py:send_completed_project`: убрана ветка `REVIEW → COMPLETED`
  - [x] Фронт (admin + upload): 8 файлов — удалены ссылки на `data_complete`/`generating_project`/`review` в маппингах ярлыков/цветов/переходов
  - [x] `admin.html`: фильтр статусов — убраны 3 устаревших `<option>`, добавлены актуальные (`awaiting_contract`, `contract_sent`, `advance_paid`, `awaiting_final_payment`, `rso_remarks_received`)
  - [x] `payment.html`: `PRE_PAYMENT_STATUSES` — убраны 3 статуса
  - [x] `test_celery_tasks_package.py`: обновлён expected
  - [x] Новый тест `test_order_status_legacy_cleanup.py` — 3 smoke-теста (enum, ALLOWED_TRANSITIONS, отсутствие task-атрибутов)
  - [x] Регенерированы `openapi.json` + `types.ts` (через `backend/.venv` с pinned pydantic 2.9.2 / fastapi 0.115.0)
  - [x] Локально: ruff ✓, ruff format ✓, mypy ✓, pytest 66/66 ✓, npm run lint ✓, npx tsc --noEmit ✓, npx vitest run 15/15 ✓, node --check на 10 модулях ✓
- **Зависимости**: B3 (смержен).
- **Разблокирует**: будущую полную зачистку `AWAITING_CONTRACT` вместе с `payment.html` (отдельная продуктовая задача).
- **Риски**: средние. Удаление Celery-task-имён (`fill_excel`/`generate_project`/`initiate_payment_flow`) без drain очереди в проде теоретически может уронить воркер, если в RabbitMQ/Redis висит сообщение с удалённым именем. На проде задачи никогда не вызывались — риск только теоретический. Миграция требует коротких окон write-lock на `orders` (пересоздание типа enum) — рекомендуется прогнать ночью.
- **Rollback**: `alembic downgrade -1` (возвращает 3 значения в enum); `git revert` ветки — в коде всё возвращается как было. Данные заявок, переведённых из legacy в `client_info_received`, обратно не восстановятся (колонка-аудит по согласованию не добавлялась; восстановление — из бэкапа БД).

## Задача: Фаза E4 — декомпозиция `upload.html` на модули (2026-04-22)
- **Статус**: Завершена
- **Описание**: `backend/static/upload.html` (2323 строки, ~92 KB) разрезан на HTML-скелет + внешний CSS + 5 JS-файлов в `backend/static/js/upload/`. Применён тот же сценарий, что и в E3 (обычные `<script>`, не ES-модули): единственный inline-хендлер `onclick="toggleSurveyCollapse()"` продолжает работать без правок HTML. Поведение страницы `/upload/<id>` не изменилось.
- **Шаги выполнения**:
  - [x] Ветка `refactor/audit-e4-upload-html-modules`, каталог `backend/static/js/upload/`
  - [x] `css/upload.css` — весь прежний inline `<style>` (611 строк, ~16 KB)
  - [x] `js/upload/config.js` — `API_BASE`, `ORDER_ID`, словари (`PARAM_LABELS`, `PARAM_TO_SURVEY`, `SURVEY_REQUIRED_FIELDS`), наборы статусов (`POST_PARSE_STATUSES`, `CUSTOM_EDITABLE_STATUSES`), mutable state (`orderData`, `isNewOrder`, `surveySavedCustom`, `uploadedCategories`, таймеры/счётчики парсинг-поллинга)
  - [x] `js/upload/utils.js` — `escapeHtml`, `formatSize`, `formatMoneyRub`, `formatHttpDetail`, `showBanner`, `strVal`/`numVal`, `syncSubmitButtonState`, `showDocsOptionalHint`, `applySurveySavedVisuals`, `showSurveyError`/`hideSurveyError`, все `$*` DOM-refs
  - [x] `js/upload/survey.js` — опросный лист (collapse/lock/unlock/hide/show), hydrate из snapshot, маппинг `parsed_params → s_*`, нормализация типов (connection/system/building), badges (prefilled/needs-input), `collectSurveyData`, `validateSurveyFields`, submit-листенер; `toggleSurveyCollapse` экспортирован на `window`
  - [x] `js/upload/contract.js` — `renderContractMeta`, `setSignedContractAcceptedState`/`resetSignedContractState`/`showContractSentState`, `showUploadAlongsideSurveyIfNeeded`, `prefillSurveyFromSaved`, `validateSignedContractFile`, `uploadSignedContract`, функция `bindSignedContractHandlers()` для drag&drop/change
  - [x] `js/upload/upload.js` (entry) — `initCustomOrderUi`, `init`, `renderChecklist`, `renderCategoryOptions`, drag&drop основной зоны, `handleFiles`, `uploadFile`, submit-обработчик «Всё загружено», `showCompleted`, polling парсинга ТУ (`showParsingState`, `startParsingPoll`, `stopParsingPoll`, `showParsingTimeout`), вызовы `bindSignedContractHandlers()` и `init()`
  - [x] `upload.html` → skeleton + `<link rel="stylesheet">` + 5 `<script>` (порядок: config → utils → survey → contract → upload). Размер 92 153 → 21 762 байт (−76%), 2323 → 402 строк
  - [x] `node --check` на каждом из 5 модулей + склейке всех JS в один файл — синтаксис чистый
  - [x] pytest (63 теста, бэкенд) проходит локально
  - [x] frontend `npm run lint` чистый
  - [x] Единственный inline-хендлер `onclick="toggleSurveyCollapse()"` сохранён и подкреплён экспортом `window.toggleSurveyCollapse`
  - [x] `docs/changelog.md`, `docs/tasktracker.md`, `docs/project.md`, `CLAUDE.md`, ✅ в roadmap
- **Зависимости**: E3 (та же механика, те же конвенции для `StaticFiles`).
- **Разблокирует**: декомпозицию `payment.html` (992 строки) по тому же сценарию; подключение eslint/prettier к `backend/static/js/`; потенциальную миграцию на Vite-сборку с единым набором ES-модулей.
- **Риски**: низкие. Код перенесён 1-в-1, поведение эквивалентно. Тесты на `upload.html` в pytest отсутствуют — никаких тест-правок не потребовалось (в отличие от E3).
- **Rollback**: `git revert` ветки `refactor/audit-e4-upload-html-modules`.

## Задача: Фаза E3 (минимальный вариант) — декомпозиция `admin.html` на модули (2026-04-22)
- **Статус**: Завершена
- **Описание**: `backend/static/admin.html` (2873 строки, ~127 KB) разрезан на HTML-скелет + внешний CSS + 5 JS-файлов в `backend/static/js/admin/`. JS-модули подключаются как обычные `<script>` (не ES-модули) — это сохраняет все 15 inline `onclick`/`onchange` в HTML без переписывания: функции остаются в глобальной области. Поведение админки не изменилось.
- **Шаги выполнения**:
  - [x] Ветка `refactor/audit-e3-admin-html-modules`, каталоги `backend/static/css/` и `backend/static/js/admin/`
  - [x] `css/admin.css` — весь прежний inline `<style>` (~586 строк, ~18 KB)
  - [x] `js/admin/config.js` — `API_BASE`, `ORDER_ID_URL_RE`, `STATUS_*`, `POST_PARSE_STATUSES`, `SURVEY_*`, глобальное состояние поллингов
  - [x] `js/admin/utils.js` — `statusBadge`/`orderTypeBadge`, форматтеры дат/чисел, `esc`, `addKeyToUrl`, `isParsedParamsEmpty`, `showOrderAlert`
  - [x] `js/admin/views-parsed.js` — рендер parsed-params, survey, сравнительная таблица (`cmp*`, `buildParsedParamsTablesHtml`, `renderParsedParams`, `renderSurveyData`, все `*FromParams`)
  - [x] `js/admin/views-calc.js` — настроечная БД вычислителя (`loadCalcConfig`, `renderCalcConfig`, `renderCalcGroups`, `initCalcConfig*`, `saveCalcConfig`, `exportCalcConfigPdf`, `calcParamChanged` + UI-state)
  - [x] `js/admin/admin.js` — auth, `apiFetch`/`apiJSON`, навигация, 4 поллинга, `approveProject`, список заявок, карточка заявки, действия (`renderActions`/`runAction`/`sendEmail`/`uploadAdminFile`), `DOMContentLoaded`
  - [x] `admin.html` → skeleton + `<link rel="stylesheet">` + 5 `<script>` (порядок: config → utils → views-parsed → views-calc → admin). Размер 129 645 → 13 131 байт (−90%).
  - [x] `node --check` на каждом из 5 модулей — чистый синтаксис
  - [x] Все 12 функций, вызываемых из inline `onclick` (`doLogin`, `doLogout`, `refreshList`, `showList`, `showOrderScreen`, `uploadAdminFile`, `initCalcConfig*`, `saveCalcConfig`, `exportCalcConfigPdf`, `calcParamChanged`, `addKeyToUrl`), присутствуют в глобальной области
  - [x] Smoke-тест через `python3 -m http.server`: 200 OK на `/admin.html` и все 5 JS + CSS
  - [x] `docs/changelog.md`, `docs/tasktracker.md`, `docs/project.md`, `CLAUDE.md`, ✅ в roadmap
- **Зависимости**: нет (чистый refactor без изменения API).
- **Разблокирует**: дальнейшую декомпозицию `upload.html` (2322 строки) и `payment.html` (992 строки) по тому же сценарию; подключение eslint/prettier к `backend/static/js/`; потенциальную миграцию на Vite-сборку.
- **Риски**: низкие. Поведение не затронуто, код перенесён 1-в-1. Единственный риск — порядок подключения `<script>` и опечатки в путях — проверены через smoke-тест.
- **Rollback**: `git revert` ветки `refactor/audit-e3-admin-html-modules`.

## Задача: Фаза E2 — Vitest-тесты на транспортный слой фронта (2026-04-22)
- **Статус**: Завершена
- **Описание**: Vitest-покрытие фронта расширено с 5 до 15 тестов. Новый модуль `frontend/src/api.test.ts` фиксирует контракт фронт ↔ бэкенд для всех 4 публичных эндпоинтов лендинга: URL, метод, заголовки, сериализация, разбор ошибок (strings detail / FastAPI validation `[{msg}]` / HTTP fallback), multipart без ручного Content-Type, override `VITE_API_BASE_URL`. Тесты не требуют `@testing-library/react` и `jsdom` — используют нативные в Node 20 `fetch`/`FormData`.
- **Шаги выполнения**:
  - [x] `frontend/src/api.test.ts` (10 тестов) — 4 describe-блока по функциям + API_BASE override
  - [x] Fetch-моки через `vi.stubGlobal('fetch', vi.fn())`
  - [x] `vitest run` — 15/15 (прирост 5 → 15)
  - [x] `tsc --noEmit`, `npm run lint`, `npm run build` — зелёные
  - [x] `docs/changelog.md`, `docs/tasktracker.md`, `docs/project.md`, `CLAUDE.md`, плашка ✅ в roadmap
- **Зависимости**: E1 (типы `OrderRequest`/`SimpleResponse`/… из сгенерированного `types.ts` импортируются в тестах).
- **Разблокирует**: E3/E4 (можно рефакторить компоненты, уверенно зная, что транспортный слой не сломан).
- **Риски**: низкие. Тесты живут в существующем CI-job `frontend`, новая зависимость не добавлена.
- **Rollback**: `git revert` ветки `feat/audit-e2-frontend-tests`.

## Задача: Фаза E1 — Typed API через `openapi-typescript` (2026-04-22)
- **Статус**: Завершена
- **Описание**: Фронт переведён на автогенерируемые TS-типы из OpenAPI-спеки бэкенда. Рукопашные `interface OrderRequest/OrderCreatedResponse/SimpleResponse` в `frontend/src/api.ts` заменены на `components['schemas'][…]` из `frontend/src/api/types.ts`, который собирается скриптом `scripts/generate-api-types.sh` из текущего FastAPI-приложения. Добавлен CI-job `api-types-drift`: любое изменение Pydantic-схем без перегенерации клиента роняет билд.
- **Шаги выполнения**:
  - [x] Добавлена dev-зависимость `openapi-typescript@7.4.4` в `frontend/package.json`
  - [x] Скрипт `scripts/generate-api-types.sh`: `app.openapi()` → `openapi.json` → `types.ts`
  - [x] Закоммичены `frontend/src/api/openapi.json` и `types.ts` (+ README в каталоге)
  - [x] `frontend/src/api.ts` переписан на сгенерированные типы; контракт с компонентами (`EmailModal.tsx`, `KpRequestModal.tsx`) сохранён
  - [x] CI-job `api-types-drift` в `.github/workflows/ci.yml` (регенерация + `git diff --exit-code`)
  - [x] `tsc --noEmit` ✓, `npm run lint` ✓, `npm test` (5/5) ✓, `npm run build` ✓
  - [x] Backend без изменений: `ruff`, `ruff format --check`, `pytest` (63/63) — зелёные
  - [x] `docs/changelog.md`, `docs/tasktracker.md`, `docs/project.md`, `CLAUDE.md`
- **Зависимости**: B1.c (строгая типизация JSONB → точные OpenAPI-схемы) — смержена.
- **Разблокирует**: E3/E4 (декомпозиция фронта), будущие фичи админки на React.
- **Риски**: низкие. Контракт публичного API не меняется, артефакты детерминированные, CI-drift-check ловит рассинхрон сразу при PR.
- **Rollback**: `git revert` ветки `feat/audit-e1-typed-api`. Никаких изменений БД/ENV/бэк-кода.

## Задача: Фаза B1.c — Строгая типизация `OrderResponse` и публичных DTO (2026-04-22)
- **Статус**: Завершена
- **Описание**: JSONB-поля в `OrderResponse`, `UploadPageInfo`, `PaymentPageInfo` переведены со свободных `dict | None` на строгие Pydantic-модели из `app.schemas.jsonb` (`TUParsedData`, `SurveyData`, `CompanyRequisites`). Для маркера ошибки парсинга карточки предприятия (`{"error": "..."}`) выделен отдельный DTO `CompanyRequisitesError`; поле `company_requisites` — Union из этих двух моделей. `build_order_response` переписан: больше не вызывает `OrderResponse.model_validate(order)`, строит DTO вручную через accessor'ы `app.repositories.order_jsonb.*` — на грязных JSONB возвращает `None` + WARNING (поведение сохранено с B1.b).
- **Шаги выполнения**:
  - [x] Новая модель `CompanyRequisitesError` в `app/schemas/jsonb/company.py` + экспорт
  - [x] Типы в `OrderResponse` / `UploadPageInfo` / `PaymentPageInfo` (`parsed_params`, `survey_data`, `company_requisites`)
  - [x] Алиас `CompanyRequisitesResponse` + хелпер `company_requisites_for_response` в `app.schemas.schemas`
  - [x] Рефакторинг `build_order_response` (accessor-based, без `model_validate(order)`)
  - [x] `app/api/landing.py`: удалён локальный `_company_requisites_for_response`, используется общий хелпер; чтение JSONB через `get_parsed_params` / `get_survey_data` (типизированно)
  - [x] `tests/test_order_response_typing.py` (11 тестов): типизация полей, happy-path, error-маркер, legacy `missing_params`, грязные данные → `None`
  - [x] `ruff check` ✓, `ruff format --check` ✓, `mypy app` ✓
  - [x] `pytest tests/` — 61/61 локально и в Docker `python:3.12-slim` (CI parity)
  - [x] `docs/changelog.md`, `docs/tasktracker.md`, `docs/project.md`, `CLAUDE.md`
- **Зависимости**: B1.a (каркас Pydantic-схем), B1.b (accessor'ы) — смержены.
- **Риски**: средние.
  - Новый OpenAPI-контракт строже: поля, не входящие в `TUParsedData`/`SurveyData`/`CompanyRequisites`, фильтруются при сериализации (`extra='ignore'`). Внешним потребителям API, которые читали неканонические ключи — они исчезнут.
  - Для грязных исторических записей `parsed_params`/`survey_data` в ответе теперь `null` вместо исходного dict. Фронт-компоненты админки и upload-страницы штатно обрабатывают `null` (проверка `isParsedParamsEmpty`, ветки для express/custom).
  - `missing_params` сознательно оставлен `list[str] | None` — legacy-коды типа `floor_plan`/`connection_scheme` в БД ещё встречаются и чинятся только на upload-странице; переход на `list[FileCategory]` увязан с финальной data-миграцией (выделено в B2.c).
- **Rollback**: `git revert` коммита. Откат данных не требуется — БД не затрагивалась.
- **Следующий шаг**: E1 — typed API через `openapi-typescript` для автогенерации TS-клиента. Теперь JSONB-поля в OpenAPI описаны строго, TS-типы будут полноценными (не `Record<string, unknown>`).

## Задача: Фаза B2.b — Удаление legacy UPPER_CASE у `FileCategory` (2026-04-22)
- **Статус**: Завершена
- **Описание**: Удалён B2.a compat-shim `FileCategory._missing_` и `_B2_LEGACY_ALIASES` / `_canonicalize` в `backend/app/services/param_labels.py`. После B2.b API строго принимает только канонические snake_case lowercase значения; запросы вида `?category=BALANCE_ACT` теперь отвечают **422 Unprocessable Entity** (BREAKING CHANGE). Данные в `orders.missing_params` уже мигрированы в B2.a (Alembic `20260421_uute_fc_lower_missing`). PG-enum `file_category` (метки на `order_files.category`) не затрагивается — labels по-прежнему UPPER_CASE-имена членов Python.
- **Шаги выполнения**:
  - [x] Удалён `FileCategory._missing_` + обновлён docstring `FileCategory`
  - [x] Удалены `_B2_LEGACY_ALIASES`, `_canonicalize` в `param_labels.py`; `get_missing_items` / `get_sample_paths` упрощены (без канонизации)
  - [x] Удалены `BALANCE_ACT` / `CONNECTION_PLAN` из `_LEGACY_DOCUMENT_PARAM_CODES`
  - [x] Тест-модуль `test_file_category_b2.py` переписан: `accepts` → `rejects`, добавлены проверки на канонический lookup и игнорирование UPPER_CASE в `param_labels`. Покрытие: 14 тестов (было 12).
  - [x] `ruff check` ✓, `ruff format --check` ✓, `mypy` ✓ (на изменённых файлах + полный `mypy app` в CI-parity)
  - [x] `pytest tests/` 52/52 — локально и в Docker `python:3.12-slim` (CI parity)
  - [x] `docs/changelog.md` (BREAKING CHANGE), `docs/tasktracker.md`, `docs/project.md`, `CLAUDE.md`
- **Зависимости**: B2.a (`FileCategory.value` → lowercase + Alembic backfill `20260421_uute_fc_lower_missing`) — смержена.
- **Риски**: средние. Внешние клиенты, не обновлённые после B2.a, начнут получать 422. До деплоя — `grep "устаревший uppercase-алиас" /var/log/...` на проде должен быть пуст. Если в логах остались записи — отложить мерж и связаться с владельцами интеграций.
- **Rollback**: `git revert` коммита B2.b возвращает `_missing_` и `_canonicalize`. Откат данных не требуется (БД уже в lowercase).

## Задача: Фаза D4 — Async/sync граница в API (2026-04-22)
- **Статус**: Завершена
- **Описание**: Из `backend/app/api/landing.py` и `backend/app/api/emails.py` убран блокирующий `SyncSession()` в async-обработчиках. Уведомление инженеру о новой заявке вынесено в Celery-задачу `notify_engineer_new_order`; остальные SMTP-вызовы (`sample-request`, `partnership`, `kp-request`) обёрнуты в `asyncio.to_thread`. Админская ручная отправка `POST /emails/{order_id}/send` делегируется новому sync-хелперу `manual_send_email_sync` и запускается через `asyncio.to_thread`.
- **Шаги выполнения**:
  - [x] Новая Celery-задача `notify_engineer_new_order` в `tasks/client_response.py`, re-export из пакета `tasks/`
  - [x] `landing.POST /order`: `notify_engineer_new_order.delay(...)` вместо `with SyncSession()`
  - [x] `landing.POST /sample-request | /partnership | /kp-request`: `await asyncio.to_thread(...)` для SMTP
  - [x] `emails.POST /{order_id}/send`: `asyncio.to_thread(manual_send_email_sync, ...)` + `ManualSendError → HTTPException`
  - [x] Новый модуль `app/services/email/manual_send.py` (+ re-export в `app.services.email`)
  - [x] CI-шаг `forbid SyncSession() in backend/app/api/` в `.github/workflows/ci.yml`
  - [x] `tests/test_async_sync_boundary.py` (3 smoke-кейса) + обновлён `test_celery_tasks_package.py` (24 задачи)
  - [x] ruff ✓, mypy ✓, pytest 50/50 (локально и в CI-parity на Python 3.12)
  - [x] `docs/changelog.md`, `docs/tasktracker.md`, `docs/project.md`
- **Зависимости**: D1.b (пакет `tasks/`), D2 (пакет `email/`).
- **Разблокирует**: D5 (Celery hardening).

## Задача: Фаза D3 — Декомпозиция `contract_generator.py` + уборка дубликата `tasks.py` (2026-04-22)
- **Статус**: Завершена
- **Описание**: Монолит `contract_generator.py` (~1.3K строк) разбит на пакет `app/services/contract/` (`number_format`, `tu_embed`, `docx_utils`, `contract_docx`, `invoice`, `__init__.py`). `contract_generator.py` — re-export. Удалён дублирующий `tasks.py` (остаток доочистки после D1.b).
- **Шаги выполнения**:
  - [x] Вынесены модули по roadmap D3
  - [x] `mypy` strict-override для `app.services.contract.*`
  - [x] Удалён `backend/app/services/tasks.py`
  - [x] `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
  - [x] ruff ✓, mypy ✓, pytest 47/47
- **Разблокирует**: D4 (async/sync в API) по roadmap.

## Задача: Фаза D2 — Декомпозиция `email_service.py` (2026-04-22)
- **Статус**: Завершена
- **Описание**: Монолитный `email_service.py` (~1K строк) разбит на пакет `app/services/email/` (`smtp`, `idempotency`, `renderers`, `service`, `__init__.py`). Публичный API через `app.services.email_service` сохранён (re-export). `send_kp_request_notification` переведён на общий `send_smtp_message`.
- **Шаги выполнения**:
  - [x] `smtp.py` — MIME, `send_smtp_message`, `send_email`
  - [x] `idempotency.py` — `has_successful_email`, `log_email`
  - [x] `renderers.py` — Jinja2, все `render_*`
  - [x] `service.py` — все `send_*`
  - [x] `email_service.py` — shim на пакет
  - [x] `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`, `CLAUDE.md`
  - [x] ruff ✓, mypy ✓, pytest 47/47
- **Зависимости**: D1.b (желательно смержен для единого audit-контекста; на функциональность email не влияет).
- **Разблокирует**: D3 (`contract_generator.py`) — выполнена 2026-04-22.

## Задача: Фаза D1.a — Явные `name=` для Celery-задач (2026-04-22)
- **Статус**: Завершена
- **Описание**: Подготовительный шаг перед декомпозицией `services/tasks.py`. Всем 23 задачам в декораторе проставлено явное `name="app.services.tasks.<funcname>"` — имя в Celery registry больше не зависит от расположения функции в файловой системе. Без этого перенос задач в подмодули сломал бы `beat_schedule` и доставку сообщений из очередей.
- **Шаги выполнения**:
  - [x] Все 9 задач без параметров `@celery_app.task` → добавлено `name="..."`
  - [x] Все 13 задач с параметрами (`bind=True`, `max_retries`, …) → добавлено `name="..."` первым параметром
  - [x] Проверка: `celery_app.tasks.keys()` — 23 задачи под прежними именами `app.services.tasks.*`
  - [x] ruff ✓, mypy --strict ✓, pytest 46/46 ✓
- **Зависимости**: нет.
- **Риски**: нулевые — имена в registry совпадают до символа со старыми.
- **Разблокирует**: D1.b (декомпозиция `tasks.py` на `tasks/{_common, tu_parsing, client_response, contract_flow, post_project_flow, reminders}.py`).

## Задача: Фаза D1.b — Декомпозиция `services/tasks.py` (2026-04-22)
- **Статус**: Завершена
- **Описание**: Монолитный `tasks.py` (~1.8K строк) разбит на пакет `app/services/tasks/` с модулями `_common`, `tu_parsing`, `client_response`, `contract_flow`, `post_project_flow`, `reminders` и `__init__.py` с re-export'ами. Имена Celery-задач (D1.a) неизменны. Добавлен re-export `compute_client_document_missing` в пакет для тестов, патчевавших `app.services.tasks.*`.
- **Предварительные условия**: D1.a (явные `name=`) — в `main` и на проде.
- **Шаги выполнения**:
  - [x] `_common.py` — `SyncSession`, хелперы, `_normalize_client_requisites`, вложения/счета
  - [x] `tu_parsing.py` — `start_tu_parsing`, `check_data_completeness` (вызовы `client_response.*` по модулю)
  - [x] `client_response.py` — info_request, `process_due_info_requests`, уведомления, `process_client_response` (lazy-вызов `contract_flow.process_card_and_contract`)
  - [x] `contract_flow.py` — договор, платёж, parse/build contract с payment.html, заглушки fill/generate; **без** `resend`/`send_completed`
  - [x] `post_project_flow.py` — `_send_post_project_delivery`, `send_completed_project`, `resend_corrected_project`, RSO-нотификации
  - [x] `reminders.py` — beat-задачи
  - [x] `__init__.py` — re-export; удалён `tasks.py`
  - [x] `tests/test_celery_tasks_package.py` + правка `test_tu_parsed_engineer_notification.py` (патчи на `tu_parsing` / `client_response`)
  - [x] ruff ✓, mypy --strict ✓, pytest 47/47
  - [ ] **После деплоя**: `celery -A app.core.celery_app inspect registered` (ожидается 23× `app.services.tasks.*`)
- **Скрипт-референс**: `scripts/split_tasks_d1b.py` (документация `T()` — 1-based inclusive, не обрезать `)`).
- **Риски**: низкие при D1.a. Импорт-циклы сняты: `process_client_response` → lazy `contract_flow`; `tu_parsing` → `client_response` (без обратного импорта на уровне модуля).
- **Разблокирует**: D2 (`email_service.py`) — выполнена 2026-04-22.

## Задача: Фаза C — Упрощение стейт-машины (отложена, 2026-04-22)
- **Статус**: Отложена (awaiting product decision)
- **Описание**: Roadmap фазы C (§ 7 плана) предполагает удаление 4 legacy-статусов: `data_complete`, `generating_project`, `review`, `awaiting_contract`. При анализе обнаружено, что статус `awaiting_contract` **не мёртвый**: активно используется в `payment.html` (экраны «загрузка карточки предприятия» и «выбор способа оплаты»), эндпоинтах `POST /landing/orders/{id}/upload-company-card` и `POST /.../select-payment-method`, а также в таске `process_company_card_and_send_contract`.
- **Проблема**: в коде есть **две параллельные ветки** оплаты — новая (`client_info_received → contract_sent` через `process_card_and_contract`, клиент грузит карточку сразу) и legacy-совместимая (`review → awaiting_contract → contract_sent` через `initiate_payment_flow` + `payment.html`). Удаление `AWAITING_CONTRACT` требует либо отказа от payment.html-ветки (UX-регресс), либо её перестройки на другие статусы (отдельная продуктовая задача).
- **Решение (2026-04-22)**: отложить фазу C; сначала получить ответ от продакта, какая из веток актуальна — и только потом сносить legacy. Legacy-статусы не мешают в проде: это только косметическое загрязнение switch-веток.
- **Зависимости**: ждёт продуктового решения о судьбе payment.html-ветки загрузки карточки.
- **Риски**: удаление без решения сломает UX для клиентов, которые не прикладывают карточку сразу через upload.html.

## Задача: Фаза B3 — Alembic: чистые имена + индексы для листинга (2026-04-22)
- **Статус**: Завершена
- **Описание**: Переименованы две миграции под соглашение `YYYYMMDD_uute_*.py` (revision ID внутри сохранены — история прода не рвётся). Добавлены три индекса под типичные запросы админки (`orders(status, created_at DESC)` и аналогичные). Миграция — `CREATE INDEX CONCURRENTLY IF NOT EXISTS`, безопасно в проде.
- **Шаги выполнения**:
  - [x] Переименование `8867df9549c4_add_order_type_and_survey_data.py` → `20260403_uute_add_order_type_and_survey_data.py`
  - [x] Переименование `rename_standard_to_custom_order_type.py` → `20260403_uute_rename_order_type_value_to_custom.py`
  - [x] Новая миграция `20260422_uute_add_listing_indexes.py` с тремя `CONCURRENTLY`-индексами (+ downgrade)
  - [x] `__table_args__` в `Order` и `OrderFile` — синхронизация SQLAlchemy metadata с БД
  - [x] Проверка графа: `alembic.ScriptDirectory.walk_revisions()` → 1 голова, цепочка из 14 без веток
  - [x] Локально: ruff ✓, mypy --strict ✓, pytest 46/46 ✓
- **Зависимости**: B2.a — смержена и на проде.
- **Риски**: низкие. `CONCURRENTLY` не блокирует таблицу, индексы создаются idempotent (`IF NOT EXISTS`).
- **Деплой на проде**: после миграции прогнать `EXPLAIN ANALYZE SELECT * FROM orders WHERE status='NEW' ORDER BY created_at DESC LIMIT 50;` — ожидается `Index Scan Backward using ix_orders_status_created_at_desc`.

## Задача: Фаза B1.a — Pydantic-схемы для JSONB (каркас) (2026-04-21)
- **Статус**: Завершена
- **Описание**: Первый шаг фазы B1 roadmap раздела 3 аудита. Создан каркас типизации JSONB-полей `Order` (`parsed_params`, `survey_data`, `company_requisites`) без изменения поведения runtime. Валидация через `TypeAdapter` при чтении, `extra='ignore'` — терпимость к историческим записям.
- **Шаги выполнения**:
  - [x] `backend/app/schemas/jsonb/tu.py` — перенос `TUParsedData` из `services/tu_schema.py`
  - [x] `backend/app/schemas/jsonb/survey.py` — новая модель `SurveyData` (поля 1:1 с `collectSurveyData()` в upload.html)
  - [x] `backend/app/schemas/jsonb/company.py` — перенос `CompanyRequisites` из `services/company_parser.py`
  - [x] `backend/app/repositories/order_jsonb.py` — accessor-методы (`get_parsed_params` / `set_parsed_params` и т.д.) с WARNING-логом на невалидных данных
  - [x] Backward-compat shim'ы в `services/tu_schema.py` и `services/company_parser.py`
  - [x] `tests/test_jsonb_schemas.py` — 23 unit-теста (30/30 passed вместе со старыми)
  - [x] Локально: ruff check ✓, ruff format ✓, mypy ✓, pytest ✓
- **Зависимости**: A-фаза смержена. Разблокирует B1.b (миграция мест чтения) и B1.c (строгая типизация `OrderResponse`).
- **Риски**: низкие. Runtime не затронут. Shim'ы обеспечивают совместимость.

## Задача: Фаза B2.a — Нормализация `FileCategory` (non-breaking, 2026-04-21)
- **Статус**: Завершена
- **Описание**: Значения `FileCategory.BALANCE_ACT` и `FileCategory.CONNECTION_PLAN` переведены в snake_case lowercase (`balance_act`, `connection_plan`). Добавлен `_missing_` в enum — старые клиенты с UPPER_CASE продолжают работать один релиз. `param_labels`, фронт, исторические значения в `orders.missing_params` нормализованы. БД PG enum `file_category` не затрагивается (labels = имена членов, не `.value`).
- **Шаги выполнения**:
  - [x] `FileCategory.value` → lowercase + `_missing_` compat-shim
  - [x] `param_labels.py` — все ключи lowercase; legacy-канонизатор в `get_missing_items`/`get_sample_paths`
  - [x] `admin.html`, `upload.html` — UPPER_CASE значения заменены
  - [x] Alembic `20260421_uute_fc_lower_missing` — миграция значений в `orders.missing_params`
  - [x] Тесты `test_file_category_b2.py` (12/12 passed)
  - [x] `docs/changelog.md`, `docs/tasktracker.md`
- **Зависимости**: B1.b — смержена.
- **Риски**: низкие. `_missing_` покрывает все внешние интеграции со старым форматом один релиз.
- **Rollback**: revert коммита + `alembic downgrade` (downgrade-миграция возвращает UPPER_CASE).

## Задача: Фаза B2.b — Удаление legacy-uppercase у `FileCategory` (плановая)
- **Статус**: Завершена 2026-04-22 (см. запись «Фаза B2.b — Удаление legacy UPPER_CASE…» в начале файла).

## Задача: Фаза B1.b — Миграция мест чтения JSONB через accessor-методы (2026-04-21)
- **Статус**: Завершена
- **Описание**: Все bare-обращения `order.parsed_params["..."]` / `.survey_data["..."]` / `.company_requisites["..."]` в бизнес-коде переведены на типизированные accessor-методы из `app.repositories.order_jsonb`. Добавлена Pydantic-валидация входящего body в `POST /landing/orders/{order_id}/survey` (422 вместо тихого принятия мусора).
- **Шаги выполнения**:
  - [x] `app/api/landing.py` — `UploadPageInfo` / `PaymentPageInfo` через `get_*_dict`; `save_survey` валидирует через `SurveyData.model_validate`; хелпер `_company_requisites_for_response` отделяет error-маркеры
  - [x] `app/api/parsing.py` — чтение через accessor; `retrigger_parsing` через `set_parsed_params(order, None)`
  - [x] `app/api/calculator_config.py` — `survey.manufacturer` через типизированный accessor
  - [x] `app/services/calculator_config_service.py` — `resolve_calculator_type_for_express`, `init_config`, `init_config_sync` через accessor
  - [x] `app/services/tasks/_common.py` и `contract_flow.py` (пакет `tasks/`, после D1.b) — `set_company_requisites`, `get_parsed_params`, `get_company_requisites_dict` в `_collect_project_attachments`, `process_card_and_contract`, `process_company_card_and_send_contract`, `parse_company_card_task`
  - [x] `app/api/admin.py` — не содержит обращений к JSONB (данные идут через `OrderResponse` автоматически; типизация там — задача B1.c)
  - [x] `app/services/email_service.py` — не требует accessor (читает только `missing_params: list[str]`)
  - [x] `[[tool.mypy.overrides]] module = ["app.schemas.jsonb.*", "app.repositories.*"]` → `strict = true`
  - [x] Новые тесты на `*_dict` хелперы. Локально: ruff ✓, mypy strict ✓ (37 файлов), pytest ✓ (34/34)
- **Осознанные исключения** (оставлен raw-доступ, прокомментировано):
  - `_resolve_initial_payment_amount` — ключ `circuits` не описан в `TUParsedData` (legacy flat-формат); accessor его фильтровал бы `extra='ignore'`.
  - `start_tu_parsing` — `model_dump(exclude={"raw_text"})`: raw_text слишком велик для JSONB.
  - Маркеры `{"error": "..."}` в `company_requisites` — отдельный формат, не `CompanyRequisites`.
- **Зависимости**: B1.a — смержена.
- **Риски**: `save_survey` теперь строго валидирует body. Реальный фронт (`collectSurveyData()` в `backend/static/upload.html`) шлёт данные ровно по схеме — регрессий в продакшене не ожидается.


## Задача: Фаза B1.c — Строгая типизация `OrderResponse` (плановая)
- **Статус**: Завершена 2026-04-22 (см. запись «Фаза B1.c — Строгая типизация `OrderResponse`…» в начале файла).

## Задача: Фаза A4 — Frontend baseline (2026-04-21)
- **Статус**: Завершена
- **Описание**: Последний шаг фазы A roadmap раздела 3 аудита. Добавлен `frontend/.env.example` с документированной `VITE_API_BASE_URL`, подключён `vitest` + первый тестовый модуль (`src/utils/pricing.test.ts`, 5 тестов на чистые функции расчёта цены). Логика цен вынесена из `CalculatorSection.tsx` в `src/utils/pricing.ts` — единый источник правды по тарифам.
- **Шаги выполнения**:
  - [x] `frontend/.env.example` с `VITE_API_BASE_URL=/api/v1`
  - [x] `frontend/src/api.ts` — читает `import.meta.env.VITE_API_BASE_URL` с fallback на `/api/v1`
  - [x] Вынос pricing-логики → `src/utils/pricing.ts` (чистые функции)
  - [x] `src/utils/pricing.test.ts` — 5 тестов (5/5 passed локально)
  - [x] `vitest` в devDependencies + скрипты `test`/`test:watch`
  - [x] Секция `test` в `vite.config.ts`
  - [x] Шаг `Test (vitest)` в CI frontend job
  - [x] `CalculatorSection.tsx` использует новый util — поведение UI идентично
  - [x] Локально: `npm test` ✓, `npm run lint` ✓, `npm run build` ✓
- **Зависимости**: фаза A (A1→A2→A3→A4) теперь полностью закрыта. Разблокирует фазу B.
- **Риски**: низкие. Prod без `.env` → fallback `/api/v1` (совпадает с предыдущим hardcoded значением). UI калькулятора не изменился.

## Задача: Фаза A3 — GitHub Actions CI (2026-04-21)
- **Статус**: Завершена
- **Описание**: Добавлен `.github/workflows/ci.yml` с четырьмя активными job-ами: lint-type (ruff+mypy), tests (pytest), frontend (lint+build), pre-commit. Workflow запускается на `push` в любую ветку и `pull_request` в `main`, с `cancel-in-progress` для экономии минут GHA. Job `alembic` (upgrade/downgrade на чистом postgres:16) временно отключён из-за структурного долга (см. задачу «Alembic initial migration»).
- **Шаги выполнения**:
  - [x] `.github/workflows/ci.yml` (4 активных job-а)
  - [x] Исправлен `EmailModal.tsx`: `catch (err: any)` → `catch (err: unknown)` + narrowing
  - [x] CI-бейдж добавлен в `README.md`
  - [x] Пост-фикс: убран `pip install -e backend[dev]` (в `pyproject.toml` нет `[build-system]`), dev-deps ставятся напрямую с теми же версиями; `pythonpath = ["."]` + `testpaths = ["tests"]` в `[tool.pytest.ini_options]`; sys.path-shim в `backend/alembic/env.py`
  - [x] Тесты pytest проходят локально на свежем venv (7/7 passed)
- **Зависимости**: A2 смержен.
- **Риски**: низкие. Runtime не затронут, правки только в CI-конфиге и env.py (sys.path-вставка безвредна в Docker).

## Задача: Alembic initial migration (chore/alembic-initial-migration)
- **Статус**: Не начата
- **Описание**: В репозитории нет initial-миграции. Первая в цепочке (`20260402_uute_fc`) уже использует таблицу `order_files`, которая создавалась ранее (вне git). В prod БД живёт с предыдущих релизов — миграции работают инкрементально; но `alembic upgrade head` на чистом Postgres падает: `UndefinedTableError: relation "order_files" does not exist`. Из-за этого CI job `alembic upgrade/downgrade` был отключён.
- **Шаги выполнения**:
  - [ ] Снять схему с prod БД: `pg_dump --schema-only --no-owner --no-privileges uute_db > /tmp/prod_schema.sql`
  - [ ] Сравнить с метадатой моделей через `alembic revision --autogenerate` на чистой БД — получить diff
  - [ ] Написать `20260101_initial_schema.py` — создаёт все таблицы, которых не хватает «до base» (orders, order_files, users и т.д.), с `down_revision = None`
  - [ ] Сдвинуть `down_revision` у `20260402_uute_fc` на новый initial
  - [ ] Проверить на чистом postgres:16: `alembic upgrade head` → `downgrade base` → `upgrade head` без ошибок
  - [ ] В проде: `alembic stamp 20260101_initial_schema` перед первым деплоем с новой цепочкой (в prod initial не применяется, только помечается)
  - [ ] Включить обратно `alembic` job в `.github/workflows/ci.yml`
- **Зависимости**: нет. Делается отдельным PR после стабилизации A-фазы.
- **Риски**: высокие без аккуратности — неверный `alembic stamp` на проде = двойное применение миграций. Проверять на staging/dev клоне БД.

## Задача: Фаза A2 — pyproject + ruff + mypy + pre-commit (2026-04-21)
- **Статус**: Завершена
- **Описание**: Настроены dev-инструменты по roadmap раздела 3 аудита (фаза A2). Добавлены `backend/pyproject.toml` и `.pre-commit-config.yaml`, описаны в `CLAUDE.md`. Код отформатирован один раз через `ruff format` (34 файла), pre-commit `--all-files` зелёный.
- **Шаги выполнения**:
  - [x] `backend/pyproject.toml`: `[project]`, `[project.optional-dependencies.dev]`, `[tool.ruff]` (line-length 100, target py312, extend-exclude=alembic), `[tool.ruff.lint]` (E/F/W/I/UP/B/RUF + baseline-ignore), `[tool.ruff.format]`, `[tool.mypy]` (strict=false + `app.*` ignore_errors), `[tool.pytest.ini_options]`
  - [x] `.pre-commit-config.yaml`: pre-commit-hooks v4.6.0 (+ check-yaml/toml/large-files), ruff-pre-commit v0.15.11 (ruff-check + ruff-format), mirrors-mypy v1.11.2 с runtime-deps
  - [x] `CLAUDE.md`: раздел «Dev-инструменты»
  - [x] `ruff format backend/` — 34 файла отформатированы, поведение не меняется
  - [x] Автофиксы end-of-file-fixer / trailing-whitespace на docs/ и frontend/
  - [x] `pre-commit run --all-files` — **все 9 хуков зелёные**
- **Baseline-ignores (снимать отдельным PR `chore/audit-ruff-cleanup`)**:
  - Ruff: I001, UP017, UP035, B904, UP042, F401, F541, RUF059, E402, RUF022, B905, F821, F841, RUF100
  - Mypy: `app.*` целиком (ignore_errors = true) до фазы D
- **Зависимости**: A1 смержен; A3 (GitHub Actions CI) идёт следом и использует эти же конфиги.
- **Риски**: Runtime не затронут (prod-образ из `requirements.txt`). Разработчикам нужно один раз выполнить `pre-commit install` локально.

## Задача: Фаза A1 — пути к фронту и uploads через Settings (2026-04-21)
- **Статус**: Завершена
- **Описание**: Выполнен первый PR фазы A roadmap раздела 3 аудита. Убран захардкоженный `FRONTEND_DIR = Path("/app/frontend-dist")` из `backend/app/main.py`, пути вынесены в `Settings.frontend_dist_dir` и `Settings.upload_dir` с factory-дефолтами (prod → абсолютные пути, dev → относительные к корню репо). Обе переменные переопределяются через ENV (`FRONTEND_DIST_DIR`, `UPLOAD_DIR`).
- **Шаги выполнения**:
  - [x] `backend/app/core/config.py`: добавлены `_default_frontend_dist_dir`, `_default_upload_dir`, `frontend_dist_dir`, переписан `upload_dir` на factory-дефолт
  - [x] `backend/app/main.py`: `FRONTEND_DIR = settings.frontend_dist_dir`
  - [x] `backend/.env.example`: задокументированы обе переменные; `FRONTEND_DIST_DIR` закомментирован (auto-fallback)
  - [x] `CLAUDE.md`: обновлена таблица ENV-переменных
  - [x] Smoke-тесты: dev-пути вычисляются корректно, переопределение через ENV работает
  - [x] `python3 -m compileall` + `ReadLints` — без ошибок
- **Зависимости**: разблокирует A2 (`pyproject.toml` + ruff + mypy + pre-commit). После merge PR — `docker compose up -d --build backend` на проде не требуется (обратно-совместимо).
- **Риски**: prod читает `/app/frontend-dist` и `/var/uute-service/uploads` как раньше (auto-fallback); dev SPA-маршруты перестают давать 404 при наличии `frontend/dist`.

## Задача: Снять ruff-baseline ignores (chore/audit-ruff-cleanup)
- **Статус**: Не начата
- **Описание**: После A2 в `backend/pyproject.toml` временно отключены 14 правил ruff (см. блок «TODO: снять в chore/audit-ruff-cleanup»). Нужно пройтись отдельным PR: включать правила по одному, править нарушения (часть — автофиксом `ruff check --fix`), тестировать, коммитить.
- **Шаги выполнения**:
  - [ ] I001 (unsorted-imports, 32) — автофикс
  - [ ] UP017 (datetime.UTC, 19) — автофикс
  - [ ] UP035 (deprecated-import, 10) — автофикс
  - [ ] B904 (raise from в except, 13) — ручной проход
  - [ ] UP042 (StrEnum, 5) — перепроверить совместимость Pydantic v2
  - [ ] F401 (unused-import, 5) — автофикс
  - [ ] F541 (f-string без placeholder, 5) — автофикс
  - [ ] F821 (undefined-name в `calculator_config_service.py:274`) — починить forward-reference
  - [ ] RUF059, E402, RUF022, B905, F841, RUF100 — штучно
- **Зависимости**: A2 смержен.
- **Приоритет**: средний (не блокирует фазы B/C/D, но чем раньше — тем строже последующая проверка).

## Задача: UX — показывать detail ответа при 422 на `/pipeline/{id}/resend-corrected-project` (2026-04-21)
- **Статус**: Не начата
- **Описание**: При smoke-тесте после деплоя 2026-04-21 инженерный эндпоинт `POST /pipeline/{order_id}/resend-corrected-project` отвечает `422 Unprocessable Entity` в трёх бизнес-сценариях (см. `backend/app/api/pipeline.py:267-314`): нет `RSO_REMARKS`, нет `GENERATED_PROJECT`, либо последний `GENERATED_PROJECT` старше/равен последним `RSO_REMARKS`. Сам код корректен (защищает от отправки клиенту того же файла), но админка показывает только «Unprocessable Entity» без `detail`, из-за чего инженер не понимает, какое условие не выполнено.
- **Шаги выполнения**:
  - [ ] Проверить в `backend/static/admin.html` обработчик ошибки для кнопки «Повторно отправить исправленный проект» — читается ли `response.json().detail` и показывается ли в тосте/алерте
  - [ ] Если нет — вывести `detail` в UI (и для других pipeline-эндпоинтов, где 400/422 несут осмысленный текст)
  - [ ] Добавить короткую подсказку в самой кнопке/секции: «Перед повторной отправкой загрузите новую версию проекта в категорию "Готовый проект"»
  - [ ] Smoke-тест: три сценария 422 → видны три разных сообщения из `detail`
  - [ ] Запись в `docs/changelog.md`
- **Зависимости**: нет; эта задача войдёт в фазу E3 roadmap раздела 3 (декомпозиция `admin.html`) или может быть сделана раньше как точечный UX-фикс.
- **Приоритет**: низкий (не блокирует работу, это UX).

## Задача: Восстановить пропущенную prod-миграцию advance_payment_model (2026-04-20)
- **Статус**: Завершена
- **Описание**: При проверке перед деплоем обнаружено, что миграция `87fcef6f52ff_20260415_uute_advance_payment_model.py` и шаблон `backend/alembic/script.py.mako` существуют только на prod-сервере (`~/uute-project/`) и никогда не коммитились в git. Миграция физически применена в prod-БД (создала колонки `advance_amount`, `advance_paid_at`, `payment_method`, …), но на чистой БД (новый стенд, CI) `alembic upgrade head` их не создаст — модель `Order` при первом запросе упадёт. Восстановлено путём: вставки миграции в репозиторий и корректировки `down_revision` у `20260416_uute_signed_contract_enums`, чтобы цепочка стала линейной.
- **Шаги выполнения**:
  - [x] Получено содержимое миграции и `script.py.mako` с prod (`ubuntu@n8n:~/uute-project`)
  - [x] Проверено, что на prod `alembic_version` = `20260416_uute_tu_parsed_notification`; колонки `advance_amount`/`advance_paid_at` присутствуют в модели `Order`, но ни одна git-миграция их не создаёт
  - [x] Подтверждено отсутствие пересечений с другими миграциями (enum-значения, добавляемые `87fcef6f52ff`, уникальны; все остальные `ALTER TYPE ADD VALUE` идемпотентны за счёт `IF NOT EXISTS` / `DO $body$`)
  - [x] Добавлены `backend/alembic/versions/87fcef6f52ff_20260415_uute_advance_payment_model.py` и `backend/alembic/script.py.mako`
  - [x] В `20260416_uute_signed_contract_enums.py` переключён `down_revision` на `"87fcef6f52ff"`
  - [x] Проверен граф миграций (скриптом Python): одна голова `20260416_uute_tu_parsed_notification`, линейная цепочка из 12 ревизий от `20260402_uute_fc`
  - [x] Записи в `docs/changelog.md` и `docs/tasktracker.md`
- **Риски и mitigation**:
  - На prod `alembic upgrade head` = nothing to do (current = head). Проверено вручную.
  - На dev/CI clean БД вся цепочка применится линейно (12 ревизий).
  - Downgrade миграций теперь проходит через `87fcef6f52ff`; если кто-то делал `alembic downgrade` до `20260412_uute_calc_configs` — теперь придётся откатиться через `87fcef6f52ff` (это снимет и колонки, и index). Для prod это не используется.
- **Зависимости**: блокирует деплой раздела 2 аудита до мерджа. После мерджа — безопасно делать `docker compose up -d --build backend`.
- **Follow-up (раздел 3 аудита)**: в фазе A3 (GitHub Actions CI) обязательно добавить job «alembic upgrade head на пустой Postgres» — это моментально ловило бы такие расхождения.

## Задача: Раздел 3 аудита — roadmap поддерживаемости и архитектуры (2026-04-20)
- **Статус**: В процессе (утверждение плана)
- **Описание**: Составлен подробный roadmap реализации раздела 3 аудита 2026-04-20 (архитектурные проблемы: «толстые» модули, async/sync смешивание, legacy-статусы, нетипизированные JSONB, несогласованный `FileCategory`, захардкоженные пути, отсутствие CI/инструментов, неиспользуемые зависимости, Celery-конфиг, миграции без единого стиля, отсутствие индексов). Документ определяет 6 фаз выполнения, последовательность ~18 PR, критерии готовности и риски.
- **Шаги выполнения**:
  - [x] Написан roadmap и сохранён в [`docs/plans/2026-04-20-audit-section-3-maintainability-roadmap.md`](plans/2026-04-20-audit-section-3-maintainability-roadmap.md)
  - [x] Запись в `docs/changelog.md` и `docs/tasktracker.md`
  - [x] Согласованы ответы на «Открытые вопросы» (§ 13.1 roadmap, 2026-04-21):
    - Legacy-статусы — живых заявок нет, тестовые удаляемы → фаза C упрощается (C1+C2 можно одним PR)
    - FileCategory — через два релиза (non-breaking → breaking)
    - `admin.html` декомпозиция — решение отложено, пока планируем минимальный вариант
    - Sentry, `psycopg3`, GitHub Actions, отсутствие coverage gate — приняты дефолты, ждут финального подтверждения в первом PR фазы A
  - [~] Фаза A (Фундамент): 4 PR — [x] A1 пути, [x] A2 pyproject+ruff+mypy+pre-commit, [x] A3 GitHub Actions CI, [ ] A4 frontend baseline
  - [ ] Фаза B (Типизация данных): 3 PR — B1 Pydantic-схемы для JSONB, B2 нормализация `FileCategory`, B3 миграции + индексы
  - [ ] Фаза C (Упрощение стейт-машины): 2 PR — C1 data-миграция legacy-статусов, C2 удаление legacy из enum
  - [ ] Фаза D (Декомпозиция): 5 PR — D1 `tasks.py`, D2 `email_service.py`, D3 `contract_generator.py`, D4 async/sync граница, D5 Celery hardening
  - [ ] Фаза E (Frontend): 4 PR — E1 typed API, E2 vitest, E3 `admin.html` модули, E4 `upload.html`
  - [ ] Фаза F (Зависимости): 1 PR — F1 унификация на `psycopg[binary] v3`
- **Зависимости**: разделы 1 и 2 аудита закрыты (`chore/audit-cleanup-docs`, `security/audit-hardening`). Строгий порядок фаз: A → B → C → D → F; E параллельно после A.
- **Оценка**: ~35 чел·дней + ~10 дней резерв на ревью/регрессы ≈ 1.5–2 месяца wall-time при 50 % загрузке.

## Задача: Срочные правки безопасности (раздел 2 аудита, 2026-04-20)
- **Статус**: Завершена
- **Описание**: Закрыты пункты 1, 2, 3, 6 раздела «Срочно (безопасность)» из аудита. Пункт 4 (rate-limit `/landing/*`) согласовано вынести на уровень Caddy в отдельной задаче. Пункт 5 (`.gitignore`) уже закрыт в предыдущей задаче 2026-04-20.
- **Шаги выполнения**:
  - [x] CORS: `Settings.cors_origins`, дефолт `["https://constructproject.ru"]`, `main.py` использует whitelist вместо `*`
  - [x] `verify_admin_key`: `secrets.compare_digest`, deprecated `_k` с WARNING в логах и маскированным выводом ключа
  - [x] `config.py`: `admin_api_key` (≥16 симв.), `openrouter_api_key`, `smtp_password` без дефолтов — `Settings()` падает на старте без них
  - [x] `landing.py`: `except Exception: pass` → `logger.exception(...)`
  - [x] `backend/.env.example`: разметка `[REQUIRED]`, `CORS_ORIGINS`, инструкция по генерации `ADMIN_API_KEY`
  - [x] Smoke-тесты: `Settings()` без env падает с ожидаемой ошибкой; с env — стартует; CORS_ORIGINS парсится из JSON; `verify_admin_key` отрабатывает header/`_k`/wrong/missing
  - [x] `python -m compileall backend/app` — без ошибок; `ReadLints` — чисто
  - [x] Обновлены `CLAUDE.md`, `docs/changelog.md`, `docs/tasktracker.md`
- **Зависимости / деплой**:
  - На сервере перед `docker compose up -d --build backend` убедиться, что в `~/uute-project/backend/.env` есть значения `ADMIN_API_KEY`, `OPENROUTER_API_KEY`, `SMTP_PASSWORD` и заполнен `CORS_ORIGINS` (JSON-список с прод-доменом). Без этого backend упадёт на старте.
  - Следующий шаг — раздел 3 аудита (поддерживаемость): декомпозиция `tasks.py` / `email_service.py` / `contract_generator.py`, типизация JSONB, нормализация enum.

## Задача: Уборка документации и репозитория после аудита (2026-04-20)
- **Статус**: Завершена
- **Описание**: По итогам полного аудита проекта закрыт пункт 1 рекомендаций — устранён мусор в репозитории, архивированы завершённые трекеры/планы, переименованы файлы с проблемными именами, синхронизированы ссылки в коде и документации, актуализирован `CLAUDE.md`.
- **Шаги выполнения**:
  - [x] Создан `docs/archive/2026-Q2/` с подкаталогами `plans/`, `superpowers/plans/`, `superpowers/specs/`
  - [x] Перенесены завершённые трекеры: `payment-advance-tasktracker.md`, `smart-survey-tasktracker.md`, `two-option-order-tasktracker.md`, `tasktracker-soprovod.md`, `tasktrecker-otchet-parsing.md`, `tasktrecker-progrssbar.md`, `plan-unified-upload-contract.md`
  - [x] Перенесены реализованные планы: `docs/plans/2026-04-16-*.md` (5 шт), `docs/superpowers/plans/*` (6 шт), `docs/superpowers/specs/*` (3 шт); пустые каталоги удалены
  - [x] Удалены: `backup_20260411.sql`, `frontend/.env`, `cursorrules`, `.cursor/rules/calculator-config-design.md:Zone.Identifier`, дубликат `docs/opros_list_form.pdf`, `docs/rekvizit_acc.md` (с реальными реквизитами; не был в git)
  - [x] Переименованы: `docs/kontrakt_ukute_template (2).md` → `docs/kontrakt_ukute_template.md`; `docs/scheme-generator-roadmap (1).md` → `docs/scheme-generator-roadmap.md`
  - [x] Перенесён `docs/cities_from_table1.md` → `backend/calculator_templates/cities_from_table1.md`
  - [x] Обновлён `.gitignore`: `*.sql`, `*Zone.Identifier`, `docs/rekvizit_acc.md`, `docs/secrets/`, `.secrets/`
  - [x] Обновлены ссылки на переименованные/перенесённые файлы: `docs/project.md`, `docs/changelog.md`, `docs/tasktracker.md`, `backend/app/services/contract_generator.py`
  - [x] `frontend/package.json`: `name` → `uute-landing`, добавлены `description` и `version` `0.1.0`
  - [x] `CLAUDE.md`: актуализирована стейт-машина (`OrderStatus` с веткой оплаты и замечаний РСО), раздел «Текущий статус разработки» под фактический production, структура `docs/` с `archive/`
  - [x] Записи в `docs/changelog.md` и `docs/tasktracker.md`
- **Зависимости**: следующий шаг аудита — раздел 2 (срочные правки безопасности: CORS, `verify_admin_key`, дефолты секретов, rate-limit)

## Задача: SVG библиотека условных обозначений и ГОСТ-рамка для схем УУТЭ (2026-04-20)
- **Статус**: Завершена
- **Описание**: Реализованы чисто строковые генераторы SVG для инженерных схем теплоснабжения и обёртки чертежных форматов A3/A4 с основной надписью; без внешних зависимостей, таблица параметров тепловычислителя на `<rect>`/`<text>`.
- **Шаги выполнения**:
  - [x] Добавить `scheme_svg_elements.py` с элементами и вспомогательными функциями
  - [x] Добавить `scheme_gost_frame.py` с `gost_frame_a3` / `gost_frame_a4`
  - [x] Обновить `docs/project.md`, `docs/changelog.md`, `docs/tasktracker.md`
- **Зависимости**: дальнейшая интеграция с превью/экспортом схем (вне этого коммита)

## Задача: Автоматизация принципиальных схем ИТП — конфиг и маппинг (2026-04-19)
- **Статус**: Завершена
- **Описание**: Заложить основу для генерации принципиальных схем теплового пункта: Pydantic-схемы выбора одной из 8 типовых конфигураций, проверка допустимых сочетаний (зависимая/независимая, клапан, ГВС, вентиляция), русские подписи для UI и извлечение подстановок в SVG из `parsed_params` заявки (`Order.survey_data` / последующая интеграция с `FileCategory.HEAT_SCHEME` — вне этого коммита).
- **Шаги выполнения**:
  - [x] Реализовать `backend/app/schemas/scheme.py` (`SchemeType`, `SchemeConfig`, `SchemeParams`, API-модели)
  - [x] Реализовать `backend/app/services/scheme_service.py` (маппинг, метки, `extract_scheme_params_from_parsed`)
  - [x] Добавить запись в `docs/changelog.md` и `docs/tasktracker.md`
- **Зависимости**: ветка `feature/avtomatizaciya-postroeniya-shem`, структура `TUParsedData` в `backend/app/services/tu_schema.py`

## Задача: DOCX договор — шаблон v2 и компактная вёрстка (2026-04-19)
- **Статус**: Завершена
- **Описание**: Синхронизировать генератор договора с новым шаблоном `kontrakt_ukute_template.md` и сделать компактную вёрстку договора: шрифт 10 pt, минимальные интервалы между строками и абзацами.
- **Шаги выполнения**:
  - [x] Сверить новый шаблон `docs/kontrakt_ukute_template.md` с `contract_generator.py`
  - [x] Обновить тексты разделов 1–15 и приложений 1–3 в генераторе
  - [x] Добавить компактный стиль параграфов для договора и таблиц
  - [x] Обновить `docs/project.md`, `docs/changelog.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/app/services/contract_generator.py`, `docs/kontrakt_ukute_template.md`

## Задача: DOCX договор — вставка ТУ и контроль размера (2026-04-19)
- **Статус**: Завершена
- **Описание**: Встроить страницы PDF ТУ в Приложение 2 договора с лестницей DPI и fallback без растра при превышении ~25 МБ; передавать путь к ТУ и поля из `parsed_params` из Celery-задач.
- **Шаги выполнения**:
  - [x] PyMuPDF в `requirements.txt`, helpers рендера/очистки PNG и цикл `generate_contract`
  - [x] Обновить `process_card_and_contract` и `process_company_card_and_send_contract`
  - [x] Актуализировать `docs/project.md`, `docs/changelog.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/app/services/contract_generator.py`, `backend/app/services/tasks.py`

## Задача: Безопасный predicate миграции статуса замечаний РСО (2026-04-16)
- **Статус**: Завершена
- **Описание**: Сделать безопасной исходную Alembic-миграцию `20260416_uute_rso_remarks_status`, чтобы backfill в `RSO_REMARKS_RECEIVED` выполнялся только для заявок без `final_paid_at` и не возвращал уже обработанные замечания после более нового `GENERATED_PROJECT`.
- **Шаги выполнения**:
  - [x] Усилить регрессионный тест `backend/tests/test_rso_status_migration.py` под итоговый безопасный predicate
  - [x] Добавить в `backend/alembic/versions/20260416_uute_rso_remarks_status.py` guard `o.final_paid_at IS NULL`
  - [x] Сохранить в исходной миграции `autocommit_block()` и хронологию `latest_remarks_at >= latest_project_at`
  - [x] Удалить follow-up backfill-файлы как лишние для финального варианта
  - [x] Обновить `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/alembic/versions/20260416_uute_rso_remarks_status.py`

## Задача: Race-fix сворачивания настроечной БД при poll-обновлениях (2026-04-16)
- **Статус**: Завершена
- **Описание**: Зафиксировать в репозитории продовый фикс для `admin.html`, чтобы poll-обновления той же заявки не переоткрывали блок «Настроечная БД вычислителя» поверх пользовательского клика на сворачивание.
- **Шаги выполнения**:
  - [x] Добавить регрессионный тест на `loadCalcConfig()` и восстановление состояния только при смене заявки
  - [x] Ограничить вызов `applyCalcConfigDetailsState(orderId)` случаями смены заявки
  - [x] Сохранить обновление `dataset.orderId` без принудительного изменения `details.open` на poll-обновлениях той же заявки
  - [x] Обновить `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/static/admin.html`, `backend/tests/test_admin_post_project_actions.py`

## Задача: Починка действий инженера для замечаний РСО (2026-04-16)
- **Статус**: Завершена
- **Описание**: Исправить админку так, чтобы post-project действия инженера не исчезали после загрузки замечаний РСО и были доступны как по статусу `rso_remarks_received`, так и по derived-флагу активных замечаний.
- **Шаги выполнения**:
  - [x] Проверить текущую логику `renderActions` и backend-эндпоинтов post-project ветки
  - [x] Добавить регрессионный тест на fallback по `has_rso_remarks`
  - [x] Починить `backend/static/admin.html`
  - [x] Обновить `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/static/admin.html`, `backend/tests/test_admin_post_project_actions.py`

## Задача: UX настроечной БД в админке (2026-04-16)
- **Статус**: Завершена
- **Описание**: Зафиксировать поведение карточки настроечной БД в админке: по умолчанию свёрнута только при первом открытии конкретной заявки, далее запоминает ручное состояние инженера; кнопка `Сохранить` после успешного сохранения снова становится неактивной до следующего редактирования.
- **Шаги выполнения**:
  - [x] Исследовать текущую реализацию `calcConfigDetails` и dirty-state кнопки `Сохранить`
  - [x] Добавить per-order хранение состояния раскрытия в `backend/static/admin.html`
  - [x] Усилить reset dirty-state после успешного сохранения настроечной БД
  - [x] Обновить `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/static/admin.html`

## Задача: Возврат email-уведомления инженеру после загрузки ТУ (2026-04-16)
- **Статус**: Завершена
- **Описание**: Вернуть письмо инженеру после успешной загрузки и парсинга ТУ, чтобы инженер снова получал email в момент, когда в админке уже доступны распарсенные данные и заявка перешла в ожидание документов от клиента.
- **Шаги выполнения**:
  - [x] Добавить регрессионный тест на постановку Celery-уведомления из `check_data_completeness`
  - [x] Добавить отдельную задачу `notify_engineer_tu_parsed` и новый `EmailType` для события парсинга ТУ
  - [x] Добавить шаблон письма инженеру с `missing_params`, статусом заявки и ссылкой на админку
  - [x] Обновить `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/app/services/tasks.py`, `backend/app/services/email_service.py`, `backend/templates/emails/tu_parsed_notification.html`, `backend/alembic/versions/20260416_uute_tu_parsed_notification_enum.py`

## Задача: Исправление enum-миграции статуса замечаний РСО (2026-04-16)
- **Статус**: Завершена
- **Описание**: Исправить Alembic-миграцию `RSO_REMARKS_RECEIVED` под ограничение PostgreSQL, где новый enum нельзя использовать в той же транзакции, в которой он был добавлен.
- **Шаги выполнения**:
  - [x] Добавить регрессионный тест на структуру миграции
  - [x] Перевести `ALTER TYPE ... ADD VALUE` в `op.get_context().autocommit_block()`
  - [x] Оставить `UPDATE orders ...` отдельным шагом после фиксации нового enum
  - [x] Добавить правило для будущих enum-миграций в `backend/alembic/README.md`
- **Зависимости**: `backend/alembic/versions/20260416_uute_rso_remarks_status.py`, PostgreSQL enum semantics

## Задача: Post-project pipeline — отдельный статус замечаний РСО (2026-04-16)
- **Статус**: Завершена
- **Описание**: Ввести отдельный `OrderStatus` для замечаний РСО, чтобы заявка явно возвращалась инженеру на исправление и после повторной отправки возвращалась обратно в ожидание оплаты/согласования.
- **Шаги выполнения**:
  - [x] `models.py` + Alembic: добавить `rso_remarks_received` в `OrderStatus` и `order_status`
  - [x] `post_project_state.py` + `schemas.py`: отвязать derived-флаги от простого факта наличия старых remark-файлов
  - [x] `landing.py`: при `upload-rso-remarks` переводить заявку в новый статус
  - [x] `pipeline.py` + `tasks.py`: повторная отправка исправленного проекта только из `rso_remarks_received` с возвратом в `awaiting_final_payment`
  - [x] `admin.html` + `payment.html`: показать новый статус и корректные действия инженера/клиента
  - [x] `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
- **Зависимости**: существующий post-project flow с `FINAL_INVOICE`, `RSO_SCAN`, `RSO_REMARKS`

## Задача: Post-project pipeline — финальный счёт и замечания РСО (2026-04-16)
- **Статус**: Завершена
- **Описание**: Реализовать утверждённый post-project flow без новых `OrderStatus`: сохранить основной статус `awaiting_final_payment`, но добавить артефакты согласования с РСО, повторную отправку исправленного проекта и 15-дневный reminder по финальной оплате.
- **Шаги выполнения**:
  - [x] `models.py` + Alembic: `FINAL_INVOICE`, `RSO_REMARKS`, `rso_scan_received_at`
  - [x] `schemas.py` + `landing.py`: derived-флаги payment/admin response и public upload `upload-rso-remarks`
  - [x] `tasks.py` + `celery_app.py`: сохранение/переиспользование финального счёта, re-delivery исправленного проекта, reminder через 15 дней
  - [x] `email_service.py` + шаблоны: тексты без обещания онлайн-эквайринга, отдельная ветка повторной отправки исправленного проекта
  - [x] `payment.html`: UX варианта A для оплаты по счёту / загрузки скана РСО / замечаний РСО
  - [x] `admin.html` + `pipeline.py`: отображение derived state и действие «Отправить исправленный проект»
  - [x] `docs/changelog.md`, `docs/tasktracker.md`, `docs/project.md`
- **Зависимости**: существующие `OrderFile`, `EmailLog`, `/payment/{id}`, Celery Beat

## Задача: Доработки писем и payment/upload flow (2026-04-16)
- **Статус**: Завершена
- **Описание**: Точечные изменения UI и почтовых сценариев: управление кнопкой сохранения настроечной БД, новые тексты писем, вложение счёта на остаток, уведомление клиента после загрузки скана сопроводительного в РСО.
- **Шаги выполнения**:
  - [x] `admin.html`: отключение кнопки «Сохранить» при отсутствии pending-изменений + блокировка на время запроса
  - [x] `admin.html`: блок настроечной БД и его группы свёрнуты по умолчанию
  - [x] `info_request.html` и `project_delivery.html`: обновлённые тексты и CTA под новый процесс
  - [x] `upload.html`: кнопка «Вернуться на сайт» после успешной загрузки signed_contract
  - [x] `tasks.py`: вложение счёта на остаток в `send_completed_project` с cleanup временного файла
  - [x] `landing.py` + `tasks.py` + `final_payment_request.html`: письмо клиенту после `upload-rso-scan` с CTA «Загрузить замечания от РСО»
  - [x] `payment.html`: в `awaiting_final_payment` показывать форму загрузки скана, пока файл `rso_scan` не загружен
- **Зависимости**: существующие шаблоны email и endpoint `POST /api/v1/landing/orders/{id}/upload-rso-scan`

## Задача: Unified upload contract flow (upload/admin)
- **Статус**: Завершена
- **Описание**: Привести frontend-статику и админ-панель к новому потоку `contract_sent/advance_paid`: отдельный клиентский экран загрузки подписанного договора, обновлённый stepper и действия инженера.
- **Шаги выполнения**:
  - [x] `upload.html`: добавить `company_card` в подписи, выделить его в чеклисте для `waiting_client_info`, реализовать отдельный сценарий `contract_sent` с upload в `upload-signed-contract` и сообщением благодарности
  - [x] `admin.html`: обновить основной `STATUS_ORDER`, сохранить legacy-статусы в `STATUS_LABELS`
  - [x] `admin.html`: ограничить approve до `advance_paid`, обновить тексты/confirm/success, скорректировать polling после approve
  - [x] `admin.html`: добавить индикатор `signed_contract` в `contract_sent`, обновить подписи категорий файлов и options селекта
  - [x] Обновить `docs/changelog.md`, `docs/project.md`, выполнить `python3 -m compileall backend/app`
- **Зависимости**: backend-эндпоинт `POST /api/v1/landing/orders/{id}/upload-signed-contract` и статусы оплаты в пайплайне

## Задача: Публичная страница оплаты /payment/{id}
- **Статус**: Завершена
- **Описание**: Статическая `payment.html`, роут в `main.py`, публичные эндпоинты в `landing.py`, Celery: генерация и отправка договора/счёта (безнал), уведомление инженеру о скане РСО.
- **Шаги выполнения**:
  - [x] `PaymentPageInfo`, API payment-page / upload-company-card / select-payment-method / upload-rso-scan
  - [x] `process_company_card_and_send_contract`, `notify_engineer_rso_scan_received`, `send_contract_delivery_to_client`
  - [x] `payment.html` (экраны, XHR, polling, лимит 25 МБ)
- **Зависимости**: статусы оплаты и `FileCategory` в модели (задача 1 в payment-advance-tasktracker)

## Задача: Модалка «Политика конфиденциальности»
- **Статус**: Завершена
- **Описание**: Добавить прокручиваемую модалку с текстом политики конфиденциальности (152-ФЗ), открываемую из футера и из формы заказа (EmailModal).
- **Шаги выполнения**:
  - [x] Создать `frontend/src/constants/privacyPolicyText.ts` с HTML-текстом политики
  - [x] Создать `frontend/src/components/PrivacyPolicyModal.tsx` (overlay, Escape, scroll-lock, dangerouslySetInnerHTML, useRef fix)
  - [x] Подключить модалку в `Footer.tsx` (ссылка «Политика конфиденциальности»)
  - [x] Подключить модалку в `EmailModal.tsx` (кнопка-ссылка в тексте согласия)
  - [x] Вставить реальный текст политики ООО «Теплосервис-Комплект»
- **Технические заметки**:
  - `PrivacyPolicyModal` использует `useRef` для стабилизации `onClose` в `useEffect`, зависимость только `[isOpen]`
  - Скролл body блокируется при открытии, восстанавливается при закрытии (возможен конфликт при вложенных модалках — при необходимости решать через счётчик)
  - z-index: все модалки на `z-50` — при росте системы модалок перейти на иерархию `z-40/z-50/z-60`

## Задача: Внедрение настроечной БД Эско-Терра в express-пайплайн
- **Статус**: Завершена
- **Описание**: Интегрировать CalculatorConfig для express-заявок (только производитель Эско-Терра). Автоопределение из parsed_params + ручной override в админке.
- **Шаги выполнения**:
  - [x] `resolve_calculator_type_for_express` — автоопределение по metering.heat_calculator_model
  - [x] `init_config_sync` — синхронная версия для Celery-задач
  - [x] API guard: для express только `esko_terra`, GET возвращает `esko_detected` и `status=not_supported_for_express`
  - [x] Автоинициализация в `start_tu_parsing` после TU_PARSED
  - [x] UI admin.html: карточка для express + кнопка «Инициализировать как Эско 3Э»
  - [x] Документация: changelog.md, tasktracker.md
- **Зависимости**: feature/calculator-config (CalculatorConfig модель, сервис, API)

## Задача: Настроечная БД вычислителя (мультиприборность)
- **Статус**: Завершена
- **Описание**: Реализовать фичу «Настроечная БД вычислителя» — JSON-шаблоны параметров для ТВ7, СПТ-941.20, ЭСКО-Терра М; модель CalculatorConfig в БД; сервис автозаполнения из ТУ; CRUD API; UI в админке; экспорт PDF
- **Шаги выполнения**:
  - [x] Создать ветку `feature/calculator-config`
  - [x] JSON-шаблоны: `tv7.json` (29 параметров), `spt941.json` (25), `esko_terra.json` (22)
  - [x] Модель `CalculatorConfig` в `models.py` + relationship в `Order`
  - [x] Alembic-миграция `20260412_uute_add_calculator_configs`
  - [x] Сервис `calculator_config_service.py`: load_template, auto_fill, init_config, update_params, export_pdf
  - [x] API-роутер `calculator_config.py`: GET/POST/PATCH/export-pdf
  - [x] Подключить роутер в `main.py`
  - [x] UI в `admin.html`: calcConfigCard с прогресс-баром, легендой, таблицей, редактированием
  - [x] Обновить changelog.md и tasktracker.md
  - [x] Коммит в ветку `feature/calculator-config`
- **Зависимости**: Модели заявок (Order, survey_data, parsed_params), tu_schema.py (структура parsed_params)

## Задача: Поле «Город объекта»
- **Статус**: Завершена
- **Описание**: Добавить обязательное поле «Город объекта» в форму заказа на лендинге и распространить по всей системе: БД, бэкенд, опросный лист, парсер ТУ, AdminPanel
- **Шаги выполнения**:
  - [x] Миграция Alembic: колонка `object_city` в `orders`
  - [x] Backend: схемы, order_service, landing API
  - [x] Парсер: автозаполнение из ТУ
  - [x] Frontend: поле в форме заказа (EmailModal)
  - [x] Опросный лист (upload.html): поле + предзаполнение + валидация
  - [x] Админ-панель (admin.html): список, карточка, сравнительная таблица

## Задача: Excel-шаблон опросного листа для клиента
- **Статус**: Завершена
- **Описание**: Подготовить Excel-совместимый шаблон опросного листа на основе текущих полей парсинга ТУ и действующего клиентского опросника, чтобы его можно было отправлять клиенту и использовать для маппинга в систему.
- **Шаги выполнения**:
  - [x] Сформирован клиентский CSV-лист с полями для проверки и дозаполнения
  - [x] Сформирован технический CSV-лист соответствия `survey_data` и `parsed_params`
  - [x] Добавлен README с инструкцией по переносу двух CSV в единый `.xlsx`
  - [x] Добавлена запись в `docs/changelog.md`
- **Зависимости**: текущая схема парсинга ТУ (`backend/app/services/tu_schema.py`) и структура опросного листа (`backend/static/upload.html`)


## Задача: Custom — заполненные поля опросного листа только для чтения
- **Статус**: Завершена
- **Описание**: При открытии страницы клиентом по ссылке из письма (waiting_client_info и т.д.) поля опросного листа, которые уже были заполнены при создании заявки, должны быть нередактируемыми.
- **Шаги выполнения**:
  - [x] `upload.html`: CSS-класс `.survey-field-locked` — визуально отличает заблокированные поля (светлый фон)
  - [x] `upload.html`: функция `lockFilledSurveyFields(surveyData)` — `readonly` для `input`/`textarea`, `pointer-events: none` для `select`
  - [x] `upload.html`: `prefillSurveyFromSaved` вызывает `lockFilledSurveyFields` после заполнения формы
- **Зависимости**: нет

## Задача: Custom — необязательные документы и свёртка опроса в админке
- **Статус**: Завершена
- **Описание**: Снять блокировку кнопки «Отправить» по загрузке документов для custom; показывать UX-подсказку об опциональности; сделать карточку опросного листа в админке сворачиваемой.
- **Шаги выполнения**:
  - [x] `upload.html`: добавлен `div#docsOptionalHint` (жёлтая подсказка) сразу под кнопкой «Отправить»
  - [x] `upload.html`: `syncSubmitButtonState()` — убрана проверка всех документов; кнопка активна при сохранённом опросе
  - [x] `upload.html`: `showDocsOptionalHint()` показывает/скрывает подсказку при наличии незагруженных документов
  - [x] `upload.html`: текст баннера после сохранения опроса обновлён (документы — опционально)
  - [x] `admin.html`: `renderSurveyData()` оборачивает секции в `<details open>` с `<summary>`
  - [x] Записи в `docs/changelog.md` и `docs/tasktracker.md`
- **Зависимости**: нет

## Задача: UX custom — опросный лист, звёздочки, свёртка, секции в админке
- **Статус**: Завершена
- **Описание**: Улучшения UX custom-пайплайна на странице клиента и в админке.
- **Шаги выполнения**:
  - [x] `upload.html`: опросный лист перемещён над блоками «Необходимые документы» и «Загрузка файлов»
  - [x] `upload.html`: на начальном экране (`status=new`) опросный лист свёрнут (аккордеон), клик раскрывает
  - [x] `upload.html`: обязательные поля опросного листа отмечены звёздочкой `*` в лейбле
  - [x] `admin.html`: «Опросный лист» разбит на секции по группам (как `parsedCard` для express), с фиксированным порядком
  - [x] Записи в `docs/changelog.md` и `docs/tasktracker.md`
- **Зависимости**: нет

## Задача: UX-правки страницы загрузки и админки (апрель 2026)
- **Статус**: Завершена
- **Описание**: Серия UX-улучшений: inline-ошибки опросного листа, переименование поля ВРУ, обновление приветствия экспресс, блокировка кнопки «Одобрить», подсказка инженеру.
- **Шаги выполнения**:
  - [x] `upload.html`: ошибки валидации survey-формы — inline под кнопкой (не вверху)
  - [x] `upload.html`: поле «Расстояние до ВРУ» → обязательное, новое название
  - [x] `upload.html`: экспресс-заявка — приветствие обновляется после отправки документов
  - [x] `admin.html`: `runAction` блокирует кнопки на время запроса, разблокирует при ошибке
  - [x] `admin.html`: подсказка инженеру под формой загрузки файлов
  - [x] `admin.html`: метка `distance_to_vru` в `param_labels` обновлена
  - [x] Запись в `docs/changelog.md` и `docs/tasktracker.md`
- **Зависимости**: нет

## Задача: Отложенный info_request, одноразовые письма, уведомление инженеру, прогресс загрузки PDF
- **Статус**: Завершена
- **Описание**: Реализация плана [`docs/archive/2026-Q2/tasktrecker-progrssbar.md`](archive/2026-Q2/tasktrecker-progrssbar.md): 24 ч до авто-`info_request`, флаги и 409 для дублей, письмо инженеру после `client-upload-done`, прогресс XHR для `generated_project` в админке.
- **Шаги выполнения**:
  - [x] Модель `waiting_client_info_at`, миграция, `process_due_info_requests` + правки `send_reminders` / `send_info_request_email`
  - [x] `has_successful_email`, `CLIENT_DOCUMENTS_RECEIVED`, шаблон и Celery-уведомление
  - [x] `OrderResponse`: `info_request_sent`, `reminder_sent`; админка и 409 в `emails.py`
  - [x] `docs/changelog.md`, `docs/project.md`, актуализация плана в `archive/2026-Q2/tasktrecker-progrssbar.md`
- **Зависимости**: миграция Alembic на PostgreSQL; перезапуск celery-worker и celery-beat после деплоя

## Задача: Валидация файла проекта перед одобрением (pipeline approve)
- **Статус**: Завершена
- **Описание**: Исключить отправку письма «Проект готов» без вложения: раньше `approve` запускал Celery до загрузки PDF администратором.
- **Шаги выполнения**:
  - [x] Проверка `generated_project` в `approve_project` (HTTP 422)
  - [x] Лог-предупреждение в `send_completed_project` при пустых вложениях
  - [x] Блокировка кнопки «Одобрить» в `admin.html` до загрузки PDF
  - [x] Запись в [`docs/changelog.md`](changelog.md)
- **Зависимости**: нет

## Задача: Кодировка UTF-8 в `admin.html`
- **Статус**: Завершена
- **Описание**: После коммита `ec45248` русский текст в [`backend/static/admin.html`](../backend/static/admin.html) в git оказался заменён на `?`. Восстановление из версии до поломки + слияние с актуальной разметкой/JS (тип заявки, опрос, enum файлов).
- **Шаги выполнения**:
  - [x] Слияние строк с `92826c5`, точечные правки (колонки таблицы, даты, `survey_reminder`, эмодзи секций парсера)
  - [x] Запись в [`docs/changelog.md`](changelog.md)
- **Зависимости**: нет

## Задача: «Вернуться на сайт» на странице загрузки документов
- **Статус**: Завершена
- **Описание**: После отправки документов и после сохранения опросного листа клиент может перейти на главную (`/`) со страницы `/upload/{id}`.
- **Шаги выполнения**:
  - [x] Карточка «Все документы получены» + опрос после успешного POST survey
  - [x] Changelog, ревью (a11y `:focus-visible` для кнопок)
- **Зависимости**: нет

## Задача: Умный опросный лист (автозаполнение из ТУ для custom)
- **Статус**: Завершена
- **Описание**: Расширение upload-страницы и API: `parsed_params`/`survey_data` в ответе upload-page, polling парсинга, маппинг ТУ → поля опроса, инициализация по всем статусам, ограничение сохранения опроса по статусу заявки.
- **Шаги выполнения**:
  - [x] Задачи 1–5 по плану [`docs/archive/2026-Q2/smart-survey-tasktracker.md`](archive/2026-Q2/smart-survey-tasktracker.md)
- **Зависимости**: сегментация `OrderType` custom/express; эндпоинт `POST /landing/orders/{id}/survey`

## Задача: Сегментация клиентов — два варианта заказа (Экспресс / Индивидуальный)
- **Статус**: В работе
- **Описание**: Клиент выбирает тип проекта в калькуляторе. Экспресс — на базе Эско 3Э, скидка 50%. Индивидуальный — полная цена, опросный лист. Подробный план: [`docs/archive/2026-Q2/two-option-order-tasktracker.md`](archive/2026-Q2/two-option-order-tasktracker.md).
- **Шаги выполнения**:
  - [x] Задача 1: `OrderType` enum, поля `order_type` и `survey_data` в модели и схемах
  - [x] Задача 2: эндпоинт `POST /landing/order` принимает и сохраняет `order_type`
  - [x] Задача 3: две карточки в калькуляторе (фронтенд)
  - [x] Задача 4: форма и сценарии опроса на upload-странице (см. умный опрос, `archive/2026-Q2/smart-survey-tasktracker.md`)
  - [x] Задача 5: `order_type` и `survey_data` в админке
  - [x] Задача 6: email-напоминание заполнить опросный лист для custom-заказов
  - [x] Задача 7: changelog и документация
- **Зависимости**: миграция Alembic на сервере (колонки `order_type`, `survey_data`)

## Задача: Регистр значений file_category (BALANCE_ACT / CONNECTION_PLAN)
- **Статус**: Завершена
- **Описание**: Устранение рассинхрона между метками PostgreSQL enum (строчные `balance_act` / `connection_plan` из миграции 20260402) и ожиданиями кода в UPPER_CASE: переименование в БД, миграция `missing_params`, обновление модели и статики.
- **Шаги выполнения**:
  - [x] Alembic `20260403_fc_upper` (rename enum + JSON)
  - [x] `FileCategory`, `param_labels`, `admin.html`, `upload.html`
  - [x] `docs/project.md`, `docs/changelog.md`
- **Зависимости**: миграция `20260402_uute_file_category`

## Задача: Отображение результатов парсинга в админке
- **Статус**: Завершена
- **Описание**: Развёрнутый UI для `parsed_params` в карточке заявки (`admin.html`): `<details>` с таблицами по секциям, пустое состояние, legacy-плоские ключи.
- **Шаги выполнения**:
  - [x] CSS и JS в `backend/static/admin.html`
  - [x] `docs/changelog.md`, `docs/project.md`, [`docs/archive/2026-Q2/tasktrecker-otchet-parsing.md`](archive/2026-Q2/tasktrecker-otchet-parsing.md)
- **Зависимости**: нет

## Задача: Категории файлов УУТЭ (FileCategory + missing_params)
- **Статус**: Завершена
- **Описание**: Актуальные категории документов для проектирования УУТЭ; миграция БД для старых `floor_plan` и устаревших кодов в `missing_params`; синхронизация `param_labels`, парсера ТУ, `upload.html`, админки. Дополнительно: пересчёт `missing_params` по четырём документам при upload-page и в Celery, чтобы старые заявки не показывали `floor_plan` / `connection_scheme` / `system_type`.
- **Шаги выполнения**:
  - [x] Обновить `FileCategory` и миграцию Alembic
  - [x] `param_labels.py`, `tu_parser.py`, статика
  - [x] `docs/changelog.md`, `docs/project.md`, tasktracker
  - [x] `compute_client_document_missing` + legacy-fix на upload-page + фиксированные 4 пункта в ответе API; `process_client_response`
- **Зависимости**: нет

## Задача: Публичные upload-tu / submit (без 401 на upload.html)
- **Статус**: Завершена
- **Описание**: Эндпоинты в `landing.py` для загрузки ТУ и старта пайплайна при статусе `new`; админские `orders`/`pipeline/start` без изменений по защите.
- **Шаги выполнения**:
  - [x] `POST .../upload-tu`, `POST .../submit`
  - [x] `upload.html` + ограничение «только ТУ» для `new`
  - [x] `PipelineResponse` в `schemas`
- **Зависимости**: задача «upload-page + order_status»

## Задача: Страница upload.html — сценарии new и waiting_client_info
- **Статус**: Завершена
- **Описание**: Расширен ответ upload-page полем `order_status`; на клиенте выбираются URL загрузки и завершения в зависимости от статуса заявки.
- **Шаги выполнения**:
  - [x] Схема `UploadPageInfo` + эндпоинт `landing.py`
  - [x] Логика и категория `tu` в `upload.html`
  - [x] Запись в `docs/changelog.md`
- **Зависимости**: нет
