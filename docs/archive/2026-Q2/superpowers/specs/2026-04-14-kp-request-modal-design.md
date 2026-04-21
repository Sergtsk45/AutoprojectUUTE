# Дизайн: Модальное окно "Запросить КП" (Шаг 2)

**Дата:** 2026-04-14
**Статус:** Утверждён

---

## Цель

Добавить в блок "Процесс работы в 3 шага" (шаг 2 — "Запросить КП") модальное окно для сбора контактных данных и файла технических условий. После отправки — письмо администратору без создания заявки в БД.

---

## Компоненты

### Frontend: `frontend/src/components/KpRequestModal.tsx`

Новый компонент. Стилизация идентична `EmailModal` (overlay `bg-black bg-opacity-50`, белая карточка `max-w-md`, кнопка закрытия, красная кнопка submit).

**Поля формы (все `required`):**

| № | Поле | Тип | HTML-тип |
|---|------|-----|----------|
| 1 | Наименование организации | `organization` | `text` |
| 2 | ФИО ответственного сотрудника | `responsible_name` | `text` |
| 3 | Телефон | `phone` | `tel` |
| 4 | Эл. почта | `email` | `email` |
| 5 | Техусловия на установку УУТЭ | `tu_file` | `file` (accept: `.pdf,.doc,.docx,.jpg,.jpeg,.png`) |

**Состояния компонента:**
- `idle` — форма готова к заполнению
- `submitting` — кнопка задизейблена, текст "Отправка..."
- `success` — экран с галочкой, текст "Спасибо! Мы свяжемся с вами в ближайшее время.", кнопка "Закрыть"
- `error` — красный блок с текстом ошибки над формой

**Props:**
```typescript
interface KpRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
}
```

При закрытии (handleClose) — сброс всех полей и состояний.

---

### Frontend: `frontend/src/api.ts`

Новая функция:
```typescript
export async function sendKpRequest(formData: FormData): Promise<SimpleResponse>
```

Метод: `POST /api/v1/landing/kp-request`
Content-Type: `multipart/form-data` (передаётся браузером автоматически при передаче `FormData`).

---

### Frontend: `frontend/src/components/ProcessSection.tsx`

- Добавить `useState<boolean>` для управления видимостью модала.
- Шаг 2: кнопку-ссылку `<a href="#calculator">Запросить КП</a>` заменить на `<button onClick={() => setKpModalOpen(true)}>Запросить КП</button>` с идентичными стилями.
- Рендерить `<KpRequestModal isOpen={kpModalOpen} onClose={() => setKpModalOpen(false)} />` в конце JSX секции.

---

### Backend: `backend/app/api/landing.py`

Новый эндпоинт:
```
POST /api/v1/landing/kp-request
Content-Type: multipart/form-data
```

**Входные данные (Form + File):**
- `organization: str`
- `responsible_name: str`
- `phone: str`
- `email: str`
- `tu_file: UploadFile`

**Логика:**
1. Прочитать содержимое файла (`await tu_file.read()`)
2. Отправить email на `settings.ADMIN_EMAIL` через существующий `email_service`:
   - Тема: `"Запрос КП — {organization}"`
   - Тело: организация, ФИО, телефон, email клиента
   - Вложение: файл ТУ с оригинальным именем
3. Вернуть `{"success": True, "message": "Запрос отправлен"}`

**Ошибки:** HTTP 500 при сбое отправки письма.

**Защита:** публичный эндпоинт (как `/landing/sample-request`), без авторизации.

---

## Ограничения

- Файл ТУ не сохраняется на диск и не попадает в БД — только во вложение письма.
- Максимальный размер файла — ограничен настройками FastAPI/Caddy (по умолчанию достаточно для ТУ).
- Валидация типа файла — только на уровне `accept` в HTML (серверной валидации типа нет).

---

## Что не входит в скоуп

- Создание заявки (`Order`) в БД
- Перенаправление на страницу загрузки
- Сохранение файла в `UPLOAD_DIR`
