# Design: Модалка «Политика конфиденциальности»

**Дата:** 2026-04-14  
**Ветка:** feature/calculator-config  
**Статус:** Approved

---

## Цель

Добавить модалку с текстом политики конфиденциальности, открываемую из двух точек лендинга: футер и форма заказа (`EmailModal`).

---

## Новые файлы

### `frontend/src/constants/privacyPolicyText.ts`
- Экспортирует единственную константу `PRIVACY_POLICY_HTML: string`
- Текст в формате HTML: `<h2>`, `<h3>`, `<p>`, `<ul>/<li>`
- Пользователь предоставит текст

### `frontend/src/components/PrivacyPolicyModal.tsx`
**Props:**
```ts
interface PrivacyPolicyModalProps {
  isOpen: boolean;
  onClose: () => void;
}
```

**Поведение:**
- `if (!isOpen) return null` — не монтируется при закрытии
- Оверлей: `fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50`
- Клик по оверлею → `onClose()`; клик внутри контейнера → `e.stopPropagation()`
- `useEffect`: при открытии устанавливает `document.body.style.overflow = 'hidden'`, при закрытии/размонтировании сбрасывает
- `useEffect`: слушает `keydown` (Escape) → `onClose()`

**Разметка:**
```
<div overlay onClick={onClose}>
  <div container onClick={stopPropagation}
       max-w-3xl max-h-[85vh] overflow-y-auto bg-white rounded-lg>
    <header flex justify-between>
      <h2>Политика конфиденциальности</h2>
      <button X onClick={onClose} />
    </header>
    <div className="prose-content" dangerouslySetInnerHTML={PRIVACY_POLICY_HTML} />
  </div>
</div>
```

**Tailwind для prose-content (inline стили через className на враппере):**
- `[&_h2]:text-lg [&_h2]:font-bold [&_h2]:text-[#263238] [&_h2]:mt-6 [&_h2]:mb-3`
- `[&_h3]:font-semibold [&_h3]:text-[#263238] [&_h3]:mt-4 [&_h3]:mb-2`
- `[&_p]:text-gray-700 [&_p]:mb-3 [&_p]:leading-relaxed`
- `[&_ul]:list-disc [&_ul]:pl-6 [&_ul]:mb-3 [&_li]:text-gray-700 [&_li]:mb-1`

---

## Изменяемые файлы

### `frontend/src/components/Footer.tsx`
- Добавить `import { useState } from 'react'`
- Добавить `import PrivacyPolicyModal from './PrivacyPolicyModal'`
- `const [isPrivacyOpen, setIsPrivacyOpen] = useState(false)`
- Ссылка «Политика конфиденциальности»: `onClick={(e) => { e.preventDefault(); setIsPrivacyOpen(true); }}`
- Добавить в JSX: `<PrivacyPolicyModal isOpen={isPrivacyOpen} onClose={() => setIsPrivacyOpen(false)} />`

### `frontend/src/components/EmailModal.tsx`
- Добавить `import PrivacyPolicyModal from './PrivacyPolicyModal'`
- Добавить локальный `useState`: `const [isPrivacyOpen, setIsPrivacyOpen] = useState(false)`
- Строку «Нажимая на кнопку, вы соглашаетесь с нашей политикой конфиденциальности» изменить:
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
- Добавить в JSX рядом с оверлеем: `<PrivacyPolicyModal isOpen={isPrivacyOpen} onClose={() => setIsPrivacyOpen(false)} />`

---

## Управление состоянием

**Вариант A (выбранный):** локальное состояние в каждом компоненте.
- `Footer` и `EmailModal` независимо управляют `isPrivacyOpen`
- Не требует изменений в `App.tsx`
- При открытии из `EmailModal` — обе модалки открыты одновременно (разные z-index не нужны, т.к. `PrivacyPolicyModal` рендерится внутри DOM `EmailModal`, но оверлей фиксированный — визуально корректно)

---

## Ожидаемые результаты

| Действие | Результат |
|----------|-----------|
| Клик «Политика конфиденциальности» в футере | Открывается модалка |
| Клик «политикой конфиденциальности» в форме заказа | Модалка открывается поверх формы, форма остаётся открытой |
| Клик по оверлею | Закрытие модалки |
| Нажатие Escape | Закрытие модалки |
| Клик X в шапке | Закрытие модалки |
| Открытие модалки | Скролл body заблокирован |
| Закрытие модалки | Скролл body восстановлен |
