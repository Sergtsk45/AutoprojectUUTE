<!--
@file: docs/backlog.md
@description: Единый реестр технического и продуктового долга проекта. Консолидирует
              открытые пункты roadmap аудита §3, хвосты завершённых фаз и отложенные
              продуктовые решения. Источник истины для планирования: из roadmap,
              tasktracker и CLAUDE.md ссылки ведут сюда.
@dependencies: docs/plans/2026-04-20-audit-section-3-maintainability-roadmap.md,
               docs/tasktracker.md, docs/changelog.md, docs/project.md, CLAUDE.md
@created: 2026-04-22
-->

# Долговой backlog проекта АвтопроектУУТЭ

> Единый реестр технического и продуктового долга. Пополняется при обнаружении
> хвостов после любой фазы аудита или при вскрытии проблем, которые осознанно
> оставляют «на потом». Закрывается отдельным PR с записью в
> [`docs/changelog.md`](changelog.md) и обновлением статуса здесь.

## 1. Как пользоваться

- **Источник истины** по долгу: этот файл. В
  [roadmap аудита](plans/2026-04-20-audit-section-3-maintainability-roadmap.md),
  [`tasktracker.md`](tasktracker.md), [`CLAUDE.md`](../CLAUDE.md) остаются только
  ссылки на конкретные пункты backlog'а (`BL-XXX`).
- **ID стабильный.** Если элемент закрыт — статус меняется на `done`, запись
  остаётся в файле (можно найти, когда закрыли и чем).
- **Новый элемент** → следующий свободный `BL-XXX` (трёхзначный), категория (A/B/C),
  заполнить все поля шаблона (см. §6).
- **Изменение приоритета/scope** → править запись + добавить строку в журнале §7.
- **Закрытие** → статус `done`, ссылка на PR/commit, дата, краткое «чем закрыт».

## 2. Легенда

**Статусы:**

- `open` — активный, можно брать в работу.
- `deferred` — отложен по явному решению (указана причина и триггер возврата).
- `blocked` — ждёт внешнее событие (решение продакта, merge другой задачи,
  prod-инцидент и т. п.); указан блокер.
- `done` — закрыт (фиксируем дату и PR).

**Приоритет** — та же матрица, что в
[roadmap §4](plans/2026-04-20-audit-section-3-maintainability-roadmap.md#4-матрица-приоритетов):

- **Impact**: H (снимает заметный риск/трение), M (умеренно), L (косметика).
- **Effort**: H (>3 чел·дней), M (1–3), L (<1).
- **Risk**: H (высокий шанс регресса), M (средний), L (низкий).

**Категории:**

- **A. Roadmap-долг** — пункты, оставшиеся незакрытыми после аудита раздела 3.
- **B. Хвосты завершённых фаз** — backward-compat shim'ы, частичные scope,
  документированные ограничения миграций, нестрогая обратимость.
- **C. Продуктовый долг** — требует решения продакт-владельца до старта.
- **D. Прочее** — вне scope аудита §3: LLM-пайплайн, email-шаблоны, мониторинг.

## 3. Индекс

| ID | Тема | Кат. | Статус | Impact | Effort | Risk | Блокер |
|---|---|:---:|:---:|:---:|:---:|:---:|---|
| [BL-001](#bl-001--f1-унификация-pg-драйвера-на-psycopgbinary-v3) | F1 — psycopg3 | A | deferred (Q3/Q4) | M | M | H | BL-002 |
| [BL-002](#bl-002--f2-baseline-нагрузочный-тест) | F2 — baseline нагрузочный тест | A | open | M | M | L | — |
| [BL-003](#bl-003--sentryglitchtip-для-backend--celery) | Sentry/Glitchtip | A | deferred | M | M | L | — |
| [BL-004](#bl-004--mypy---strict-для-repositories) | mypy `--strict` для `repositories/*` | A | open | M | L | L | — |
| [BL-005](#bl-005--pytest-coverage--40-) | pytest coverage ≥ 40 % | A | open | M | M | L | — |
| [BL-006](#bl-006--миграция-adminhtml-на-react) | `admin.html` → React (эпик) | A | deferred | L | H | M | BL-017 |
| [BL-010](#bl-010--удалить-backward-compat-shim-servicestaskspy) | Shim `services/tasks.py` | B | open | L | L | L | 1 релиз после D1 |
| [BL-011](#bl-011--удалить-backward-compat-shim-servicesemail_servicepy) | Shim `services/email_service.py` | B | open | L | L | L | 1 релиз после D2 |
| [BL-012](#bl-012--удалить-backward-compat-shim-servicescontract_generatorpy) | Shim `services/contract_generator.py` | B | open | L | L | L | 1 релиз после D3 |
| [BL-013](#bl-013--full-scope-c1c2-удалить-awaiting_contract-и-legacy-payment-flow) | Full-scope C1/C2: `AWAITING_CONTRACT` | B | blocked | M | M | M | BL-030 |
| [BL-014](#bl-014--строгая-валидация-jsonb-при-записи-llm-ответов--метрика-дрейфа) | Строгая JSONB-валидация LLM-ответов | B | open | M | M | M | — |
| [BL-015](#bl-015--унифицировать-pydanticfastapi-между-dev-и-ci) | Pydantic/FastAPI drift в E1 | B | open | L | L | L | — |
| [BL-016](#bl-016--eslint--prettier-для-backendstaticjs) | ESLint/Prettier для `backend/static/js/**` | B | open | M | L | L | — |
| [BL-017](#bl-017--сборщик-esbuildvite-для-статики-backendstatic) | Сборщик (esbuild/Vite) для static | B | open | L | M | M | BL-016 |
| [BL-018](#bl-018--structlog--sentry-для-celery-логов) | `structlog` / Sentry для Celery | B | open | M | L | L | BL-003 |
| [BL-019](#bl-019--b2b-downgrade-миграции-не-восстанавливает-upper_case) | B2.b downgrade — нестрогая обратимость | B | accepted | L | L | L | — |
| [BL-020](#bl-020--c1c2-downgrade-не-восстанавливает-статусы-заявок) | C1+C2 downgrade — нестрогая обратимость | B | accepted | L | L | L | — |
| [BL-021](#bl-021--orderstatus-lowercase-python-values-vs-uppercase-db-storage) | `OrderStatus` lowercase Python vs UPPERCASE DB | B | open | M | M | M | — |
| [BL-030](#bl-030--решение-по-двум-веткам-оплаты) | Решение: одна ветка оплаты из двух | C | blocked | H | L | M | продакт |
| [BL-031](#bl-031--консолидация-или-удаление-paymenthtml) | Консолидация/удаление `payment.html` | C | blocked | M | M | M | BL-030 |
| [BL-032](#bl-032--регрессионные-тесты-llm-парсера-ту) | Регрессионные тесты LLM парсера ТУ | D | open | H | H | M | — |
| [BL-033](#bl-033--snapshot-тесты-для-email-шаблонов) | Snapshot-тесты email-шаблонов | D | open | M | M | L | — |
| [BL-034](#bl-034--убрать-_k-query-параметр-для-admin-auth) | Убрать `?_k=` query для admin auth | D | open | M | L | L | — |

---

## 4. Элементы

### A. Roadmap-долг

#### BL-001 — F1: унификация PG-драйвера на `psycopg[binary] v3`

- **Источник:**
  [roadmap §10, F1](plans/2026-04-20-audit-section-3-maintainability-roadmap.md#f1-унификация-pg-драйвера).
- **Статус:** `deferred` (решение
  [§13.1 п.5](plans/2026-04-20-audit-section-3-maintainability-roadmap.md#131-принятые-решения-2026-04-21) — отложено в Q3/Q4).
- **Приоритет:** Impact M / Effort M / Risk **H** (возможно падение RPS).
- **Блокер:** [BL-002](#bl-002--f2-baseline-нагрузочный-тест) — без baseline RPS
  мигрировать драйвер небезопасно.
- **Триггер возврата:** закрытие BL-002 или прод-инцидент на стыке
  `asyncpg` ↔ `psycopg2-binary`.
- **DoD:** `requirements.txt` без `asyncpg` и `psycopg2-binary`, сравнительная
  таблица RPS в PR, `alembic upgrade → downgrade → upgrade` зелёный.

#### BL-002 — F2: baseline нагрузочный тест

- **Источник:** вскрыто в ходе планирования F1; в roadmap явно отсутствовал.
- **Статус:** `open`.
- **Приоритет:** Impact M / Effort M / Risk L.
- **Описание:** Нужен фиксированный сценарий `ab`/`wrk`/`k6` по ключевым
  эндпоинтам (`POST /api/v1/landing/orders`, `GET /api/v1/admin/orders`,
  `POST /api/v1/landing/orders/{id}/files`) с baseline-таблицей в репо. Без
  него любой драйверный/инфраструктурный рефакторинг (BL-001) делается вслепую.
- **DoD:** в `docs/perf/` лежит сценарий + последняя таблица с RPS/latency/err%
  по каждому эндпоинту на dev-стенде; CI-джоб или скрипт запускает сценарий
  ровно одной командой.

#### BL-003 — Sentry/Glitchtip для backend + Celery

- **Источник:**
  [roadmap §13.1 п.4](plans/2026-04-20-audit-section-3-maintainability-roadmap.md#131-принятые-решения-2026-04-21).
- **Статус:** `deferred` (отдельной задачей после фазы D — фаза D закрыта).
- **Приоритет:** Impact M / Effort M / Risk L.
- **Описание:** Celery-исключения сейчас видны только в stdout worker'а;
  FastAPI-ошибки — только в access-логе nginx/uvicorn. Нужен единый
  агрегатор: Sentry SDK для FastAPI + Celery, DSN через ENV.
- **Связано:** [BL-018](#bl-018--structlog--sentry-для-celery-логов) — JSON-логи
  удобнее после подключения Sentry.

#### BL-004 — mypy `--strict` для `repositories/*`

- **Источник:**
  [roadmap §11 DoD](plans/2026-04-20-audit-section-3-maintainability-roadmap.md#11-критерии-готовности-всего-раздела-dod).
- **Статус:** `open`.
- **Приоритет:** Impact M / Effort L / Risk L.
- **Описание:** `mypy --strict` сейчас включён только на
  `services/tasks/*`, `services/email/*`, `services/contract/*`, `schemas/jsonb/*`.
  DoD раздела 3 требует также `repositories/*`. В `backend/pyproject.toml`
  добавить override и вычистить возникшие ошибки.

#### BL-005 — pytest coverage ≥ 40 %

- **Источник:**
  [roadmap §11 DoD](plans/2026-04-20-audit-section-3-maintainability-roadmap.md#11-критерии-готовности-всего-раздела-dod).
- **Статус:** `open`.
- **Приоритет:** Impact M / Effort M / Risk L.
- **Описание:** Сейчас coverage-gate в CI — только отчёт без fail-порога
  (см. [§13.1 п.7](plans/2026-04-20-audit-section-3-maintainability-roadmap.md#131-принятые-решения-2026-04-21)).
  Нужно (а) измерить текущее покрытие, (б) закрыть пробелы до 40 % (в первую
  очередь `api/`, `services/tasks/`, `services/contract/`), (в) поднять
  fail-порог в CI.

#### BL-006 — Миграция `admin.html` на React

- **Источник:**
  [roadmap §13.1 п.3](plans/2026-04-20-audit-section-3-maintainability-roadmap.md#131-принятые-решения-2026-04-21).
- **Статус:** `deferred` (эпик ~10 чел·дней, оценивается отдельно).
- **Приоритет:** Impact L / Effort H / Risk M.
- **Блокер:** сначала закрываем
  [BL-017](#bl-017--сборщик-esbuildvite-для-статики-backendstatic) — сборщик
  для статики; без него React-миграция ломает простую схему «vanilla-JS +
  inline onclick».
- **DoD:** `admin.html` заменён на маршрут React-SPA; все inline `onclick`
  переехали в React-компоненты; функциональная регрессия = 0.

---

### B. Хвосты завершённых фаз

#### BL-010 — Удалить backward-compat shim `services/tasks.py`

- **Источник:** [D1.b](tasktracker.md) — «1 релиз потом удалить» из
  [roadmap §8 Общий подход](plans/2026-04-20-audit-section-3-maintainability-roadmap.md#8-фаза-d--декомпозиция-толстых-модулей).
- **Статус:** `open`.
- **Приоритет:** Impact L / Effort L / Risk L.
- **Триггер:** 1 релиз с даты merge D1 прошёл, новых импортов `from
  app.services.tasks import …` в стороннем коде не появилось
  (проверить `rg "from app.services.tasks import"`).
- **DoD:** shim-файл удалён, `from app.services.tasks import <task>` продолжает
  работать через пакет `services/tasks/__init__.py`.

#### BL-011 — Удалить backward-compat shim `services/email_service.py`

- **Источник:** [D2](tasktracker.md).
- **Статус:** `open`.
- **Приоритет:** Impact L / Effort L / Risk L.
- **Триггер/DoD:** аналогично BL-010, но для пакета `services/email/`.

#### BL-012 — Удалить backward-compat shim `services/contract_generator.py`

- **Источник:** [D3](tasktracker.md).
- **Статус:** `open`.
- **Приоритет:** Impact L / Effort L / Risk L.
- **Триггер/DoD:** аналогично BL-010, но для пакета `services/contract/`.

#### BL-013 — Full-scope C1/C2: удалить `AWAITING_CONTRACT` и legacy payment-flow

- **Источник:** [C1+C2 запись в tasktracker (2026-04-22)](tasktracker.md) —
  revised scope, `AWAITING_CONTRACT` оставлен.
- **Статус:** `blocked` (ждёт [BL-030](#bl-030--решение-по-двум-веткам-оплаты)).
- **Приоритет:** Impact M / Effort M / Risk M.
- **Описание:** Нужно убрать `AWAITING_CONTRACT` из `OrderStatus`,
  `ALLOWED_TRANSITIONS[CLIENT_INFO_RECEIVED] → AWAITING_CONTRACT`, task
  `process_company_card_and_send_contract`, эндпоинты
  `/landing/orders/{id}/upload-company-card` и
  `/landing/orders/{id}/select-payment-method`, а также (скорее всего)
  `backend/static/payment.html`. Требует предварительного решения по
  BL-030/BL-031.
- **DoD:** enum `order_status` в PostgreSQL не содержит `awaiting_contract`;
  нет упоминаний в Python/JS/HTML; миграция обратима как минимум на уровне
  схемы.

#### BL-014 — Строгая валидация JSONB при записи LLM-ответов + метрика дрейфа

- **Источник:** [roadmap §6, B1, Risk/Rollback](plans/2026-04-20-audit-section-3-maintainability-roadmap.md#b1-pydantic-схемы-для-jsonb).
- **Статус:** `open`.
- **Приоритет:** Impact M / Effort M / Risk M.
- **Описание:** Сейчас чтение `parsed_params`/`survey_data`/`company_requisites`
  валидируется с `extra="ignore"` и fallback'ом в `None` + WARN-лог. На записи
  LLM-ответа строгая валидация **не включена**, чтобы смена prompt'а не роняла
  пайплайн. Нужна (а) опциональная строгая валидация за feature-flag, (б)
  Prometheus-метрика `parsed_params_schema_drift_total{schema="tu"}` и алёрт.
- **DoD:** метрика в `/metrics`, алёрт в `docs/ops/`, в prod включён «soft»
  режим (WARN+metric), в dev — `strict`.

#### BL-015 — Унифицировать Pydantic/FastAPI между dev и CI

- **Источник:** [E1 post-mortem](changelog.md) (drift `openapi.json` из-за
  `pydantic 2.12 vs 2.9`).
- **Статус:** `open`.
- **Приоритет:** Impact L / Effort L / Risk L.
- **Описание:** В
  [`scripts/generate-api-types.sh`](../scripts/generate-api-types.sh) стоит
  version-guard на `pydantic==2.9.2` / `fastapi==0.115.0`. Хрупко: любой
  `pip install` в dev ломает drift-check. Варианты: (а) поднять pin в
  `requirements.txt` + prod-образе, (б) всегда регенерировать OpenAPI внутри
  того же Docker-образа, что CI (`docker compose run --rm backend
  scripts/generate-api-types.sh`).
- **DoD:** не нужен version-guard в скрипте; запустить скрипт локально и в
  CI — тот же результат без ручных обходов.

#### BL-016 — ESLint + Prettier для `backend/static/js/**`

- **Источник:** вскрыто после E3/E4 (модули там только `node --check`).
- **Статус:** `open`.
- **Приоритет:** Impact M / Effort L / Risk L.
- **Описание:** 11 JS-файлов в `backend/static/js/admin/` и
  `backend/static/js/upload/` не покрыты линтером. Во frontend/ ESLint есть,
  но он смотрит только `frontend/src`. Нужен отдельный `.eslintrc` в
  `backend/static/` (env: browser + globals), CI-джоб `eslint backend/static/js`.
- **DoD:** CI-джоб зелёный, все 11 файлов проходят ESLint + Prettier.

#### BL-017 — Сборщик (esbuild/Vite) для статики `backend/static/`

- **Источник:** roadmap §9 E3 — «не вошло в минимальный вариант».
- **Статус:** `open`.
- **Приоритет:** Impact L / Effort M / Risk M.
- **Блокер:** после [BL-016](#bl-016--eslint--prettier-для-backendstaticjs)
  (проще настроить сборщик поверх уже линтящегося кода).
- **Описание:** Сейчас `<script>` загружаются «обычно» (не модули) ради
  глобальных функций для inline `onclick`. Сборщик даст минификацию,
  ES-модули, code-splitting, но потребует либо переписать inline-хендлеры,
  либо явно эмитить globals через esbuild `--global-name`.
- **DoD:** `backend/static/js/**/*.js` собираются в один или несколько бандлов;
  `admin.html` и `upload.html` подключают только бандлы; исходники остаются в
  репо, сборка — часть Docker-образа backend.

#### BL-018 — `structlog` + Sentry для Celery-логов

- **Источник:** roadmap §8 D5.
- **Статус:** `open`.
- **Приоритет:** Impact M / Effort L / Risk L.
- **Блокер:** удобнее **после** [BL-003](#bl-003--sentryglitchtip-для-backend--celery).
- **Описание:** Заменить стандартный logger на `structlog` с JSON-renderer в
  prod и `ConsoleRenderer` в dev. Все Celery-задачи получают `order_id`, `task_id`
  и `event_type` как context vars через `celery.signals.before_task_publish` /
  `task_prerun`.
- **DoD:** логи worker'а в prod — валидный JSON построчно; `order_id`/`task_id`
  присутствуют в каждой записи; Sentry-breadcrumbs используют тот же context.

#### BL-019 — B2.b downgrade миграции не восстанавливает `UPPER_CASE`

- **Источник:** [B2.b changelog](changelog.md) / [B2.b tasktracker](tasktracker.md).
- **Статус:** `accepted` (задокументированное ограничение; закрывать не планируется).
- **Приоритет:** Impact L / Effort L / Risk L.
- **Описание:** В downgrade мы поднимаем enum-тип с legacy-значениями, но данные
  остаются в `snake_case lowercase`. Для нашего прод-сценария (тестовые данные,
  один писатель) это безопасно. Если в будущем потребуется строгая обратимость —
  завести отдельный BL-XXX.

#### BL-020 — C1+C2 downgrade не восстанавливает статусы заявок

- **Источник:** [C1+C2 changelog](changelog.md) / миграция
  `20260422_uute_drop_legacy_order_statuses.py`.
- **Статус:** `accepted` (задокументированное ограничение).
- **Приоритет:** Impact L / Effort L / Risk L.
- **Описание:** Downgrade пересоздаёт enum с 3 legacy-значениями, но заявки,
  переведённые в `client_info_received` на upgrade, обратно не восстанавливаются
  (нет хранения оригинального статуса). Безопасно в нашем сценарии (прод-данных
  в legacy не было).

#### BL-021 — `OrderStatus` lowercase Python values vs UPPERCASE DB storage

- **Источник:** prod-инцидент миграции C1/C2 (2026-04-22): миграция
  `20260422_uute_drop_legacy_order_statuses.py` была написана под lowercase,
  но прод-БД хранила enum-метки в UPPERCASE — потребовался hotfix
  (коммит `64d7e07`, `fix(migration): C1/C2 — enum values must be UPPERCASE`).
- **Статус:** `open`.
- **Приоритет:** Impact M / Effort M / Risk **M** (любая будущая миграция над
  `order_status` может снова «не попасть» в реальное содержимое БД).
- **Описание:** В [`backend/app/models/models.py`](../backend/app/models/models.py)
  для колонки `Order.status` тип `Enum(OrderStatus)` сконфигурирован **без**
  `values_callable=_enum_db_values`. В этом режиме SQLAlchemy персистит
  Python-имя члена enum (`OrderStatus.NEW.name == "NEW"`), а не его `.value`
  (`"new"`). В результате:
  - в Python-коде и в JSON API фигурируют lowercase-значения (`"new"`,
    `"client_info_received"`, …) — это `.value` и контракт наружу;
  - в PostgreSQL-типе `order_status` и в колонке `orders.status` хранятся
    UPPERCASE-метки (`"NEW"`, `"CLIENT_INFO_RECEIVED"`, …);
  - эту асимметрию легко пропустить при написании миграций (прецедент — C1/C2).
- **Варианты решения:**
  1. **Зафиксировать текущее поведение как инвариант.** Добавить комментарий
     над `OrderStatus` и `Order.status`, что в БД хранятся `.name` (UPPERCASE),
     а также юнит-тест, проверяющий `inspect(Order).columns['status'].type.enum_class`
     и `native_enum=True` + отсутствие `values_callable`. Все будущие миграции
     над `order_status` пишем под UPPERCASE.
  2. **Симметрия с остальными enum'ами.** Подключить
     `values_callable=_enum_db_values` к `Order.status` и миграцией перевести
     PostgreSQL-тип на lowercase (backfill данных + `CREATE TYPE … AS ENUM`
     с новыми метками + `USING lower(status::text)::order_status_new`). Риск
     выше — одна «тяжёлая» миграция на всех заявках, но дальше правила едины.
- **Триггер возврата:** любая следующая миграция, меняющая значения
  `order_status` (BL-013 full-scope C1/C2), либо первый bug-ticket, где эта
  асимметрия сыграла.
- **DoD:**
  - в `backend/app/models/models.py` есть явный комментарий-инвариант у
    `OrderStatus` и у `Order.status`;
  - в `backend/tests/` есть тест, который падает при случайной смене поведения
    (например, при добавлении `values_callable`);
  - в `docs/project.md` — короткий подраздел «Enum conventions» с описанием,
    какие enum хранятся как `.value` (lowercase), какие как `.name` (UPPERCASE),
    и почему.

---

### C. Продуктовый долг

#### BL-030 — Решение по двум веткам оплаты

- **Источник:** [tasktracker: Фаза C отложена](tasktracker.md).
- **Статус:** `blocked` (ждёт ответа продакт-владельца).
- **Приоритет:** Impact **H** / Effort L / Risk M.
- **Описание:** В коде параллельны две ветки:
  1. **Основная:** `client_info_received → contract_sent` через
     `process_card_and_contract` (клиент грузит карточку сразу вместе с ТУ).
  2. **Legacy-совместимая:** `client_info_received → awaiting_contract →
     contract_sent` через `process_company_card_and_send_contract` + отдельная
     страница `payment.html` (bank_transfer + YooKassa-заглушка, выбор способа
     оплаты).
- **Что нужно решить:** оставляем основную и гасим legacy? Или legacy — целевой
  UX (отдельная страница оплаты с выбором метода), а основная — устаревший
  shortcut? После ответа запускаются [BL-013](#bl-013--full-scope-c1c2-удалить-awaiting_contract-и-legacy-payment-flow) и
  [BL-031](#bl-031--консолидация-или-удаление-paymenthtml).

#### BL-031 — Консолидация или удаление `payment.html`

- **Источник:** follow-up BL-030.
- **Статус:** `blocked` (ждёт BL-030).
- **Приоритет:** Impact M / Effort M / Risk M.
- **Описание:** `backend/static/payment.html` — автономный UI без общего
  layer'а с `upload.html` (дубликаты стилей, собственная авторизация по
  order-key). Если BL-030 решит «оставляем только основную ветку» — страницу
  удалить целиком вместе с эндпоинтами. Если «legacy — целевая» — вынести в
  общий layout (`css/upload.css`, общий JS-модуль для order-key).

---

### D. Прочее (вне scope аудита §3)

#### BL-032 — Регрессионные тесты LLM парсера ТУ

- **Источник:** roadmap
  [§1 Не-цели](plans/2026-04-20-audit-section-3-maintainability-roadmap.md#не-цели) —
  LLM-пайплайн вынесен за scope аудита §3.
- **Статус:** `open`.
- **Приоритет:** Impact **H** / Effort H / Risk M.
- **Описание:** Сейчас `tu_schema.py` + prompt живут без фиксации поведения.
  Смена LLM-модели (OpenRouter) или правка prompt'а может (а) уронить парсер,
  (б) изменить набор ключей в `parsed_params` — см. [BL-014](#bl-014--строгая-валидация-jsonb-при-записи-llm-ответов--метрика-дрейфа).
  Нужен (а) корпус из 10–20 реальных ТУ в `backend/tests/fixtures/tu/`, (б)
  тесты golden-output с допусками на числовые поля, (в) mock LLM-клиента по
  умолчанию и отдельный маркер `@pytest.mark.llm_live` для интеграционного
  прогона.
- **DoD:** `pytest -m "not llm_live"` прогоняет весь парсер на 10+ фикстурах
  за <5 с; `pytest -m llm_live` явно бьёт реальный OpenRouter (off в CI).

#### BL-033 — Snapshot-тесты для email-шаблонов

- **Источник:** вскрыто после D2.
- **Статус:** `open`.
- **Приоритет:** Impact M / Effort M / Risk L.
- **Описание:** 17 Jinja2-шаблонов в `backend/app/services/email/templates/`
  покрыты точечно (рендер + наличие ключевых подстрок). Нет snapshot'ов на
  полный HTML — визуальная регрессия (сломанный `<table>`, пропавшая ссылка)
  заметна только на проде. Нужны: фикстура `Order` в разных статусах +
  snapshot HTML через `syrupy` или `pytest-regressions`.
- **DoD:** на каждый из 17 шаблонов есть snapshot-тест; `pytest` падает при
  любом изменении рендера без обновления snapshot'а.

#### BL-034 — Убрать `?_k=` query-параметр для admin auth

- **Источник:** [`CLAUDE.md`](../CLAUDE.md) — раздел «Auth», исторически
  зафиксированный пункт безопасности.
- **Статус:** `open`.
- **Приоритет:** Impact M / Effort L / Risk L.
- **Описание:** Admin API сейчас принимает ключ и как HTTP-header
  `X-Admin-Key`, и как query-параметр `?_k=...`. Query-вариант — рудимент
  ранних демо (удобно открыть ссылку из Telegram/почты), но ключ попадает в
  access-логи nginx, history браузера и `Referer` при переходе на внешние
  ресурсы. Нужно (а) заменить использования `?_k=` на header во всём фронте
  (`admin.html`, `payment.html`, inline-ссылки в письмах), (б) удалить приём
  `?_k=` в FastAPI-зависимости admin-auth, (в) зафиксировать как breaking в
  `changelog.md`.
- **DoD:** `rg "_k=" backend/ frontend/` возвращает 0 релевантных совпадений;
  admin-auth в тестах работает только через header.

---

## 5. Закрытые элементы (done)

<!--
Сюда переносим элементы со статусом `done`, с датой, ссылкой на PR/commit и
кратким «чем закрыт». Новые пункты — вверх списка (reverse chronological).
-->

_Пока пусто. После закрытия первых BL-пунктов здесь появится хронология._

---

## 6. Шаблон новой записи

```md
#### BL-XXX — Короткое имя

- **Источник:** <roadmap/tasktracker/changelog-запись/PR/issue>.
- **Статус:** `open` | `deferred` | `blocked` | `accepted` | `done`.
- **Приоритет:** Impact H/M/L / Effort H/M/L / Risk H/M/L.
- **Блокер:** <ID другого BL / внешнее событие / «—»>.
- **Триггер возврата:** <что должно случиться, чтобы взять в работу>.
- **Описание:** <суть долга, ссылки на файлы/строки>.
- **DoD:** <проверяемый критерий закрытия>.
```

## 7. Журнал изменений backlog'а

| Дата | ID | Изменение |
|---|---|---|
| 2026-04-22 | BL-021 | Добавлено по итогам prod-инцидента миграции C1/C2: `OrderStatus` хранится в БД как `.name` (UPPERCASE), а не `.value` (lowercase) — зафиксировать как инвариант или унифицировать с остальными enum'ами. |
| 2026-04-22 | — | Файл создан. Перенесены пункты из roadmap §3, tasktracker и постмортемов фаз A–E. |
