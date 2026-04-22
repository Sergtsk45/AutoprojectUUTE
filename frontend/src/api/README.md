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

```bash
# из корня репо, требует установленные backend (venv) и frontend (npm ci)
./scripts/generate-api-types.sh
```

Скрипт: импортирует FastAPI `app`, экспортирует `app.openapi()` в JSON,
запускает `openapi-typescript` → `types.ts`.

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
