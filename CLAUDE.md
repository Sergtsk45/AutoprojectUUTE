# CLAUDE.md — Инструкции для Claude Code Agent

## Проект

**УУТЭ Проектировщик** — сервис автоматизированного проектирования узлов учёта тепловой энергии (УУТЭ) по Приказу Минстроя №1036/пр. Клиент загружает технические условия (ТУ), LLM извлекает параметры, система формирует проект и отправляет результат.

- Репозиторий: https://github.com/Sergtsk45/AutoprojectUUTE
- Сервер: Ubuntu 22.04, IP 195.209.210.27 (путь: `~/uute-project`)
- Домен: constructproject.ru
- Swagger (local): http://localhost:8000/docs

---

## Технический стек

| Слой | Технологии |
|------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy async (asyncpg), Pydantic v2 |
| Фоновые задачи | Celery, Redis (брокер + backend) |
| База данных | PostgreSQL 16 |
| AI / LLM | OpenRouter API через openai SDK (`google/gemini-2.5-flash` по умолчанию) |
| Email | Яндекс SMTP (smtp.yandex.ru:465, SSL) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Инфра | Docker Compose, Caddy (reverse proxy + SSL) |

**Важно:** OpenRouter подключается через `openai` SDK, НЕ через `anthropic` SDK.

---

## Архитектура

```
Internet → Caddy (443/SSL) → uute-backend:8000 (FastAPI)
                                   ├── /api/v1/*         → API роуты
                                   ├── /upload/{id}      → страница загрузки клиента
                                   ├── /admin            → админ-панель инженера
                                   ├── /static/*         → backend/static/
                                   ├── /assets/*         → frontend/dist/assets/
                                   └── /{any}            → React SPA (catch-all)

Внутренняя сеть (uute-net):
  uute-backend ←→ postgres (5432)
               ←→ redis (6379)
  celery-worker    → фоновые задачи (парсинг, email, проверка)
  celery-beat      → автонапоминания (ежедневно 10:00 МСК)
```

### Стейт-машина заявки (OrderStatus)

Полный набор переходов — в `ALLOWED_TRANSITIONS` (`backend/app/models/models.py`). Основной happy-path:

```
new → tu_parsing → tu_parsed ─┬→ waiting_client_info → client_info_received ─┐
                               └→ data_complete ←──────────────────────────────┘
data_complete → generating_project → review → awaiting_contract → contract_sent
              → advance_paid → awaiting_final_payment ─┬→ completed
                                                       └→ rso_remarks_received → awaiting_final_payment
Любой статус → error → new (перезапуск)
```

Ключевые статусы оплаты/согласования:
- `awaiting_contract` — инженер одобрил проект, ожидаем реквизиты клиента
- `contract_sent` — договор + счёт на 50 % отправлены, ждём аванс
- `advance_paid` — аванс получен, проект уехал клиенту
- `awaiting_final_payment` — ожидаем скан РСО, замечания РСО или оплату остатка
- `rso_remarks_received` — получены замечания РСО, заявка возвращена инженеру; после повторной отправки исправленного проекта снова `awaiting_final_payment`

---

## Файловая структура

```
AutoprojectUUTE/
├── backend/
│   ├── app/
│   │   ├── api/           # Роуты FastAPI (orders, pipeline, emails, parsing, admin, landing)
│   │   ├── core/          # config.py, database.py, celery_app.py, auth.py
│   │   ├── models/        # models.py — SQLAlchemy ORM + enums
│   │   ├── schemas/       # Pydantic схемы запросов/ответов
│   │   ├── services/      # order_service, email/, contract/ (+ shims email_service, contract_generator), tu_parser, tasks
│   │   └── main.py        # FastAPI app, роутеры, статика, SPA
│   ├── alembic/           # Миграции БД
│   ├── templates/         # Jinja2 шаблоны email + образцы документов
│   ├── static/            # admin.html, upload.html (серверная статика)
│   ├── requirements.txt
│   └── .env / .env.example
├── frontend/
│   ├── src/
│   │   ├── components/    # React компоненты лендинга
│   │   ├── App.tsx
│   │   ├── api.ts         # HTTP клиент
│   │   └── main.tsx
│   └── dist/              # Сборка Vite (монтируется в Docker как /app/frontend-dist)
├── docs/
│   ├── changelog.md             # Хронология изменений (актуальный)
│   ├── tasktracker.md           # Активные/недавние задачи
│   ├── project.md               # Архитектурные заметки
│   ├── calculator-config-design.md   # Дизайн настроечной БД вычислителя
│   ├── kontrakt_ukute_template.md    # Текстовый шаблон договора (сборка в `app.services.contract`)
│   ├── scheme-generator-roadmap.md   # Активный roadmap по принципиальным схемам
│   ├── templates/                    # CSV/MD-шаблоны (опросный лист и пр.)
│   └── archive/2026-Q2/              # Завершённые task-трекеры и реализованные планы
├── docker-compose.yml     # Dev: только postgres + redis
├── docker-compose.prod.yml # Prod: полный стек (на сервере)
└── CLAUDE.md
```

### Ключевые модели (backend/app/models/models.py)

| Модель | Таблица | Назначение |
|--------|---------|-----------|
| `Order` | `orders` | Заявка (клиент, статус, parsed_params, missing_params) |
| `OrderFile` | `order_files` | Файлы заявки (category: FileCategory enum) |
| `EmailLog` | `email_log` | Лог отправленных писем |

### Ключевые API роуты

| Метод | Путь | Защита | Назначение |
|-------|------|--------|-----------|
| POST | `/api/v1/orders` | admin key | Создать заявку |
| GET | `/api/v1/orders/{id}` | admin key | Получить заявку |
| GET | `/api/v1/orders` | admin key | Список заявок |
| POST | `/api/v1/orders/{id}/files` | admin key | Загрузить файл (admin) |
| POST | `/api/v1/pipeline/{id}/start` | admin key | Запустить парсинг ТУ |
| POST | `/api/v1/pipeline/{id}/client-upload` | admin key | Клиент загружает файлы |
| POST | `/api/v1/pipeline/{id}/client-upload-done` | admin key | Клиент нажал «Готово» |
| POST | `/api/v1/pipeline/{id}/approve` | admin key | Инженер одобрил проект |
| GET | `/api/v1/landing/orders/{id}/upload-page` | публичный | Инфо для upload.html |
| POST | `/api/v1/landing/orders/{id}/upload-tu` | публичный | Загрузка ТУ (статус new) |
| POST | `/api/v1/landing/orders/{id}/submit` | публичный | Запуск парсинга (статус new) |

**Аутентификация admin:** заголовок `X-Admin-Key` (основной канал, constant-time через `secrets.compare_digest`). Query-параметр `?_k=…` — deprecated fallback с WARNING в логах, удалить в следующем релизе.

---

## Быстрый старт (production)

```bash
# Обновление и пересборка
cd ~/uute-project
git pull
cd frontend && npm run build && cd ..
docker compose -f docker-compose.prod.yml up -d --build

# Перезагрузка Caddy (если менялся Caddyfile)
docker exec n8n-caddy-1 caddy reload --config /etc/caddy/Caddyfile
```

### Локальная разработка

```bash
# Поднять postgres + redis
docker-compose up -d

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # заполнить секреты
uvicorn app.main:app --reload --port 8000

# Celery worker (в отдельном терминале)
celery -A app.core.celery_app worker -l info -Q default

# Celery beat (в отдельном терминале)
celery -A app.core.celery_app beat -l info

# Frontend
cd frontend && npm install && npm run dev
```

---

## Управление сервером

```bash
# Статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Логи
docker logs uute-backend -f --tail 50
docker logs uute-project-celery-worker-1 -f --tail 50
docker logs uute-project-celery-beat-1 -f --tail 50

# Перезапуск отдельного контейнера
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml restart celery-worker

# Полная пересборка
docker compose -f docker-compose.prod.yml up -d --build
```

### Контейнеры production

| Имя | Роль | Сети |
|-----|------|------|
| `uute-backend` | FastAPI + статика | uute-net, n8n_web |
| `uute-project-celery-worker-1` | Фоновые задачи | uute-net |
| `uute-project-celery-beat-1` | Планировщик (напоминания) | uute-net |
| `uute-project-postgres-1` | БД | uute-net |
| `uute-project-redis-1` | Очередь + кеш | uute-net |

---

## База данных

```bash
# Бэкап перед миграцией (обязательно!)
docker exec uute-project-postgres-1 pg_dump -U uute uute_db > backup_$(date +%Y%m%d).sql

# Создать миграцию
# ВАЖНО: код запечён в образ. Если модели менялись после последнего --build,
# скопировать обновлённый models.py в контейнер перед autogenerate:
# docker cp backend/app/models/models.py uute-backend:/app/app/models/models.py
docker exec -e PYTHONPATH=/app uute-backend alembic revision --autogenerate -m "описание"
# После генерации — проверить файл и скопировать его обратно на хост:
# docker cp uute-backend:/app/alembic/versions/<файл>.py backend/alembic/versions/

# ВАЖНО для enum-колонок: autogenerate НЕ создаёт CREATE TYPE автоматически.
# В upgrade() перед add_column вручную добавить:
#   my_enum = sa.Enum('val1', 'val2', name='type_name')
#   my_enum.create(op.get_bind(), checkfirst=True)
# server_default должен совпадать с фактическими строками enum (строчные!).

# Применить миграции
docker exec -e PYTHONPATH=/app uute-backend alembic upgrade head

# Откат миграции
docker exec -e PYTHONPATH=/app uute-backend alembic downgrade -1

# Прямой доступ к БД
docker exec -it uute-project-postgres-1 psql -U uute -d uute_db
```

**Соглашение по именованию миграций:** `YYYYMMDD_uute_<описание>` (например, `20260403_fc_upper`).

**Индексы (фаза B3, 2026-04-22).** В БД уже созданы под частые запросы:
- `ix_orders_created_at_desc` — сортировка списка заявок «по новизне».
- `ix_orders_status_created_at_desc` — композитный под админский listing с фильтром по статусу (`WHERE status=? ORDER BY created_at DESC LIMIT ?`).
- `ix_order_files_order_id_category` — `(order_id, category)` под частый паттерн «файлы заявки X категории Y».
Декларации в `__table_args__` моделей `Order`/`OrderFile` — metadata синхронизирована с БД. Миграция (`20260422_uute_listing_idx`) создаёт их `CONCURRENTLY` — прод не блокируется. При добавлении новых горячих запросов — сначала проверять планом (`EXPLAIN ANALYZE`), потом добавлять индекс тем же шаблоном (`CONCURRENTLY IF NOT EXISTS`).

---

## Фронтенд

```bash
# Сборка (production)
cd ~/uute-project/frontend
npm run build
# dist/ автоматически монтируется в контейнер как /app/frontend-dist
docker restart uute-backend

# Dev-сервер
npm run dev  # http://localhost:5173
```

Vite собирает в `frontend/dist/`. В Docker это монтируется как `/app/frontend-dist`. FastAPI отдаёт `/assets/*` из `frontend-dist/assets/` и `index.html` для всех остальных GET (catch-all).

---

## Конфигурация

Все настройки — `backend/app/core/config.py` (Pydantic Settings).

### Ключевые переменные окружения (backend/.env)

| Переменная | Назначение |
|-----------|-----------|
| `DATABASE_URL` | postgresql+asyncpg://uute:…@postgres:5432/uute_db |
| `REDIS_URL` | redis://redis:6379/0 |
| `UPLOAD_DIR` | /var/uute-service/uploads (prod) / `<repo>/uploads` (dev, auto) |
| `FRONTEND_DIST_DIR` | /app/frontend-dist (prod, auto) / `<repo>/frontend/dist` (dev, auto) |
| `ADMIN_API_KEY` | ключ для X-Admin-Key |
| `ADMIN_EMAIL` | email инженера для уведомлений |
| `OPENROUTER_API_KEY` | ключ OpenRouter (sk-or-v1-…) |
| `OPENROUTER_MODEL` | модель (google/gemini-2.5-flash) |
| `SMTP_HOST` / `SMTP_PORT` | smtp.yandex.ru / 465 |
| `SMTP_USER` / `SMTP_PASSWORD` | Яндекс почта |
| `APP_BASE_URL` | https://constructproject.ru |

### Добавление новой переменной

1. Добавить в `backend/app/core/config.py` класс `Settings`
2. Добавить в `backend/.env.example` с заглушкой
3. Добавить в `backend/.env` на сервере
4. Пересобрать: `docker compose -f docker-compose.prod.yml up -d --build backend`

---

## Стандарты кода

### Dev-инструменты (фаза A2 аудита)

- Конфигурация: [`backend/pyproject.toml`](backend/pyproject.toml) — ruff (E/F/W/I/UP/B/RUF), mypy, pytest.
- Pre-commit: [`.pre-commit-config.yaml`](.pre-commit-config.yaml). Установка:

  ```bash
  pip install --user pre-commit
  pre-commit install     # в корне репо; теперь крючки запускаются перед каждым commit
  ```

- Ручной прогон: `pre-commit run --all-files`.
- Dev-зависимости: `pip install -e "backend[dev]"` (из корня репо).
- Mypy в режиме baseline: существующие ошибки в `app.*` игнорируются, новые модули (фазы B/D) заводятся в `[[tool.mypy.overrides]]` со `strict = true`.

### Frontend baseline (фаза A4 аудита)

- Env-шаблон: [`frontend/.env.example`](frontend/.env.example). Для локальной разработки — `cp frontend/.env.example frontend/.env.local`.
- `VITE_API_BASE_URL` — опциональная. По умолчанию `/api/v1` (same-origin в prod, vite proxy в dev).
- Тесты: [vitest](https://vitest.dev/). Запуск:

  ```bash
  cd frontend
  npm test           # одноразовый прогон (CI)
  npm run test:watch # watch-режим для локальной разработки
  ```

- Первый тестовый модуль: `frontend/src/utils/pricing.test.ts` (расчёт цены калькулятора). Пример как тестировать чистые функции.
- Новые чистые функции выносить в `src/utils/*.ts` и покрывать тестами в `src/utils/*.test.ts`.

### JSONB-поля `Order` (фаза B1 аудита)

- Каноническое место Pydantic-моделей — [`backend/app/schemas/jsonb/`](backend/app/schemas/jsonb/):
  - `TUParsedData` (tu.py) — результат LLM-парсинга ТУ.
  - `SurveyData` (survey.py) — опросный лист клиента.
  - `CompanyRequisites` (company.py) — реквизиты заказчика.
- В бизнес-коде использовать **accessor-методы** из [`app.repositories.order_jsonb`](backend/app/repositories/order_jsonb.py), а НЕ голые `order.parsed_params["..."]`:

  ```python
  from app.repositories.order_jsonb import get_parsed_params, set_parsed_params

  parsed = get_parsed_params(order)  # TUParsedData | None
  if parsed is not None:
      total_load = parsed.heat_loads.total_load  # типизированный float | None
  ```

- Accessor-методы валидируют данные при чтении (`extra='ignore'`): исторические записи с устаревшими ключами не падают, но в лог пишется WARNING.
- Обратная совместимость: `from app.services.tu_schema import TUParsedData` и `from app.services.company_parser import CompanyRequisites` продолжают работать — это shim'ы.

### Python (Backend)

- Все async функции через `async def` + `await`
- SQLAlchemy сессии получаются через `Depends(get_db)` — НЕ создавать вручную
- Валидация на уровне Pydantic схем (`backend/app/schemas/`)
- Бизнес-логика — в `services/`, роуты в `api/` — только тонкий слой
- Enum значения: `OrderStatus`, `FileCategory`, `EmailType` — в `models/models.py`
- Переходы статусов — только через `ALLOWED_TRANSITIONS` + `order.can_transition_to()`
- Новые категории файлов — добавлять в `FileCategory` + миграция Alembic + `param_labels.py`

### TypeScript / React (Frontend)

- Компоненты — функциональные, с хуками
- Типизация: явные интерфейсы, без `any`
- HTTP запросы — через `frontend/src/api.ts`
- JSDoc обязателен для: публичных API, сложной бизнес-логики, неочевидных воркараундов
- Пропускать JSDoc для: простых геттеров, тривиального CRUD, приватных хелперов

```typescript
/**
 * Описание функции.
 * @param param - описание
 * @returns описание
 * @throws {ErrorType} когда
 */
async function example(param: string): Promise<Result> { ... }
```

### Общие правила

- Не добавляй фичи, рефакторинг или «улучшения» сверх запрошенного
- Не добавляй обработку ошибок для невозможных сценариев
- Не создавай абстракции для одноразовых операций
- Валидация только на системных границах (пользовательский ввод, внешние API)
- SQL — только через SQLAlchemy ORM, никогда не конкатенировать строки запросов

---

## Git-workflow

### Именование веток

```
<type>/<описание>

feature/tu-parser-improvements
fix/missing-params-sync
hotfix/email-crash
refactor/order-service
docs/api-readme
test/auth-coverage
chore/update-deps
```

### Conventional Commits

```
<type>(<scope>): <subject>

feat(parser): add system_type normalization
fix(api): handle null parsed_params
docs(changelog): update file category entries
refactor(service): extract validation logic
chore: bump openai sdk version
```

**Типы:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `style`
**Правила subject:** строчные, без точки, повелительное наклонение, до 50 символов

### Контрольный список перед коммитом

- [ ] Изменение атомарное (одна логическая правка)
- [ ] Проверил `git diff` — нет лишнего
- [ ] Секреты не попали в коммит
- [ ] Если изменилась БД — миграция создана и протестирована
- [ ] Обновлены `docs/changelog.md` и `docs/tasktracker.md`

### Запрещено

- Force push в `main`
- Коммитить секреты, API ключи, `.env`
- Коммитить большие бинарники
- Пушить без проверки

---

## Рабочий процесс разработки

### Реализация новой задачи

1. Прочитай задачу, уточни требования
2. Изучи затрагиваемые файлы перед правкой
3. Реализуй минимально необходимое
4. Обнови `docs/changelog.md`
5. Обнови `docs/tasktracker.md`
6. Коммит с Conventional Commits сообщением

### Перед деструктивными действиями

- Бэкап БД: `docker exec uute-project-postgres-1 pg_dump -U uute uute_db > backup.sql`
- Подтверди у пользователя перед `DROP TABLE`, `rm -rf`, удалением volumes

---

## Документирование изменений

### docs/changelog.md

Формат записи:

```markdown
## [YYYY-MM-DD] — Краткое название изменения

### Добавлено
- В [`путь/к/файлу`](../путь/к/файлу): что именно добавлено

### Изменено
- Что изменено и как

### Исправлено
- Что исправлено
```

Каждое значимое изменение — отдельный блок. Дата абсолютная (YYYY-MM-DD). Ссылки на файлы — относительные от `docs/`.

### docs/tasktracker.md

Формат задачи:

```markdown
## Задача: Название задачи
- **Статус**: В работе | Завершена | Отложена
- **Описание**: Что делается и зачем
- **Шаги выполнения**:
  - [ ] Шаг 1
  - [x] Шаг 2 (выполнен)
- **Зависимости**: другие задачи или миграции
```

Задачи не удаляются после завершения — меняется статус на `Завершена`. Новые задачи добавляются сверху.

---

## Частые задачи

### Новый API эндпоинт

1. Создать/изменить файл в `backend/app/api/`
2. При необходимости добавить Pydantic схемы в `backend/app/schemas/`
3. Бизнес-логику — в `backend/app/services/`
4. Подключить роутер в `backend/app/main.py` (если новый файл)
5. Для admin-защиты: `dependencies=[Depends(verify_admin_key)]` на роутере
6. Пересобрать: `docker compose -f docker-compose.prod.yml up -d --build backend`

### Новая модель БД

1. Изменить `backend/app/models/models.py`
2. Бэкап: `docker exec uute-project-postgres-1 pg_dump -U uute uute_db > backup.sql`
3. Код в контейнере запечён в образ — если `--build` не делался после изменения моделей, скопировать вручную:
   `docker cp backend/app/models/models.py uute-backend:/app/app/models/models.py`
4. Создать миграцию: `docker exec -e PYTHONPATH=/app uute-backend alembic revision --autogenerate -m "YYYYMMDD_uute_описание"`
5. Скопировать файл миграции обратно на хост:
   `docker cp uute-backend:/app/alembic/versions/<файл>.py backend/alembic/versions/`
6. Проверить файл: если добавляется enum-колонка — вручную добавить `CREATE TYPE` перед `add_column` (autogenerate не делает это автоматически); `server_default` — строчные значения
7. Применить: `docker exec -e PYTHONPATH=/app uute-backend alembic upgrade head`
8. Закоммитить файл миграции в git

### Новая Celery задача

1. Реализация — в **подходящем** файле пакета `backend/app/services/tasks/` (фаза D1.b, 2026-04-22), например `client_response.py` или `contract_flow.py` — **не** раздувать `_common.py` бизнес-логикой. У каждой задачи: `@celery_app.task(name="app.services.tasks.<funcname>", ...)` — явное имя обязательно (см. D1.a), чтобы смена модуля не ломала очереди.
2. Re-export: добавить имя в `backend/app/services/tasks/__init__.py` (импорт + `__all__`, если публичный API).
3. Вызвать из нужного места через `.delay()` или `.apply_async()`
4. Для периодических задач — добавить в `beat_schedule` в `backend/app/core/celery_app.py` (строка `task: "app.services.tasks...."`).
5. Перезапустить воркер: `docker compose -f docker-compose.prod.yml restart celery-worker`

### Новая категория файлов (FileCategory)

1. Добавить значение в `FileCategory` enum в `backend/app/models/models.py`
2. Создать миграцию Alembic (`ALTER TYPE file_category ADD VALUE`)
3. Добавить подпись в `backend/app/services/param_labels.py`
4. Обновить логику в `tu_parser.py` если нужно
5. Обновить статику `admin.html`, `upload.html`

### Обновление кода на сервере

```bash
cd ~/uute-project
git pull
cd frontend && npm run build && cd ..
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Текущий статус разработки

**Фаза:** Production — полный цикл от лендинга до отправки проекта и обработки замечаний РСО.

**Реализовано (апрель 2026):**
- Полный цикл стейт-машины: `new → tu_parsing → tu_parsed → waiting_client_info → client_info_received → data_complete → generating_project → review → awaiting_contract → contract_sent → advance_paid → awaiting_final_payment → completed`, с веткой `rso_remarks_received` для возврата проекта инженеру.
- Парсинг ТУ через LLM (OpenRouter / `google/gemini-2.5-flash`), типизированные `parsed_params` (`backend/app/schemas/jsonb/tu.py`; `services/tu_schema.py` — backward-compat shim).
- Сегментация заказов: `OrderType.express` / `OrderType.custom`, опросный лист (`upload.html`) с автозаполнением из ТУ для custom.
- Категории файлов (`FileCategory.<member>.value`, snake_case lowercase после B2):
  `tu`, `balance_act`, `connection_plan`, `heat_point_plan`, `heat_scheme`,
  `company_card`, `signed_contract`, `generated_project`, `final_invoice`,
  `rso_scan`, `rso_remarks`.
  - В PG enum `file_category` метки — **имена членов Python** (`TU`, `BALANCE_ACT`, …), а не `.value`. SQLAlchemy без `values_callable` persist имена.
  - `FileCategory._missing_` (B2.a compat-shim) принимает устаревшие UPPER_CASE значения с `WARNING` в лог. В B2.b будет удалён → 422 на uppercase.
- Публичные эндпоинты лендинга (`/api/v1/landing/...`): создание заявки, upload ТУ/документов, опросный лист, страница оплаты `/payment/{id}`, загрузка скана РСО и замечаний.
- Договор: пакет `app.services.contract` (shim `contract_generator.py`) собирает DOCX по шаблону `docs/kontrakt_ukute_template.md` с встраиванием PDF ТУ в Приложение 2 (PyMuPDF, лестница DPI, fallback ~25 МБ).
- Email-уведомления (Jinja2 + SMTP Яндекс): запрос данных, напоминания, отправка готового проекта, уведомления инженеру (новая заявка, ТУ распарсены, документы клиента получены, скан РСО), уведомление о замечаниях РСО, повторная отправка исправленного проекта.
- Celery Beat: ежедневные напоминания, отложенный `info_request` через 24 ч, 15-дневный reminder по финальной оплате.
- Админ-панель `/admin`: список заявок, карточка с парсингом ТУ, опросным листом по секциям, действиями инженера на post-project ветке (отправка исправленного проекта), карточка «Настроечная БД вычислителя» с автозаполнением из ТУ и экспортом PDF.
- Настроечная БД (`CalculatorConfig`): JSON-шаблоны ТВ7, СПТ-941.20, ЭСКО-Терра М; для express автоинициализация на ЭСКО-Терра; CRUD через `/api/v1/orders/{id}/calculator-config`.
- React лендинг: калькулятор с двумя вариантами (Экспресс/Индивидуальный), форма заказа (EmailModal) с полем «Город объекта» и модалкой политики конфиденциальности, FAQ, образцы проектов, скачивание опросного листа `/downloads/opros_list_form.pdf`.
- Auth: `X-Admin-Key` header или `?_k=` query (последний желательно убрать — см. backlog в `docs/changelog.md`).

**Активные направления:**
- Автоматизация принципиальных схем ИТП (см. [`docs/scheme-generator-roadmap.md`](docs/scheme-generator-roadmap.md), черновики SVG-генераторов уже в `backend/app/services/scheme_*`).

**Backlog / технический долг:**
- Безопасность: ограничить CORS до доменов, перевести `verify_admin_key` на `secrets.compare_digest`, отказаться от `?_k=` в публичных URL, убрать дефолты секретов из `config.py`, добавить rate-limit на `/landing/*`.
- Декомпозиция «толстых» модулей: `services/tasks/` (пакет, D1.b), `services/email/` + shim `email_service.py` (D2), `services/contract/` + shim `contract_generator.py` (D3).
- Удаление legacy-статусов / нормализация enum после миграции данных.
- Типизация JSONB-полей (`parsed_params`, `survey_data`, `company_requisites`) Pydantic-моделями.
- CI (pytest + ruff + mypy + eslint), error-tracking (Sentry/Glitchtip), генерация TypeScript-клиента из OpenAPI.

---

## Правила безопасности

- **НИКОГДА** не выводи содержимое `.env`
- **НИКОГДА** не удаляй Docker volumes (`pgdata`, `uploads`) без подтверждения пользователя
- **НИКОГДА** не делай force push в `main`
- **НИКОГДА** не коммить секреты, API ключи, токены
- **ВСЕГДА** делай бэкап БД перед миграциями
- **ВСЕГДА** валидируй пользовательский ввод на серверной стороне
- **ВСЕГДА** используй параметризованные запросы (SQLAlchemy ORM — уже безопасен)
- Перед деструктивными действиями (DROP TABLE, rm -rf, alembic downgrade) — запроси подтверждение

### Безопасность runtime-конфигурации (с 2026-04-20)

- `ADMIN_API_KEY` (≥16 симв.), `OPENROUTER_API_KEY`, `SMTP_PASSWORD` — **required** в `.env`. Без них `Settings()` падает на старте (см. `backend/app/core/config.py`). Дефолтов больше нет.
- `verify_admin_key` (`backend/app/core/auth.py`) сравнивает ключ через `secrets.compare_digest` (без timing-leak). Основной канал — заголовок `X-Admin-Key`. Query-параметр `?_k=` оставлен как deprecated на 1 релиз: при использовании пишет WARNING в лог с маскированным ключом.
- CORS управляется через ENV `CORS_ORIGINS` (JSON-список, парсится Pydantic v2). Дефолт — только `https://constructproject.ru`. Wildcard `*` в `allow_origins` запрещён (несовместим с `allow_credentials=True` по спеке).

### Файлы конфигурации (prod, на сервере)

- `~/uute-project/backend/.env` — все секреты
- `~/uute-project/docker-compose.prod.yml` — production контейнеры
- `/home/ubuntu/n8n/Caddyfile` — Caddy (общий с другими проектами на сервере)
