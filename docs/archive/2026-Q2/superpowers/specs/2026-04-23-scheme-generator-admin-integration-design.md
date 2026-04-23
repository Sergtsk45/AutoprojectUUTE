# Спецификация: Интеграция конфигуратора схем с админ-панелью и пайплайном

**Дата:** 2026-04-23  
**Задача:** Roadmap задача 7 — Интеграция с пайплайном и админкой  
**Автор:** Claude (по запросу Sergey)

---

## 1. Обзор

Данная спецификация описывает интеграцию конфигуратора принципиальных схем теплового пункта с существующим пайплайном обработки заявок и админ-панелью.

### Цели

1. **Автоматическая генерация PDF схемы** — если клиент заполнил конфигуратор, система автоматически генерирует PDF при обработке ответа клиента
2. **Отображение конфигурации в админке** — администратор видит выбранную клиентом конфигурацию и статус генерации
3. **Исключение схемы из missing_params** — если конфигурация выбрана, `heat_scheme` не требуется от клиента вручную

### Выбранный подход

**Оптимистичная автогенерация** — схема генерируется сразу в `process_client_response`, если в `survey_data` есть `scheme_config` и отсутствует файл `heat_scheme`. Даже если некоторые параметры из `parsed_params` пусты, схема генерируется с доступными данными.

---

## 2. Архитектура

### 2.1 Изменяемые компоненты

#### `backend/app/services/tasks.py`

**Функция:** `process_client_response`

**Изменения:**
- Добавление проверки наличия `scheme_config` в `order.survey_data`
- Вызов новой функции `_auto_generate_scheme_if_configured` перед вычислением `missing_params`
- Обновление вызова `compute_client_document_missing` с передачей `survey_data`

**Новая вспомогательная функция:** `_auto_generate_scheme_if_configured(session, order) -> bool`

**Назначение:** Автоматическая генерация PDF схемы на основе сохраненной конфигурации.

**Логика:**
1. Извлекает `scheme_config` из `order.survey_data`
2. Валидирует конфигурацию через `SchemeConfig` Pydantic-модель
3. Определяет тип схемы через `resolve_scheme_type()`
4. Извлекает параметры из `parsed_params` через `extract_scheme_params_from_parsed()`
5. Генерирует SVG через `render_scheme()`
6. Рендерит PDF через `render_scheme_pdf()`
7. Сохраняет файл в upload-папку заявки
8. Создает запись `OrderFile(category=FileCategory.HEAT_SCHEME)`
9. Возвращает `True` при успехе, `False` при ошибке

**Обработка ошибок:**
- Все исключения логируются через `logger.error(..., exc_info=True)`
- При ошибке функция возвращает `False`, схема остается в `missing_params`
- Пайплайн не блокируется, обработка заявки продолжается

#### `backend/app/services/param_labels.py`

**Функция:** `compute_client_document_missing`

**Изменения сигнатуры:**
```python
def compute_client_document_missing(
    uploaded_categories: set[str],
    survey_data: dict | None = None
) -> list[str]:
```

**Новая логика:**
- При проверке каждого кода из `CLIENT_DOCUMENT_PARAM_CODES`
- Для `heat_scheme`: если `survey_data` содержит `scheme_config`, код пропускается (не добавляется в `missing`)
- Для остальных кодов: логика без изменений

**Обновление вызовов:**
- В `tasks.py` → `process_client_response`: передавать `order.survey_data`
- В других местах (если есть): передавать `None` или соответствующие данные

#### `backend/static/admin.html`

**Функция:** `renderParsedParams`

**Изменения:**
- Добавление новой секции "Конфигурация схемы" после существующих секций parsed_params
- Проверка наличия `scheme_config` в `order.survey_data`
- Рендеринг таблицы с читаемым представлением конфигурации
- Отображение статуса генерации и ссылки на PDF (если файл существует)

### 2.2 Новые зависимости

Отсутствуют. Используются существующие функции из `scheme_service`, `scheme_svg_renderer`, `scheme_pdf_renderer`.

---

## 3. Поток данных

### 3.1 Сценарий 1: Клиент заполнил конфигуратор

```
Клиент на upload.html
    │
    ▼
Заполняет конфигуратор (тип, клапан, ГВС, вентиляция)
    │
    ▼
POST /api/v1/schemes/{order_id}/generate
    │
    ├─ Генерация PDF
    ├─ Сохранение OrderFile(category=heat_scheme)
    └─ Запись scheme_config в survey_data
    │
    ▼
Клиент нажимает "Отправить документы"
    │
    ▼
POST /api/v1/orders/{order_id}/client-upload-done
    │
    ▼
Celery: process_client_response
    │
    ├─ uploaded_categories = {f.category.value for f in order.files}
    ├─ "heat_scheme" уже в uploaded_categories
    └─ missing = compute_client_document_missing(uploaded_categories, survey_data)
        └─ heat_scheme не добавляется в missing
    │
    ▼
Переход к process_card_and_contract (если company_card загружена)
```

### 3.2 Сценарий 2: Клиент заполнил конфигуратор, но не сгенерировал PDF

```
Клиент на upload.html
    │
    ▼
Заполняет конфигуратор, но НЕ нажимает "Подтвердить"
    │
    ▼
Нажимает "Отправить документы"
    │
    ▼
Celery: process_client_response
    │
    ├─ uploaded_categories = {f.category.value for f in order.files}
    ├─ "heat_scheme" НЕ в uploaded_categories
    ├─ survey_data["scheme_config"] существует
    │
    ├─ Вызов _auto_generate_scheme_if_configured(session, order)
    │   │
    │   ├─ Извлечение scheme_config
    │   ├─ Валидация через Pydantic
    │   ├─ Определение типа схемы
    │   ├─ Извлечение параметров из parsed_params
    │   ├─ Генерация SVG
    │   ├─ Рендеринг PDF
    │   ├─ Сохранение файла
    │   └─ Создание OrderFile → возврат True
    │
    ├─ uploaded_categories.add("heat_scheme")
    └─ missing = compute_client_document_missing(uploaded_categories, survey_data)
        └─ heat_scheme не добавляется в missing
    │
    ▼
Переход к process_card_and_contract
```

### 3.3 Сценарий 3: Автогенерация упала с ошибкой

```
Celery: process_client_response
    │
    ├─ _auto_generate_scheme_if_configured(session, order)
    │   │
    │   └─ Exception (например, невалидная конфигурация)
    │       │
    │       ├─ logger.error("Ошибка автогенерации...", exc_info=True)
    │       └─ return False
    │
    ├─ "heat_scheme" остается НЕ в uploaded_categories
    └─ missing = compute_client_document_missing(uploaded_categories, survey_data)
        └─ heat_scheme добавляется в missing (т.к. файла нет)
    │
    ▼
Заявка возвращается в waiting_client_info (company_card отсутствует)
или
Переход к process_card_and_contract (но missing_params содержит heat_scheme)
```

---

## 4. UI в админ-панели

### 4.1 Визуальная структура

Новая секция "Конфигурация схемы" добавляется в функцию `renderParsedParams` после существующих секций (Подключение, Нагрузки, Адреса и т.д.).

**Макет секции:**

```
┌─────────────────────────────────────────────────────┐
│ Конфигурация схемы                                  │
├─────────────────────────────────────────────────────┤
│ Поле                      │ Значение                │
├───────────────────────────┼─────────────────────────┤
│ Тип присоединения         │ Зависимая               │
│ Регулирующий клапан       │ Да (3-ходовой)          │
│ Система ГВС               │ Да                      │
│ Вентиляция                │ Нет                     │
│ Статус                    │ ✓ Сгенерирована         │
└─────────────────────────────────────────────────────┘
[↓ Скачать PDF схемы]
```

### 4.2 Логика отображения

**Условие показа секции:**
```javascript
if (order.survey_data && order.survey_data.scheme_config) {
    // Рендерим секцию
}
```

**Маппинг значений на русский:**

| Поле JSON              | Значение          | Отображение                    |
|------------------------|-------------------|--------------------------------|
| `connection_type`      | `"dependent"`     | "Зависимая"                   |
| `connection_type`      | `"independent"`   | "Независимая"                 |
| `has_valve` (dep)      | `true`            | "Да (3-ходовой)"              |
| `has_valve` (indep)    | `true`            | "Да (2-ходовой)"              |
| `has_valve`            | `false`           | "Нет"                         |
| `has_gwp`              | `true`            | "Да"                          |
| `has_gwp`              | `false`           | "Нет"                         |
| `has_ventilation`      | `true`            | "Да"                          |
| `has_ventilation`      | `false`           | "Нет"                         |

**Определение статуса:**

```javascript
// Ищем файл категории heat_scheme
const schemeFile = order.files.find(f => f.category === 'heat_scheme');

if (schemeFile) {
    status = '✓ Сгенерирована';
    showDownloadButton = true;
    downloadUrl = `/api/v1/admin/files/${schemeFile.id}/download`;
} else {
    status = '⏳ Ожидает генерации';
    showDownloadButton = false;
}
```

### 4.3 Реализация в JavaScript

**Новая функция:**

```javascript
function renderSchemeConfigSection(schemeConfig, files) {
    if (!schemeConfig) return '';
    
    const typeLabel = schemeConfig.connection_type === 'dependent' 
        ? 'Зависимая' 
        : 'Независимая';
    
    let valveLabel = 'Нет';
    if (schemeConfig.has_valve) {
        valveLabel = schemeConfig.connection_type === 'dependent'
            ? 'Да (3-ходовой)'
            : 'Да (2-ходовой)';
    }
    
    const gwpLabel = schemeConfig.has_gwp ? 'Да' : 'Нет';
    const ventLabel = schemeConfig.has_ventilation ? 'Да' : 'Нет';
    
    const schemeFile = files.find(f => f.category === 'heat_scheme');
    const statusLabel = schemeFile ? '✓ Сгенерирована' : '⏳ Ожидает генерации';
    
    const rows = [
        parsedTableRow('Тип присоединения', `<td class="parsed-value-cell">${esc(typeLabel)}</td>`),
        parsedTableRow('Регулирующий клапан', `<td class="parsed-value-cell">${esc(valveLabel)}</td>`),
        parsedTableRow('Система ГВС', `<td class="parsed-value-cell">${esc(gwpLabel)}</td>`),
        parsedTableRow('Вентиляция', `<td class="parsed-value-cell">${esc(ventLabel)}</td>`),
        parsedTableRow('Статус', `<td class="parsed-value-cell">${esc(statusLabel)}</td>`),
    ];
    
    let downloadButton = '';
    if (schemeFile) {
        const downloadUrl = `${API_BASE}/admin/files/${schemeFile.id}/download`;
        downloadButton = `
            <div style="margin-top: 12px;">
                <a href="${downloadUrl}" 
                   class="btn btn-primary btn-sm"
                   target="_blank"
                   onclick="this.href = addKeyToUrl(this.href)">
                    ↓ Скачать PDF схемы
                </a>
            </div>`;
    }
    
    return parsedSectionHtml('Конфигурация схемы', rows) + downloadButton;
}
```

**Интеграция в `renderParsedParams`:**

```javascript
function renderParsedParams(parsed, surveyData, files) {
    // ... существующий код рендеринга секций ...
    
    // Добавляем секцию конфигурации схемы
    if (surveyData && surveyData.scheme_config) {
        sections.push(renderSchemeConfigSection(surveyData.scheme_config, files));
    }
    
    return sections.join('');
}
```

### 4.4 CSS-стили

Используются существующие классы:
- `.parsed-section` — обертка секции
- `.parsed-section-title` — заголовок секции
- `.parsed-params-table` — таблица параметров
- `.parsed-label-cell` — ячейка с названием поля
- `.parsed-value-cell` — ячейка со значением
- `.btn.btn-primary.btn-sm` — кнопка скачивания

Дополнительных стилей не требуется.

---

## 5. Детали реализации

### 5.1 Функция `_auto_generate_scheme_if_configured`

**Расположение:** `backend/app/services/tasks.py`

**Сигнатура:**
```python
def _auto_generate_scheme_if_configured(session: Session, order: Order) -> bool:
    """
    Автоматическая генерация PDF схемы на основе сохраненной конфигурации.
    
    Args:
        session: SQLAlchemy session
        order: Order instance с загруженными связями
    
    Returns:
        True если схема успешно сгенерирована, False при ошибке
    
    Raises:
        Не выбрасывает исключения, логирует ошибки
    """
```

**Псевдокод:**

```python
def _auto_generate_scheme_if_configured(session: Session, order: Order) -> bool:
    try:
        # 1. Импорты (внутри функции, как в остальных Celery-задачах)
        from app.schemas.scheme import SchemeConfig
        from app.services.scheme_service import (
            resolve_scheme_type, 
            extract_scheme_params_from_parsed
        )
        from app.services.scheme_svg_renderer import render_scheme
        from app.services.scheme_pdf_renderer import render_scheme_pdf
        
        # 2. Извлечение и валидация конфигурации
        scheme_config_dict = order.survey_data["scheme_config"]
        scheme_config = SchemeConfig(**scheme_config_dict)
        
        # 3. Определение типа схемы
        scheme_type = resolve_scheme_type(scheme_config)
        if not scheme_type:
            logger.error(
                "Невалидная конфигурация схемы для order=%s: %s", 
                order.id, 
                scheme_config_dict
            )
            return False
        
        # 4. Извлечение параметров для SVG
        params = extract_scheme_params_from_parsed(
            parsed_params=order.parsed_params,
            order_data={
                "project_number": order.project_number,
                "object_address": order.object_address,
                "company_name": order.company_name,
            }
        )
        
        # 5. Генерация SVG
        svg_content = render_scheme(scheme_type, params)
        
        # 6. Генерация PDF
        pdf_bytes = render_scheme_pdf(
            svg_content=svg_content,
            stamp_data=params.model_dump(),
            format="a3"
        )
        
        # 7. Сохранение файла в upload-папку
        upload_dir = Path(settings.upload_folder) / str(order.id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"scheme_{order.project_number or order.id}_auto.pdf"
        file_path = upload_dir / filename
        
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
        
        # 8. Создание записи OrderFile
        order_file = OrderFile(
            order_id=order.id,
            category=FileCategory.HEAT_SCHEME,
            original_filename=filename,
            stored_filename=filename,
            file_size=len(pdf_bytes),
        )
        session.add(order_file)
        session.commit()
        
        logger.info(
            "Автогенерация схемы успешна для order=%s, файл=%s", 
            order.id, 
            filename
        )
        return True
        
    except Exception as e:
        logger.error(
            "Ошибка автогенерации схемы для order=%s: %s", 
            order.id, 
            e, 
            exc_info=True
        )
        return False
```

### 5.2 Изменения в `process_client_response`

**Текущая логика (упрощенно):**

```python
def process_client_response(self, order_id: str):
    with SyncSession() as session:
        order = _get_order(session, oid)
        
        uploaded_categories = {f.category.value for f in order.files}
        missing = compute_client_document_missing(uploaded_categories)
        
        # ... проверка company_card ...
```

**Новая логика:**

```python
def process_client_response(self, order_id: str):
    with SyncSession() as session:
        order = _get_order(session, oid)
        
        uploaded_categories = {f.category.value for f in order.files}
        
        # НОВОЕ: Автогенерация схемы, если конфигурация заполнена
        if (
            order.survey_data 
            and "scheme_config" in order.survey_data
            and "heat_scheme" not in uploaded_categories
        ):
            success = _auto_generate_scheme_if_configured(session, order)
            if success:
                # Обновляем список загруженных категорий
                uploaded_categories.add("heat_scheme")
                # Обновляем order.files из БД
                session.refresh(order)
        
        # ИЗМЕНЕНО: Передаем survey_data в compute_client_document_missing
        missing = compute_client_document_missing(
            uploaded_categories, 
            order.survey_data
        )
        
        # ... остальная логика без изменений ...
```

### 5.3 Изменения в `compute_client_document_missing`

**Текущая реализация:**

```python
def compute_client_document_missing(uploaded_categories: set[str]) -> list[str]:
    """Какие из обязательных документов ещё не загружены."""
    return [c for c in CLIENT_DOCUMENT_PARAM_CODES if c not in uploaded_categories]
```

**Новая реализация:**

```python
def compute_client_document_missing(
    uploaded_categories: set[str],
    survey_data: dict | None = None
) -> list[str]:
    """
    Какие из обязательных документов ещё не загружены.
    
    Args:
        uploaded_categories: Множество кодов уже загруженных файлов
        survey_data: Данные опросного листа (для проверки автогенерации схемы)
    
    Returns:
        Список кодов недостающих документов
    """
    missing = []
    for code in CLIENT_DOCUMENT_PARAM_CODES:
        if code in uploaded_categories:
            continue
        
        # Специальная логика для heat_scheme:
        # Если есть схема в конфигураторе — не требуем загрузку вручную
        if code == "heat_scheme":
            if survey_data and "scheme_config" in survey_data:
                continue
        
        missing.append(code)
    
    return missing
```

### 5.4 Обновление других вызовов

Необходимо найти все места, где вызывается `compute_client_document_missing`, и обновить вызовы:

**Список файлов для проверки:**
- `backend/app/services/tasks.py` — обновлено выше
- `backend/app/services/order_service.py` — возможно используется
- `backend/app/api/landing.py` — возможно используется
- `backend/app/services/tu_parser.py` — возможно используется

**Стратегия обновления:**
- Если контекст позволяет передать `survey_data` → передать
- Если контекста нет → передать `None` (логика останется прежней)

---

## 6. Обработка ошибок

### 6.1 Ошибки автогенерации

**Возможные причины:**
- Невалидная конфигурация в `survey_data` (не проходит Pydantic-валидацию)
- Отсутствие обязательных параметров в `parsed_params`
- Ошибки генерации SVG (геометрия, элементы)
- Ошибки рендеринга PDF (WeasyPrint)
- Ошибки файловой системы (нет прав, диск заполнен)

**Обработка:**
1. Все исключения перехватываются в `try/except` блоке
2. Логирование через `logger.error(..., exc_info=True)` с полным stack trace
3. Функция возвращает `False`
4. `heat_scheme` остается в `missing_params`
5. Заявка продолжает обрабатываться по обычному пайплайну

**Результат для клиента:**
- Получает email с запросом загрузить схему вручную (как раньше)
- Администратор видит в админке: "Статус: ⏳ Ожидает генерации" (файл отсутствует)

### 6.2 Ошибки отображения в админке

**Возможные причины:**
- Некорректная структура `scheme_config` в `survey_data`
- Отсутствующие поля в конфигурации

**Обработка:**
- JavaScript-код использует безопасный доступ к полям (`schemeConfig?.connection_type`)
- При отсутствии поля отображается "—" или пропускается строка
- Ошибки логируются в консоль браузера, но не ломают страницу

---

## 7. Тестирование

### 7.1 Модульные тесты

**Файл:** `backend/tests/test_scheme_integration.py` (новый)

**Тесты для `_auto_generate_scheme_if_configured`:**
1. Успешная генерация с полными параметрами
2. Успешная генерация с частичными параметрами (пустые поля в `parsed_params`)
3. Ошибка: невалидная конфигурация (несуществующая комбинация)
4. Ошибка: отсутствует `scheme_config` в `survey_data`
5. Ошибка: ошибка файловой системы (мокируем `open()`)

**Тесты для `compute_client_document_missing`:**
1. Все документы загружены → `missing = []`
2. `heat_scheme` отсутствует, но есть `scheme_config` → `heat_scheme` не в `missing`
3. `heat_scheme` отсутствует, `scheme_config` нет → `heat_scheme` в `missing`
4. `survey_data = None` → логика работает как раньше

### 7.2 Интеграционные тесты

**Сценарий 1:** Полный цикл с конфигуратором
1. Создать заявку через API
2. Сохранить `scheme_config` через `POST /api/v1/schemes/{order_id}/generate`
3. Загрузить остальные документы (company_card, tu и т.д.)
4. Вызвать `POST /api/v1/orders/{order_id}/client-upload-done`
5. Проверить: создан файл `heat_scheme`, `missing_params` не содержит `heat_scheme`

**Сценарий 2:** Автогенерация при отсутствии предварительной генерации
1. Создать заявку
2. Сохранить только `scheme_config` в `survey_data` (без генерации PDF)
3. Загрузить остальные документы
4. Вызвать `POST /api/v1/orders/{order_id}/client-upload-done`
5. Проверить: автогенерация выполнена, файл создан

**Сценарий 3:** Ошибка автогенерации
1. Создать заявку с невалидной конфигурацией в `survey_data`
2. Вызвать `process_client_response`
3. Проверить: файл не создан, `heat_scheme` в `missing_params`, ошибка залогирована

### 7.3 UI-тесты (ручные)

**Админ-панель:**
1. Открыть заявку с заполненной конфигурацией → видна секция "Конфигурация схемы"
2. Проверить корректность маппинга (зависимая/независимая, клапан, ГВС, вентиляция)
3. Если схема сгенерирована → статус "✓ Сгенерирована", кнопка скачивания работает
4. Если схема не сгенерирована → статус "⏳ Ожидает генерации", кнопка скрыта
5. Открыть заявку без конфигурации → секция не отображается

---

## 8. Миграции данных

Миграции БД не требуются. Все изменения связаны с логикой приложения, структура таблиц не меняется.

**Примечание:** `survey_data` и `parsed_params` — JSONB-поля, схема свободная.

---

## 9. Безопасность

### 9.1 Валидация входных данных

- `scheme_config` валидируется через Pydantic-модель `SchemeConfig` при автогенерации
- Недопустимые комбинации параметров отклоняются `model_validator`

### 9.2 Безопасность файловой системы

- Все файлы сохраняются в изолированную папку `settings.upload_folder / order.id`
- Имя файла формируется программно: `f"scheme_{order.project_number or order.id}_auto.pdf"`
- Нет пользовательского ввода в пути файлов

### 9.3 Доступ к файлам в админке

- Используется существующий endpoint `/api/v1/admin/files/{file_id}/download`
- Требуется API-ключ (`_k` параметр) для доступа
- Проверка прав доступа администратора выполняется на уровне API

---

## 10. Производительность

### 10.1 Автогенерация в Celery-задаче

- Генерация схемы выполняется синхронно внутри `process_client_response`
- Ожидаемое время генерации: 1-3 секунды (SVG + WeasyPrint)
- Не блокирует обработку других заявок (Celery-воркер обрабатывает задачи последовательно)

### 10.2 Оптимизации (если потребуется)

Если генерация станет узким местом:
1. Вынести автогенерацию в отдельную Celery-задачу (`auto_generate_scheme.delay(order_id)`)
2. Использовать асинхронную генерацию (если WeasyPrint поддерживает)
3. Кэшировать SVG-шаблоны (сейчас генерируются программно каждый раз)

---

## 11. Документация

После реализации обновить:

### 11.1 `docs/changelog.md`

```markdown
## [2026-04-23] - Интеграция конфигуратора схем с пайплайном

### Добавлено
- Автоматическая генерация PDF схемы при обработке ответа клиента
- Отображение конфигурации схемы в админ-панели (секция "Конфигурация схемы")
- Исключение heat_scheme из missing_params, если схема сгенерирована через конфигуратор

### Изменено
- `tasks.py`: добавлена автогенерация в process_client_response
- `param_labels.py`: compute_client_document_missing теперь принимает survey_data
- `admin.html`: новая секция в renderParsedParams для отображения конфигурации

### Исправлено
- Клиенты больше не должны вручную загружать схему, если заполнили конфигуратор
```

### 11.2 `docs/tasktracker.md`

```markdown
## Задача: Интеграция конфигуратора схем (roadmap задача 7)
- **Статус**: Завершена
- **Описание**: Автогенерация PDF при обработке ответа клиента, отображение в админке
- **Шаги выполнения**:
  - [x] Добавлена функция _auto_generate_scheme_if_configured в tasks.py
  - [x] Обновлена логика compute_client_document_missing
  - [x] Добавлено отображение конфигурации в admin.html
  - [x] Написаны тесты
  - [x] Обновлена документация
```

### 11.3 `docs/project.md`

Обновить секцию "Пайплайн обработки заявок":

```markdown
### Обработка ответа клиента (process_client_response)

1. Проверка загруженных файлов
2. **Автогенерация схемы** (если scheme_config в survey_data и heat_scheme отсутствует)
3. Вычисление missing_params (с учетом автогенерации)
4. Проверка company_card
5. Переход к генерации договора
```

### 11.4 `CLAUDE.md`

Обновить список файлов конфигуратора схем:

```markdown
### Конфигуратор схем
- `backend/app/services/tasks.py` — автогенерация в process_client_response
- `backend/app/services/param_labels.py` — логика missing_params с учетом конфигуратора
- `backend/static/admin.html` — отображение конфигурации в админке
```

---

## 12. Риски и ограничения

### 12.1 Неполные параметры в parsed_params

**Риск:** Схема может быть сгенерирована с пустыми полями (расходы, температуры, давления).

**Митигация:**
- Это не критично, т.к. основная топология схемы определяется `scheme_config`
- Пустые поля отображаются как "—" на схеме (читаемо)
- Администратор может увидеть это в админке и запросить дополнительную информацию

### 12.2 Ошибки WeasyPrint

**Риск:** WeasyPrint может упасть с ошибкой на специфических системах или при отсутствии шрифтов.

**Митигация:**
- Все ошибки перехватываются и логируются
- Система не блокируется, клиент получает запрос загрузить схему вручную
- Dockerfile должен содержать все необходимые зависимости WeasyPrint

### 12.3 Производительность Celery

**Риск:** Генерация схемы может замедлить обработку заявок.

**Митигация:**
- Генерация занимает 1-3 секунды (приемлемо для синхронной обработки)
- При необходимости можно вынести в отдельную Celery-задачу

---

## 13. Критерии приемки

### Функциональные требования

- [ ] Если `scheme_config` в `survey_data` и `heat_scheme` отсутствует → автогенерация выполняется
- [ ] Сгенерированный файл сохраняется как `OrderFile(category=heat_scheme)`
- [ ] `heat_scheme` не добавляется в `missing_params`, если есть `scheme_config`
- [ ] Админка отображает конфигурацию схемы с корректным маппингом на русский
- [ ] Статус "✓ Сгенерирована" и кнопка скачивания отображаются, если файл существует
- [ ] Статус "⏳ Ожидает генерации" отображается, если файл отсутствует
- [ ] При ошибке автогенерации система не блокируется, ошибка логируется

### Нефункциональные требования

- [ ] Код покрыт модульными тестами (>80% coverage для новых функций)
- [ ] Интеграционные тесты проходят для всех сценариев
- [ ] Обновлена документация (changelog, tasktracker, project.md, CLAUDE.md)
- [ ] UI-тесты админки выполнены вручную

---

## 14. Заключение

Данная спецификация описывает полную интеграцию конфигуратора схем с существующим пайплайном обработки заявок. Решение использует оптимистичную автогенерацию, минимизируя изменения в кодовой базе и обеспечивая отказоустойчивость при ошибках генерации.

Основные преимущества подхода:
- Простота реализации (используются существующие функции генерации)
- Прозрачность для клиента (схема генерируется автоматически)
- Отказоустойчивость (ошибки не блокируют пайплайн)
- Минимальные изменения в UI (только одна новая секция в админке)

Следующий шаг: создание детального плана реализации с разбивкой на подзадачи.
