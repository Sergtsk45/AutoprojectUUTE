# API-типы (автогенерация)

Этот каталог содержит артефакты, сгенерированные из OpenAPI-спеки бэкенда.
Единый источник правды — Pydantic-схемы в `backend/app/` и FastAPI-роутеры.

## Файлы

- **`openapi.json`** — снимок OpenAPI 3.1-спеки, экспортированный из
  `app.openapi()`. Коммитится в репозиторий (источник для `types.ts` и
  для CI-проверки `api-types-drift`).
- **`types.ts`** — TS-типы, сгенерированные из `openapi.json` утилитой
  [`openapi-typescript`](https://github.com/openapi-ts/openapi-typescript).
  Коммитится в репозиторий; редактировать руками **нельзя** (CI падает
  при рассинхроне).

## Как перегенерировать

Скрипт [`scripts/generate-api-types.sh`](../../../scripts/generate-api-types.sh) требует **точных pinned-версий** Python-зависимостей из [`backend/requirements.txt`](../../../backend/requirements.txt) (особенно `pydantic` и `fastapi` — разные минорные версии Pydantic по-разному ставят `additionalProperties` в OpenAPI и ломают CI-drift-check).

Рекомендованный путь — локальный venv:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
./scripts/generate-api-types.sh
```

Скрипт автоматически подхватит `backend/.venv/bin/python`. Если версии `pydantic`/`fastapi` не совпадают с `requirements.txt`, скрипт падает с подробной инструкцией — чинит рассинхрон локально до пуша.

Альтернатива без venv — Docker с тем же образом, что в CI (`python:3.12-slim`). Команда печатается в сообщении об ошибке скрипта.

## Что делать при CI-фейле «API-типы рассинхронизированы»

1. Локально: `./scripts/generate-api-types.sh`.
2. Закоммитить обновлённые `openapi.json` и `types.ts` в том же PR, где
   изменились Pydantic-схемы или роутеры.

Если диф затронул только описания (docstring) — значит бэкендер обновил
комментарий в Pydantic-модели. Это нормальный кейс, регенерация проходит
за пару секунд.

## Использование во фронте

Типы подключаются через `frontend/src/api.ts`:

```ts
import type { OrderRequest, OrderCreatedResponse } from './api';
```

Не импортируйте `types.ts` напрямую — публичное API модуля живёт в `api.ts`
(это позволит подменить транспорт без правки компонентов).
