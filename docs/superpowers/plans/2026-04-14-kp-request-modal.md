# KP Request Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a modal form to Step 2 ("Запросить КП") in ProcessSection that collects 5 required fields (organization, name, phone, email, TU file) and sends an email notification to the admin without creating an order in the DB.

**Architecture:** New `KpRequestModal.tsx` component + `sendKpRequest` in `api.ts` → `POST /api/v1/landing/kp-request` (multipart/form-data) → `send_kp_request_notification` in `email_service.py` sends email to admin with TU file attached.

**Tech Stack:** React 18 + TypeScript + Tailwind CSS (frontend); FastAPI + smtplib + MIMEApplication (backend)

---

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| **Create** | `frontend/src/components/KpRequestModal.tsx` | Modal component with 5 required fields |
| **Modify** | `frontend/src/api.ts` | Add `sendKpRequest(formData: FormData)` |
| **Modify** | `frontend/src/components/ProcessSection.tsx` | Wire modal, replace `<a>` with `<button>` in Step 2 |
| **Modify** | `backend/app/api/landing.py` | Add `POST /kp-request` endpoint |
| **Modify** | `backend/app/services/email_service.py` | Add `send_kp_request_notification` |

---

## Task 1: Backend — добавить `send_kp_request_notification` в email_service.py

**Files:**
- Modify: `backend/app/services/email_service.py` (append after `send_partnership_request`)

- [ ] **Step 1: Добавить функцию в конец `email_service.py`**

Добавить после строки 532 (конец `send_partnership_request`), перед `def send_survey_reminder`:

```python
def send_kp_request_notification(
    organization: str,
    responsible_name: str,
    phone: str,
    email: str,
    tu_filename: str,
    tu_bytes: bytes,
) -> bool:
    """Переслать запрос КП инженеру с файлом ТУ во вложении."""
    html_body = (
        "<html><body style='font-family:sans-serif'>"
        "<h2 style='color:#263238'>Запрос коммерческого предложения</h2>"
        f"<p><b>Организация:</b> {organization}</p>"
        f"<p><b>ФИО ответственного:</b> {responsible_name}</p>"
        f"<p><b>Телефон:</b> {phone}</p>"
        f"<p><b>Email:</b> {email}</p>"
        "<p>Технические условия приложены к письму.</p>"
        "</body></html>"
    )
    subject = f"Запрос КП — {organization}"

    msg = MIMEMultipart("mixed")
    msg["From"] = formataddr((settings.smtp_from_name, settings.smtp_from))
    msg["To"] = settings.admin_email
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    part = MIMEApplication(tu_bytes, Name=tu_filename)
    part.add_header("Content-Disposition", "attachment", filename=tu_filename)
    msg.attach(part)

    try:
        if settings.smtp_use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, context=context, timeout=30
            ) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=30
            ) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        logger.info("Запрос КП отправлен инженеру: %s", organization)
        return True
    except Exception as e:
        logger.error("Ошибка отправки запроса КП: %s", e, exc_info=True)
        return False
```

- [ ] **Step 2: Проверить синтаксис**

```bash
cd backend && python -c "from app.services.email_service import send_kp_request_notification; print('OK')"
```

Ожидается: `OK`

- [ ] **Step 3: Коммит**

```bash
git add backend/app/services/email_service.py
git commit -m "feat(email): add send_kp_request_notification with file attachment"
```

---

## Task 2: Backend — endpoint `POST /landing/kp-request`

**Files:**
- Modify: `backend/app/api/landing.py` (добавить после эндпоинта `/partnership`)

- [ ] **Step 1: Добавить Pydantic-схему в раздел `# ── Schemas ──`**

После класса `PartnershipRequest` (строка ~63) добавить:

```python
class KpRequest(BaseModel):
    organization: str = Field(..., min_length=2, max_length=255)
    responsible_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=5, max_length=50)
    email: EmailStr
```

- [ ] **Step 2: Добавить `Form` в импорты FastAPI**

Строка 8 сейчас:
```python
from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
```

Заменить на:
```python
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
```

- [ ] **Step 3: Добавить эндпоинт после `/partnership` (после строки ~156)**

```python
@router.post("/kp-request", response_model=SimpleResponse)
async def kp_request(
    organization: str = Form(..., min_length=2, max_length=255),
    responsible_name: str = Form(..., min_length=2, max_length=255),
    phone: str = Form(..., min_length=5, max_length=50),
    email: str = Form(...),
    tu_file: UploadFile = File(...),
):
    """Сценарий D: Запрос коммерческого предложения.

    Принимает контактные данные и файл ТУ, отправляет письмо инженеру.
    Заявка в БД не создаётся.
    """
    from app.services.email_service import send_kp_request_notification

    tu_bytes = await tu_file.read()
    tu_filename = tu_file.filename or "tu.pdf"

    send_kp_request_notification(
        organization=organization,
        responsible_name=responsible_name,
        phone=phone,
        email=email,
        tu_filename=tu_filename,
        tu_bytes=tu_bytes,
    )

    return SimpleResponse(
        success=True,
        message="Запрос КП принят. Мы свяжемся с вами в ближайшее время.",
    )
```

- [ ] **Step 4: Проверить синтаксис**

```bash
cd backend && python -c "from app.api.landing import router; print('OK')"
```

Ожидается: `OK`

- [ ] **Step 5: Проверить через curl (нужен запущенный бэкенд)**

```bash
curl -s -X POST http://localhost:8000/api/v1/landing/kp-request \
  -F "organization=ООО Тест" \
  -F "responsible_name=Иванов Иван Иванович" \
  -F "phone=+79001234567" \
  -F "email=test@example.com" \
  -F "tu_file=@/tmp/test.txt" | python3 -m json.tool
```

Ожидается: `{"success": true, "message": "Запрос КП принят..."}`

- [ ] **Step 6: Коммит**

```bash
git add backend/app/api/landing.py
git commit -m "feat(api): add POST /landing/kp-request endpoint"
```

---

## Task 3: Frontend — добавить `sendKpRequest` в `api.ts`

**Files:**
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: Добавить функцию в конец `api.ts`**

```typescript
export async function sendKpRequest(formData: FormData): Promise<SimpleResponse> {
  const resp = await fetch(`${API_BASE}/landing/kp-request`, {
    method: 'POST',
    body: formData,
    // Content-Type не указываем — браузер сам ставит multipart/form-data с boundary
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Ошибка сервера' }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}
```

- [ ] **Step 2: Коммит**

```bash
git add frontend/src/api.ts
git commit -m "feat(frontend): add sendKpRequest api function"
```

---

## Task 4: Frontend — создать `KpRequestModal.tsx`

**Files:**
- Create: `frontend/src/components/KpRequestModal.tsx`

- [ ] **Step 1: Создать файл**

```tsx
import React, { useState } from 'react';
import { X } from 'lucide-react';
import { sendKpRequest } from '../api';

interface KpRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const KpRequestModal: React.FC<KpRequestModalProps> = ({ isOpen, onClose }) => {
  const [organization, setOrganization] = useState('');
  const [responsibleName, setResponsibleName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [tuFile, setTuFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleClose = () => {
    setOrganization('');
    setResponsibleName('');
    setPhone('');
    setEmail('');
    setTuFile(null);
    setIsSubmitting(false);
    setIsSubmitted(false);
    setError('');
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tuFile) return;
    setIsSubmitting(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('organization', organization);
      formData.append('responsible_name', responsibleName);
      formData.append('phone', phone);
      formData.append('email', email);
      formData.append('tu_file', tuFile);
      await sendKpRequest(formData);
      setIsSubmitted(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка. Попробуйте позже.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4 relative max-h-[90vh] overflow-y-auto">
        <button
          onClick={handleClose}
          className="absolute top-3 right-3 text-gray-500 hover:text-gray-700"
        >
          <X size={24} />
        </button>

        {!isSubmitted ? (
          <>
            <h3 className="text-xl font-bold mb-4 text-[#263238]">
              Запросить коммерческое предложение
            </h3>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="kp-organization" className="block text-sm font-medium text-gray-700 mb-1">
                  Наименование организации *
                </label>
                <input
                  type="text"
                  id="kp-organization"
                  value={organization}
                  onChange={(e) => setOrganization(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                  required
                />
              </div>

              <div className="mb-4">
                <label htmlFor="kp-responsible-name" className="block text-sm font-medium text-gray-700 mb-1">
                  ФИО ответственного сотрудника *
                </label>
                <input
                  type="text"
                  id="kp-responsible-name"
                  value={responsibleName}
                  onChange={(e) => setResponsibleName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                  required
                />
              </div>

              <div className="mb-4">
                <label htmlFor="kp-phone" className="block text-sm font-medium text-gray-700 mb-1">
                  Телефон *
                </label>
                <input
                  type="tel"
                  id="kp-phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                  required
                />
              </div>

              <div className="mb-4">
                <label htmlFor="kp-email" className="block text-sm font-medium text-gray-700 mb-1">
                  Эл. почта *
                </label>
                <input
                  type="email"
                  id="kp-email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                  required
                />
              </div>

              <div className="mb-4">
                <label htmlFor="kp-tu-file" className="block text-sm font-medium text-gray-700 mb-1">
                  Техусловия на установку УУТЭ *
                </label>
                <input
                  type="file"
                  id="kp-tu-file"
                  accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                  onChange={(e) => setTuFile(e.target.files?.[0] ?? null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935] text-sm"
                  required
                />
              </div>

              <div className="mt-6">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-[#E53935] hover:bg-red-700 text-white font-medium py-2 px-4 rounded-md transition-colors disabled:bg-red-300"
                >
                  {isSubmitting ? 'Отправка...' : 'Запросить КП'}
                </button>
              </div>

              <p className="mt-4 text-xs text-gray-500">
                Нажимая на кнопку, вы соглашаетесь с нашей политикой конфиденциальности
              </p>
            </form>
          </>
        ) : (
          <div className="text-center py-8">
            <div className="text-[#E53935] text-5xl mb-4">✓</div>
            <h3 className="text-xl font-bold mb-2 text-[#263238]">Спасибо!</h3>
            <p className="text-gray-600 mb-6">
              Ваш запрос принят. Мы свяжемся с вами в ближайшее время.
            </p>
            <button
              onClick={handleClose}
              className="bg-gray-200 hover:bg-gray-300 text-[#263238] font-medium py-2 px-4 rounded-md transition-colors"
            >
              Закрыть
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default KpRequestModal;
```

- [ ] **Step 2: Коммит**

```bash
git add frontend/src/components/KpRequestModal.tsx
git commit -m "feat(frontend): add KpRequestModal component"
```

---

## Task 5: Frontend — подключить модал в `ProcessSection.tsx`

**Files:**
- Modify: `frontend/src/components/ProcessSection.tsx`

- [ ] **Step 1: Добавить импорты**

Заменить строку 1:
```tsx
import React from 'react';
```
На:
```tsx
import React, { useState } from 'react';
```

После строки `import { FileText, Clock3, FileCheck } from 'lucide-react';` добавить:
```tsx
import KpRequestModal from './KpRequestModal';
```

- [ ] **Step 2: Добавить состояние модала в компонент**

Заменить строку:
```tsx
const ProcessSection: React.FC = () => {
```
На:
```tsx
const ProcessSection: React.FC = () => {
  const [kpModalOpen, setKpModalOpen] = useState(false);
```

- [ ] **Step 3: Изменить action шага 2**

Найти блок шага 2 в массиве `steps` (там где `title: 'Шаг 2'`) и заменить `action`:
```tsx
    {
      icon: <Clock3 size={48} className="text-[#E53935]" />,
      title: 'Шаг 2',
      description: 'Получите коммерческое предложение за 15 минут',
      action: {
        text: 'Запросить КП',
        link: '#calculator'
      }
    },
```
На:
```tsx
    {
      icon: <Clock3 size={48} className="text-[#E53935]" />,
      title: 'Шаг 2',
      description: 'Получите коммерческое предложение за 15 минут',
      action: {
        text: 'Запросить КП',
        link: '#'
      }
    },
```

- [ ] **Step 4: Заменить рендер ссылки шага 2 на кнопку**

Текущий код рендерит все шаги одинаково через `<a href={step.action.link}>`. Нужно добавить условие для шага 2 (index === 1).

Найти блок рендера ссылки (строки ~84-90):
```tsx
              <a 
                href={step.action.link}
                {...(step.action.download ? { download: step.action.download } : {})}
                className="inline-block text-[#E53935] font-medium hover:text-red-700 transition-colors"
              >
                {step.action.text}
              </a>
```

Заменить на:
```tsx
              {index === 1 ? (
                <button
                  onClick={() => setKpModalOpen(true)}
                  className="inline-block text-[#E53935] font-medium hover:text-red-700 transition-colors"
                >
                  {step.action.text}
                </button>
              ) : (
                <a
                  href={step.action.link}
                  {...(step.action.download ? { download: step.action.download } : {})}
                  className="inline-block text-[#E53935] font-medium hover:text-red-700 transition-colors"
                >
                  {step.action.text}
                </a>
              )}
```

- [ ] **Step 5: Добавить рендер модала перед закрывающим тегом `</section>`**

Найти строку `    </section>` (в самом конце return) и перед ней добавить:
```tsx
        <KpRequestModal isOpen={kpModalOpen} onClose={() => setKpModalOpen(false)} />
```

- [ ] **Step 6: Проверить TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Ожидается: нет ошибок.

- [ ] **Step 7: Коммит**

```bash
git add frontend/src/components/ProcessSection.tsx
git commit -m "feat(frontend): wire KpRequestModal into ProcessSection step 2"
```

---

## Task 6: Сборка и деплой

**Files:** нет новых файлов

- [ ] **Step 1: Собрать фронтенд**

```bash
cd frontend && npm run build
```

Ожидается: `dist/` обновлён без ошибок.

- [ ] **Step 2: Пересобрать и перезапустить backend-контейнер (на сервере)**

```bash
cd ~/uute-project
git pull
cd frontend && npm run build && cd ..
docker compose -f docker-compose.prod.yml up -d --build backend
```

- [ ] **Step 3: Проверить в браузере**

1. Открыть `https://constructproject.ru/#process`
2. Нажать "Запросить КП" в шаге 2 — должно открыться модальное окно с 5 полями
3. Попробовать отправить пустую форму — браузер должен показать ошибку валидации на первом незаполненном поле
4. Заполнить все поля, прикрепить PDF, нажать "Запросить КП"
5. Убедиться, что появляется экран с галочкой "Спасибо!"
6. Проверить почту администратора — должно прийти письмо с темой "Запрос КП — {организация}" и файлом во вложении

- [ ] **Step 4: Обновить docs/changelog.md**

Добавить блок:

```markdown
## [2026-04-14] — Модальное окно "Запросить КП"

### Добавлено
- В [`frontend/src/components/KpRequestModal.tsx`](../frontend/src/components/KpRequestModal.tsx): новый модальный компонент с 5 обязательными полями (организация, ФИО, телефон, email, файл ТУ)
- В [`frontend/src/api.ts`](../frontend/src/api.ts): функция `sendKpRequest` для отправки multipart/form-data
- В [`backend/app/api/landing.py`](../backend/app/api/landing.py): эндпоинт `POST /api/v1/landing/kp-request`
- В [`backend/app/services/email_service.py`](../backend/app/services/email_service.py): функция `send_kp_request_notification` с вложением файла ТУ

### Изменено
- В [`frontend/src/components/ProcessSection.tsx`](../frontend/src/components/ProcessSection.tsx): кнопка "Запросить КП" в шаге 2 теперь открывает модальное окно
```

- [ ] **Step 5: Коммит changelog**

```bash
git add docs/changelog.md
git commit -m "docs(changelog): add KP request modal entry"
```
