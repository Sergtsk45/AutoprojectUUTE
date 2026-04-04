# Фича: Умный опросный лист (автозаполнение из парсинга ТУ)

> Для custom-заказов: опросный лист заблокирован → клиент загружает ТУ → парсинг → данные из ТУ заполняют поля формы → клиент редактирует и дополняет → отправляет.

---

## Задача 1: Расширить ответ upload-page для custom-заказов (бэкенд)
- **Статус**: Завершена
- **Описание**: Эндпоинт `GET /landing/orders/{id}/upload-page` должен отдавать `parsed_params` и `order_type`, чтобы фронт мог предзаполнить форму. Сейчас `parsed_params` доступен только через админский `/orders/{id}`.
- **Шаги выполнения**:
  - [x] В `UploadPageInfo` добавить: `parsed_params: dict | None = None`, `order_type: str | None = None`, `survey_data: dict | None = None`
  - [x] В `get_upload_page_info` (landing.py): для `OrderType.CUSTOM` — `parsed_params` если не пустой, `survey_data` если не `None`; для express оба `None`
  - [x] Также включать survey_data если уже заполнен
  - [x] Убедиться что order_type уже есть в UploadPageInfo (из предыдущего спринта)
- **Зависимости**: нет — предыдущий спринт завершён

### Промпт для Cursor

```
GOAL: Эндпоинт upload-page отдаёт parsed_params для custom-заказов.

CONTEXT:
- backend/app/api/landing.py — эндпоинт get_upload_page_info
- backend/app/schemas/schemas.py — UploadPageInfo
- parsed_params хранится в Order.parsed_params (JSONB)
- survey_data хранится в Order.survey_data (JSONB)
- order_type хранится в Order.order_type (enum)

FILES:
- backend/app/schemas/schemas.py — расширить UploadPageInfo
- backend/app/api/landing.py — передавать новые поля

TASK:
1. В UploadPageInfo добавить:
   - order_type: str | None = None
   - parsed_params: dict | None = None
   - survey_data: dict | None = None

2. В get_upload_page_info (landing.py):
   - Всегда передавать order_type = order.order_type.value
   - Если order.order_type == OrderType.CUSTOM:
     - Передавать parsed_params = order.parsed_params (если не пустой)
     - Передавать survey_data = order.survey_data (если не None)
   - Для express-заказов parsed_params и survey_data = None (не нужны клиенту)

EXPECTED RESULT:
GET /landing/orders/{id}/upload-page для custom-заказа со статусом tu_parsed возвращает:
{
  "order_type": "custom",
  "parsed_params": {"heat_loads": {"heating_load": 0.15, ...}, ...},
  "survey_data": null,
  ...
}

CONSTRAINTS:
- Не ломать существующую логику для express-заказов и статусов new / waiting_client_info
- parsed_params может содержать вложенные объекты — отдавать как есть
- Не добавлять новые эндпоинты — расширяем существующий
```

---

## Задача 2: Изменить поведение кнопки «Отправить» для custom-заказов (фронтенд)
- **Статус**: Завершена
- **Описание**: Сейчас после клика «Отправить» для новой заявки вызывается `/submit` и показывается экран «Готово». Для custom-заказов вместо «Готово» нужно показать состояние ожидания парсинга, а затем — форму опросного листа с предзаполненными данными.
- **Шаги выполнения**:
  - [x] После `/submit` для custom-заказа: вместо `showCompleted()` показать блок ожидания парсинга
  - [x] Запустить polling `GET /landing/orders/{id}/upload-page` каждые 5 секунд
  - [x] Когда `order_status` станет `tu_parsed` или далее по пайплайну — остановить polling
  - [x] Извлечь `parsed_params` из ответа и вызвать `prefillSurvey(parsedParams)`; подмешать `survey_data` при наличии
  - [x] Показать блок `#surveyCard` с разблокированными полями
  - [x] Для express-заказов — поведение без изменений (showCompleted)
- **Зависимости**: Задача 1

### Промпт для Cursor

```
GOAL: После загрузки ТУ для custom-заказа — polling парсинга → автозаполнение формы.

CONTEXT:
- backend/static/upload.html — ванильный JS, одностраничное приложение
- Переменная orderData содержит order_type из API
- isNewOrder = true для статуса 'new'
- Текущее поведение: submit → POST /submit → showCompleted()
- Новое поведение для custom: submit → POST /submit → showParsing() → poll → prefillSurvey() → showSurvey()

FILES:
- backend/static/upload.html

TASK:
1. Модифицировать обработчик кнопки submitBtn:
   - Если orderData.order_type === 'custom' && isNewOrder:
     - НЕ вызывать showCompleted()
     - Вызвать новую функцию showParsingState()
     - Запустить startParsingPoll()
   - Иначе (express или waiting_client_info):
     - Поведение без изменений (showCompleted)

2. Функция showParsingState():
   - Скрыть #uploadCard
   - Показать новый блок #parsingCard (создать в HTML):
     - Спиннер (используй существующий стиль .spinner)
     - Текст «Анализируем технические условия...»
     - Подтекст «Обычно это занимает 30-60 секунд»
     - Прогресс-бар (анимированный, неопределённый)

3. Функция startParsingPoll():
   - setInterval каждые 5 секунд:
     - GET /api/v1/landing/orders/{ORDER_ID}/upload-page
     - Если response.order_status === 'tu_parsed' или далее:
       - clearInterval
       - Вызвать prefillSurvey(response.parsed_params)
       - Скрыть #parsingCard, показать #surveyCard
       - showBanner('success', 'Анализ завершён! Проверьте и дополните данные.')
     - Если response.order_status === 'error':
       - clearInterval
       - showBanner('error', 'Ошибка анализа ТУ. Попробуйте загрузить файл снова.')
       - Показать #uploadCard обратно
   - Таймаут: через 5 минут (60 итераций) остановить и показать сообщение «Анализ занимает больше времени...»

4. HTML-блок #parsingCard (добавить между #uploadCard и #surveyCard):
   <div id="parsingCard" class="card" style="display:none; text-align:center; padding:40px 20px;">
     <div class="spinner-dark" style="width:40px; height:40px; margin:0 auto 20px; border-width:3px;"></div>
     <h3 style="margin:0 0 8px; font-size:18px;">Анализируем технические условия</h3>
     <p style="color:#64748b; margin:0 0 20px;">Обычно это занимает 30–60 секунд</p>
     <div style="height:4px; background:#e2e8f0; border-radius:2px; overflow:hidden;">
       <div style="width:30%; height:100%; background:#3b82f6; border-radius:2px; animation: parseProgress 2s ease-in-out infinite;"></div>
     </div>
   </div>

5. CSS: добавить @keyframes parseProgress { 0% {width:10%; margin-left:0} 50% {width:40%; margin-left:30%} 100% {width:10%; margin-left:90%} }

EXPECTED RESULT:
Custom-заказ: загрузил ТУ → нажал «Отправить» → красивый экран ожидания → через 30-60 сек форма опросного листа появляется с заполненными полями.

CONSTRAINTS:
- Ванильный JS, без фреймворков
- Не ломать express-флоу (для express → showCompleted как раньше)
- Не ломать waiting_client_info-флоу (загрузка доп. документов)
- Polling строго через публичный эндпоинт /landing/orders/{id}/upload-page (без X-Admin-Key)
```

---

## Задача 3: Маппинг parsed_params → поля опросного листа (фронтенд)
- **Статус**: Не начата
- **Описание**: Функция prefillSurvey(parsedParams) берёт вложенный JSON из парсера и расставляет значения по полям формы. Поля с данными помечаются визуально (зелёная рамка = «заполнено из ТУ»). Пустые поля — обычные (клиент заполняет сам).
- **Шаги выполнения**:
  - [ ] Создать объект PARAM_TO_SURVEY_MAP — маппинг путей
  - [ ] Функция prefillSurvey: обход маппинга, установка значений
  - [ ] Визуальная индикация: предзаполненные поля с зелёной рамкой + подписью «из ТУ»
  - [ ] Пустые обязательные поля с жёлтой рамкой + подписью «требуется заполнить»
  - [ ] Разблокировать все поля формы (убрать disabled)
  - [ ] Секция «Приборы учёта» — manufacturer всегда пустой (в ТУ не указан)
- **Зависимости**: Задача 2, форма из предыдущего спринта

### Промпт для Cursor

```
GOAL: Автозаполнение полей опросного листа данными из parsed_params.

CONTEXT:
- backend/static/upload.html — опросный лист уже создан (предыдущий спринт)
- parsed_params — вложенный JSON от парсера ТУ, структура:
  {
    "heat_loads": {"total_load": 0.6, "heating_load": 0.45, "hot_water_load": 0.15, "ventilation_load": null},
    "pipeline": {"pipe_outer_diameter_mm": 76, "pipe_inner_diameter_mm": null},
    "coolant": {"supply_temp": 130, "return_temp": 70, "temp_schedule": "130/70", "supply_pressure_kgcm2": 6.0, "return_pressure_kgcm2": 4.5},
    "connection": {"connection_type": "зависимая", "system_type": "закрытая"},
    "metering": {"heat_calculator_model": null, "flowmeter_model": null, "heat_meter_class": 2},
    "object": {"object_type": "МКД", "object_address": "..."},
    "parse_confidence": 0.85,
    "warnings": [...]
  }

FILES:
- backend/static/upload.html

TASK:
1. Создать маппинг (объект JS):
   const PARAM_TO_SURVEY = {
     // parsed_params path → survey form field id
     'heat_loads.heating_load': 'heat_load_heating',
     'heat_loads.hot_water_load': 'heat_load_hw',
     'heat_loads.ventilation_load': 'heat_load_vent',
     'coolant.supply_pressure_kgcm2': 'pressure_supply',
     'coolant.return_pressure_kgcm2': 'pressure_return',
     'coolant.temp_schedule': 'temp_schedule',
     'connection.connection_type': 'connection_type',
     'connection.system_type': 'system_type',
     'pipeline.pipe_outer_diameter_mm': 'pipe_dn_supply',
     'metering.heat_meter_class': 'accuracy_class',
     'object.object_type': 'building_type',
   };

2. Функция getNestedValue(obj, path):
   - Разбивает path по '.' и рекурсивно получает значение
   - Возвращает null если путь не существует

3. Функция prefillSurvey(parsedParams):
   - Убрать disabled со всех полей #surveyCard
   - Для каждого маппинга:
     - Получить значение через getNestedValue
     - Если значение != null:
       - Установить value элемента (input.value = ..., select — найти option)
       - Для select: нормализовать значение (connection_type "зависимая" → option value)
       - Добавить CSS класс .prefilled — зелёная левая граница
       - Добавить маленький бейдж «из ТУ» справа от поля
     - Если значение == null и поле обязательное:
       - Добавить CSS класс .needs-input — жёлтая левая граница
       - Бейдж «заполните»
   - Показать блок с confidence: «Уверенность анализа: 85%»
   - Если есть warnings — показать список предупреждений

4. CSS:
   .prefilled { border-left: 3px solid #16a34a !important; }
   .prefilled-badge {
     font-size: 11px; color: #16a34a; background: #f0fdf4;
     padding: 2px 6px; border-radius: 4px; margin-left: 8px;
   }
   .needs-input { border-left: 3px solid #d97706 !important; }
   .needs-badge {
     font-size: 11px; color: #d97706; background: #fffbeb;
     padding: 2px 6px; border-radius: 4px; margin-left: 8px;
   }

5. Нормализация значений для select:
   - connection_type: "зависимая" → "dependent", "независимая" → "independent"
     (или как у тебя сделаны option value в форме)
   - system_type: "закрытая" → "closed", "открытая" → "open"
   - temp_schedule: "130/70" → найти option "130/70" или ближайший
   - building_type: "МКД" → "residential", "нежилое" → "commercial"
     (адаптировать под реальные option value)

6. Отдельно обработать секцию «Приборы учёта»:
   - manufacturer — всегда пустой, с бейджем «выберите производителя»
   - flow_meter_type — если в metering есть flowmeter_model содержащий "ультразвук" → "ultrasonic"
   - Остальные поля приборов — пустые по умолчанию

EXPECTED RESULT:
После парсинга ТУ форма выглядит:
- Нагрузки, давления, температуры — заполнены зелёным
- Производитель, тип расходомера — пустые жёлтым
- Клиент видит что 70% работы сделано, дополняет остальное

CONSTRAINTS:
- Все поля остаются редактируемыми (клиент может исправить данные из парсинга)
- Бейджи «из ТУ» не блокируют поля
- При повторном открытии страницы (status tu_parsed) — данные берутся из parsed_params
- Если survey_data уже сохранён — использовать его вместо parsed_params (приоритет)
```

---

## Задача 4: Инициализация формы при повторном входе (фронтенд)
- **Статус**: Не начата
- **Описание**: Если клиент закрыл страницу и вернулся позже (статус tu_parsed или далее) — форма должна отобразиться сразу с данными. Не нужно заново загружать ТУ.
- **Шаги выполнения**:
  - [ ] В функции `init()`: проверить order_type и order_status
  - [ ] Если custom + статус tu_parsed / waiting_client_info / client_info_received:
    - Показать #surveyCard сразу (не #uploadCard)
    - Если есть survey_data — заполнить из него
    - Иначе — заполнить из parsed_params
  - [ ] Если custom + статус new — показать #uploadCard + заблокированный #surveyCard
  - [ ] Если custom + статус tu_parsing — показать #parsingCard + запустить polling
- **Зависимости**: Задачи 1, 2, 3

### Промпт для Cursor

```
GOAL: Корректная инициализация upload-страницы для custom-заказа в любом статусе.

CONTEXT:
- backend/static/upload.html
- Функция init() загружает orderData из GET /landing/orders/{id}/upload-page
- orderData теперь содержит: order_type, order_status, parsed_params, survey_data

FILES:
- backend/static/upload.html

TASK:
Расширить функцию init() — после загрузки orderData добавить ветвление:

if (orderData.order_type === 'custom') {
  const status = orderData.order_status;

  if (status === 'new') {
    // Показать загрузку ТУ + заблокированную форму
    showUploadWithLockedSurvey();
  }
  else if (status === 'tu_parsing') {
    // Парсинг в процессе — показать ожидание + polling
    showParsingState();
    startParsingPoll();
  }
  else if (['tu_parsed', 'waiting_client_info', 'client_info_received', 'data_complete'].includes(status)) {
    // Форма доступна
    if (orderData.survey_data) {
      // Уже заполнял — показать сохранённые данные
      prefillSurveyFromSaved(orderData.survey_data);
    } else if (orderData.parsed_params) {
      // Первый раз после парсинга — предзаполнить из ТУ
      prefillSurvey(orderData.parsed_params);
    }
    showSurveyCard();
    // Также показать загрузку доп. документов если waiting_client_info
    if (status === 'waiting_client_info' || status === 'client_info_received') {
      showUploadCardForDocs();
    }
  }
  else if (['review', 'completed'].includes(status)) {
    showCompleted();
  }
  else if (status === 'error') {
    showBanner('error', 'Произошла ошибка. Свяжитесь с нами.');
  }
} else {
  // Express — стандартное поведение без изменений
  // ... существующая логика ...
}

Функции:
- showUploadWithLockedSurvey(): показать #uploadCard + #surveyCard с disabled полями и overlay «Сначала загрузите ТУ»
- showSurveyCard(): показать #surveyCard, скрыть #uploadCard и #parsingCard
- showUploadCardForDocs(): показать дополнительный блок загрузки документов (чеклист) ВМЕСТЕ с формой
- prefillSurveyFromSaved(surveyData): заполнить поля из плоского JSON survey_data (без маппинга вложенности — ключи = id полей)

EXPECTED RESULT: Клиент может закрыть и открыть страницу в любой момент — увидит правильное состояние.

CONSTRAINTS:
- Не дублировать логику init() — вынести в функции
- Express-заказы: init() работает как раньше
- Для статусов после tu_parsed: форма уже редактируемая
```

---

## Задача 5: Обновить docs и tasktracker
- **Статус**: Не начата
- **Описание**: Зафиксировать изменения.
- **Шаги выполнения**:
  - [ ] Запись в docs/changelog.md
  - [ ] Обновить docs/tasktracker.md
- **Зависимости**: Задачи 1-4

---

## Порядок выполнения

```
Задача 1 (бэкенд: upload-page)    ████████████  готово
Задача 2 (фронт: polling)          ████████████  готово
Задача 3 (фронт: маппинг)          ░░░░░░████░░  ~2-3 часа
Задача 4 (фронт: init)             ░░░░░░░░░░██  ~1 час
Задача 5 (docs)                     ░░░░░░░░░░░█  ~15 мин
                                    ────────────────
                                    Итого: ~1 день
```

**Критический путь**: 1 → 2 → 3 → 4 → 5 (строго последовательно)
