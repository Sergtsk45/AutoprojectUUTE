#!/usr/bin/env bash
# @file: scripts/generate-api-types.sh
# @description: Генерация TS-типов для фронтенда из OpenAPI-спеки бэкенда.
#   Фаза E1 roadmap аудита — устраняет рассинхрон ручных интерфейсов в
#   frontend/src/api.ts с Pydantic-схемами backend/app/api/*.
#
#   Алгоритм:
#     1. Выбрать Python — либо из `backend/.venv/bin/python`, либо из $PYTHON,
#        либо из `python3`. ВАЖНО: Python должен иметь установленные пакеты
#        из `backend/requirements.txt` точно той же версии (`pydantic`,
#        `fastapi`), иначе OpenAPI-спека отличается (разные Pydantic-версии
#        по-разному ставят `additionalProperties` на dict-полях) и CI-job
#        `api-types-drift` роняет билд.
#     2. `app.openapi()` → `frontend/src/api/openapi.json` (sort_keys=True,
#        индентация 2 — детерминировано).
#     3. `openapi-typescript` → `frontend/src/api/types.ts`.
#
#   Оба артефакта коммитятся в репо и проверяются в CI.
#
# @usage:
#     # Вариант 1: системный python3 с установленными pinned-зависимостями
#     ./scripts/generate-api-types.sh
#
#     # Вариант 2: venv
#     python3 -m venv backend/.venv
#     backend/.venv/bin/pip install -r backend/requirements.txt
#     ./scripts/generate-api-types.sh   # скрипт подхватит backend/.venv
#
#     # Вариант 3: явный интерпретатор
#     PYTHON=/path/to/python ./scripts/generate-api-types.sh
#
# @created: 2026-04-22 (фаза E1)
# @updated: 2026-04-22 (post-CI fix: version guard + venv autodetect)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
FRONTEND_DIR="${REPO_ROOT}/frontend"
OUT_DIR="${FRONTEND_DIR}/src/api"
OPENAPI_JSON="${OUT_DIR}/openapi.json"
TYPES_TS="${OUT_DIR}/types.ts"
REQUIREMENTS_FILE="${BACKEND_DIR}/requirements.txt"

mkdir -p "${OUT_DIR}"

# ── Выбор интерпретатора Python ──────────────────────────────────────────────
# Приоритет: $PYTHON → backend/.venv/bin/python → python3
if [ -n "${PYTHON:-}" ]; then
    PY="${PYTHON}"
elif [ -x "${BACKEND_DIR}/.venv/bin/python" ]; then
    PY="${BACKEND_DIR}/.venv/bin/python"
else
    PY="$(command -v python3)"
fi

echo "[generate-api-types] using python: ${PY}"

# ── Версионный guard: pydantic/fastapi должны совпадать с requirements.txt ──
# Разные Pydantic по-разному ставят additionalProperties в OpenAPI; рассинхрон
# ломает CI-drift-check. Логика: вытаскиваем pin из requirements.txt, сверяем
# c установленной версией. Несовпадение → ошибка с инструкцией.
check_pinned_version() {
    local pkg="$1"
    local pinned
    pinned="$(grep -E "^${pkg}==" "${REQUIREMENTS_FILE}" | head -1 | cut -d= -f3 || true)"
    if [ -z "${pinned}" ]; then
        return 0
    fi
    local installed
    installed="$("${PY}" -c "import importlib.metadata as m; print(m.version('${pkg}'))" 2>/dev/null || echo "MISSING")"
    if [ "${installed}" != "${pinned}" ]; then
        cat >&2 <<EOF
[generate-api-types] ERROR: версия ${pkg} не совпадает с backend/requirements.txt
  установлено: ${installed}
  требуется:   ${pinned}

Это приведёт к рассинхрону OpenAPI-спеки с CI (job api-types-drift).
Решение:
  # через venv (рекомендуется)
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -r backend/requirements.txt
  ./scripts/generate-api-types.sh

  # или через Docker (точно как в CI)
  docker run --rm -v "\$PWD":/repo -w /repo -e ADMIN_API_KEY=dummy-0123456789abcdef \\
    -e SMTP_PASSWORD=dummy -e OPENROUTER_API_KEY=dummy-0123456789abcdef \\
    python:3.12-slim bash -c '
      apt-get update -qq && apt-get install -qq -y --no-install-recommends curl ca-certificates gnupg nodejs npm >/dev/null
      pip install -q -r backend/requirements.txt
      cd frontend && npm ci --silent && cd /repo
      ./scripts/generate-api-types.sh'
EOF
        exit 2
    fi
    echo "[generate-api-types] ${pkg}==${installed} (matches requirements.txt) ✓"
}

check_pinned_version pydantic
check_pinned_version fastapi

# ── Шаг 1. openapi.json из FastAPI-приложения ────────────────────────────────
# Dummy-ENV: Pydantic Settings требует эти поля, но для openapi() они не читаются
# (ни SMTP, ни Admin API Key, ни OpenRouter не инициализируются при построении
# схемы). Значения должны удовлетворять валидаторам (min length, формат).
echo "[generate-api-types] exporting ${OPENAPI_JSON}"
cd "${BACKEND_DIR}"
SMTP_PASSWORD="${SMTP_PASSWORD:-generate-api-types-dummy}" \
ADMIN_API_KEY="${ADMIN_API_KEY:-generate-api-types-dummy-0123456789abcdef}" \
OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-generate-api-types-dummy-0123456789abcdef}" \
"${PY}" -c "
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
