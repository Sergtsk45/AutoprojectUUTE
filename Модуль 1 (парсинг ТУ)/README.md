# УУТЭ Проектировщик — Бэкенд

Сервис автоматизированного проектирования узлов учёта тепловой энергии
по Приказу Минстроя №1036/пр.

## Быстрый старт

### 1. Поднять PostgreSQL + Redis

```bash
docker-compose up -d
```

### 2. Установить зависимости

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 3. Настроить окружение

```bash
cp .env.example .env
# Отредактировать .env
```

### 4. Создать таблицы (миграция)

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 5. Запустить API

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger-документация: http://localhost:8000/docs

### 6. Запустить Celery-воркер

```bash
celery -A app.core.celery_app worker -l info -Q default
```

### 7. Запустить Celery Beat (автонапоминания)

```bash
celery -A app.core.celery_app beat -l info
```

Напоминания клиентам отправляются ежедневно в 10:00 МСК
для заявок в статусе `waiting_client_info` (не более 3 раз).

## Структура проекта

```
uute-service/
├── app/
│   ├── api/
│   │   ├── orders.py          # CRUD заявок, загрузка файлов
│   │   ├── pipeline.py        # Запуск пайплайна, действия клиента/инженера
│   │   ├── emails.py          # Предпросмотр писем, ручная отправка, лог
│   │   └── parsing.py         # Результаты парсинга ТУ, перезапуск
│   ├── core/
│   │   ├── celery_app.py      # Конфигурация Celery + Beat-расписание
│   │   ├── config.py          # Настройки (pydantic-settings)
│   │   └── database.py        # Async SQLAlchemy engine + session
│   ├── models/
│   │   └── models.py          # Order, OrderFile, EmailLog + стейт-машина
│   ├── schemas/
│   │   └── schemas.py         # Pydantic-схемы для API
│   ├── services/
│   │   ├── order_service.py   # Бизнес-логика заявок
│   │   ├── email_service.py   # SMTP + Jinja2 рендеринг + отправка + лог
│   │   ├── param_labels.py    # Справочник параметров и образцов документов
│   │   ├── tu_schema.py       # Pydantic-схема параметров ТУ по 1036
│   │   ├── tu_parser.py       # Парсинг PDF: pymupdf + Claude API/Vision
│   │   └── tasks.py           # Celery-задачи (оркестратор)
│   └── main.py                # FastAPI-приложение
├── static/
│   └── upload.html            # Страница загрузки файлов клиентом
├── templates/
│   ├── emails/                # Jinja2-шаблоны писем
│   │   ├── base.html          #   Общий каркас
│   │   ├── info_request.html  #   Запрос документов
│   │   ├── reminder.html      #   Напоминание
│   │   ├── project_delivery.html  # Проект готов
│   │   └── error_notification.html # Ошибка
│   └── samples/               # PDF-образцы для клиентов
├── alembic/                   # Миграции БД
├── docker-compose.yml         # PostgreSQL + Redis
├── requirements.txt
└── .env.example
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

## Email API (отладка и ручное управление)

```
GET  /api/v1/emails/{id}/preview/info-request      → HTML-предпросмотр письма-запроса
GET  /api/v1/emails/{id}/preview/reminder           → HTML-предпросмотр напоминания
GET  /api/v1/emails/{id}/preview/project-delivery   → HTML-предпросмотр «проект готов»
POST /api/v1/emails/{id}/send                       → Ручная отправка письма
GET  /api/v1/emails/{id}/log                        → Лог отправленных писем
```

## Страница загрузки для клиента

Клиент получает в письме ссылку: `https://yourdomain.ru/upload/<order_id>`

Страница показывает чек-лист необходимых документов, позволяет загрузить
файлы с drag-and-drop, прогресс-баром и выбором категории.

## Парсинг технических условий (Модуль 1)

Автоматическое извлечение параметров из PDF с техническими условиями.

**Два режима:**
- Текстовый PDF → pymupdf извлекает текст → Claude API (текстовый промпт)
- Скан PDF → pymupdf рендерит страницы в PNG → Claude Vision API

**Извлекаемые параметры:**
- РСО: наименование, адрес, контакты
- Документ: номер ТУ, дата, срок действия
- Заявитель: наименование, адрес
- Объект: тип, адрес, город
- Тепловые нагрузки: общая, отопление, вентиляция, ГВС (Гкал/ч)
- Трубопроводы: наружный диаметр (мм)
- Теплоноситель: температурный график, давления (кг/см²)
- Приборы: рекомендуемые модели, класс, интерфейс, архив
- Схема: тип присоединения, тип системы

**Валидация:**
- Pydantic-схема с диапазонами значений
- Перекрёстные проверки (сумма нагрузок, температура подачи > обратки)
- Список обязательных полей для продолжения

```
GET  /api/v1/parsing/{id}/result     → Результат парсинга
POST /api/v1/parsing/{id}/retrigger  → Перезапуск парсинга
```

## Стейт-машина заявки

```
new → tu_parsing → tu_parsed → waiting_client_info → client_info_received
                       ↓                                       ↓
                  data_complete ←──────────────────────────────┘
                       ↓
              generating_project → review → completed
```

Любой статус может перейти в `error`.
Из `error` можно вернуть в `new` для перезапуска.
