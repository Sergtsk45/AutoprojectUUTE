# Дизайн: Необязательные документы в custom-пайплайне + сворачивание опросного листа в админке

**Дата:** 2026-04-10
**Статус:** Утверждён

---

## Контекст

В пайплайне **custom** после парсинга ТУ клиент попадает на страницу загрузки (`upload.html`) в статусах `TU_PARSED` / `WAITING_CLIENT_INFO`. Сейчас кнопка «Всё загружено — отправить» заблокирована пока не выполнены **оба** условия: опросный лист сохранён И все требуемые документы загружены.

В пайплайне **express** клиент отправляет заявку только с ТУ без дополнительных документов.

---

## Требования

1. **Custom pipeline — необязательные документы:**
   - Опросный лист — **обязателен**
   - Дополнительные документы (акт балансового разграничения, схема подключения и пр.) — **необязательны**
   - Кнопка «Отправить» активна как только опросный лист сохранён, независимо от загрузки документов
   - Если документы не загружены — показывать явную подсказку под кнопкой

2. **Admin.html — сворачиваемый опросный лист:**
   - Карточка «Опросный лист» должна сворачиваться/разворачиваться по клику на заголовок
   - Паттерн: тот же `<details>/<summary>` что использован внутри карточки parsedCard
   - По умолчанию: развёрнута

---

## Затрагиваемые файлы

- `backend/static/upload.html`
- `backend/static/admin.html`

Бэкенд изменений **не требует**: логика 24-часовых уведомлений уже реализована в `tasks.py` (`send_info_request_email`, `process_due_info_requests`).

---

## Детали реализации

### 1. upload.html — `syncSubmitButtonState()`

**Текущая логика (customPost):**
```javascript
if (!surveySavedCustom) {
  $submitBtn.disabled = true;
  $submitBtn.title = 'Сначала сохраните опросный лист внизу страницы';
  return;
}
$submitBtn.title = '';
const mp = orderData.missing_params || [];
if (mp.length === 0) { $submitBtn.disabled = false; return; }
const allDone = mp.every(code => uploadedCategories.has(code));
$submitBtn.disabled = !allDone;
if (!allDone) { $submitBtn.title = 'Загрузите все документы из списка выше'; }
```

**Новая логика:**
```javascript
if (!surveySavedCustom) {
  $submitBtn.disabled = true;
  $submitBtn.title = 'Сначала сохраните опросный лист внизу страницы';
  return;
}
$submitBtn.disabled = false;
$submitBtn.title = '';
// Показываем/скрываем подсказку про необязательные документы
const mp = orderData.missing_params || [];
const allDone = mp.length === 0 || mp.every(code => uploadedCategories.has(code));
showDocsOptionalHint(!allDone);
```

### 2. upload.html — элемент подсказки

Добавить `<div id="docsOptionalHint">` сразу под кнопкой «Всё загружено — отправить»:

```html
<div id="docsOptionalHint" style="display:none; margin-top:10px; padding:10px 14px;
  border-radius:8px; background:var(--c-warn-bg); border:1px solid #fde68a;
  font-size:13px; color:#92400e; line-height:1.5;">
  Вы можете отправить заявку сейчас — инженер свяжется с вами для уточнения деталей.
  Либо дополнительно загрузите документы из списка выше для ускорения обработки.
</div>
```

Функция `showDocsOptionalHint(show)` показывает/скрывает этот элемент.

### 3. upload.html — баннер после сохранения опроса

**Текущий текст:**
> «Опросный лист сохранён. Теперь при необходимости догрузите файлы и нажмите «Всё загружено — отправить».»

**Новый текст:**
> «Опросный лист сохранён. Вы можете отправить заявку сейчас или дополнительно загрузить документы из списка выше.»

### 4. admin.html — сворачиваемый опросный лист

В функции `renderSurveyData()` обернуть содержимое в `<details open>`:

```javascript
function renderSurveyData(survey) {
  const card = document.getElementById('surveyCard');
  const content = document.getElementById('surveyContent');
  if (!survey || ...) { card.style.display = 'none'; return; }

  // Строим HTML секций как сейчас...
  const sectionsHtml = ...;

  content.innerHTML = `
    <details open class="parsed-params-details">
      <summary>Данные опросного листа ▶</summary>
      <div class="parsed-details-body">${sectionsHtml}</div>
    </details>`;
  card.style.display = 'block';
}
```

CSS `.parsed-params-details` уже присутствует в admin.html (используется для parsedCard).

---

## Сценарии

| Ситуация | Поведение |
|----------|-----------|
| Custom, опрос не сохранён | Кнопка заблокирована, tooltip: «Сначала сохраните опросный лист» |
| Custom, опрос сохранён, документы не все | Кнопка активна, показывается жёлтая подсказка |
| Custom, опрос сохранён, все документы загружены | Кнопка активна, подсказка скрыта |
| Express | Поведение не меняется |

---

## Бэкенд — уведомления (без изменений)

Если клиент отправляет без доп. документов:
- `client-upload-done` → `CLIENT_INFO_RECEIVED` → `process_client_response` → `check_data_completeness`
- Если `missing_params` не пуст → `WAITING_CLIENT_INFO`, планируется `send_info_request_email` через 24ч
- Инженер может отправить письмо вручную из админки (`sendEmail info_request`)
