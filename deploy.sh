#!/usr/bin/env bash
# deploy.sh — атомарный деплой УУТЭ на production-сервере.
#
# ВАЖНО: всегда пересобирает ВСЕ сервисы вместе, чтобы исключить
# рассинхронизацию кода между backend и celery-worker/celery-beat.
# (Именно частичный --build backend вызвал «Received unregistered task»
# в апреле 2026 после PR D4.)
#
# Использование:
#   ssh ubuntu@195.209.210.27
#   cd ~/uute-project && bash deploy.sh

set -euo pipefail

COMPOSE="docker compose -f docker-compose.prod.yml"
FRONTEND_DIR="$(dirname "$0")/frontend"

echo "╔══════════════════════════════════════╗"
echo "║         УУТЭ — деплой на prod        ║"
echo "╚══════════════════════════════════════╝"

# ── 1. Получаем свежий код ─────────────────────────────────────────────
echo ""
echo "→ [1/4] git pull"
git pull

# ── 2. Собираем фронтенд ──────────────────────────────────────────────
echo ""
echo "→ [2/4] npm build"
cd "$FRONTEND_DIR"
npm ci --silent
npm run build
cd - > /dev/null

# ── 3. Пересобираем ВСЕ контейнеры атомарно ──────────────────────────
# НИКОГДА не передавать имя конкретного сервиса — только --build без списка.
# celery-worker и celery-beat ДОЛЖНЫ быть пересобраны вместе с backend,
# иначе воркер может не знать о новых Celery-задачах.
echo ""
echo "→ [3/4] docker compose up --build (все сервисы)"
$COMPOSE up -d --build

# ── 4. Проверяем статус ────────────────────────────────────────────────
echo ""
echo "→ [4/4] статус контейнеров"
sleep 3
$COMPOSE ps

echo ""
echo "╔══════════════════════════════════════╗"
echo "║         Деплой завершён ✓            ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Логи воркера (последние 20 строк):"
docker logs uute-project-celery-worker-1 --tail=20 2>&1 | grep -E "ready|task|ERROR" || true
