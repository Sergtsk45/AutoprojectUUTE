# Privacy Policy Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить прокручиваемую модалку «Политика конфиденциальности», открываемую из футера и из формы заказа (EmailModal).

**Architecture:** Локальное состояние `isPrivacyOpen` в каждом компоненте-потребителе (Footer, EmailModal). Текст политики хранится в отдельном файле-константе как HTML-строка и вставляется через `dangerouslySetInnerHTML`. Модалка монтируется/размонтируется через `if (!isOpen) return null`.

**Tech Stack:** React 18, TypeScript, Tailwind CSS (Tailwind arbitrary variant selectors `[&_tag]:class`), Vite.

---

## File Map

| Действие | Файл | Роль |
|----------|------|------|
| Create | `frontend/src/constants/privacyPolicyText.ts` | HTML-текст политики как константа |
| Create | `frontend/src/components/PrivacyPolicyModal.tsx` | Компонент модалки |
| Modify | `frontend/src/components/Footer.tsx` | Добавить trigger + рендер модалки |
| Modify | `frontend/src/components/EmailModal.tsx` | Добавить ссылку-trigger + рендер модалки |

---

### Task 1: Создать файл с текстом политики конфиденциальности

**Files:**
- Create: `frontend/src/constants/privacyPolicyText.ts`

- [ ] **Step 1: Создать файл-константу с placeholder-текстом**

Создать файл `frontend/src/constants/privacyPolicyText.ts` со следующим содержимым:

```typescript
export const PRIVACY_POLICY_HTML: string = `
<h2>Политика конфиденциальности</h2>
<p>Дата вступления в силу: 01 января 2025 года</p>

<h3>1. Общие положения</h3>
<p>Настоящая Политика конфиденциальности определяет порядок обработки и защиты персональных данных пользователей сервиса УУТЭ Проект (далее — Сервис), расположенного по адресу constructproject.ru.</p>
<p>Используя Сервис, вы соглашаетесь с условиями настоящей Политики конфиденциальности.</p>

<h3>2. Какие данные мы собираем</h3>
<p>В процессе использования Сервиса мы можем собирать следующие персональные данные:</p>
<ul>
  <li>Имя и фамилия</li>
  <li>Адрес электронной почты</li>
  <li>Номер телефона</li>
  <li>Адрес объекта</li>
  <li>Наименование организации</li>
</ul>

<h3>3. Цели обработки данных</h3>
<p>Собранные данные используются исключительно для:</p>
<ul>
  <li>Обработки заявок на разработку проектной документации</li>
  <li>Связи с клиентом по вопросам выполнения заказа</li>
  <li>Отправки уведомлений о статусе заявки</li>
  <li>Направления образцов проектной документации</li>
</ul>

<h3>4. Основание для обработки</h3>
<p>Обработка персональных данных осуществляется на основании согласия субъекта персональных данных (статья 6, пункт 1 Федерального закона № 152-ФЗ «О персональных данных»).</p>

<h3>5. Передача данных третьим лицам</h3>
<p>Мы не передаём ваши персональные данные третьим лицам, за исключением случаев, предусмотренных действующим законодательством Российской Федерации.</p>

<h3>6. Хранение данных</h3>
<p>Персональные данные хранятся на защищённых серверах в течение срока, необходимого для выполнения заказа, но не более 3 лет с момента последнего обращения.</p>

<h3>7. Права пользователя</h3>
<p>Вы вправе в любое время:</p>
<ul>
  <li>Запросить информацию об обрабатываемых персональных данных</li>
  <li>Потребовать исправления или удаления ваших данных</li>
  <li>Отозвать согласие на обработку персональных данных</li>
</ul>
<p>Для реализации своих прав направьте запрос на электронный адрес: info@constructproject.ru</p>

<h3>8. Безопасность данных</h3>
<p>Мы принимаем технические и организационные меры для защиты ваших данных от несанкционированного доступа, изменения, раскрытия или уничтожения.</p>

<h3>9. Изменения политики</h3>
<p>Мы оставляем за собой право вносить изменения в настоящую Политику конфиденциальности. Актуальная версия всегда доступна на сайте constructproject.ru.</p>

<h3>10. Контакты</h3>
<p>По вопросам, связанным с обработкой персональных данных, обращайтесь:</p>
<ul>
  <li>Email: info@constructproject.ru</li>
</ul>
`;
```

> **Важно:** После выполнения задачи пользователь заменит этот placeholder-текст на свой готовый текст политики. Структура файла (экспорт `PRIVACY_POLICY_HTML`) должна остаться неизменной.

- [ ] **Step 2: Убедиться, что файл создан**

```bash
ls frontend/src/constants/
```
Ожидаемый вывод: в списке есть `privacyPolicyText.ts` и `siteLegal.ts`.

- [ ] **Step 3: Закоммитить**

```bash
git add frontend/src/constants/privacyPolicyText.ts
git commit -m "feat(privacy): add privacy policy HTML constant"
```

---

### Task 2: Создать компонент PrivacyPolicyModal

**Files:**
- Create: `frontend/src/components/PrivacyPolicyModal.tsx`

- [ ] **Step 1: Создать компонент**

Создать файл `frontend/src/components/PrivacyPolicyModal.tsx`:

```tsx
import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { PRIVACY_POLICY_HTML } from '../constants/privacyPolicyText';

interface PrivacyPolicyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const PrivacyPolicyModal: React.FC<PrivacyPolicyModalProps> = ({ isOpen, onClose }) => {
  useEffect(() => {
    if (!isOpen) return;

    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg w-full max-w-3xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 shrink-0">
          <h2 className="text-xl font-bold text-[#263238]">Политика конфиденциальности</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors"
            aria-label="Закрыть"
          >
            <X size={24} />
          </button>
        </div>

        <div
          className="overflow-y-auto px-6 py-4
            [&_h2]:text-lg [&_h2]:font-bold [&_h2]:text-[#263238] [&_h2]:mt-6 [&_h2]:mb-3
            [&_h3]:font-semibold [&_h3]:text-[#263238] [&_h3]:mt-5 [&_h3]:mb-2
            [&_p]:text-gray-700 [&_p]:mb-3 [&_p]:leading-relaxed
            [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:mb-3
            [&_li]:text-gray-700 [&_li]:mb-1"
          dangerouslySetInnerHTML={{ __html: PRIVACY_POLICY_HTML }}
        />
      </div>
    </div>
  );
};

export default PrivacyPolicyModal;
```

- [ ] **Step 2: Проверить TypeScript-компиляцию**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```
Ожидаемый вывод: нет ошибок.

- [ ] **Step 3: Закоммитить**

```bash
git add frontend/src/components/PrivacyPolicyModal.tsx
git commit -m "feat(privacy): add PrivacyPolicyModal component"
```

---

### Task 3: Обновить Footer.tsx

**Files:**
- Modify: `frontend/src/components/Footer.tsx`

- [ ] **Step 1: Добавить импорты и состояние**

Открыть `frontend/src/components/Footer.tsx`.

Строку:
```tsx
import React from 'react';
```
Заменить на:
```tsx
import React, { useState } from 'react';
import PrivacyPolicyModal from './PrivacyPolicyModal';
```

- [ ] **Step 2: Добавить useState в тело компонента**

Сразу после строки `const Footer: React.FC = () => {` добавить:
```tsx
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false);
```

- [ ] **Step 3: Обновить ссылку «Политика конфиденциальности»**

Найти:
```tsx
<a href="#" className="text-gray-300 hover:text-[#E53935] transition-colors mr-6">
  Политика конфиденциальности
</a>
```
Заменить на:
```tsx
<a
  href="#"
  onClick={(e) => { e.preventDefault(); setIsPrivacyOpen(true); }}
  className="text-gray-300 hover:text-[#E53935] transition-colors mr-6 cursor-pointer"
>
  Политика конфиденциальности
</a>
```

- [ ] **Step 4: Добавить рендер модалки перед закрывающим тегом `</footer>`**

Найти закрывающий тег `</footer>` и добавить перед ним:
```tsx
      <PrivacyPolicyModal isOpen={isPrivacyOpen} onClose={() => setIsPrivacyOpen(false)} />
```

- [ ] **Step 5: Проверить TypeScript-компиляцию**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```
Ожидаемый вывод: нет ошибок.

- [ ] **Step 6: Запустить dev-сервер и проверить вручную**

```bash
cd frontend && npm run dev
```

Проверить:
1. Открыть `http://localhost:5173`
2. Прокрутить до футера
3. Кликнуть «Политика конфиденциальности» — должна открыться модалка с текстом
4. Проверить закрытие по X, по оверлею, по Escape
5. Проверить, что при открытой модалке страница не прокручивается

- [ ] **Step 7: Закоммитить**

```bash
git add frontend/src/components/Footer.tsx
git commit -m "feat(privacy): wire privacy modal into Footer"
```

---

### Task 4: Обновить EmailModal.tsx

**Files:**
- Modify: `frontend/src/components/EmailModal.tsx`

- [ ] **Step 1: Добавить импорт PrivacyPolicyModal**

Найти в `frontend/src/components/EmailModal.tsx`:
```tsx
import { X } from 'lucide-react';
```
Добавить строку после:
```tsx
import PrivacyPolicyModal from './PrivacyPolicyModal';
```

- [ ] **Step 2: Добавить состояние isPrivacyOpen**

Найти блок существующих `useState`:
```tsx
  const [email, setEmail] = useState('');
```
Перед ним добавить:
```tsx
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false);
```

- [ ] **Step 3: Заменить текст политики на ссылку**

Найти:
```tsx
              <p className="mt-4 text-xs text-gray-500">
                Нажимая на кнопку, вы соглашаетесь с нашей политикой конфиденциальности
              </p>
```
Заменить на:
```tsx
              <p className="mt-4 text-xs text-gray-500">
                Нажимая на кнопку, вы соглашаетесь с нашей{' '}
                <button
                  type="button"
                  onClick={() => setIsPrivacyOpen(true)}
                  className="underline hover:text-[#E53935] transition-colors"
                >
                  политикой конфиденциальности
                </button>
              </p>
```

- [ ] **Step 4: Добавить рендер PrivacyPolicyModal**

Найти закрывающий тег оверлея EmailModal (последний `</div>` перед закрывающим тегом компонента):
```tsx
    </div>
  );
};

export default EmailModal;
```
Добавить модалку перед `);`:
```tsx
      <PrivacyPolicyModal isOpen={isPrivacyOpen} onClose={() => setIsPrivacyOpen(false)} />
    </div>
  );
};

export default EmailModal;
```

> **Примечание:** `PrivacyPolicyModal` имеет `fixed inset-0 z-50`, поэтому визуально она корректно отобразится поверх EmailModal независимо от места в DOM.

- [ ] **Step 5: Проверить TypeScript-компиляцию**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```
Ожидаемый вывод: нет ошибок.

- [ ] **Step 6: Проверить вручную**

1. Открыть форму заказа (кнопка «Заказать проект» или аналог)
2. Кликнуть «политикой конфиденциальности» в тексте под кнопкой
3. Убедиться, что модалка открылась **поверх** формы заказа (форма видна под оверлеем)
4. Закрыть модалку — форма заказа должна остаться открытой
5. Проверить закрытие по X, оверлею, Escape

- [ ] **Step 7: Закоммитить**

```bash
git add frontend/src/components/EmailModal.tsx
git commit -m "feat(privacy): add privacy policy link in EmailModal"
```

---

### Task 5: Обновить текст политики

**Files:**
- Modify: `frontend/src/constants/privacyPolicyText.ts`

- [ ] **Step 1: Заменить placeholder на реальный текст**

Пользователь предоставляет готовый текст политики. Открыть `frontend/src/constants/privacyPolicyText.ts` и заменить содержимое шаблонного текста внутри backtick-строки на реальный HTML-текст.

Структура файла должна остаться:
```typescript
export const PRIVACY_POLICY_HTML: string = `
  <!-- реальный текст политики -->
`;
```

- [ ] **Step 2: Проверить отображение**

Запустить `npm run dev`, открыть модалку из футера, убедиться, что текст корректно отображается с правильным форматированием (заголовки, параграфы, списки).

- [ ] **Step 3: Собрать production-сборку**

```bash
cd frontend && npm run build 2>&1 | tail -10
```
Ожидаемый вывод: сборка завершается без ошибок, файлы в `dist/`.

- [ ] **Step 4: Закоммитить**

```bash
git add frontend/src/constants/privacyPolicyText.ts
git commit -m "feat(privacy): insert real privacy policy text"
```

---

## После всех задач

Обновить `docs/changelog.md` и `docs/tasktracker.md`.
