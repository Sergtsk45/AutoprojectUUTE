#!/usr/bin/env bash
# @file: scripts/generate-api-types.sh
# @description: Генерация TS-типов для фронтенда из OpenAPI-спеки бэкенда.
#   Фаза E1 roadmap аудита — устраняет рассинхрон ручных интерфейсов в
#   frontend/src/api.ts с Pydantic-схемами backend/app/api/*.
#
#   Алгоритм:
#     1. Запустить Python в окружении backend (с dummy-ENV для обязательных
#        настроек) → импортировать FastAPI `app` → вызвать `app.openapi()` →
#        дампнуть JSON в frontend/src/api/openapi.json.
#     2. `openapi-typescript` превращает openapi.json в типизированный
#        frontend/src/api/types.ts (paths, operations, components.schemas).
#
#   Оба артефакта коммитятся в репо и проверяются в CI (шаг api-types-drift).
#
# @usage:
#     ./scripts/generate-api-types.sh
#
#   Требует установленный backend (pip install -r backend/requirements.txt)
#   и frontend (npm install). В CI используется те же шаги, что в обычной
#   backend-/frontend-job.
#
# @created: 2026-04-22 (фаза E1)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
FRONTEND_DIR="${REPO_ROOT}/frontend"
OUT_DIR="${FRONTEND_DIR}/src/api"
OPENAPI_JSON="${OUT_DIR}/openapi.json"
TYPES_TS="${OUT_DIR}/types.ts"

mkdir -p "${OUT_DIR}"

# ── Шаг 1. openapi.json из FastAPI-приложения ────────────────────────────────
# Dummy-ENV: Pydantic Settings требует эти поля, но для openapi() они не читаются
# (ни SMTP, ни Admin API Key, ни OpenRouter не инициализируются при построении
# схемы). Значения должны удовлетворять валидаторам (min length, формат).
echo "[generate-api-types] exporting ${OPENAPI_JSON}"
cd "${BACKEND_DIR}"
SMTP_PASSWORD="${SMTP_PASSWORD:-generate-api-types-dummy}" \
ADMIN_API_KEY="${ADMIN_API_KEY:-generate-api-types-dummy-0123456789abcdef}" \
OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-generate-api-types-dummy-0123456789abcdef}" \
python3 -c "
import json
from app.main import app

spec = app.openapi()
with open('${OPENAPI_JSON}', 'w', encoding='utf-8') as f:
    json.dump(spec, f, indent=2, ensure_ascii=False, sort_keys=True)
    f.write('\n')
"

# ── Шаг 2. types.ts ──────────────────────────────────────────────────────────
echo "[generate-api-types] generating ${TYPES_TS}"
cd "${FRONTEND_DIR}"
if [ ! -x "node_modules/.bin/openapi-typescript" ]; then
    echo "[generate-api-types] openapi-typescript не установлен. Запустите:" >&2
    echo "    cd frontend && npm install" >&2
    exit 1
fi

npx --no-install openapi-typescript "${OPENAPI_JSON}" --output "${TYPES_TS}"

echo "[generate-api-types] done"
