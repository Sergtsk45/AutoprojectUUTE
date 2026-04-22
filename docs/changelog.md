# Changelog

## [2026-04-22] — Фаза B3: приведение имён alembic-миграций к соглашению

### Изменено
- `backend/alembic/versions/20260403_file_category_uppercase_bc.py` → `20260403_uute_file_category_uppercase_bc.py` (добавлен префикс `uute_` — соответствие соглашению `YYYYMMDD_uute_<описание>.py` из `CLAUDE.md`).
- `backend/alembic/versions/87fcef6f52ff_20260415_uute_advance_payment_model.py` → `20260415_uute_advance_payment_model.py` (убран лидирующий alembic-хеш из имени файла).

### Не затронуто
- `revision` и `down_revision` внутри файлов оставлены без изменений: таблица `alembic_version` в проде хранит именно эти идентификаторы (`20260403_fc_upper`, `87fcef6f52ff`), и их правка потребовала бы дополнительной миграции с риском разрыва чейна. Имена файлов Alembic вообще не анализирует — только значения полей `revision` внутри.
- Остальные 12 миграций уже соответствуют соглашению.
- Требование B3 по индексам админского листинга (`ix_orders_created_at_desc`, `ix_orders_status_created_at_desc`, `ix_order_files_order_id_category`) было реализовано параллельно в рамках миграции `20260422_uute_add_listing_indexes.py` (создание `CONCURRENTLY`, без блокировки таблиц) и прописано в `Order.__table_args__` / `OrderFile.__table_args__`.

### Проверено
- `alembic.script.ScriptDirectory.walk_revisions()` локально возвращает все 14 ревизий, один head (`20260422_uute_listing_idx`), без разрывов.
- `pytest` (63 теста backend) проходит локально.

### Результат
- `ls backend/alembic/versions/*.py` теперь единообразный: каждый файл начинается с `YYYYMMDD_uute_`. Нулевые расходы на код, чистая гигиена репозитория.

---

## [2026-04-22] — Фаза E4: декомпозиция `upload.html` на модули

### Добавлено
- [`backend/static/css/upload.css`](../backend/static/css/upload.css) (~16 KB, 611 строк) — вынос inline `<style>` из `upload.html`.
- Каталог [`backend/static/js/upload/`](../backend/static/js/upload/) с пятью JS-модулями (обычные `<script>`, не ES-модули — сохранён единственный inline `onclick="toggleSurveyCollapse()"`):
  - [`config.js`](../backend/static/js/upload/config.js) — константы (`API_BASE`, `ORDER_ID`, `PARAM_LABELS`, `POST_PARSE_STATUSES`, `CUSTOM_EDITABLE_STATUSES`, `PARAM_TO_SURVEY`, `SURVEY_REQUIRED_FIELDS`) и mutable state (`orderData`, `isNewOrder`, `surveySavedCustom`, `uploadedCategories`, таймеры/счётчики парсинг-поллинга).
  - [`utils.js`](../backend/static/js/upload/utils.js) — чистые хелперы (`escapeHtml`, `formatSize`, `formatMoneyRub`, `formatHttpDetail`, `showBanner`, `strVal`/`numVal`), UI-состояния (`syncSubmitButtonState`, `showDocsOptionalHint`, `applySurveySavedVisuals`, `showSurveyError`/`hideSurveyError`), DOM-refs (`$loading`, `$main`, `$checklist`, `$dropzone`, `$surveyCard`, `$contractSentCard` и др.).
  - [`survey.js`](../backend/static/js/upload/survey.js) — опросный лист: collapse/expand/lock/unlock, hydrate из snapshot, маппинг `parsed_params → s_*`, нормализация типов подключения/систем/зданий, decorations (prefilled/needs-input badges), `collectSurveyData`, `validateSurveyFields`, обработчик submit. `toggleSurveyCollapse` экспортируется на `window`.
  - [`contract.js`](../backend/static/js/upload/contract.js) — экран «договор и оплата»: `renderContractMeta`, `setSignedContractAcceptedState`/`resetSignedContractState`/`showContractSentState`, `showUploadAlongsideSurveyIfNeeded`, `prefillSurveyFromSaved`, `validateSignedContractFile`, `uploadSignedContract` (XHR + прогресс) и функция `bindSignedContractHandlers()` для drag&drop/change.
  - [`upload.js`](../backend/static/js/upload/upload.js) — entry: `initCustomOrderUi`, `init`, `renderChecklist`, `renderCategoryOptions`, drag&drop-листенеры основной зоны, `handleFiles`, `uploadFile` (XHR + прогресс), обработчик submit «Всё загружено», `showCompleted`, polling парсинга ТУ (`showParsingState`, `startParsingPoll`, `stopParsingPoll`, `showParsingTimeout`). В конце — вызов `bindSignedContractHandlers()` и `init()`.

### Изменено
- [`backend/static/upload.html`](../backend/static/upload.html) сократился **с 92 153 → 21 762 байт** (−76%), с 2323 → 402 строк: удалены inline `<style>` (~612 строк) и inline `<script>` (~1318 строк), добавлены `<link rel="stylesheet" href="/static/css/upload.css">` и пять `<script src="/static/js/upload/*.js">` в конце `<body>`. Порядок подключения `config → utils → survey → contract → upload` гарантирует, что все глобальные символы доступны до первого вызова. Единственный inline `onclick="toggleSurveyCollapse()"` в HTML оставлен как был (функция экспонирована на `window` из `survey.js`).

### Не затронуто
- Ни одна функция не переименована и не переработана — код перенесён 1-в-1, поведение страницы `/upload/<id>` эквивалентно.
- `backend/static/payment.html` остаётся монолитным (не входит в минимальный сценарий E4).
- Никаких новых зависимостей (сборщика нет, ES-модули не используются).

### Проверено
- `node --check` на каждом из 5 модулей + склейка всех JS в один файл — синтаксис чистый.
- `backend` pytest (63 теста) проходит локально на Python 3.10 с теми же env-переменными, что и CI.
- Frontend `npm run lint` без ошибок (изменения не затронули `frontend/`).
- Единственный inline-хендлер (`onclick="toggleSurveyCollapse()"`) сохранён и покрыт экспортом `window.toggleSurveyCollapse = toggleSurveyCollapse` в `survey.js`.

### Результат
- Кэш браузера теперь переиспользует CSS/JS между посещениями страницы.
- Диффы новых фич в `upload.html` / `upload.css` / `js/upload/*.js` становятся узкоцелевыми — больше не меняется один 2,3-тысячный файл.
- Готова площадка для перехода на ES-модули/сборщик: единственный inline-хендлер можно заменить на `addEventListener` без правок в остальных файлах.

---

## [2026-04-22] — Фаза E3 (минимальный вариант): декомпозиция `admin.html` на модули

### Добавлено
- Каталог [`backend/static/css/`](../backend/static/css/) и файл [`admin.css`](../backend/static/css/admin.css) (~18 KB) — вынос inline `<style>` из `admin.html`.
- Каталог [`backend/static/js/admin/`](../backend/static/js/admin/) с пятью JS-модулями (обычные `<script>`, не ES-модули, чтобы inline `onclick`/`onchange` в HTML продолжали работать без изменений):
  - [`config.js`](../backend/static/js/admin/config.js) — константы (`API_BASE`, `ORDER_ID_URL_RE`, `STATUS_LABELS/COLORS/ORDER`, `POST_PARSE_STATUSES`, `SURVEY_LABELS/VALUE_MAP/SECTIONS`) и глобальное состояние поллингов (`currentOrderId`, таймеры).
  - [`utils.js`](../backend/static/js/admin/utils.js) — чистые хелперы: `statusBadge`, `orderTypeBadge`, `formatNum`, `fmtNum`, `addKeyToUrl`, `isParsedParamsEmpty`, `showOrderAlert`, `esc`, `formatDate`, `formatDateFull`, `formatSize`.
  - [`views-parsed.js`](../backend/static/js/admin/views-parsed.js) — рендер разобранных параметров ТУ, опросного листа и сравнительной таблицы parsed vs survey (все `cmp*`, `buildParsedParamsTablesHtml`, `renderParsedParams`, `renderSurveyData`, `*FromParams`).
  - [`views-calc.js`](../backend/static/js/admin/views-calc.js) — настроечная БД вычислителя (`loadCalcConfig`, `renderCalcConfig`, `renderCalcGroups`, `initCalcConfig*`, `saveCalcConfig`, `exportCalcConfigPdf`, `calcParamChanged` + UI-state).
  - [`admin.js`](../backend/static/js/admin/admin.js) — entry: auth, fetch-хелперы (`apiFetch`/`apiJSON`), навигация, четыре поллинга (waiting-email / sending-project / payment-flow / parsing), `approveProject`, список заявок (`refreshList`, `renderStats`, `renderOrdersTable`), карточка заявки (`loadOrder`, `renderOrder`, `renderProgress`, `renderPaymentCard`, `renderFiles`, `renderEmailLog`), действия (`renderActions`, `runAction`, `sendEmail`, `uploadAdminFile`) и `DOMContentLoaded`.

### Изменено
- [`backend/static/admin.html`](../backend/static/admin.html) сократился **с 129 645 → 13 131 байт** (−90%): удалены inline `<style>` (~586 строк) и inline `<script>` (~2045 строк), добавлены `<link rel="stylesheet" href="/static/css/admin.css">` и пять `<script src="/static/js/admin/*.js">` в конце `<body>`. Порядок подключения `config → utils → views-parsed → views-calc → admin` гарантирует, что все глобальные функции определены до первого `onclick` (15 inline-хендлеров в HTML остались без правок).

### Не затронуто
- Ни одна функция не переименована и не переработана — код перенесён 1-в-1, поведение админки эквивалентно.
- `backend/static/upload.html` и `backend/static/payment.html` остались без изменений: их декомпозиция — отдельный пункт backlog (B1/B2 в расширенном варианте), не входит в «минимальный» E3.
- Никаких новых зависимостей (сборщика нет, ES-модули не используются).

### Проверено
- `node --check` на каждом из 5 модулей — чистый синтаксис.
- Локальный `python3 -m http.server` по `backend/static/`: `/admin.html`, `/css/admin.css` и все пять `/js/admin/*.js` отдаются HTTP 200.
- Полный аудит глобальных функций, вызываемых из inline `onclick` (`doLogin`, `doLogout`, `refreshList`, `showList`, `showOrderScreen`, `uploadAdminFile`, `initCalcConfig`, `initCalcConfigExpress`, `saveCalcConfig`, `exportCalcConfigPdf`, `calcParamChanged`, `addKeyToUrl`) — все 12 определены в модулях. `window.actionBtns` по-прежнему выставляется в `renderActions`.

### Связано с roadmap
- [Раздел E3](plans/2026-04-20-audit-section-3-maintainability-roadmap.md) — «минимальный» сценарий закрыт. Для среднего/полного варианта (бандлер + ES-модули + тесты на UI) потребуется отдельная задача.
- DoD выполнен: «`admin.html` уменьшился до <30 КБ (skeleton + подключение модулей)».

### Откат
- `git revert` ветки `refactor/audit-e3-admin-html-modules`: удаляет новые `css/admin.css` и `js/admin/*.js`, восстанавливает inline-версию `admin.html`.

---

## [2026-04-22] — Фаза E2: Vitest-тесты на транспортный слой фронта

### Добавлено
- Новый тест-модуль [`frontend/src/api.test.ts`](../frontend/src/api.test.ts) (10 тестов): покрытие публичных функций `requestSample`, `createOrder`, `sendPartnershipRequest`, `sendKpRequest`. Зафиксированы:
  - URL/метод/заголовки/сериализация тела JSON для всех JSON-эндпоинтов;
  - контракт multipart-запроса `kp-request` (Content-Type **не** ставится вручную — только браузер/Undici со своим boundary);
  - разбор ошибок FastAPI: строковый `detail`, валидационный массив `detail=[{msg}]`, HTTP-fallback на невалидном JSON;
  - override `VITE_API_BASE_URL` через `vi.stubEnv` + динамический импорт модуля.

### Изменено
- Итог vitest: `npm test` теперь прогоняет 15 тестов (было 5 — только `utils/pricing.test.ts`).

### Не затронуто
- Никаких новых зависимостей — тесты используют встроенный в Node 20 `fetch`/`FormData` и штатный `vi.stubGlobal` из vitest 2.1. `@testing-library/react` оставлен на будущую фазу (тесты компонентов вне scope E2).
- `vitest.config` без изменений (`environment: 'node'` достаточен, `jsdom` не подключался).

### Проверено
- `vitest run` — 15/15 зелёных, 2 тест-файла.
- `tsc --noEmit`, `npm run lint`, `npm run build` — зелёные.

### Связано с roadmap
- [Раздел E2](plans/2026-04-20-audit-section-3-maintainability-roadmap.md): DoD «`npm test` в CI зелёный на >0 тестов» — выполнен (5 → 15).
- Фронт-тесты уже гоняются в CI-job `frontend` (`npm test`), отдельный шаг не нужен.

### Откат
- `git revert` ветки `feat/audit-e2-frontend-tests`. Удаление файла `src/api.test.ts` возвращает vitest на исходные 5 тестов.

---

## [2026-04-22] — Фаза E1: Typed API через `openapi-typescript`

### Добавлено
- Dev-зависимость [`openapi-typescript@7.4.4`](https://github.com/openapi-ts/openapi-typescript) в [`frontend/package.json`](../frontend/package.json).
- Скрипт [`scripts/generate-api-types.sh`](../scripts/generate-api-types.sh): импортирует FastAPI-приложение, экспортирует `app.openapi()` в `frontend/src/api/openapi.json` и регенерирует `frontend/src/api/types.ts`. Идемпотентен, работает с dummy-ENV (SMTP/ADMIN/OPENROUTER) — схемы не инициализируют внешние ресурсы. Автоматически подхватывает `backend/.venv/bin/python` и падает с понятной инструкцией, если версии `pydantic`/`fastapi` не совпадают с `backend/requirements.txt` (разные Pydantic-версии по-разному ставят `additionalProperties` в OpenAPI — это ломало CI-job).
- Сгенерированные артефакты [`frontend/src/api/openapi.json`](../frontend/src/api/openapi.json) (~155 KB) и [`frontend/src/api/types.ts`](../frontend/src/api/types.ts) (~121 KB) — **коммитятся в репо**, источник правды для TS-клиента. README в том же каталоге объясняет контракт и процесс обновления.
- CI-job `api-types-drift` в [`.github/workflows/ci.yml`](../.github/workflows/ci.yml): перегенерирует артефакты и падает по `git diff --exit-code`, если Pydantic-схема поменялась, а скрипт не прогнали. Fail-инструкция печатает первые 120 строк diff для диагностики.

### Изменено
- [`frontend/src/api.ts`](../frontend/src/api.ts) переписан: ручные `interface OrderRequest/OrderCreatedResponse/SimpleResponse` заменены на алиасы `components['schemas'][…]` из сгенерированного `types.ts`. Публичные функции (`requestSample`, `createOrder`, `sendPartnershipRequest`, `sendKpRequest`) сохранили сигнатуры — компоненты `EmailModal.tsx` / `KpRequestModal.tsx` не меняются. Ошибки API теперь разбираются единообразно (`handleJsonResponse`) — нет копипасты try/catch.
- В [`frontend/package-lock.json`](../frontend/package-lock.json) URL артефактов переведены на `registry.npmjs.org` (integrity-хеши идентичны).

### UX/контракт API
- **Публичный контракт фронта без изменений.** Все 4 вызова лендинга работают как раньше: те же URL, те же поля запроса. Фронт-билд теперь падает по TS-ошибке, если бэк поменяет схему без регенерации клиента.
- **Закрыт классический рассинхрон** между ручной `OrderRequest` в старом `api.ts` и Pydantic на бэке (OpenAPI помечает `order_type` обязательным с дефолтом `express`; сгенерированный тип это фиксирует — фронт уже и так всегда отправляет `order_type`).

### Не затронуто
- Backend-код (`app/*.py`) **не менялся** — E1 — чисто инструментация фронта и CI.
- Legacy-страницы на Jinja (`admin.html`, `upload.html`, `payment.html`) — они не импортируют `frontend/src/api.ts` и типы, продолжают работать через собственный JS.
- Ручные тесты `pricing.test.ts` — без изменений.

### Проверено
- Backend: `ruff check`, `ruff format --check`, `pytest backend/tests/` (63/63) — всё зелёное.
- Frontend: `tsc --noEmit`, `npm run lint`, `npm test` (5/5), `npm run build` — зелёные.
- `scripts/generate-api-types.sh` идемпотентен: повторный прогон не выдаёт diff.

### Связано с roadmap
- [Раздел E1](plans/2026-04-20-audit-section-3-maintainability-roadmap.md): DoD «Typed API через openapi-typescript, CI-drift-check» — выполнен.
- Разблокировано предыдущей фазой B1.c: в OpenAPI теперь точно описаны `company_requisites`, `parsed_params`, `survey_data` — при следующих итерациях TS-клиент получит эти структуры «бесплатно».
- Следующий логичный шаг — E3/E4 (декомпозиция React-компонентов и legacy HTML).

### Откат
- `git revert` ветки `feat/audit-e1-typed-api`. Никаких миграций БД или ENV-изменений не внесено; CI-job без ветки просто отключается.

---

## [2026-04-22] — Фаза B1.c: строгая типизация `OrderResponse` и публичных DTO

### Добавлено
- Новая Pydantic-модель [`CompanyRequisitesError`](../backend/app/schemas/jsonb/company.py) — маркер неудачного парсинга «Карточки предприятия» (`{"error": "..."}`). Выделена отдельно, чтобы Union-тип `OrderResponse.company_requisites` точно описывал оба варианта в OpenAPI и TS-клиентах.
- Алиас `CompanyRequisitesResponse = CompanyRequisites | CompanyRequisitesError` в [`app.schemas.schemas`](../backend/app/schemas/schemas.py) — общее имя для всех DTO.
- Хелпер `company_requisites_for_response(order)` в `app.schemas.schemas` — единая точка сборки `company_requisites` из ORM-объекта: `None` / `CompanyRequisitesError` / `CompanyRequisites` (через accessor с WARN+None на грязных данных).
- Тест-модуль [`tests/test_order_response_typing.py`](../backend/tests/test_order_response_typing.py) (11 тестов): проверка типизации полей, happy-path, error-маркер, legacy `missing_params`, невалидные `parsed_params` / `survey_data` (→ `None` + WARNING).

### Изменено
- [`OrderResponse`](../backend/app/schemas/schemas.py):
  - `parsed_params: dict | None` → `parsed_params: TUParsedData | None`
  - `survey_data: dict | None` → `survey_data: SurveyData | None`
  - `company_requisites: dict | None` → `company_requisites: CompanyRequisites | CompanyRequisitesError | None`
  - `missing_params: list | None` → `missing_params: list[str] | None` (сознательно сохранено как plain-строки — в БД бывают legacy-коды `floor_plan`/`connection_scheme`/и т.п., которые чинятся только на upload-странице через `fix_legacy_client_document_params`).
- [`UploadPageInfo`](../backend/app/schemas/schemas.py) и [`PaymentPageInfo`](../backend/app/schemas/schemas.py) — те же JSONB-поля строго типизированы.
- `build_order_response` переписан: больше **не вызывает** `OrderResponse.model_validate(order)` — строит DTO вручную через accessor'ы `app.repositories.order_jsonb.*`, которые уже валидируют JSONB и возвращают `None` + WARNING на невалидных исторических записях. Это устраняет риск падения ответа при грязных данных после смены типов.
- [`backend/app/api/landing.py`](../backend/app/api/landing.py): локальный `_company_requisites_for_response` удалён (используется общий `company_requisites_for_response`). Чтение `parsed_params`/`survey_data` в `upload-page` — через `get_parsed_params`/`get_survey_data` (типизированные модели).

### UX/контракт API
- **Фронт-контракт сохранён.** Все ключи JSON-ответов остаются прежними:
  - `payment.html` / `admin.html` — читают `data.company_requisites.error`: при ошибке парсинга бэкенд отдаёт `{"error": "..."}` (`CompanyRequisitesError.model_dump()` выдаёт ровно этот dict).
  - `admin.html` — читает `order.parsed_params.object.object_address` и т. п.: `TUParsedData.model_dump()` публикует те же вложенные ключи.
- **OpenAPI теперь строже.** Для внешних потребителей OpenAPI-схема описывает точную структуру JSONB; поля, не входящие в Pydantic-модели (`extra='ignore'`), при сериализации фильтруются. Для LLM-парсера это не критично — Pydantic-модели `TUParsedData`/`SurveyData`/`CompanyRequisites` полностью покрывают ожидаемые ключи.
- **Новое поведение на грязных данных.** Если в БД исторически невалидный `parsed_params`/`survey_data`, в ответе API соответствующее поле будет `null` (раньше — возвращался исходный dict «как есть»). В логе — WARNING с причиной. Для custom-заказов это означает пустой опрос на фронте вместо падения страницы (сохранено поведение B1.b).

### Не затронуто
- `OrderListItem` — без JSONB-полей, типизация не меняется.
- `PipelineResponse`, `OrderCreate`, `FileResponse`, `EmailLogResponse` — без изменений.
- `missing_params` — остаётся `list[str] | None` (см. выше причину). Переход на `list[FileCategory]` увязан с финальной data-миграцией legacy-кодов в БД и в scope B1.c не входит.

### Проверено
- `ruff check` ✓, `ruff format --check` ✓, `mypy --config-file backend/pyproject.toml backend/app` ✓ (55 файлов).
- `pytest backend/tests/` — 61/61 (добавлены 11 новых тестов).
- CI-parity прогон в Docker `python:3.12-slim`: все шаги зелёные.

### Связано с roadmap
- [Раздел B1.c](plans/2026-04-20-audit-section-3-maintainability-roadmap.md): DoD «строгие Pydantic-схемы на JSONB в OrderResponse» — выполнен для `parsed_params`/`survey_data`/`company_requisites`. `missing_params` — открытый вопрос, зависит от B2.c (финальная миграция legacy-кодов).
- Разблокирует **E1** (typed API через `openapi-typescript`): TS-клиент теперь получает полноценные типы JSONB-полей вместо `Record<string, unknown>`.

### Rollback
- `git revert` коммита возвращает `dict | None` в DTO и старый `build_order_response`. Схемы в БД не затрагивались — откат данных не требуется.

---

## [2026-04-22] — Фаза B2.b: удаление legacy UPPER_CASE у `FileCategory` (BREAKING CHANGE API)

### Удалено
- `FileCategory._missing_` (compat-shim, B2.a) — case-insensitive lookup из `backend/app/models/models.py`. После B2.b enum строго принимает только канонические `.value` (snake_case lowercase).
- `_B2_LEGACY_ALIASES` и `_canonicalize` из [`backend/app/services/param_labels.py`](../backend/app/services/param_labels.py) — `get_missing_items` / `get_sample_paths` больше не подменяют UPPER_CASE → lowercase.
- Записи `BALANCE_ACT` / `CONNECTION_PLAN` из множества `_LEGACY_DOCUMENT_PARAM_CODES` (исторические данные мигрированы Alembic-ревизией `20260421_uute_fc_lower_missing` в B2.a).

### Изменено
- Тест-модуль [`backend/tests/test_file_category_b2.py`](../backend/tests/test_file_category_b2.py): `test_missing_accepts_legacy_uppercase` → `test_missing_rejects_legacy_uppercase` и т. п. Покрытие: 14 тестов (рост с 12), включая регрессии на канонический lowercase-lookup и поведение `get_missing_items` / `get_sample_paths` на устаревших кодах.
- `FileCategory` docstring обновлён: явно указано, что в B2.b API возвращает 422 на uppercase-входы.

### BREAKING CHANGE
- **API:** запросы вида `?category=BALANCE_ACT` / `?category=CONNECTION_PLAN` теперь отвечают **422 Unprocessable Entity** вместо тихой канонизации. До B2.b такие запросы принимались с `WARNING` в лог (`FileCategory: принят устаревший uppercase-алиас …`).
- **Контракт миграции:** клиент должен использовать только `balance_act` / `connection_plan` (snake_case lowercase). Любые внешние интеграции, не обновлённые после релиза B2.a, поломаются.

### Не затронуто
- **PG-enum `file_category`** на `order_files.category` — labels по-прежнему UPPER_CASE-имена членов Python (`BALANCE_ACT`, …). SQLAlchemy без `values_callable` persist имена, не `.value`. RENAME enum-меток в БД (`ALTER TYPE ... RENAME VALUE`) — отдельная задача, требует zero-downtime migration с переключением на `values_callable`; в scope B2.b не входит.
- Данные в `orders.missing_params` (JSONB-массив) уже мигрированы B2.a (Alembic `20260421_uute_fc_lower_missing`).

### Проверено
- `ruff check` ✓, `ruff format --check` ✓, `mypy app/models/models.py app/services/param_labels.py` ✓.
- `pytest tests/` — 52/52 (14 в `test_file_category_b2.py`).
- CI-parity в Docker `python:3.12-slim`: `ruff` + `mypy app` (55 файлов) + `pytest tests/` (52/52) — зелёные.

### Связано с roadmap
- [Раздел B2.b](plans/2026-04-20-audit-section-3-maintainability-roadmap.md): DoD «`SELECT DISTINCT category FROM files` → только lowercase-значения» сохраняется (см. оговорку про PG-enum выше); «API на UPPER_CASE → 422» — выполнено.

### Rollback
- `git revert` коммита B2.b возвращает `_missing_` и `_canonicalize`. Данные в БД (`orders.missing_params`) уже в lowercase — никаких операций над БД для отката не требуется. Если нужно вернуть исходный B2.a-shim вместе с logs — достаточно git revert.

---

## [2026-04-22] — Фаза D4: Async/sync граница — убран `SyncSession()` из async-роутеров

### Добавлено
- Celery-задача [`notify_engineer_new_order`](../backend/app/services/tasks/client_response.py) — асинхронное уведомление инженера о новой заявке. Регистрируется под именем `app.services.tasks.notify_engineer_new_order`.
- Хелпер [`app.services.email.manual_send.manual_send_email_sync`](../backend/app/services/email/manual_send.py) и исключение `ManualSendError` — переиспользуемая sync-обёртка над `SyncSession + SMTP` для админской ручной отправки; вызывается через `asyncio.to_thread` из `POST /emails/{order_id}/send`.
- CI-шаг `forbid SyncSession() in backend/app/api/` в [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — падает при появлении `SyncSession()` в async-роутерах.
- Smoke-тесты [`tests/test_async_sync_boundary.py`](../backend/tests/test_async_sync_boundary.py): запрет `SyncSession()` в `app/api/`, регистрация задачи, `ManualSendError(404)` на отсутствующей заявке.

### Изменено
- [`backend/app/api/landing.py`](../backend/app/api/landing.py):
  - `POST /landing/order` больше не открывает `SyncSession()` в async-обработчике — уведомление инженеру уходит best-effort через `notify_engineer_new_order.delay(...)`; event loop не блокируется.
  - `POST /landing/sample-request`, `/partnership`, `/kp-request` — SMTP-вызовы выполняются через `await asyncio.to_thread(...)`. UX ответа не меняется (`success=True` как раньше; `/kp-request` по-прежнему отвечает 500, если SMTP упал).
- [`backend/app/api/emails.py`](../backend/app/api/emails.py): `POST /emails/{order_id}/send` делегирует sync-часть хелперу `manual_send_email_sync` через `asyncio.to_thread`; 404/409/400 пробрасываются через `ManualSendError` → `HTTPException`. Ответ остаётся синхронным (админ получает `success`/`message` в том же запросе).

### UX/контракт API
- `POST /landing/order`: было — уведомление уходило (или падало с exception в try/except) до ответа 201; теперь уходит асинхронно. **Гарантия атомарности email+заявка ослаблена**, но: (а) `try/except` уже глушил ошибки SMTP; (б) при недоступности брокера `.delay()` обёрнут в `try/except` — создание заявки не падает.
- Остальные эндпоинты сохраняют прежние статусы ответа и тело.

### Проверено
- `ruff check` ✓, `ruff format --check` ✓, `mypy` ✓, `pytest tests/` 50/50 (добавлены 3 новых теста).
- CI-parity прогон в Docker (python:3.12-slim) — все шаги зелёные.

### Связано с roadmap
- [Раздел D4](plans/2026-04-20-audit-section-3-maintainability-roadmap.md): DoD «`rg SyncSession backend/app/api/` = 0 совпадений» выполнен. Следующий шаг — D5 (Celery hardening).

---

## [2026-04-22] — Фаза D3: `contract_generator.py` → пакет `services/contract/`

### Добавлено
- Пакет [`backend/app/services/contract/`](../backend/app/services/contract/):
  - [`number_format.py`](../backend/app/services/contract/number_format.py) — пропись сумм, `fmt_rub`, `ru_date`, `extract_city`.
  - [`tu_embed.py`](../backend/app/services/contract/tu_embed.py) — растр PDF ТУ в PNG, лимит размера DOCX, `TU_DPI_LADDER`.
  - [`docx_utils.py`](../backend/app/services/contract/docx_utils.py) — таблицы и параграфы python-docx для договора.
  - [`contract_docx.py`](../backend/app/services/contract/contract_docx.py) — контекст, разделы 1–15, приложения, `generate_contract`, `generate_contract_number`.
  - [`invoice.py`](../backend/app/services/contract/invoice.py) — `generate_invoice`.
- Re-export: [`__init__.py`](../backend/app/services/contract/__init__.py). Совместимость: тонкий [`contract_generator.py`](../backend/app/services/contract_generator.py) — re-export из пакета (импорты `app.services.contract_generator` без смены путей в вызовах).

### Изменено
- **Удалён** дублирующий модуль `backend/app/services/tasks.py` (лог-дубликат рядом с пакетом `tasks/` после D1.b; `import app.services.tasks` по-прежнему ведёт в пакет `tasks/`).

### Проверено
- `ruff check backend/` ✓, `mypy` (override `app.services.contract.*`, strict) ✓, `pytest` 47/47.

### Исправлено (после CI)
- `pyproject.toml`: для `app.services.contract.*` в `disable_error_code` добавлен `valid-type` — в CI (Python 3.12) mypy иначе падает на аннотациях `Document` из python-docx (фабрика вместо класса в стабах).

---

## [2026-04-22] — Фаза D2: `email_service.py` → пакет `services/email/`

### Добавлено
- Пакет [`backend/app/services/email/`](../backend/app/services/email/):
  - [`smtp.py`](../backend/app/services/email/smtp.py) — `build_mime_message`, `send_smtp_message` (единая точка SSL/STARTTLS + login + `send_message`), `send_email`.
  - [`idempotency.py`](../backend/app/services/email/idempotency.py) — `has_successful_email`, `log_email` (логи по клиентским письмам с `order.client_email`).
  - [`renderers.py`](../backend/app/services/email/renderers.py) — Jinja2, `COMMON_CONTEXT`, все `render_*` (в т.ч. уведомления инженеру: ТУ, документы, подписанный договор).
  - [`service.py`](../backend/app/services/email/service.py) — все `send_*` и оркестрация.
- Re-export публичного API в [`__init__.py`](../backend/app/services/email/__init__.py). Совместимость: тонкий [`email_service.py`](../backend/app/services/email_service.py) — `from .email import *` (импорты `app.services.email_service` не меняются).

### Изменено
- `send_kp_request_notification` вместо дублирования блока try/except + SMTP вызывает общий `send_smtp_message` (поведение доставки то же, логирование — через слой `smtp`).

### Проверено
- `ruff check app/services/email app/services/email_service.py` ✓, `mypy app/services/email app/services/email_service.py` ✓, `pytest` 47/47 (с `SMTP_PASSWORD`, `ADMIN_API_KEY`, `OPENROUTER_API_KEY` в окружении).

---

## [2026-04-22] — Фаза D1.b: `services/tasks.py` → пакет `services/tasks/`

### Добавлено
- Пакет [`backend/app/services/tasks/`](../backend/app/services/tasks/): публичный API `app.services.tasks` прежний (`import app.services.tasks as tasks` и `from app.services.tasks import ...` без изменений).
- Подмодули:
  - [`_common.py`](../backend/app/services/tasks/_common.py) — `SyncSession`, хелперы БД, `_normalize_client_requisites`, вложения проекта, `FINAL_*` / `INFO_REQUEST_*` константы.
  - [`tu_parsing.py`](../backend/app/services/tasks/tu_parsing.py) — `start_tu_parsing`, `check_data_completeness`.
  - [`client_response.py`](../backend/app/services/tasks/client_response.py) — `send_info_request_email`, `process_due_info_requests`, уведомления инженеру, `process_client_response`.
  - [`contract_flow.py`](../backend/app/services/tasks/contract_flow.py) — `process_card_and_contract`, заглушки `fill_excel` / `generate_project`, платёжный флоу, `parse_company_card_task`, `process_company_card_and_send_contract`.
  - [`post_project_flow.py`](../backend/app/services/tasks/post_project_flow.py) — `send_completed_project`, `resend_corrected_project`, RSO-нотификации.
  - [`reminders.py`](../backend/app/services/tasks/reminders.py) — beat-задачи напоминаний.
- Re-export в [`__init__.py`](../backend/app/services/tasks/__init__.py): все задачи + `compute_client_document_missing` (для тестов, патч `app.services.tasks.*`).
- Скрипт-референс [`scripts/split_tasks_d1b.py`](../scripts/split_tasks_d1b.py) — логика line-range (см. docstring `T()`: 1-based inclusive, не обрезать закрывающие скобки).
- Тест [`tests/test_celery_tasks_package.py`](../backend/tests/test_celery_tasks_package.py) — 23 зарегистрированных имени `app.services.tasks.*`.

### Изменено
- **Удалён** монолитный **`backend/app/services/tasks.py`** (≈1.8K строк) — теперь **пакет** `tasks/`.
- **`tests/test_tu_parsed_engineer_notification.py`** — патчи перенесены на реальные модули-носители (`tu_parsing`, `client_response`), т.к. `patch(tasks, "_get_order")` больше не подменял имя, импортированное в подмодуле из `_common`.

### Проверено
- D1.a: `name="app.services.tasks.<funcname>"` — без изменений, registry совпадает.
- `ruff` ✓, `mypy --strict` ✓, `pytest tests/ -q` → 47/47 (вкл. smoke registry).

### Следующий шаг
- **D4** (roadmap) — async/sync граница в API.

---

## [2026-04-22] — Фаза D1.a: Явные `name=` для всех Celery-задач (подготовка к декомпозиции)

### Изменено
- **`backend/app/services/tasks.py`** — всем 23 Celery-задачам добавлен параметр `name="app.services.tasks.<funcname>"` в декораторе `@celery_app.task`. До этого Celery вычислял имя автоматически как `<module>.<funcname>`; при будущем перемещении функций в подмодули (D1.b) имена в registry сломались бы (`beat_schedule` и сообщения в очереди завязаны на полные имена).

### Зачем
Подготовительный шаг перед декомпозицией «толстого» `services/tasks.py` (1717 строк, 70 КБ) на пакет `tasks/{_common, tu_parsing, client_response, contract_flow, post_project_flow, reminders}.py` — roadmap фаза D1. Отдельный атомарный PR, чтобы снизить риск: даже если D1.b задержится или отменится, защита имён уже в проде.

### Проверено
- `celery_app.tasks.keys()` — все 23 задачи зарегистрированы по именам `app.services.tasks.*` (совпадают с именами до изменения).
- `beat_schedule` ссылается на `send_reminders`, `process_due_info_requests`, `send_final_payment_reminders_after_rso_scan` — все три имени сохранились.
- `ruff` ✓, `mypy --strict` ✓, `pytest tests/ -q` → 46/46.

### Не меняется
- Поведение задач (retries, delays, логика).
- Имена задач в registry (строки совпадают до символа).
- API или БД.

### Следующий шаг
- **D1.b** — собственно декомпозиция `tasks.py` на 6 подмодулей (`_common`, `tu_parsing`, `client_response`, `contract_flow`, `post_project_flow`, `reminders`) + `__init__.py` с re-export'ами для backward-compat.

---

## [2026-04-22] — Фаза B3: Alembic — чистые имена + индексы для листинга

### Добавлено
- Alembic-миграция [`20260422_uute_add_listing_indexes.py`](../backend/alembic/versions/20260422_uute_add_listing_indexes.py) — создаёт 3 индекса `CREATE INDEX CONCURRENTLY IF NOT EXISTS` (безопасно в проде, не блокирует таблицу):
  - `ix_orders_created_at_desc` — сортировка «по новизне» в админском listing.
  - `ix_orders_status_created_at_desc` — композитный под `WHERE status = ? ORDER BY created_at DESC` (топ-кейс).
  - `ix_order_files_order_id_category` — под частый паттерн `[f for f in order.files if f.category.value == "tu"]` (см. `app/services/tasks/`, `landing.py`).
  - Downgrade — reversible (`DROP INDEX CONCURRENTLY IF EXISTS`).
  - Защита `if bind.dialect.name != "postgresql": return` — миграция no-op на SQLite/тестах.

### Изменено
- **Переименованы две Alembic-миграции** под соглашение `YYYYMMDD_uute_<описание>.py` (см. CLAUDE.md). Revision ID внутри файлов **не меняются**, чтобы не ломать уже применённую историю в `alembic_version`:
  - `8867df9549c4_add_order_type_and_survey_data.py` → `20260403_uute_add_order_type_and_survey_data.py` (revision = `8867df9549c4` сохранён).
  - `rename_standard_to_custom_order_type.py` → `20260403_uute_rename_order_type_value_to_custom.py` (revision = `rename_standard_to_custom` сохранён).
- **`backend/app/models/models.py`** — добавлены `__table_args__` с `Index(...)`-декларациями на `Order` (2 индекса) и `OrderFile` (1 индекс). SQLAlchemy metadata теперь синхронизирована с БД — это подготовка к будущей initial-миграции (`chore/alembic-initial-migration`).

### Проверено (локально)
- `ruff check` + `ruff format --check` + `mypy --strict` по `app/` — чисто.
- `alembic.ScriptDirectory.walk_revisions()` — одна голова (`20260422_uute_listing_idx`), цепочка длиной 14, без дубликатов и веток.
- `pytest tests/ -q` — 46/46 зелёных.

### Деплой
- **Migration runtime** — первые два индекса `CONCURRENTLY` создаются параллельно чтению, ожидаемое время на ~10k заявок <1 сек. Третий индекс на `order_files` — аналогично.
- **EXPLAIN до/после** — собирается на проде после миграции (см. PR description).

### Следующий шаг
- **Фаза C** по roadmap: упрощение стейт-машины — удаление legacy-статусов (`data_complete`, `generating_project`, `review`, `awaiting_contract`) из `OrderStatus`. По § 13.1 roadmap C1+C2 можно объединить в один PR, так как legacy-заявок в проде нет.

## [2026-04-21] — Фаза B2.a: Нормализация `FileCategory` (non-breaking)

### Добавлено
- Alembic-миграция [`20260421_uute_file_category_lowercase_missing_params.py`](../backend/alembic/versions/20260421_uute_file_category_lowercase_missing_params.py): нормализует исторические значения в `orders.missing_params` JSONB (`BALANCE_ACT` → `balance_act`, `CONNECTION_PLAN` → `connection_plan`). Reversible (downgrade возвращает UPPER_CASE).
- Новый тест-модуль [`tests/test_file_category_b2.py`](../backend/tests/test_file_category_b2.py) (12 тестов): все `.value` — snake_case lowercase, `_missing_` принимает legacy-алиасы, `param_labels.*` корректно работает и на lowercase, и на UPPER_CASE.

### Изменено
- **`backend/app/models/models.py` → `FileCategory`:**
  - `BALANCE_ACT = "balance_act"` (было `"BALANCE_ACT"`).
  - `CONNECTION_PLAN = "connection_plan"` (было `"CONNECTION_PLAN"`).
  - Добавлен classmethod `_missing_(value)` — case-insensitive lookup с `WARNING` в лог: старые клиенты (`?category=BALANCE_ACT`) продолжают работать, **но в B2.b (следующий PR) это станет 422**.
- **`backend/app/services/param_labels.py`:**
  - `CLIENT_DOCUMENT_PARAM_CODES`, `MISSING_PARAM_LABELS`, `SAMPLE_DOCUMENTS` переведены на snake_case lowercase.
  - `_LEGACY_DOCUMENT_PARAM_CODES` расширен UPPER_CASE-кодами — `client_document_list_needs_migration` теперь триггерит миграцию списка для заявок с legacy-значениями в `missing_params`.
  - `get_missing_items` / `get_sample_paths` канонизируют входные коды через `_canonicalize` — письмо «запрос документов» не ломается на старых заявках.
- **Фронтенд:**
  - [`backend/static/admin.html`](../backend/static/admin.html): `<option value>` в форме загрузки файла + словарь `catLabels`.
  - [`backend/static/upload.html`](../backend/static/upload.html): `PARAM_LABELS` перешёл на lowercase ключи.

### Не меняется
- **PG enum `file_category`** — labels остаются UPPER_CASE именами членов (`BALANCE_ACT`, `CONNECTION_PLAN`, …). SQLAlchemy без `values_callable` persist имена, а не `.value`, поэтому смена `.value` не требует `ALTER TYPE ... RENAME VALUE`.
- **Старые файлы в хранилище** (`.../BALANCE_ACT/<uuid>_<name>`) — доступны через `order_files.storage_path` (хранится в БД как относительный путь). Новые файлы сохраняются в `.../balance_act/...`.

### API-контракт
- `GET /api/v1/files?category=balance_act` — канонический формат.
- `GET /api/v1/files?category=BALANCE_ACT` — **по-прежнему работает** в этом релизе (deprecation WARNING в логах). В B2.b будет отвергнут с 422.

### Следующий шаг
- **B2.b** (планируется в отдельном PR через 1–2 релиза): убрать `FileCategory._missing_` compat-shim и legacy-алиасы в `param_labels._B2_LEGACY_ALIASES`. После этого uppercase-значения API категорически не принимаются.

## [2026-04-21] — Фаза B1.b: Миграция мест чтения JSONB через accessor-методы

### Добавлено
- В [`app/repositories/order_jsonb.py`](../backend/app/repositories/order_jsonb.py) — три вспомогательных хелпера `get_*_dict(order)`: валидированный `dict` для шаблонизаторов и legacy-функций (`_normalize_client_requisites`, `auto_fill`), мусорные ключи фильтруются через `extra='ignore'`.
- 4 новых теста в [`tests/test_jsonb_schemas.py`](../backend/tests/test_jsonb_schemas.py) на `*_dict` хелперы (34/34 passed).

### Изменено
- **`backend/app/api/landing.py`:**
  - `POST /landing/orders/{order_id}/survey` — **теперь валидирует тело через Pydantic** (`SurveyData.model_validate(body)`). Некорректные данные → `HTTP 422`. Неизвестные ключи молча отбрасываются (`extra='ignore'`).
  - `UploadPageInfo` / `PaymentPageInfo` собираются через `get_parsed_params_dict` / `get_survey_data_dict`. Ответы с невалидными историческими данными больше не ломают страницу — возвращается пустой объект + WARNING в логе.
  - Введён хелпер `_company_requisites_for_response(order)` — отделяет маркеры ошибок парсинга (`{"error": "..."}`) от нормальных реквизитов.
- **`backend/app/api/parsing.py`:** чтение через accessor, сброс `parsed_params` при `retrigger_parsing` — через `set_parsed_params(order, None)`.
- **`backend/app/api/calculator_config.py`:** `survey_data.get("manufacturer")` → `survey.manufacturer` (типизированно). `auto_fill` получает валидированные dict.
- **`backend/app/services/calculator_config_service.py`:** `resolve_calculator_type_for_express`, `init_config`, `init_config_sync` — через accessor + `*_dict`.
- **`backend/app/services/tasks.py`:**
  - `_collect_project_attachments`: убран локальный `TUParsedData.model_validate`, переведён на `get_parsed_params(order)`.
  - `process_card_and_contract`, `process_company_card_and_send_contract`:
    - `set_company_requisites(order, requisites)` вместо ручного `.model_dump(mode="json")`.
    - Чтение `doc_info` / `rso_info` через типизированный `parsed.document` / `parsed.rso`.
    - `_normalize_client_requisites(get_company_requisites_dict(order), ...)` вместо raw-dict.
  - `parse_company_card_task`: `set_company_requisites(order, requisites)`.
  - Сознательно оставлен raw-доступ в трёх местах (прокомментировано):
    - `_resolve_initial_payment_amount` — ключ `circuits` не описан в `TUParsedData` (устаревший flat-формат).
    - `start_tu_parsing` — ручной `model_dump(exclude={"raw_text"})`: raw_text слишком велик для JSONB.
    - Маркеры ошибок `{"error": "..."}` в `company_requisites` — не `CompanyRequisites`, отдельный формат.

### Инструменты
- [`backend/pyproject.toml`](../backend/pyproject.toml) → `[[tool.mypy.overrides]]`: для `app.schemas.jsonb.*` и `app.repositories.*` включён `strict = true`. Отключены три known-false-positive кода (`no-untyped-call`, `attr-defined`, `arg-type`, `assignment`) — подробные причины в комментарии.

### Безопасность / поведение
- `save_survey` теперь **возвращает 422** на невалидное тело. Реальный фронт (`backend/static/upload.html`) шлёт ровно `collectSurveyData()` — совпадает со схемой, регрессий не ожидается.
- Места, где показывалась ошибка парсинга карточки предприятия (`{"error": "..."}`), продолжают работать — хелпер `_company_requisites_for_response` сохраняет этот особый формат.

### Следующий шаг
- **B1.c** (строгая типизация `OrderResponse` в `schemas.py`) — в связке с **E1** (typed API через `openapi-typescript`), т.к. это формальный breaking change контракта API.

## [2026-04-21] — Фаза B1.a: Pydantic-схемы для JSONB (каркас)

### Добавлено
- Новый модуль [`backend/app/schemas/jsonb/`](../backend/app/schemas/jsonb/):
  - `tu.py` — `TUParsedData` и все её submodel'и (перенесены из `services/tu_schema.py`).
  - `survey.py` — новая модель `SurveyData` для `Order.survey_data` (опросный лист клиента). Поля 1:1 с `collectSurveyData()` в `backend/static/upload.html`.
  - `company.py` — `CompanyRequisites` (перенесена из `services/company_parser.py`).
  - `__init__.py` — публичный API модуля.
- Новый слой [`backend/app/repositories/`](../backend/app/repositories/):
  - `order_jsonb.py` — типизированные accessor-методы `get_parsed_params/set_parsed_params`, `get_survey_data/set_survey_data`, `get_company_requisites/set_company_requisites`. Валидация через `TypeAdapter` происходит **при чтении** с `extra='ignore'`. На невалидных исторических данных — WARNING в лог + возврат `None` (не падаем).
- [`backend/tests/test_jsonb_schemas.py`](../backend/tests/test_jsonb_schemas.py) — 23 unit-теста на модели + accessor-методы (валидация, границы, fallback, backward-compat имортов).

### Изменено
- [`backend/app/services/tu_schema.py`](../backend/app/services/tu_schema.py) — превращён в backward-compat shim (реэкспорт из `app.schemas.jsonb.tu`). Все существующие импорты (`from app.services.tu_schema import TUParsedData`) продолжают работать.
- [`backend/app/services/company_parser.py`](../backend/app/services/company_parser.py) — удалено локальное определение `CompanyRequisites`, добавлен реэкспорт из `app.schemas.jsonb.company`. Поведение парсера не изменилось.

### Безопасность / деплой
- **Runtime не затронут.** Места чтения JSONB в бизнес-коде пока обращаются к полям как раньше (`order.parsed_params["heat_loads"]`). Это будет переписано в следующем PR **B1.b**.
- Модели JSONB используют `extra='ignore'` — исторические записи с устаревшими ключами читаются без ошибок (важно для миграций промпта LLM).

### Следующие шаги (B1.b, B1.c)
- **B1.b:** переписать все места чтения (`admin.py`, `landing.py`, `contract_generator.py`, `email_service.py`, `tasks.py`, `calculator_config_service.py`) через accessor-методы из `app.repositories.order_jsonb`.
- **B1.c:** строгая типизация `OrderResponse` — breaking для фронта, делать в связке с E1 (typed API).

## [2026-04-21] — Фаза A4: Frontend baseline (vitest + .env.example)

### Добавлено
- [`frontend/.env.example`](../frontend/.env.example) — шаблон env для фронта с `VITE_API_BASE_URL=/api/v1`. Документирует поведение в prod (same-origin), dev (vite proxy) и при выносе API на отдельный домен.
- [`frontend/src/utils/pricing.ts`](../frontend/src/utils/pricing.ts) — чистые функции расчёта цены (`calcIndividualPrice`, `calcExpressPrice`, `formatPrice`) + константы `INDIVIDUAL_PRICES` / `EXPRESS_PRICE`. Единый источник правды по тарифам.
- [`frontend/src/utils/pricing.test.ts`](../frontend/src/utils/pricing.test.ts) — 5 unit-тестов на pricing (vitest).
- **`vitest`** (v2.1.x) в `frontend/package.json` → `devDependencies`. Скрипты `test` (vitest run) и `test:watch` (watch-режим).
- Секция `test` в [`frontend/vite.config.ts`](../frontend/vite.config.ts) (node environment, `src/**/*.{test,spec}.{ts,tsx}`).
- Шаг **`Test (vitest)`** в CI `frontend` job (между lint и build).

### Изменено
- [`frontend/src/api.ts`](../frontend/src/api.ts): `const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'` — обратно-совместимо, без `.env` работает как раньше.
- [`frontend/src/components/CalculatorSection.tsx`](../frontend/src/components/CalculatorSection.tsx): удалён дублирующий расчёт цен (`useState` + `useEffect` с inline-объектом prices), подключён `src/utils/pricing.ts`. Поведение UI не изменилось.

### Безопасность / деплой
- **Runtime не затронут.** Prod-образ использует `/api/v1` как раньше (переменная не задана → fallback).
- CI frontend-job стал строже: теперь падает не только на lint/build, но и на регрессии pricing.

## [2026-04-21] — Фаза A3: GitHub Actions CI

### Добавлено
- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — четыре активных job:
  - **lint-type** — `ruff check` + `ruff format --check` + `mypy` на `backend/`.
  - **tests** — `pytest backend/tests/` (7 unit-тестов, БД не требуется).
  - **frontend** — `node 20`, `npm ci` + `npm run lint` + `npm run build`.
  - **pre-commit** — прогон всех хуков через `pre-commit/action@v3.0.1` (кэшируется).
- Конкурентность: `concurrency.group=ci-${{ github.ref }}, cancel-in-progress=true` — автоматически отменяет предыдущие прогоны в той же ветке.
- CI-бейдж в корневом [`README.md`](../README.md).

### Изменено
- [`frontend/src/components/EmailModal.tsx`](../frontend/src/components/EmailModal.tsx) — убран `any` в `catch (err)`, заменён на `unknown` + narrowing через `err instanceof Error`.
- [`backend/pyproject.toml`](../backend/pyproject.toml) — в `[tool.pytest.ini_options]` добавлены `pythonpath = ["."]` и `testpaths = ["tests"]` (пути относительно backend/). Без этого pytest без editable install не находил пакет `app`.
- [`backend/alembic/env.py`](../backend/alembic/env.py) — добавлен sys.path-shim: корень `backend/` вставляется в `sys.path` перед `from app.*` импортами. В Docker безвреден (WORKDIR=/app уже в path), в dev/CI делает `alembic` работоспособным без editable install.

### Исправлено
- CI `lint-type` и `tests` изначально падали на `pip install -e "backend[dev]"` из-за отсутствия секции `[build-system]` в `pyproject.toml`. Решение: dev-deps ставятся напрямую по тем же версиям (`pip install "ruff>=0.6,<1.0" ...`). Editable install вернём, когда появится фаза, где пакет `app` имеет смысл инсталлировать как distribution.

### Известные ограничения
- **Job `alembic` временно отключён (закомментирован в `ci.yml`)**. На чистой БД `alembic upgrade head` падает с `UndefinedTableError: relation "order_files" does not exist`: в репо нет initial-миграции, первая в цепочке уже ссылается на таблицу, созданную «до base». Включим обратно после задачи `chore/alembic-initial-migration` (см. `docs/tasktracker.md`). В prod это не воспроизводится — БД живёт с предыдущих релизов.

### Безопасность / деплой
- **Runtime не затронут.** Workflow запускается на `push` (все ветки) и `pull_request` в `main`.
- В job-ах, требующих `Settings()`, заданы фейковые значения `ADMIN_API_KEY`, `SMTP_PASSWORD`, `OPENROUTER_API_KEY` — в тестах они не используются.

## [2026-04-21] — Фаза A2: pyproject + ruff + mypy + pre-commit

### Добавлено
- [`backend/pyproject.toml`](../backend/pyproject.toml) — PEP 621-конфиг: `[project]` (имя, Python ≥3.12), `[project.optional-dependencies.dev]` (ruff, mypy, pytest, pytest-asyncio, pytest-cov, httpx, pre-commit), настройки `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.format]`, `[tool.mypy]`, `[tool.pytest.ini_options]`. Dev-зависимости ставятся через `pip install -e "backend[dev]"`; prod продолжает использовать `requirements.txt` без изменений.
- [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) — хуки: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`, `check-merge-conflict`, `check-added-large-files`, `ruff-check --fix`, `ruff-format`, `mypy` (с runtime-зависимостями Pydantic/SQLAlchemy/FastAPI). Установка: `pip install --user pre-commit && pre-commit install`.
- В [`CLAUDE.md`](../CLAUDE.md) раздел «Dev-инструменты» с инструкцией по установке и запуску.

### Изменено
- Однократный прогон `ruff format backend/` — 34 файла `backend/app/**/*.py` переформатированы (LF, двойные кавычки, trailing-commas); поведение кода не меняется.
- Автофиксы хуков `end-of-file-fixer` и `trailing-whitespace` — добавлены финальные переводы строк в ряде docs- и frontend-файлов (косметика).

### Безопасность / деплой
- **Runtime не затронут.** Prod-образ собирается по-прежнему из `requirements.txt`; pyproject используется только dev-инструментами.
- Ruff линтинг настроен в режиме **baseline**: кириллица в строках/комментариях не триггерит RUF001/002/003; правила с массовыми нарушениями (I001, UP017, UP035, B904 и др.) временно в `ignore` — будут сняты отдельным PR `chore/audit-ruff-cleanup`.
- Mypy в режиме baseline: существующий код в `app.*` игнорируется через `[[tool.mypy.overrides]] ignore_errors = true`; новые модули (фазы B1/D1–D3) будут заводиться со `strict = true`.

## [2026-04-21] — Фаза A1: пути к фронту и uploads вынесены в Settings

### Изменено
- В [`backend/app/core/config.py`](../backend/app/core/config.py) добавлены поля `frontend_dist_dir` и `upload_dir` (перезаписан) с factory-дефолтами. Логика дефолтов:
  - `FRONTEND_DIST_DIR` — prod: `/app/frontend-dist` (если существует); dev: `<repo>/frontend/dist`.
  - `UPLOAD_DIR` — prod: `/var/uute-service/uploads` (если существует); dev: `<repo>/uploads`.
  - Оба значения переопределяются переменными окружения.
- В [`backend/app/main.py`](../backend/app/main.py) убран захардкоженный `FRONTEND_DIR = Path("/app/frontend-dist")`; теперь используется `settings.frontend_dist_dir`.
- В [`backend/.env.example`](../backend/.env.example) задокументирован `FRONTEND_DIST_DIR` (оставлен закомментированным — auto-fallback в коде), обновлено описание `UPLOAD_DIR`.
- В [`CLAUDE.md`](../CLAUDE.md) в таблице ENV-переменных уточнены значения `UPLOAD_DIR` и добавлен `FRONTEND_DIST_DIR`.

### Безопасность / деплой
- **Prod не требует изменений.** Если обе переменные не заданы в `backend/.env` на сервере, код автоматически выбирает prod-пути (`/app/frontend-dist`, `/var/uute-service/uploads`) за счёт проверки существования каталогов. Поведение идентично прежнему.
- **Dev-среда** (`uvicorn backend.app.main:app --reload` на хосте): SPA-маршруты больше не зависят от существования `/app/frontend-dist` — после `cd frontend && npm run build` backend отдаёт SPA из `frontend/dist`.
- Pydantic-валидация обязательных полей (`ADMIN_API_KEY`, `OPENROUTER_API_KEY`, `SMTP_PASSWORD`) сохранена.

## [2026-04-21] — Раздел 3 аудита: решения по открытым вопросам

### Изменено
- В [`docs/plans/2026-04-20-audit-section-3-maintainability-roadmap.md`](plans/2026-04-20-audit-section-3-maintainability-roadmap.md) добавлена секция **§ 13.1 «Принятые решения (2026-04-21)»**. Зафиксировано:
  - Legacy-статусы: живых заявок в проде нет, все записи в `orders` тестовые и удаляемы → фаза C упрощается, C1+C2 допустимо слить в один PR.
  - `FileCategory` нормализация: делаем **через два релиза** (non-breaking → breaking).
  - `admin.html` декомпозиция: ответ отложен; пока планируем минимальный вариант (модули без React).
  - Sentry, `psycopg3`, CI provider, coverage gate — приняты дефолты (отложено / GitHub Actions / без fail-порога).
- В § 7 roadmap добавлено примечание о том, что data-миграция в C1 теперь не требуется.

### Безопасность / деплой
- Решений, меняющих runtime, нет — только планирование. Следующий шаг — открыть PR `chore/audit-a1-paths` (фаза A, пункт A1).

## [2026-04-20] — Восстановление пропущенной prod-миграции advance_payment_model

### Добавлено
- Файл [`backend/alembic/versions/87fcef6f52ff_20260415_uute_advance_payment_model.py`](../backend/alembic/versions/87fcef6f52ff_20260415_uute_advance_payment_model.py) — миграция `87fcef6f52ff`, которая создаёт enum `payment_method` и добавляет в `orders` колонки `payment_method`, `payment_amount`, `advance_amount`, `advance_paid_at`, `final_paid_at`, `company_requisites`, `contract_number`; дополняет значения в enum-ах `order_status` (`AWAITING_CONTRACT`, `CONTRACT_SENT`, `ADVANCE_PAID`, `AWAITING_FINAL_PAYMENT`), `file_category` (`COMPANY_CARD`, `CONTRACT`, `INVOICE`, `RSO_SCAN`), `email_type` (`PROJECT_READY_PAYMENT`, `CONTRACT_DELIVERY`, `ADVANCE_RECEIVED`, `FINAL_PAYMENT_REQUEST`, `FINAL_PAYMENT_RECEIVED`); заменяет unique-constraint на unique-индекс в `calculator_configs`. Миграция была сгенерирована через `alembic revision --autogenerate` прямо на production-сервере 2026-04-14 и применена к prod-БД, но никогда не попала в git — на clean БД `alembic upgrade head` не создавал `advance_amount`/`advance_paid_at`, хотя модель `Order` (`backend/app/models/models.py:256-257`) эти колонки читает. Это блокировало любой re-deploy на новой инфраструктуре.
- Файл [`backend/alembic/script.py.mako`](../backend/alembic/script.py.mako) — стандартный шаблон Alembic для `alembic revision`; ранее отсутствовал в репозитории, из-за чего нельзя было сгенерировать новые миграции локально.

### Изменено
- В [`backend/alembic/versions/20260416_uute_signed_contract_enums.py`](../backend/alembic/versions/20260416_uute_signed_contract_enums.py): `down_revision` переключён с `"20260412_uute_calc_configs"` на `"87fcef6f52ff"`. Это встраивает восстановленную миграцию в линейную цепочку без появления двух голов. На prod БД ничего не меняется (alembic_version = `20260416_uute_tu_parsed_notification`, `upgrade head` = nothing to do), на чистой БД цепочка корректно пройдёт все 12 ревизий от `20260402_uute_fc` до текущей головы.

### Безопасность / деплой
- Перед следующим деплоем (`docker compose up -d --build backend`) на prod сверить `docker exec uute-project-postgres-1 psql -U postgres -d uute -c "SELECT version_num FROM alembic_version;"` — должно быть `20260416_uute_tu_parsed_notification`, `alembic upgrade head` ничего не применит.
- На dev-стендах, клонирующих репо заново: `alembic upgrade head` корректно пройдёт всю цепочку.

## [2026-04-20] — Раздел 3 аудита: roadmap по поддерживаемости и архитектуре

### Добавлено
- Файл [`docs/plans/2026-04-20-audit-section-3-maintainability-roadmap.md`](plans/2026-04-20-audit-section-3-maintainability-roadmap.md) — подробный roadmap по разделу 3 аудита (пункты 3.1–3.11): 6 фаз (Фундамент, Типизация данных, Упрощение стейт-машины, Декомпозиция «толстых» модулей, Frontend, Зависимости), матрица приоритетов (impact × effort × risk), mermaid-граф зависимостей фаз, критерии готовности, риски с mitigation, открытые вопросы для продакта, последовательность из ~18 PR.

## [2026-04-20] — Раздел 2 аудита: срочные правки безопасности

### Изменено
- В [`backend/app/main.py`](../backend/app/main.py): `CORSMiddleware` больше не использует wildcard `*`; список origin-ов читается из `settings.cors_origins` (ENV `CORS_ORIGINS`, JSON-список). Дефолт — только `https://constructproject.ru`. Сочетание `*` + `allow_credentials=True` всё равно отбрасывалось браузерами по спеке, поэтому регрессов на проде нет.
- В [`backend/app/core/auth.py`](../backend/app/core/auth.py): `verify_admin_key` теперь сравнивает ключ через `secrets.compare_digest` (защита от timing-атак). Query-параметр `?_k=` оставлен как deprecated fallback и при использовании логируется WARNING с маскированным ключом — чтобы найти и убрать оставшихся клиентов перед его удалением.
- В [`backend/app/core/config.py`](../backend/app/core/config.py): убраны небезопасные дефолты для секретов — `admin_api_key` (≥16 симв.), `openrouter_api_key`, `smtp_password` теперь `Field(..., ...)` без значения. Если переменных нет в `.env`, `Settings()` падает с понятной ошибкой Pydantic. Добавлено поле `cors_origins: list[str]`.
- В [`backend/.env.example`](../backend/.env.example): помечены `[REQUIRED]` поля, добавлен `CORS_ORIGINS` с примером JSON-списка, добавлена подсказка по генерации `ADMIN_API_KEY` через `secrets.token_urlsafe(32)`.

### Исправлено
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): тихий `except Exception: pass` после `send_new_order_notification` (создание заявки) заменён на `logger.exception(...)` — теперь сбои отправки уведомления инженеру попадают в логи и не маскируются.

### Безопасность
- Wildcard CORS больше не разрешён. Перед деплоем убедиться, что в боевом `.env` задан `CORS_ORIGINS` со всеми реальными origin-ами (как минимум прод-домен; для preview-стендов — добавить их в JSON-список).
- При обновлении на сервере **обязательно** проверить, что в `~/uute-project/backend/.env` есть `ADMIN_API_KEY`, `OPENROUTER_API_KEY`, `SMTP_PASSWORD` — иначе backend не стартует.

## [2026-04-20] — Уборка документации и репозитория после аудита

### Добавлено
- Каталог [`docs/archive/2026-Q2/`](archive/2026-Q2/) со всеми завершёнными task-трекерами и реализованными планами (включая `payment-advance-tasktracker.md`, `smart-survey-tasktracker.md`, `two-option-order-tasktracker.md`, `tasktracker-soprovod.md`, `tasktrecker-otchet-parsing.md`, `tasktrecker-progrssbar.md`, `plan-unified-upload-contract.md`, а также `plans/2026-04-16-*.md`, `superpowers/plans/*.md`, `superpowers/specs/*.md`).
- В [`.gitignore`](../.gitignore): `*.sql`, `*Zone.Identifier`, `docs/rekvizit_acc.md`, `docs/secrets/`, `.secrets/` — чтобы локальные дампы БД, артефакты Windows/WSL и реквизиты ИП больше не попадали в git.

### Изменено
- Переименованы файлы с пробелами и `(N)` в имени:
  - `docs/kontrakt_ukute_template (2).md` → [`docs/kontrakt_ukute_template.md`](kontrakt_ukute_template.md)
  - `docs/scheme-generator-roadmap (1).md` → [`docs/scheme-generator-roadmap.md`](scheme-generator-roadmap.md)
- Перенесён справочник городов: `docs/cities_from_table1.md` → [`backend/calculator_templates/cities_from_table1.md`](../backend/calculator_templates/cities_from_table1.md) (рядом с другими шаблонами калькулятора).
- В [`frontend/package.json`](../frontend/package.json): `name` изменён с placeholder `vite-react-typescript-starter` на `uute-landing`, добавлены `description` и `version` `0.1.0`.
- В [`CLAUDE.md`](../CLAUDE.md): актуализированы стейт-машина (`OrderStatus` с веткой оплаты и замечаний РСО), раздел «Текущий статус разработки» (полный production-флоу + backlog), описание структуры `docs/` (включая `archive/`).
- В [`backend/app/services/contract_generator.py`](../backend/app/services/contract_generator.py): docstring и комментарии указывают на новое имя шаблона `docs/kontrakt_ukute_template.md`.
- В [`docs/project.md`](project.md), [`docs/changelog.md`](changelog.md), [`docs/tasktracker.md`](tasktracker.md): обновлены ссылки на переименованные/перенесённые в архив файлы.

### Удалено
- Пустые/устаревшие файлы:
  - `backup_20260411.sql` (пустой дамп в корне репо)
  - `frontend/.env` (пустой файл)
  - `cursorrules` (устаревший — актуальные правила теперь в `.cursor/rules/`)
  - `.cursor/rules/calculator-config-design.md:Zone.Identifier` (артефакт WSL/Windows)
  - `docs/opros_list_form.pdf` (полный дубликат [`frontend/public/downloads/opros_list_form.pdf`](../frontend/public/downloads/opros_list_form.pdf), md5 совпадает)
  - `docs/rekvizit_acc.md` (содержал реальные реквизиты ИП; в git ещё не был зафиксирован, поэтому из истории убирать не требуется)

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
- В [`backend/app/services/contract_generator.py`](../backend/app/services/contract_generator.py): текст договора и приложений синхронизирован с шаблоном [`docs/kontrakt_ukute_template.md`](kontrakt_ukute_template.md), включая обновлённые формулировки разделов 4–14 и приложений 1–3.
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
- Статический файл [`frontend/public/downloads/opros_list_form.pdf`](../frontend/public/downloads/opros_list_form.pdf): единственный источник опросного листа (ранее дублировался в `docs/opros_list_form.pdf`, дубль удалён — см. запись `[2026-04-20]`).

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
