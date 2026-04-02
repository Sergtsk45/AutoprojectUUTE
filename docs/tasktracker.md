# Task tracker

## Задача: Категории файлов УУТЭ (FileCategory + missing_params)
- **Статус**: Завершена
- **Описание**: Актуальные категории документов для проектирования УУТЭ; миграция БД для старых `floor_plan` и устаревших кодов в `missing_params`; синхронизация `param_labels`, парсера ТУ, `upload.html`, админки.
- **Шаги выполнения**:
  - [x] Обновить `FileCategory` и миграцию Alembic
  - [x] `param_labels.py`, `tu_parser.py`, статика
  - [x] `docs/changelog.md`, `docs/project.md`, tasktracker
- **Зависимости**: нет

## Задача: Публичные upload-tu / submit (без 401 на upload.html)
- **Статус**: Завершена
- **Описание**: Эндпоинты в `landing.py` для загрузки ТУ и старта пайплайна при статусе `new`; админские `orders`/`pipeline/start` без изменений по защите.
- **Шаги выполнения**:
  - [x] `POST .../upload-tu`, `POST .../submit`
  - [x] `upload.html` + ограничение «только ТУ» для `new`
  - [x] `PipelineResponse` в `schemas`
- **Зависимости**: задача «upload-page + order_status»

## Задача: Страница upload.html — сценарии new и waiting_client_info
- **Статус**: Завершена
- **Описание**: Расширен ответ upload-page полем `order_status`; на клиенте выбираются URL загрузки и завершения в зависимости от статуса заявки.
- **Шаги выполнения**:
  - [x] Схема `UploadPageInfo` + эндпоинт `landing.py`
  - [x] Логика и категория `tu` в `upload.html`
  - [x] Запись в `docs/changelog.md`
- **Зависимости**: нет
