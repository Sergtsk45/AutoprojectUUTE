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

```
new → tu_parsing → tu_parsed ─┬→ waiting_client_info → client_info_received ─┬→ data_complete
                               └→ data_complete ←──────────────────────────────┘
data_complete → generating_project → review → completed
Любой статус → error → new (перезапуск)
```

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
│   │   ├── services/      # Бизнес-логика: order_service, email_service, tu_parser, tasks
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
│   ├── changelog.md       # Хронология изменений
│   ├── tasktracker.md     # Задачи и их статус
│   └── project.md         # Архитектурные заметки
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

**Аутентификация admin:** заголовок `X-Admin-Key` или query-параметр `?_k=…`

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
| `UPLOAD_DIR` | /var/uute-service/uploads |
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

1. Добавить функцию в `backend/app/services/tasks.py` с декоратором `@celery_app.task`
2. Вызвать из нужного места через `.delay()` или `.apply_async()`
3. Для периодических задач — добавить в `beat_schedule` в `backend/app/core/celery_app.py`
4. Перезапустить воркер: `docker compose -f docker-compose.prod.yml restart celery-worker`

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

**Фаза:** MVP — пайплайн обработки заявок (активна)

**Реализовано (апрель 2026):**
- Стейт-машина заявок: `new → tu_parsing → ... → completed`
- Парсинг ТУ через LLM (OpenRouter/Gemini) с нормализацией `system_type`
- Категории файлов: `tu`, `BALANCE_ACT`, `CONNECTION_PLAN`, `heat_point_plan`, `heat_scheme`
- Публичные эндпоинты лендинга (upload-tu, submit) без авторизации
- Страница загрузки клиента (`/upload/{id}`) — два сценария: `new` и `waiting_client_info`
- Автонапоминания клиентам через Celery Beat
- Админ-панель (`/admin`): список заявок, карточка, результаты парсинга ТУ
- React лендинг (SPA): форма заявки, калькулятор, FAQ, образцы проектов
- Fallback auth: `X-Admin-Key` header или `?_k=` query

**Следующие этапы:**
- Генерация Excel (заполнение шаблона параметрами из ТУ)
- Интеграция T-FLEX для генерации проектной документации
- Email: отправка готового проекта клиенту

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

### Файлы конфигурации (prod, на сервере)

- `~/uute-project/backend/.env` — все секреты
- `~/uute-project/docker-compose.prod.yml` — production контейнеры
- `/home/ubuntu/n8n/Caddyfile` — Caddy (общий с другими проектами на сервере)
