# Object City Field Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить обязательное поле «Город объекта» (`object_city`) в форму заказа на лендинге и распространить его по всей системе: БД, бэкенд, опросный лист, парсер, админ-панель.

**Architecture:** Отдельная колонка `object_city TEXT` в таблице `orders` (nullable для обратной совместимости). Поле обязательно в форме заказа на лендинге, опционально в БД. Парсер ТУ уже извлекает `object.city` — после парсинга, если `order.object_city` пустой, он автоматически заполняется из ТУ. В опросном листе (custom-заказы) город — обязательное поле с предзаполнением из парсера.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), Alembic (миграции), React/TypeScript (frontend EmailModal), Vanilla JS + HTML (upload.html, admin.html).

---

## Файловая карта изменений

| Файл | Действие | Что меняется |
|------|----------|-------------|
| `backend/app/models/models.py` | Modify | Добавить `object_city = Column(Text, nullable=True)` |
| `backend/alembic/versions/` | Create | Миграция ADD COLUMN object_city |
| `backend/app/schemas/schemas.py` | Modify | `object_city: str \| None` в OrderCreate, OrderResponse, OrderListItem |
| `backend/app/services/order_service.py` | Modify | Передавать `object_city` при создании заявки |
| `backend/app/api/landing.py` | Modify | `object_city: str` (обязательное) в OrderRequest; передавать в OrderCreate |
| `backend/app/services/tasks.py` | Modify | После парсинга: если `order.object_city` пустой — взять из `parsed.object.city` |
| `frontend/src/api.ts` | Modify | Добавить `object_city: string` в интерфейс `OrderRequest` |
| `frontend/src/components/EmailModal.tsx` | Modify | Добавить поле «Город объекта *» для `purpose === 'order'` |
| `backend/static/upload.html` | Modify | Поле `s_city` в группе "1. Объект"; PARAM_TO_SURVEY; collectSurveyData; SURVEY_REQUIRED_FIELDS |
| `backend/static/admin.html` | Modify | Столбец «Город» в списке; строка в карточке; строка в таблице сравнения |
| `docs/changelog.md` | Modify | Запись об изменении |
| `docs/tasktracker.md` | Modify | Новая задача |

---

## Task 1: Модель БД — добавить object_city

**Files:**
- Modify: `backend/app/models/models.py`

- [ ] **Step 1: Добавить колонку в модель**

В файле `backend/app/models/models.py` после строки с `object_address` (строка 153) добавить:

```python
    # Город объекта
    object_city = Column(Text, nullable=True)
```

Итоговый блок (строки 151–155) должен выглядеть:
```python
    # Контактные данные клиента
    client_name = Column(String(255), nullable=False)
    client_email = Column(String(255), nullable=False, index=True)
    client_phone = Column(String(50), nullable=True)
    client_organization = Column(String(255), nullable=True)

    # Адрес объекта
    object_address = Column(Text, nullable=True)

    # Город объекта
    object_city = Column(Text, nullable=True)
```

- [ ] **Step 2: Создать миграцию Alembic**

Скопировать обновлённый models.py в контейнер:
```bash
docker cp backend/app/models/models.py uute-backend:/app/app/models/models.py
```

Создать миграцию:
```bash
docker exec -e PYTHONPATH=/app uute-backend alembic revision --autogenerate -m "20260411_uute_add_object_city"
```

Ожидаемый вывод: `Generating .../alembic/versions/xxxx_20260411_uute_add_object_city.py`

- [ ] **Step 3: Скопировать миграцию на хост и проверить**

```bash
docker cp uute-backend:/app/alembic/versions/<файл>.py backend/alembic/versions/
```

Открыть файл. Убедиться, что в `upgrade()` есть:
```python
op.add_column('orders', sa.Column('object_city', sa.Text(), nullable=True))
```
А в `downgrade()` есть:
```python
op.drop_column('orders', 'object_city')
```

Если autogenerate не добавил — написать вручную.

- [ ] **Step 4: Применить миграцию**

```bash
docker exec -e PYTHONPATH=/app uute-backend alembic upgrade head
```

Ожидаемый вывод: `Running upgrade ... -> ..., 20260411_uute_add_object_city`

- [ ] **Step 5: Проверить колонку в БД**

```bash
docker exec -it uute-project-postgres-1 psql -U uute -d uute_db -c "\d orders" | grep object_city
```

Ожидаемый вывод: `object_city | text | ...`

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/models.py backend/alembic/versions/
git commit -m "feat(db): add object_city column to orders"
```

---

## Task 2: Схемы Pydantic и сервис создания заявки

**Files:**
- Modify: `backend/app/schemas/schemas.py`
- Modify: `backend/app/services/order_service.py`

- [ ] **Step 1: Обновить OrderCreate в schemas.py**

В классе `OrderCreate` (строки 18–26) добавить поле после `object_address`:

```python
class OrderCreate(BaseModel):
    """Создание заявки — данные из формы на лендинге."""

    client_name: str = Field(..., min_length=2, max_length=255, examples=["Иванов И.И."])
    client_email: EmailStr = Field(..., examples=["ivanov@example.ru"])
    client_phone: str | None = Field(None, max_length=50, examples=["+7 999 123-45-67"])
    client_organization: str | None = Field(None, max_length=255, examples=["ООО Теплосеть"])
    object_address: str | None = Field(None, examples=["г. Москва, ул. Строителей, д. 5"])
    object_city: str | None = Field(None, max_length=255, examples=["Москва"])
    order_type: str | None = Field(None)
```

- [ ] **Step 2: Обновить OrderResponse в schemas.py**

В классе `OrderResponse` (строки 36–61) добавить поле после `object_address`:

```python
    object_address: str | None
    object_city: str | None
    parsed_params: dict | None
```

- [ ] **Step 3: Обновить OrderListItem в schemas.py**

В классе `OrderListItem` (строки 64–76) добавить поле после `object_address`:

```python
    object_address: str | None
    object_city: str | None
    created_at: datetime
```

- [ ] **Step 4: Обновить create_order в order_service.py**

В методе `create_order` (строки 27–41) добавить передачу `object_city`:

```python
    async def create_order(self, data: OrderCreate) -> Order:
        """Создать новую заявку."""
        order = Order(
            client_name=data.client_name,
            client_email=data.client_email,
            client_phone=data.client_phone,
            client_organization=data.client_organization,
            object_address=data.object_address,
            object_city=data.object_city,
            status=OrderStatus.NEW,
            order_type=OrderType(data.order_type) if data.order_type else OrderType.EXPRESS,
        )
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/schemas.py backend/app/services/order_service.py
git commit -m "feat(backend): add object_city to schemas and order_service"
```

---

## Task 3: API лендинга — сделать object_city обязательным

**Files:**
- Modify: `backend/app/api/landing.py`

- [ ] **Step 1: Обновить OrderRequest**

В классе `OrderRequest` (строки 40–48) добавить обязательное поле `object_city`:

```python
class OrderRequest(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=255)
    client_email: EmailStr
    client_phone: str | None = Field(None, max_length=50)
    client_organization: str | None = Field(None, max_length=255)
    object_address: str | None = None
    object_city: str = Field(..., min_length=2, max_length=255)
    circuits: int | None = Field(None, ge=1, le=10)
    price: int | None = None
    order_type: str = Field("express", pattern="^(express|custom)$")
```

- [ ] **Step 2: Передавать object_city при создании заявки**

В эндпоинте `create_order_from_landing` (строки 103–110) добавить `object_city`:

```python
    order_data = OrderCreate(
        client_name=data.client_name,
        client_email=data.client_email,
        client_phone=data.client_phone,
        client_organization=data.client_organization,
        object_address=data.object_address,
        object_city=data.object_city,
        order_type=data.order_type,
    )
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/landing.py
git commit -m "feat(api): make object_city required in landing order creation"
```

---

## Task 4: Парсер — автозаполнение object_city из ТУ

**Files:**
- Modify: `backend/app/services/tasks.py`

- [ ] **Step 1: После парсинга записать city в order.object_city**

В задаче `start_tu_parsing` (файл `backend/app/services/tasks.py`), после строки `order.missing_params = determine_missing_params(parsed)` (строка ~135) добавить блок:

```python
            # Если город ещё не указан клиентом — взять из ТУ
            if not order.object_city and parsed.object.city:
                order.object_city = parsed.object.city
```

Итоговый блок (контекст):
```python
            # Сохраняем в БД
            order.parsed_params = parsed.model_dump(
                exclude={"raw_text"},
                mode="json",
            )
            order.missing_params = determine_missing_params(parsed)

            # Если город ещё не указан клиентом — взять из ТУ
            if not order.object_city and parsed.object.city:
                order.object_city = parsed.object.city

            _transition(session, order, OrderStatus.TU_PARSED)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/tasks.py
git commit -m "feat(parser): populate order.object_city from parsed TU if not set"
```

---

## Task 5: Frontend — TypeScript интерфейс и форма заказа

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/components/EmailModal.tsx`

- [ ] **Step 1: Обновить интерфейс OrderRequest в api.ts**

В интерфейсе `OrderRequest` (строки 3–12) добавить обязательное поле:

```typescript
export interface OrderRequest {
  client_name: string;
  client_email: string;
  client_phone?: string;
  client_organization?: string;
  object_address?: string;
  object_city: string;
  circuits?: number;
  price?: number;
  order_type?: string;
}
```

- [ ] **Step 2: Добавить state `city` в EmailModal.tsx**

Добавить состояние после `const [address, setAddress] = useState('');` (строка 22):

```typescript
  const [city, setCity] = useState('');
```

- [ ] **Step 3: Добавить сброс поля city в handleClose**

В функции `handleClose` добавить `setCity('');` после `setAddress('');`:

```typescript
  const handleClose = () => {
    setEmail('');
    setName('');
    setCompany('');
    setPhone('');
    setAddress('');
    setCity('');
    setIsSubmitted(false);
    setError('');
    setRedirectUrl('');
    onClose();
  };
```

- [ ] **Step 4: Добавить переменную showCityField**

После строки `const showAddressField = purpose === 'order';` (строка 91) добавить:

```typescript
  const showCityField = purpose === 'order';
```

- [ ] **Step 5: Передать city в createOrder**

В `handleSubmit`, в блоке `purpose === 'order'`, обновить вызов `createOrder`:

```typescript
      } else if (purpose === 'order') {
        const result = await createOrder({
          client_name: name,
          client_email: email,
          client_phone: phone || undefined,
          object_address: address || undefined,
          object_city: city,
          circuits: orderDefaults?.circuits,
          price: orderDefaults?.price,
          order_type: orderType ?? 'express',
        });
        setRedirectUrl(`/upload/${result.order_id}`);
```

- [ ] **Step 6: Добавить поле «Город объекта» в форму**

После блока `showAddressField` (после закрывающего `</div>` для адреса, перед `<div className="mt-6">`), добавить блок города:

```tsx
              {showCityField && (
                <div className="mb-4">
                  <label htmlFor="modal-city" className="block text-sm font-medium text-gray-700 mb-1">
                    Город объекта *
                  </label>
                  <input
                    type="text"
                    id="modal-city"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    placeholder="Москва"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                    required
                  />
                </div>
              )}
```

Расположение: между блоком `showAddressField` и `<div className="mt-6">`.

- [ ] **Step 7: Пересобрать фронтенд**

```bash
cd frontend && npm run build
```

Ожидаемый вывод: `✓ built in ...s`

- [ ] **Step 8: Проверить форму вручную**

```bash
# Перезапустить backend чтобы отдал новый dist
docker restart uute-backend
```

Открыть http://localhost:8000 (или dev-сервер `npm run dev`), нажать «Заказать проект» — убедиться что:
- Поле «Город объекта *» отображается после «Адрес объекта»
- Без заполнения города форма не отправляется
- После заполнения и отправки нет ошибок (422 от бэкенда)

- [ ] **Step 9: Commit**

```bash
git add frontend/src/api.ts frontend/src/components/EmailModal.tsx frontend/dist/
git commit -m "feat(frontend): add required object_city field to order form"
```

---

## Task 6: Опросный лист (upload.html) — поле «Город»

**Files:**
- Modify: `backend/static/upload.html`

Все изменения — в одном файле. Выполнять последовательно.

- [ ] **Step 1: Добавить поле s_city в HTML-форму**

В группе "1. Объект" (около строки 670, после блока `s_heat_supply_source`), перед закрывающим `</div>` группы добавить:

```html
            <div class="form-row">
              <label for="s_city">Город объекта <span class="required-star">*</span></label>
              <input type="text" id="s_city" placeholder="Москва">
            </div>
```

Итоговая группа "1. Объект" будет выглядеть:
```html
          <div class="survey-group">
            <div class="survey-group-title">1. Объект</div>
            <div class="form-row">
              <label for="s_building_type">Тип здания <span class="required-star">*</span></label>
              <select id="s_building_type">...</select>
            </div>
            <div class="form-row-inline">
              <div class="form-row">
                <label for="s_floors">Этажность</label>
                <input type="number" id="s_floors" ...>
              </div>
              <div class="form-row">
                <label for="s_construction_year">Год постройки</label>
                <input type="number" id="s_construction_year" ...>
              </div>
            </div>
            <div class="form-row">
              <label for="s_heat_supply_source">Источник теплоснабжения <span class="required-star">*</span></label>
              <input type="text" id="s_heat_supply_source" ...>
            </div>
            <div class="form-row">
              <label for="s_city">Город объекта <span class="required-star">*</span></label>
              <input type="text" id="s_city" placeholder="Москва">
            </div>
          </div>
```

- [ ] **Step 2: Добавить маппинг city в PARAM_TO_SURVEY**

В объекте `PARAM_TO_SURVEY` (около строки 1500) добавить запись:

```javascript
    const PARAM_TO_SURVEY = {
      'heat_loads.total_load': 'heat_load_total',
      // ... существующие ...
      'object.object_type': 'building_type',
      'rso.rso_name': 'heat_supply_source',
      'object.city': 'city',   // ← добавить
    };
```

- [ ] **Step 3: Добавить city в collectSurveyData**

В функции `collectSurveyData` (около строки 1918) добавить `city` в возвращаемый объект после `heat_supply_source`:

```javascript
    function collectSurveyData() {
      const manufacturer = strVal('s_manufacturer');
      return {
        building_type: strVal('s_building_type') || null,
        floors: numVal('s_floors'),
        construction_year: numVal('s_construction_year'),
        heat_supply_source: strVal('s_heat_supply_source') || null,
        city: strVal('s_city') || null,   // ← добавить
        connection_type: strVal('s_connection_type') || null,
        // ... остальное без изменений ...
      };
    }
```

- [ ] **Step 4: Добавить city в SURVEY_REQUIRED_FIELDS**

В массиве `SURVEY_REQUIRED_FIELDS` (около строки 1963) добавить:

```javascript
    const SURVEY_REQUIRED_FIELDS = [
      ['s_building_type',       'str'],
      ['s_heat_supply_source',  'str'],
      ['s_city',                'str'],   // ← добавить после heat_supply_source
      ['s_connection_type',     'str'],
      // ... остальное без изменений ...
    ];
```

- [ ] **Step 5: Проверить вручную**

Открыть upload-страницу любого custom-заказа в браузере (напр. http://localhost:8000/upload/<id>).
Убедиться, что:
- В группе «1. Объект» появилось поле «Город объекта *»
- Если у заявки есть `parsed_params.object.city` — поле предзаполнено с пометкой «из ТУ»
- Без заполнения города нажатие «Сохранить опросный лист» показывает ошибку валидации

- [ ] **Step 6: Commit**

```bash
git add backend/static/upload.html
git commit -m "feat(survey): add required city field to custom order survey form"
```

---

## Task 7: Админ-панель (admin.html) — отображение города

**Files:**
- Modify: `backend/static/admin.html`

- [ ] **Step 1: Добавить заголовок столбца «Город» в таблицу заявок**

В `<thead>` таблицы заявок (около строки 569–578):

```html
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Клиент</th>
                  <th>Email</th>
                  <th>Объект</th>
                  <th>Город</th>
                  <th>Статус</th>
                  <th>Тип заявки</th>
                  <th>Дата</th>
                </tr>
              </thead>
```

- [ ] **Step 2: Добавить ячейку города в renderOrdersTable**

В функции `renderOrdersTable` (около строки 1403–1413) добавить `<td>` с городом после `<td>${esc(o.object_address || '—')}</td>`:

```javascript
      tbody.innerHTML = orders.map(o => `
        <tr onclick="showOrderScreen('${o.id}')">
          <td class="td-id">${o.id.slice(0,8)}</td>
          <td class="td-name">${esc(o.client_name)}</td>
          <td>${esc(o.client_email)}</td>
          <td>${esc(o.object_address || '—')}</td>
          <td>${esc(o.object_city || '—')}</td>
          <td>${statusBadge(o.status)}</td>
          <td>${orderTypeBadge(o.order_type)}</td>
          <td class="td-date">${formatDate(o.created_at)}</td>
        </tr>
      `).join('');
```

- [ ] **Step 3: Добавить поле «Город объекта» в карточку заявки**

В функции `renderOrder` (около строки 1447–1455), в массиве `fields`, добавить «Город объекта» после «Адрес объекта»:

```javascript
      const fields = [
        ['Имя клиента', order.client_name],
        ['Email', order.client_email],
        ['Телефон', order.client_phone || '—'],
        ['Организация', order.client_organization || '—'],
        ['Адрес объекта', order.object_address || '—'],
        ['Город объекта', order.object_city || '—'],
        ['Дата создания', formatDateFull(order.created_at)],
        ['Обновлена', formatDateFull(order.updated_at)],
        ['Повторных запросов', order.retry_count],
      ];
```

- [ ] **Step 4: Добавить «Город» в таблицу сравнения ТУ vs опросный лист**

В функции `renderComparisonTable` (около строки 1210), в блоке секции «Объект» (после строки с «Адрес объекта», около строки 1261), добавить строку города:

```javascript
        cmpRow('Город',           cmpParsedCell(obj.city), cmpSurveyCell('city', survey.city), obj.city, survey.city),
        cmpRow('Тип здания',      cmpParsedCell(null), cmpSurveyCell('building_type', survey.building_type), null, survey.building_type),
```

Добавить перед строкой `cmpRow('Тип здания', ...)`.

- [ ] **Step 5: Проверить вручную**

Открыть http://localhost:8000/admin, убедиться что:
- В таблице заявок появился столбец «Город»
- В карточке заявки отображается «Город объекта»
- В таблице сравнения ТУ vs опросный лист есть строка «Город»

- [ ] **Step 6: Commit**

```bash
git add backend/static/admin.html
git commit -m "feat(admin): show object_city in orders list, card, and comparison table"
```

---

## Task 8: Обновить документацию

**Files:**
- Modify: `docs/changelog.md`
- Modify: `docs/tasktracker.md`

- [ ] **Step 1: Добавить запись в changelog.md**

Добавить в начало `docs/changelog.md`:

```markdown
## [2026-04-11] — Поле «Город объекта»

### Добавлено
- В [`backend/app/models/models.py`](../backend/app/models/models.py): колонка `object_city TEXT` в таблице `orders`
- В [`backend/alembic/versions/`](../backend/alembic/versions/): миграция `20260411_uute_add_object_city`
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): обязательное поле `object_city` в `OrderRequest`
- В [`frontend/src/components/EmailModal.tsx`](../frontend/src/components/EmailModal.tsx): поле «Город объекта *» в форме заказа
- В [`backend/static/upload.html`](../backend/static/upload.html): поле «Город объекта *» в опросном листе (группа «Объект»), предзаполнение из ТУ
- В [`backend/static/admin.html`](../backend/static/admin.html): столбец «Город» в списке заявок, строка в карточке, строка в сравнительной таблице

### Изменено
- В [`backend/app/services/tasks.py`](../backend/app/services/tasks.py): после парсинга ТУ — автозаполнение `order.object_city` из `parsed_params.object.city`
```

- [ ] **Step 2: Добавить задачу в tasktracker.md**

Добавить в начало `docs/tasktracker.md`:

```markdown
## Задача: Поле «Город объекта»
- **Статус**: Завершена
- **Описание**: Добавить обязательное поле «Город объекта» в форму заказа на лендинге и распространить по всей системе: БД, бэкенд, опросный лист, парсер ТУ, AdminPanel
- **Шаги выполнения**:
  - [x] Миграция Alembic: колонка `object_city` в `orders`
  - [x] Backend: схемы, order_service, landing API
  - [x] Парсер: автозаполнение из ТУ
  - [x] Frontend: поле в форме заказа (EmailModal)
  - [x] Опросный лист (upload.html): поле + предзаполнение + валидация
  - [x] Админ-панель (admin.html): список, карточка, сравнительная таблица
```

- [ ] **Step 3: Commit**

```bash
git add docs/changelog.md docs/tasktracker.md
git commit -m "docs: add object_city feature to changelog and tasktracker"
```

---

## Task 9: Production деплой

- [ ] **Step 1: Пересобрать и задеплоить**

```bash
cd ~/uute-project
git pull
cd frontend && npm run build && cd ..
docker compose -f docker-compose.prod.yml up -d --build
```

- [ ] **Step 2: Применить миграцию на проде**

```bash
docker exec -e PYTHONPATH=/app uute-backend alembic upgrade head
```

- [ ] **Step 3: Проверить на проде**

- Открыть https://constructproject.ru, нажать «Заказать проект» — убедиться в наличии поля «Город объекта *»
- Открыть https://constructproject.ru/admin — убедиться в столбце «Город» и строке в карточке
