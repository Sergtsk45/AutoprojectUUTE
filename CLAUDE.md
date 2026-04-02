# CLAUDE.md — Инструкции для Claude Code

## Проект
УУТЭ Проектировщик — сервис проектирования узлов учёта тепловой энергии.
Репозиторий: https://github.com/Sergtsk45/AutoprojectUUTE
Сервер: Ubuntu 22.04, IP 195.209.210.27
Домен: constructproject.ru

## Быстрый старт (уже развёрнуто)
```bash
cd ~/uute-project
docker compose -f docker-compose.prod.yml up -d --build
docker exec n8n-caddy-1 caddy reload --config /etc/caddy/Caddyfile
```

## Основные команды

### Управление
```bash
# Статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Логи
docker logs uute-backend -f --tail 50
docker logs uute-project-celery-worker-1 -f --tail 50

# Перезапуск
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml restart celery-worker

# Полная пересборка после git pull
docker compose -f docker-compose.prod.yml up -d --build
```

### База данных
```bash
# Миграции
docker exec -e PYTHONPATH=/app uute-backend alembic revision --autogenerate -m "описание"
docker exec -e PYTHONPATH=/app uute-backend alembic upgrade head

# Прямой доступ к БД
docker exec uute-project-postgres-1 psql -U uute -d uute_db
```

### Фронтенд
```bash
cd ~/uute-project/frontend
npm run build
docker restart uute-backend  # подхватит новый dist/
```

## Архитектура деплоя
```
Internet → Caddy (443/SSL) → uute-backend:8000 (FastAPI)
                                   ├── /api/*     → API роуты
                                   ├── /upload/*  → страница загрузки
                                   ├── /admin     → админка
                                   └── /*         → React SPA

Внутренняя сеть (uute-net):
  uute-backend ←→ postgres (5432)
               ←→ redis (6379)
  celery-worker → фоновые задачи
  celery-beat   → автонапоминания
```

## Файлы конфигурации
- `backend/.env` — все секреты (SMTP, API ключи, БД пароль)
- `docker-compose.prod.yml` — production контейнеры
- `/home/ubuntu/n8n/Caddyfile` — конфиг Caddy (общий с другими проектами)

## Правила безопасности
- НИКОГДА не показывай содержимое .env
- НИКОГДА не удаляй volumes (pgdata, uploads) без подтверждения
- Перед деструктивными действиями (DROP TABLE, rm -rf) — спроси подтверждение
- Бэкап БД перед миграциями: `docker exec uute-project-postgres-1 pg_dump -U uute uute_db > backup.sql`

## Стек
- Python 3.12, FastAPI, SQLAlchemy async, Celery, Redis
- React 18, TypeScript, Vite, Tailwind
- PostgreSQL 16, Docker Compose, Caddy
- AI: OpenRouter (openai SDK), не anthropic SDK
- Email: Яндекс SMTP (smtp.yandex.ru:465 SSL)

## Частые задачи

### Обновление кода
```bash
cd ~/uute-project
git pull
cd frontend && npm run build && cd ..
docker compose -f docker-compose.prod.yml up -d --build
```

### Добавление переменной окружения
1. Добавить в `backend/app/core/config.py` (Settings)
2. Добавить в `backend/.env.example`
3. Добавить в `backend/.env` на сервере
4. Пересобрать: `docker compose -f docker-compose.prod.yml up -d --build backend`

### Новый API эндпоинт
1. Создать/изменить файл в `backend/app/api/`
2. Подключить роутер в `backend/app/main.py`
3. Пересобрать backend

### Новая модель БД
1. Изменить `backend/app/models/models.py`
2. `docker exec -e PYTHONPATH=/app uute-backend alembic revision --autogenerate -m "описание"`
3. `docker exec -e PYTHONPATH=/app uute-backend alembic upgrade head`

## Контейнеры
| Имя | Роль | Сеть |
|------|------|------|
| uute-backend | FastAPI + статика | uute-net + n8n_web |
| uute-project-celery-worker-1 | Фоновые задачи | uute-net |
| uute-project-celery-beat-1 | Планировщик | uute-net |
| uute-project-postgres-1 | БД | uute-net |
| uute-project-redis-1 | Очередь | uute-net |
