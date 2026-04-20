# Custom Optional Docs + Admin Survey Collapse — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Разрешить клиентам custom-пайплайна отправлять заявку без дополнительных документов (только опросный лист обязателен), показывать UX-подсказку об опциональности документов, и сделать карточку опросного листа сворачиваемой в admin.html.

**Architecture:** Все изменения — только во фронтенд-статике (`upload.html`, `admin.html`). Бэкенд не затрагивается: механизм 24-часовых уведомлений уже реализован в `tasks.py`. Изменения в `syncSubmitButtonState()` убирают проверку загрузки всех документов; новый элемент подсказки показывается когда опрос сохранён но документы не все загружены.

**Tech Stack:** Ванильный JS, HTML, Tailwind-подобные CSS-переменные в `<style>`.

---

## Затрагиваемые файлы

- Modify: `backend/static/upload.html`
  - `syncSubmitButtonState()` (строки ~975–1006): убрать требование всех документов
  - Добавить `<div id="docsOptionalHint">` после кнопки submitBtn (~строка 882)
  - Добавить функцию `showDocsOptionalHint(show)` рядом с `applySurveySavedVisuals`
  - Текст баннера после сохранения опроса (~строка 1974)
  - Вызов `showDocsOptionalHint` при init и после событий загрузки файла

- Modify: `backend/static/admin.html`
  - `renderSurveyData()` (~строки 1094–1120): обернуть секции в `<details open>`

---

### Task 1: Добавить HTML-элемент подсказки в upload.html

**Files:**
- Modify: `backend/static/upload.html` (область кнопки submitBtn, ~строка 882)

- [ ] **Step 1: Найти кнопку submitBtn и добавить подсказку сразу после неё**

Найти блок:
```html
          <button class="btn btn-primary" id="submitBtn" disabled>
            Всё загружено — отправить
          </button>
```
Заменить на:
```html
          <button class="btn btn-primary" id="submitBtn" disabled>
            Всё загружено — отправить
          </button>
          <div id="docsOptionalHint" style="display:none; margin-top:10px; padding:10px 14px; border-radius:8px; background:var(--c-warn-bg); border:1px solid #fde68a; font-size:13px; color:#92400e; line-height:1.5;">
            Вы можете отправить заявку сейчас — инженер свяжется с вами для уточнения деталей.<br>
            Либо дополнительно загрузите документы из списка выше для ускорения обработки.
          </div>
```

- [ ] **Step 2: Убедиться что элемент находится в правильном месте**

Открыть `backend/static/upload.html`, найти `id="docsOptionalHint"` — должен быть сразу после `id="submitBtn"`.

---

### Task 2: Добавить функцию showDocsOptionalHint и обновить syncSubmitButtonState

**Files:**
- Modify: `backend/static/upload.html` (JS-блок, области ~1008–1006)

- [ ] **Step 1: Добавить функцию showDocsOptionalHint рядом с applySurveySavedVisuals**

Найти строку:
```javascript
    function applySurveySavedVisuals(saved) {
```
Перед ней добавить:
```javascript
    function showDocsOptionalHint(show) {
      const el = document.getElementById('docsOptionalHint');
      if (el) el.style.display = show ? 'block' : 'none';
    }

```

- [ ] **Step 2: Обновить syncSubmitButtonState — убрать требование всех документов**

Найти и заменить весь блок `if (customPost)`:

Текущий код:
```javascript
      const customPost =
        orderData &&
        orderData.order_type === 'custom' &&
        CUSTOM_EDITABLE_STATUSES.includes(orderData.order_status);
      if (customPost) {
        if (!surveySavedCustom) {
          $submitBtn.disabled = true;
          $submitBtn.title = 'Сначала сохраните опросный лист внизу страницы';
          return;
        }
        $submitBtn.title = '';
        const mp = orderData.missing_params || [];
        if (mp.length === 0) {
          $submitBtn.disabled = false;
          return;
        }
        const allDone = mp.every(code => uploadedCategories.has(code));
        $submitBtn.disabled = !allDone;
        if (!allDone) {
          $submitBtn.title = 'Загрузите все документы из списка выше';
        }
        return;
      }
```

Заменить на:
```javascript
      const customPost =
        orderData &&
        orderData.order_type === 'custom' &&
        CUSTOM_EDITABLE_STATUSES.includes(orderData.order_status);
      if (customPost) {
        if (!surveySavedCustom) {
          $submitBtn.disabled = true;
          $submitBtn.title = 'Сначала сохраните опросный лист внизу страницы';
          showDocsOptionalHint(false);
          return;
        }
        $submitBtn.disabled = false;
        $submitBtn.title = '';
        const mp = orderData.missing_params || [];
        const allDone = mp.length === 0 || mp.every(code => uploadedCategories.has(code));
        showDocsOptionalHint(!allDone);
        return;
      }
```

- [ ] **Step 3: Добавить showDocsOptionalHint(false) при isNewOrder ветке**

Найти:
```javascript
      if (isNewOrder) {
        $submitBtn.disabled = uploadedCategories.size === 0;
        return;
      }
```
Заменить на:
```javascript
      if (isNewOrder) {
        $submitBtn.disabled = uploadedCategories.size === 0;
        showDocsOptionalHint(false);
        return;
      }
```

- [ ] **Step 4: Добавить showDocsOptionalHint(false) в конце syncSubmitButtonState**

Найти последние строки функции `syncSubmitButtonState`:
```javascript
      $submitBtn.title = '';
      $submitBtn.disabled = uploadedCategories.size === 0;
    }
```
Заменить на:
```javascript
      $submitBtn.title = '';
      $submitBtn.disabled = uploadedCategories.size === 0;
      showDocsOptionalHint(false);
    }
```

---

### Task 3: Обновить текст баннера после сохранения опроса

**Files:**
- Modify: `backend/static/upload.html` (JS-блок, ~строка 1974)

- [ ] **Step 1: Найти и заменить текст баннера**

Найти:
```javascript
        showBanner('success', 'Опросный лист сохранён. Теперь при необходимости догрузите файлы и нажмите «Всё загружено — отправить».', 12000);
```
Заменить на:
```javascript
        showBanner('success', 'Опросный лист сохранён. Вы можете отправить заявку сейчас или дополнительно загрузить документы из списка выше.', 12000);
```

---

### Task 4: Сделать опросный лист в admin.html сворачиваемым

**Files:**
- Modify: `backend/static/admin.html` (функция `renderSurveyData`, ~строки 1094–1120)

- [ ] **Step 1: Найти функцию renderSurveyData и изучить её структуру**

Найти блок формирования HTML секций в `renderSurveyData`. Текущий код строит массив `sections` и собирает итоговый HTML:
```javascript
    function renderSurveyData(survey) {
      const card = document.getElementById('surveyCard');
      const content = document.getElementById('surveyContent');
      if (!survey || typeof survey !== 'object' || Object.keys(survey).length === 0) {
```

- [ ] **Step 2: Обернуть содержимое в details/summary**

Найти место где `content.innerHTML` присваивается — финальный `html` собирается из секций. Заменить присвоение:

Найти полный блок формирования итоговых секций. После массива секций:
```javascript
      const html = sections.length > 0
        ? sections.join('')
        : '<p class="parsed-empty-msg">Опросный лист не заполнен</p>';
```
Заменить на:
```javascript
      const sectionsHtml = sections.length > 0
        ? sections.join('')
        : '<p class="parsed-empty-msg">Опросный лист не заполнен</p>';
      const html = `<details open class="parsed-params-details">
        <summary>Данные опросного листа &#9654;</summary>
        <div class="parsed-details-body">${sectionsHtml}</div>
      </details>`;
```

- [ ] **Step 3: Убедиться что класс parsed-params-details есть в admin.html**

Найти в admin.html:
```
grep -n "parsed-params-details" backend/static/admin.html
```
Ожидается: класс уже объявлен в `<style>` (используется в buildParsedParamsTablesHtml). Если не найден — добавить в `<style>`:
```css
.parsed-params-details { margin-top: 0; }
.parsed-params-details summary { cursor: pointer; font-size: 13px; color: var(--c-text-secondary); user-select: none; }
.parsed-details-body { margin-top: 12px; }
```

---

### Task 5: Коммит

**Files:** все изменённые файлы

- [ ] **Step 1: Проверить diff**

```bash
git diff backend/static/upload.html backend/static/admin.html
```

- [ ] **Step 2: Закоммитить**

```bash
git add backend/static/upload.html backend/static/admin.html
git commit -m "feat(upload,admin): optional docs in custom pipeline, collapsible survey in admin"
```

- [ ] **Step 3: Обновить changelog и tasktracker**

Добавить запись в `docs/changelog.md` и `docs/tasktracker.md`.
