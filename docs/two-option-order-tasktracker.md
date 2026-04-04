# Фича: Два варианта заказа (Экспресс / Индивидуальный)

> Клиент выбирает: экспресс-проект на Эско 3Э со скидкой 50% или индивидуальный проект с выбором оборудования за полную цену.

---

## Задача 1: Поле `order_type` в модели Order (бэкенд)
- **Статус**: Завершена
- **Описание**: Добавить поле `order_type` (express / custom) в модель Order, миграцию Alembic, обновить схемы Pydantic. Express = Эско 3Э, скидка 50%. Custom = полная цена, опросный лист.
- **Шаги выполнения**:
  - [x] Добавить `OrderType` enum в `models.py` (`EXPRESS = "express"`, `CUSTOM = "custom"`)
  - [x] Добавить колонку `order_type` в модель `Order` (default=`EXPRESS`)
  - [x] Добавить колонку `survey_data` (JSONB, nullable) в модель `Order` — для данных опросного листа
  - [x] Создать миграцию Alembic: `alembic revision --autogenerate -m "add_order_type_and_survey_data"`
  - [x] Обновить `OrderCreate` — добавить `order_type: str | None`
  - [x] Обновить `OrderResponse` — добавить `order_type`, `survey_data`
  - [x] Обновить `OrderListItem` — добавить `order_type`
- **Зависимости**: нет — это фундамент для всех остальных задач

### Промпт для Cursor (бэкенд)

```
GOAL: Добавить поле order_type (express/custom) и survey_data в модель Order.

CONTEXT:
- Файл моделей: backend/app/models/models.py
- Схемы: backend/app/schemas/schemas.py
- Уже есть enum OrderStatus, FileCategory, EmailType — делать по аналогии
- БД: PostgreSQL, миграции через Alembic

FILES:
- backend/app/models/models.py — добавить OrderType enum и два поля в Order
- backend/app/schemas/schemas.py — обновить OrderCreate, OrderResponse, OrderListItem

TASK:
1. Создать enum OrderType(str, enum.Enum) с EXPRESS = "express", CUSTOM = "custom"
2. В модель Order добавить:
   - order_type = Column(Enum(OrderType), nullable=False, default=OrderType.EXPRESS)
   - survey_data = Column(JSONB, nullable=True, default=None) — данные из опросного листа
3. В OrderCreate добавить: order_type: str | None = Field(None)
4. В OrderResponse добавить: order_type: OrderType, survey_data: dict | None
5. В OrderListItem добавить: order_type: OrderType

EXPECTED RESULT: Модель готова, схемы обновлены. После этого создаём миграцию.

CONSTRAINTS:
- Не менять существующие поля и логику
- Default = EXPRESS чтобы старые заявки не сломались
- Не трогать ALLOWED_TRANSITIONS
```

### Промпт для Claude (VPS)

```
GOAL: Создать и применить миграцию Alembic для order_type и survey_data.

SERVER CONTEXT:
- Проект: ~/uute-project/backend
- Виртуальное окружение: source .venv/bin/activate
- БД: PostgreSQL (docker-compose)

COMMANDS:
cd ~/uute-project/backend
source .venv/bin/activate
alembic revision --autogenerate -m "add_order_type_and_survey_data"
# Проверить сгенерированный файл миграции
cat alembic/versions/*add_order_type*.py
alembic upgrade head

EXPECTED RESULT: В таблице orders появились колонки order_type (enum, default express) и survey_data (jsonb, nullable).

CHECKS:
docker exec -it postgres psql -U uute_user -d uute_db -c "\d orders"
# Убедиться что колонки order_type и survey_data есть
docker exec -it postgres psql -U uute_user -d uute_db -c "SELECT column_name, data_type, column_default FROM information_schema.columns WHERE table_name='orders' AND column_name IN ('order_type','survey_data');"
```

---

## Задача 2: Обновить эндпоинт создания заказа (бэкенд)
- **Статус**: Завершена
- **Описание**: `POST /api/v1/landing/order` должен принимать `order_type` и сохранять в заявке. Для custom-заказа цена = полная, для express = 50%.
- **Шаги выполнения**:
  - [x] В `landing.py` → `OrderRequest` добавить `order_type: str | None = "express"`
  - [x] В `create_order_from_landing` передавать `order_type` при создании Order
  - [x] В `OrderService.create_order` сохранять `order_type` в модель
  - [x] В уведомлении инженеру (`send_new_order_notification`) передавать `order_type`
- **Зависимости**: Задача 1

### Промпт для Cursor (бэкенд)

```
GOAL: Эндпоинт POST /landing/order принимает и сохраняет order_type.

CONTEXT:
- backend/app/api/landing.py — эндпоинт create_order_from_landing
- backend/app/services/order_service.py — метод create_order
- Задача 1 уже выполнена: в модели Order есть order_type и survey_data

FILES:
- backend/app/api/landing.py — добавить order_type в OrderRequest и логику
- backend/app/services/order_service.py — обновить create_order

TASK:
1. В OrderRequest (landing.py) добавить: order_type: str = Field("express", pattern="^(express|custom)$")
2. В create_order_from_landing: передать order.order_type = OrderType(data.order_type) при создании
3. В OrderService.create_order: принять order_type, сохранить в модель
4. В send_new_order_notification добавить параметр order_type для отображения в письме инженеру

EXPECTED RESULT: При создании заявки с order_type="custom" в БД сохраняется custom.

CONSTRAINTS:
- Дефолт = "express" чтобы текущий фронтенд не ломался
- Не ломать существующий флоу sample-request и partnership
```

---

## Задача 3: Две кнопки в калькуляторе (фронтенд)
- **Статус**: Завершена
- **Описание**: Заменить одну кнопку «Заказать проект за X ₽» на две карточки: экспресс (50% скидка, Эско 3Э) и индивидуальный (полная цена, выбор оборудования). Модалка EmailModal получает новый параметр `orderType`.
- **Шаги выполнения**:
  - [x] Перевёрстать нижнюю часть `CalculatorSection.tsx` — две карточки вместо одной кнопки
  - [x] Добавить state `orderType: 'express' | 'custom'`
  - [x] Вычислять `discountPrice = Math.round(price * 0.5)`
  - [x] При клике на карточку — `setOrderType(...)` + `setShowModal(true)`
  - [x] В `EmailModal` передавать `orderType` через props
  - [x] В `EmailModal` при `purpose === 'order'` отправлять `order_type` в API
  - [x] В `api.ts` добавить `order_type` в `OrderRequest` и `createOrder`
- **Зависимости**: Задача 2

### Промпт для Cursor (фронтенд)

```
GOAL: Заменить одну кнопку заказа на два варианта: экспресс (-50%) и индивидуальный.

CONTEXT:
- frontend/src/components/CalculatorSection.tsx — секция калькулятора
- frontend/src/components/EmailModal.tsx — модалка заказа
- frontend/src/api.ts — функция createOrder
- Цены: {1: 22500, 2: 35000, 3: 50000} — это полные цены
- Экспресс = price * 0.5, пояснение «на базе Эско 3Э, 3 дня»
- Индивидуальный = price (полная), пояснение «с выбором оборудования»

FILES:
- frontend/src/components/CalculatorSection.tsx
- frontend/src/components/EmailModal.tsx
- frontend/src/api.ts

TASK:
1. CalculatorSection.tsx: после расчёта цены показать два блока:
   - Блок «Экспресс» — скидка 50%, бейдж «Популярный выбор», подпись «На базе Эско 3Э • 3 рабочих дня», кнопка зелёная
   - Блок «Индивидуальный» — полная цена, подпись «Выбор оборудования • опросный лист», кнопка стандартная
   Каждый блок при клике: setShowModal(true) с соответствующим orderType

2. EmailModal.tsx:
   - Новый prop: orderType?: 'express' | 'custom'
   - При purpose='order': передавать order_type в createOrder()
   - В success-экране для custom показать: «Опросный лист будет доступен после загрузки ТУ»

3. api.ts:
   - Добавить order_type?: string в OrderRequest
   - Передавать в body createOrder

EXPECTED RESULT: Клиент видит два варианта с ценами, выбирает, заполняет форму, заявка создаётся с нужным order_type.

CONSTRAINTS:
- Стилизация: Tailwind, цветовая схема лендинга (#E53935 red, #263238 dark)
- Экспресс-кнопка: bg-green-600 чтобы визуально отличалась
- Responsive: на мобильных карточки стекаются вертикально
- Не ломать флоу «Получить образец» и «Стать партнёром»
```

---

## Задача 4: Веб-форма опросного листа на upload-странице (фронтенд + бэкенд)
- **Статус**: Завершена
- **Описание**: Для custom-заказов на странице `/upload/{order_id}` после загрузки ТУ показать интерактивную форму опросного листа. Данные сохраняются в поле `survey_data` модели Order как JSON.
- **Шаги выполнения**:
  - [x] Бэкенд: добавить `order_type` в ответ `GET /landing/orders/{id}/upload-page` (UploadPageInfo)
  - [x] Бэкенд: новый эндпоинт `POST /landing/orders/{id}/survey` — приём данных опросного листа
  - [x] Фронтенд: в `upload.html` добавить секцию формы опросного листа (скрыта для express)
  - [x] Форма: 6 групп полей (объект, теплоснабжение, нагрузки, трубопроводы, приборы, доп.)
  - [x] Валидация обязательных полей на клиенте (manufacturer обязателен)
  - [x] При сабмите — POST survey_data JSON на сервер
  - [x] Показывать форму только если order_type === 'custom'
- **Зависимости**: Задача 1, Задача 2

### Промпт для Cursor (бэкенд — эндпоинт survey)

```
GOAL: Эндпоинт для приёма данных опросного листа от клиента.

CONTEXT:
- backend/app/api/landing.py — публичные эндпоинты
- Модель Order уже имеет survey_data (JSONB) из Задачи 1
- Опросный лист заполняется клиентом для custom-заказов

FILES:
- backend/app/api/landing.py
- backend/app/schemas/schemas.py — UploadPageInfo

TASK:
1. В UploadPageInfo добавить: order_type: str | None = None
2. В get_upload_page_info: передавать order.order_type.value в ответ
3. Новый эндпоинт POST /landing/orders/{order_id}/survey:
   - Принимает JSON body (произвольная структура — dict)
   - Проверяет что order существует
   - Проверяет что order.order_type == CUSTOM
   - Сохраняет body в order.survey_data
   - Возвращает SimpleResponse(success=True, message="Опросный лист сохранён")
4. Эндпоинт публичный (без X-Admin-Key)

EXPECTED RESULT: POST /landing/orders/{id}/survey с JSON → сохраняется в survey_data.

CONSTRAINTS:
- Не валидировать структуру survey_data жёстко — она может меняться
- Для express-заказов → 400 «Опросный лист не требуется для экспресс-заказа»
```

### Промпт для Cursor (фронтенд — форма в upload.html)

```
GOAL: Добавить интерактивную форму опросного листа УУТЭ в upload.html для custom-заказов.

CONTEXT:
- backend/static/upload.html — страница загрузки файлов
- Переменная orderData содержит order_type из API
- Форма показывается ТОЛЬКО если orderData.order_type === 'custom'
- Данные отправляются POST /api/v1/landing/orders/{ORDER_ID}/survey

FILES:
- backend/static/upload.html

TASK:
Добавить после блока загрузки файлов (#uploadCard) новый блок #surveyCard:

Группа 1 — Объект:
- building_type: select (Жилое / Общественное / Промышленное)
- floors: number input
- construction_year: number input
- heat_supply_source: text input — источник теплоснабжения (котельная, ТЭЦ, ИТП и т.п.)

Группа 2 — Теплоснабжение:
- connection_type: select (Зависимая / Независимая)
- system_type: select (Открытая / Закрытая)
- temp_schedule: select (150/70, 130/70, 95/70)
- pressure_supply: number input (кгс/см²)
- pressure_return: number input (кгс/см²)

Группа 3 — Тепловые нагрузки:
- heat_load_heating: number input (Гкал/ч) — отопление
- heat_load_hw: number input (Гкал/ч) — ГВС
- heat_load_vent: number input (Гкал/ч) — вентиляция
- heat_load_tech: number input (Гкал/ч) — технология (необязательно)

Группа 4 — Трубопроводы:
- pipe_dn_supply: number input (Ду подачи, мм)
- pipe_dn_return: number input (Ду обратки, мм)
- has_mud_separators: select (Да / Нет) — наличие грязевиков
- has_filters: select (Да / Нет) — наличие фильтров

Группа 5 — Приборы учёта (ключевая секция):
- manufacturer: select с options:
  Эско 3Э, Теплоком, Логика (СПТ), Пульсар, Другой
- manufacturer_other: text input (показывать если manufacturer === 'other')
- flow_meter_type: select (Ультразвуковой / Электромагнитный)
- calculator_model: text input (необязательно)
- accuracy_class: select (1 / 2)

Группа 6 — Дополнительно:
- has_pressure_regulator: checkbox
- distance_to_vru: number input (м) — расстояние до ВРУ
- rso_requirements: textarea (необязательно)
- comments: textarea (необязательно)

UI:
- Стилизация в духе существующего upload.html
- Группы с заголовками, визуально разделены
- Кнопка «Сохранить опросный лист» → POST /landing/orders/{ORDER_ID}/survey
- После успешной отправки — зелёный бейдж «Опросный лист заполнен»
- Если order_type !== 'custom' → блок surveyCard скрыт (display: none)

EXPECTED RESULT: Клиент с custom-заказом видит форму, заполняет, данные уходят в survey_data.

CONSTRAINTS:
- Ванильный JS (как весь upload.html), никаких фреймворков
- Не ломать существующую логику загрузки файлов
- Форма между #uploadCard и #completedCard
- Минимальная валидация: manufacturer обязателен, остальное на усмотрение
```

---

## Задача 5: Отображение survey_data в админке
- **Статус**: Завершена
- **Описание**: В карточке заявки в админке показывать данные опросного листа (если есть) — аналогично блоку parsed_params.
- **Шаги выполнения**:
  - [x] В ответ API `/orders/{id}` уже добавлены `order_type` и `survey_data` (Задача 1)
  - [x] В `admin.html` добавить блок отображения survey_data
  - [x] Показывать бейдж order_type в карточке заявки (Экспресс / Индивидуальный)
  - [x] В таблице списка заявок добавить колонку «Тип»
- **Зависимости**: Задача 1, Задача 4

### Промпт для Cursor (фронтенд — админка)

```
GOAL: Показать order_type и survey_data в админке.

CONTEXT:
- backend/static/admin.html — SPA-админка на ванильном JS
- API OrderResponse уже отдаёт order_type и survey_data
- survey_data — произвольный JSON с ключами из опросного листа

FILES:
- backend/static/admin.html

TASK:
1. В таблице заявок (renderOrderRow):
   - Добавить колонку «Тип» после «Статус»
   - express → бейдж зелёный «Экспресс», custom → бейдж фиолетовый «Индивидуальный»

2. В карточке заявки (renderOrder):
   - Рядом со статусом показать бейдж типа заказа
   - Если survey_data не пустой — показать блок «Опросный лист» (между parsed_params и actions)
   - Структура: таблица ключ-значение с человекочитаемыми подписями
   - Маппинг ключей survey_data → русские подписи (manufacturer → «Производитель» и т.д.)

EXPECTED RESULT: Инженер видит тип заказа и данные опросного листа в админке.

CONSTRAINTS:
- Стилизация как у существующего блока parsed_params
- Если survey_data === null → блок не показывать
```

---

## Задача 6: Email-уведомление с ссылкой на опросный лист (бэкенд)
- **Статус**: Завершена
- **Описание**: Для custom-заказов после создания заявки клиент получает email с напоминанием заполнить опросный лист (ссылка на upload-страницу). Новый тип письма `SURVEY_REMINDER`.
- **Шаги выполнения**:
  - [x] Добавить `SURVEY_REMINDER = "survey_reminder"` в EmailType
  - [x] Создать шаблон `templates/emails/survey_reminder.html`
  - [x] В `create_order_from_landing` для custom-заказов отправлять письмо с ссылкой
  - [x] Текст: «Заполните опросный лист для подбора оборудования» + кнопка на /upload/{id}
- **Зависимости**: Задача 1, Задача 2

### Промпт для Cursor (бэкенд)

```
GOAL: Email клиенту с напоминанием заполнить опросный лист (для custom-заказов).

CONTEXT:
- backend/app/models/models.py — enum EmailType
- backend/app/services/email_service.py — функции отправки
- backend/templates/emails/ — Jinja2-шаблоны, base.html есть
- Существующие шаблоны: info_request.html, sample_delivery.html — образцы стиля

FILES:
- backend/app/models/models.py — добавить SURVEY_REMINDER в EmailType
- backend/templates/emails/survey_reminder.html — новый шаблон
- backend/app/services/email_service.py — функция send_survey_reminder
- backend/app/api/landing.py — вызвать при создании custom-заказа

TASK:
1. EmailType += SURVEY_REMINDER = "survey_reminder"
2. Шаблон survey_reminder.html:
   - Наследует base.html
   - Текст: «Вы заказали индивидуальный проект УУТЭ. Для подбора оборудования заполните опросный лист.»
   - Кнопка «Заполнить опросный лист» → {{ upload_url }}
   - Пояснение: «Укажите предпочтительного производителя приборов, параметры трубопроводов и нагрузки»
3. send_survey_reminder(session, order) в email_service.py
4. В landing.py: после создания custom-заказа вызвать send_survey_reminder

EXPECTED RESULT: Клиент custom-заказа получает email со ссылкой на upload-страницу.

CONSTRAINTS:
- Стиль письма как у info_request.html
- Не ломать send_new_order_notification (уведомление инженеру)
```

---

## Задача 7: Обновить changelog и документацию
- **Статус**: Завершена
- **Описание**: Зафиксировать изменения в docs/changelog.md и docs/tasktracker.md.
- **Шаги выполнения**:
  - [x] Добавить запись в changelog.md
  - [x] Обновить tasktracker.md — добавить все задачи этой фичи
  - [x] Обновить docs/project.md если нужно
- **Зависимости**: Задачи 1-6

---

## Порядок выполнения

```
Задача 1 (модель)          ██░░░░░░░░░░░░  ~1 час
Задача 2 (эндпоинт)        ░░██░░░░░░░░░░  ~30 мин
Задача 3 (калькулятор)      ░░░░████░░░░░░  ~2-3 часа
Задача 4 (опросный лист)    ░░░░░░░░██████  ~3-4 часа
Задача 5 (админка)          ░░░░░░░░░░░░██  ~1 час
Задача 6 (email)            ░░░░░░░░░░██░░  ~1 час
Задача 7 (docs)             ░░░░░░░░░░░░░█  ~30 мин
                            ─────────────────
                            Итого: ~1.5-2 дня
```

**Критический путь**: 1 → 2 → 3 (фронт) + 4 (параллельно) → 5 → 6 → 7
