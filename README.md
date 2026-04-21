# УУТЭ Проектировщик

[![CI](https://github.com/Sergtsk45/AutoprojectUUTE/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Sergtsk45/AutoprojectUUTE/actions/workflows/ci.yml)

Сервис автоматизированного проектирования узлов учёта тепловой энергии
по Приказу Минстроя №1036/пр.

## Быстрый старт

### 1. Поднять PostgreSQL + Redis

```bash
docker-compose up -d
```

### 2. Бэкенд

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

Настроить окружение:

```bash
cp .env.example .env
# Отредактировать .env
```

Создать таблицы (миграция):

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

Запустить API:

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger-документация: http://localhost:8000/docs

Запустить Celery-воркер:

```bash
celery -A app.core.celery_app worker -l info -Q default
```

Запустить Celery Beat (автонапоминания):

```bash
celery -A app.core.celery_app beat -l info
```

Напоминания клиентам отправляются ежедневно в 10:00 МСК
для заявок в статусе `waiting_client_info` (не более 3 раз).

## Фронтенд (лендинг)

```bash
cd frontend
npm install
npm run dev
```

## Структура проекта

```
uute-project/
├── backend/
│   ├── app/
│   │   ├── api/           # Роуты FastAPI
│   │   ├── core/          # Celery, конфиг, БД
│   │   ├── models/        # SQLAlchemy-модели
│   │   ├── schemas/       # Pydantic-схемы
│   │   ├── services/      # Бизнес-логика
│   │   └── main.py        # FastAPI-приложение
│   ├── alembic/           # Миграции БД
│   ├── templates/         # Jinja2-шаблоны писем
│   ├── static/            # Страница загрузки файлов
│   ├── requirements.txt
│   └── .env.example
├── frontend/              # Vite + React + TypeScript лендинг
└── docker-compose.yml
```

## API — основной флоу

```
1. POST   /api/v1/orders                          → Создать заявку
2. POST   /api/v1/orders/{id}/files?category=tu   → Загрузить ТУ
3. POST   /api/v1/pipeline/{id}/start              → Запустить обработку

   ... автоматически: парсинг ТУ → проверка → письмо клиенту ...

4. GET    /api/v1/orders/{id}/upload-page          → Инфо для страницы загрузки
5. POST   /api/v1/pipeline/{id}/client-upload      → Клиент загружает файлы
6. POST   /api/v1/pipeline/{id}/client-upload-done → Клиент нажал «Готово»

   ... автоматически: проверка → Excel → T-FLEX → review ...

7. POST   /api/v1/pipeline/{id}/approve            → Инженер одобрил
8. GET    /api/v1/orders/{id}                      → Статус заявки
```
