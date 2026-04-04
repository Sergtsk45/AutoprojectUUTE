# Отчёт-трекер: отображение результатов парсинга ТУ в админке

## Задача: карточка «Результат парсинга ТУ» (`/admin`)

- **Статус**: Завершена
- **Описание**: В карточке заявки показываются уверенность парсинга, свёрнутый блок «Извлечённые параметры» с таблицами по группам (данные из `orders.parsed_params`), недостающие поля и предупреждения. При пустом `parsed_params` — сообщение «Парсинг не выполнен». Реализация только во фронтенде: `backend/static/admin.html` (vanilla JS).
- **Файлы**: [`backend/static/admin.html`](../backend/static/admin.html)

### Шаги выполнения

- [x] Карточка `#parsedCard` всегда видна при открытой заявке; пустое состояние `parsed_params`
- [x] CSS: `.parsed-params-details`, таблицы `.parsed-params-table`, `.parsed-null` / `.parsed-value`
- [x] Функции `fmtNum`, `fmtParsedValueCell`, `buildParsedParamsTablesHtml`, fallback с плоских legacy-ключей при отсутствии вложенной схемы
- [x] Порядок блоков: уверенность → `<details>` с таблицами → недостающие данные → предупреждения
- [x] Документация: `changelog.md`, `project.md`, этот файл

### Соответствие UI ↔ JSON (`parsed_params`)

Маппинг ориентирован на сериализацию `TUParsedData` (`model_dump` в Celery). Поддержаны альтернативные ключи из примеров/старых данных (`document_info`, `validity_date`, `communication_interface`).

| Блок UI | Путь в JSON |
|--------|-------------|
| РСО | `rso.rso_name`, fallback `document_info.rso_name` |
| Номер / дата ТУ | `document.tu_number`, `document.tu_date` (или `document_info.*`) |
| Действует до | `document.tu_valid_to` или `document_info.validity_date` |
| Адрес объекта | `object.object_address` или `document.object_address` |
| Тепловые нагрузки | `heat_loads.*`; legacy: `heat_load_ot`, `heat_load_gvs`, `heat_load_vent` |
| Теплоноситель | `coolant.*`; legacy: `t_supply`, `t_return`, `p_supply`, `p_return` |
| Трубопровод | `pipeline.pipe_outer_diameter_mm`, `pipe_wall_thickness_mm` (если есть), `pipe_inner_diameter_mm` |
| Подключение | `connection.system_type`; схема: `connection_scheme` / `connection_type` / `heating_system` |
| Учёт | `metering.heat_meter_class`, `metering.data_interface` или `communication_interface` |

### Чеклист проверки в браузере

1. Заявка без парсинга (`parsed_params` null или `{}`): карточка видна, текст «Парсинг не выполнен», при наличии — блок недостающих данных.
2. Заявка после парсинга: процент уверенности, раскрытие «Извлечённые параметры ▶», таблицы с единицами, для `null` — «—» серым.
3. Предупреждения и `missing_params` отображаются после таблиц.

### Зависимости

- Данные уже приходят в `GET /api/v1/orders/{id}` в поле `parsed_params` (изменения бэкенда не требуются).
