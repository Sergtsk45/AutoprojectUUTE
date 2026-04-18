# Task tracker

## Задача: DOCX договор — вставка ТУ и контроль размера (2026-04-19)
- **Статус**: Завершена
- **Описание**: Встроить страницы PDF ТУ в Приложение 2 договора с лестницей DPI и fallback без растра при превышении ~25 МБ; передавать путь к ТУ и поля из `parsed_params` из Celery-задач.
- **Шаги выполнения**:
  - [x] PyMuPDF в `requirements.txt`, helpers рендера/очистки PNG и цикл `generate_contract`
  - [x] Обновить `process_card_and_contract` и `process_company_card_and_send_contract`
  - [x] Актуализировать `docs/project.md`, `docs/changelog.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/app/services/contract_generator.py`, `backend/app/services/tasks.py`

## Задача: Race-fix сворачивания настроечной БД при poll-обновлениях (2026-04-16)
- **Статус**: Завершена
- **Описание**: Зафиксировать в репозитории продовый фикс для `admin.html`, чтобы poll-обновления той же заявки не переоткрывали блок «Настроечная БД вычислителя» поверх пользовательского клика на сворачивание.
- **Шаги выполнения**:
  - [x] Добавить регрессионный тест на `loadCalcConfig()` и восстановление состояния только при смене заявки
  - [x] Ограничить вызов `applyCalcConfigDetailsState(orderId)` случаями смены заявки
  - [x] Сохранить обновление `dataset.orderId` без принудительного изменения `details.open` на poll-обновлениях той же заявки
  - [x] Обновить `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/static/admin.html`, `backend/tests/test_admin_post_project_actions.py`

## Задача: Починка действий инженера для замечаний РСО (2026-04-16)
- **Статус**: Завершена
- **Описание**: Исправить админку так, чтобы post-project действия инженера не исчезали после загрузки замечаний РСО и были доступны как по статусу `rso_remarks_received`, так и по derived-флагу активных замечаний.
- **Шаги выполнения**:
  - [x] Проверить текущую логику `renderActions` и backend-эндпоинтов post-project ветки
  - [x] Добавить регрессионный тест на fallback по `has_rso_remarks`
  - [x] Починить `backend/static/admin.html`
  - [x] Обновить `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/static/admin.html`, `backend/tests/test_admin_post_project_actions.py`

## Задача: UX настроечной БД в админке (2026-04-16)
- **Статус**: Завершена
- **Описание**: Зафиксировать поведение карточки настроечной БД в админке: по умолчанию свёрнута только при первом открытии конкретной заявки, далее запоминает ручное состояние инженера; кнопка `Сохранить` после успешного сохранения снова становится неактивной до следующего редактирования.
- **Шаги выполнения**:
  - [x] Исследовать текущую реализацию `calcConfigDetails` и dirty-state кнопки `Сохранить`
  - [x] Добавить per-order хранение состояния раскрытия в `backend/static/admin.html`
  - [x] Усилить reset dirty-state после успешного сохранения настроечной БД
  - [x] Обновить `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/static/admin.html`

## Задача: Возврат email-уведомления инженеру после загрузки ТУ (2026-04-16)
- **Статус**: Завершена
- **Описание**: Вернуть письмо инженеру после успешной загрузки и парсинга ТУ, чтобы инженер снова получал email в момент, когда в админке уже доступны распарсенные данные и заявка перешла в ожидание документов от клиента.
- **Шаги выполнения**:
  - [x] Добавить регрессионный тест на постановку Celery-уведомления из `check_data_completeness`
  - [x] Добавить отдельную задачу `notify_engineer_tu_parsed` и новый `EmailType` для события парсинга ТУ
  - [x] Добавить шаблон письма инженеру с `missing_params`, статусом заявки и ссылкой на админку
  - [x] Обновить `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/app/services/tasks.py`, `backend/app/services/email_service.py`, `backend/templates/emails/tu_parsed_notification.html`, `backend/alembic/versions/20260416_uute_tu_parsed_notification_enum.py`

## Задача: Исправление enum-миграции статуса замечаний РСО (2026-04-16)
- **Статус**: Завершена
- **Описание**: Исправить Alembic-миграцию `RSO_REMARKS_RECEIVED` под ограничение PostgreSQL, где новый enum нельзя использовать в той же транзакции, в которой он был добавлен.
- **Шаги выполнения**:
  - [x] Добавить регрессионный тест на структуру миграции
  - [x] Перевести `ALTER TYPE ... ADD VALUE` в `op.get_context().autocommit_block()`
  - [x] Оставить `UPDATE orders ...` отдельным шагом после фиксации нового enum
  - [x] Добавить правило для будущих enum-миграций в `backend/alembic/README.md`
- **Зависимости**: `backend/alembic/versions/20260416_uute_rso_remarks_status.py`, PostgreSQL enum semantics

## Задача: Post-project pipeline — отдельный статус замечаний РСО (2026-04-16)
- **Статус**: Завершена
- **Описание**: Ввести отдельный `OrderStatus` для замечаний РСО, чтобы заявка явно возвращалась инженеру на исправление и после повторной отправки возвращалась обратно в ожидание оплаты/согласования.
- **Шаги выполнения**:
  - [x] `models.py` + Alembic: добавить `rso_remarks_received` в `OrderStatus` и `order_status`
  - [x] `post_project_state.py` + `schemas.py`: отвязать derived-флаги от простого факта наличия старых remark-файлов
  - [x] `landing.py`: при `upload-rso-remarks` переводить заявку в новый статус
  - [x] `pipeline.py` + `tasks.py`: повторная отправка исправленного проекта только из `rso_remarks_received` с возвратом в `awaiting_final_payment`
  - [x] `admin.html` + `payment.html`: показать новый статус и корректные действия инженера/клиента
  - [x] `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
- **Зависимости**: существующий post-project flow с `FINAL_INVOICE`, `RSO_SCAN`, `RSO_REMARKS`

## Задача: Post-project pipeline — финальный счёт и замечания РСО (2026-04-16)
- **Статус**: Завершена
- **Описание**: Реализовать утверждённый post-project flow без новых `OrderStatus`: сохранить основной статус `awaiting_final_payment`, но добавить артефакты согласования с РСО, повторную отправку исправленного проекта и 15-дневный reminder по финальной оплате.
- **Шаги выполнения**:
  - [x] `models.py` + Alembic: `FINAL_INVOICE`, `RSO_REMARKS`, `rso_scan_received_at`
  - [x] `schemas.py` + `landing.py`: derived-флаги payment/admin response и public upload `upload-rso-remarks`
  - [x] `tasks.py` + `celery_app.py`: сохранение/переиспользование финального счёта, re-delivery исправленного проекта, reminder через 15 дней
  - [x] `email_service.py` + шаблоны: тексты без обещания онлайн-эквайринга, отдельная ветка повторной отправки исправленного проекта
  - [x] `payment.html`: UX варианта A для оплаты по счёту / загрузки скана РСО / замечаний РСО
  - [x] `admin.html` + `pipeline.py`: отображение derived state и действие «Отправить исправленный проект»
  - [x] `docs/changelog.md`, `docs/tasktracker.md`, `docs/project.md`
- **Зависимости**: существующие `OrderFile`, `EmailLog`, `/payment/{id}`, Celery Beat

## Задача: Доработки писем и payment/upload flow (2026-04-16)
- **Статус**: Завершена
- **Описание**: Точечные изменения UI и почтовых сценариев: управление кнопкой сохранения настроечной БД, новые тексты писем, вложение счёта на остаток, уведомление клиента после загрузки скана сопроводительного в РСО.
- **Шаги выполнения**:
  - [x] `admin.html`: отключение кнопки «Сохранить» при отсутствии pending-изменений + блокировка на время запроса
  - [x] `admin.html`: блок настроечной БД и его группы свёрнуты по умолчанию
  - [x] `info_request.html` и `project_delivery.html`: обновлённые тексты и CTA под новый процесс
  - [x] `upload.html`: кнопка «Вернуться на сайт» после успешной загрузки signed_contract
  - [x] `tasks.py`: вложение счёта на остаток в `send_completed_project` с cleanup временного файла
  - [x] `landing.py` + `tasks.py` + `final_payment_request.html`: письмо клиенту после `upload-rso-scan` с CTA «Загрузить замечания от РСО»
  - [x] `payment.html`: в `awaiting_final_payment` показывать форму загрузки скана, пока файл `rso_scan` не загружен
- **Зависимости**: существующие шаблоны email и endpoint `POST /api/v1/landing/orders/{id}/upload-rso-scan`

## Задача: Unified upload contract flow (upload/admin)
- **Статус**: Завершена
- **Описание**: Привести frontend-статику и админ-панель к новому потоку `contract_sent/advance_paid`: отдельный клиентский экран загрузки подписанного договора, обновлённый stepper и действия инженера.
- **Шаги выполнения**:
  - [x] `upload.html`: добавить `company_card` в подписи, выделить его в чеклисте для `waiting_client_info`, реализовать отдельный сценарий `contract_sent` с upload в `upload-signed-contract` и сообщением благодарности
  - [x] `admin.html`: обновить основной `STATUS_ORDER`, сохранить legacy-статусы в `STATUS_LABELS`
  - [x] `admin.html`: ограничить approve до `advance_paid`, обновить тексты/confirm/success, скорректировать polling после approve
  - [x] `admin.html`: добавить индикатор `signed_contract` в `contract_sent`, обновить подписи категорий файлов и options селекта
  - [x] Обновить `docs/changelog.md`, `docs/project.md`, выполнить `python3 -m compileall backend/app`
- **Зависимости**: backend-эндпоинт `POST /api/v1/landing/orders/{id}/upload-signed-contract` и статусы оплаты в пайплайне

## Задача: Публичная страница оплаты /payment/{id}
- **Статус**: Завершена
- **Описание**: Статическая `payment.html`, роут в `main.py`, публичные эндпоинты в `landing.py`, Celery: генерация и отправка договора/счёта (безнал), уведомление инженеру о скане РСО.
- **Шаги выполнения**:
  - [x] `PaymentPageInfo`, API payment-page / upload-company-card / select-payment-method / upload-rso-scan
  - [x] `process_company_card_and_send_contract`, `notify_engineer_rso_scan_received`, `send_contract_delivery_to_client`
  - [x] `payment.html` (экраны, XHR, polling, лимит 25 МБ)
- **Зависимости**: статусы оплаты и `FileCategory` в модели (задача 1 в payment-advance-tasktracker)

## Задача: Модалка «Политика конфиденциальности»
- **Статус**: Завершена
- **Описание**: Добавить прокручиваемую модалку с текстом политики конфиденциальности (152-ФЗ), открываемую из футера и из формы заказа (EmailModal).
- **Шаги выполнения**:
  - [x] Создать `frontend/src/constants/privacyPolicyText.ts` с HTML-текстом политики
  - [x] Создать `frontend/src/components/PrivacyPolicyModal.tsx` (overlay, Escape, scroll-lock, dangerouslySetInnerHTML, useRef fix)
  - [x] Подключить модалку в `Footer.tsx` (ссылка «Политика конфиденциальности»)
  - [x] Подключить модалку в `EmailModal.tsx` (кнопка-ссылка в тексте согласия)
  - [x] Вставить реальный текст политики ООО «Теплосервис-Комплект»
- **Технические заметки**:
  - `PrivacyPolicyModal` использует `useRef` для стабилизации `onClose` в `useEffect`, зависимость только `[isOpen]`
  - Скролл body блокируется при открытии, восстанавливается при закрытии (возможен конфликт при вложенных модалках — при необходимости решать через счётчик)
  - z-index: все модалки на `z-50` — при росте системы модалок перейти на иерархию `z-40/z-50/z-60`

## Задача: Внедрение настроечной БД Эско-Терра в express-пайплайн
- **Статус**: Завершена
- **Описание**: Интегрировать CalculatorConfig для express-заявок (только производитель Эско-Терра). Автоопределение из parsed_params + ручной override в админке.
- **Шаги выполнения**:
  - [x] `resolve_calculator_type_for_express` — автоопределение по metering.heat_calculator_model
  - [x] `init_config_sync` — синхронная версия для Celery-задач
  - [x] API guard: для express только `esko_terra`, GET возвращает `esko_detected` и `status=not_supported_for_express`
  - [x] Автоинициализация в `start_tu_parsing` после TU_PARSED
  - [x] UI admin.html: карточка для express + кнопка «Инициализировать как Эско 3Э»
  - [x] Документация: changelog.md, tasktracker.md
- **Зависимости**: feature/calculator-config (CalculatorConfig модель, сервис, API)

## Задача: Настроечная БД вычислителя (мультиприборность)
- **Статус**: Завершена
- **Описание**: Реализовать фичу «Настроечная БД вычислителя» — JSON-шаблоны параметров для ТВ7, СПТ-941.20, ЭСКО-Терра М; модель CalculatorConfig в БД; сервис автозаполнения из ТУ; CRUD API; UI в админке; экспорт PDF
- **Шаги выполнения**:
  - [x] Создать ветку `feature/calculator-config`
  - [x] JSON-шаблоны: `tv7.json` (29 параметров), `spt941.json` (25), `esko_terra.json` (22)
  - [x] Модель `CalculatorConfig` в `models.py` + relationship в `Order`
  - [x] Alembic-миграция `20260412_uute_add_calculator_configs`
  - [x] Сервис `calculator_config_service.py`: load_template, auto_fill, init_config, update_params, export_pdf
  - [x] API-роутер `calculator_config.py`: GET/POST/PATCH/export-pdf
  - [x] Подключить роутер в `main.py`
  - [x] UI в `admin.html`: calcConfigCard с прогресс-баром, легендой, таблицей, редактированием
  - [x] Обновить changelog.md и tasktracker.md
  - [x] Коммит в ветку `feature/calculator-config`
- **Зависимости**: Модели заявок (Order, survey_data, parsed_params), tu_schema.py (структура parsed_params)

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

## Задача: Excel-шаблон опросного листа для клиента
- **Статус**: Завершена
- **Описание**: Подготовить Excel-совместимый шаблон опросного листа на основе текущих полей парсинга ТУ и действующего клиентского опросника, чтобы его можно было отправлять клиенту и использовать для маппинга в систему.
- **Шаги выполнения**:
  - [x] Сформирован клиентский CSV-лист с полями для проверки и дозаполнения
  - [x] Сформирован технический CSV-лист соответствия `survey_data` и `parsed_params`
  - [x] Добавлен README с инструкцией по переносу двух CSV в единый `.xlsx`
  - [x] Добавлена запись в `docs/changelog.md`
- **Зависимости**: текущая схема парсинга ТУ (`backend/app/services/tu_schema.py`) и структура опросного листа (`backend/static/upload.html`)


## Задача: Custom — заполненные поля опросного листа только для чтения
- **Статус**: Завершена
- **Описание**: При открытии страницы клиентом по ссылке из письма (waiting_client_info и т.д.) поля опросного листа, которые уже были заполнены при создании заявки, должны быть нередактируемыми.
- **Шаги выполнения**:
  - [x] `upload.html`: CSS-класс `.survey-field-locked` — визуально отличает заблокированные поля (светлый фон)
  - [x] `upload.html`: функция `lockFilledSurveyFields(surveyData)` — `readonly` для `input`/`textarea`, `pointer-events: none` для `select`
  - [x] `upload.html`: `prefillSurveyFromSaved` вызывает `lockFilledSurveyFields` после заполнения формы
- **Зависимости**: нет

## Задача: Custom — необязательные документы и свёртка опроса в админке
- **Статус**: Завершена
- **Описание**: Снять блокировку кнопки «Отправить» по загрузке документов для custom; показывать UX-подсказку об опциональности; сделать карточку опросного листа в админке сворачиваемой.
- **Шаги выполнения**:
  - [x] `upload.html`: добавлен `div#docsOptionalHint` (жёлтая подсказка) сразу под кнопкой «Отправить»
  - [x] `upload.html`: `syncSubmitButtonState()` — убрана проверка всех документов; кнопка активна при сохранённом опросе
  - [x] `upload.html`: `showDocsOptionalHint()` показывает/скрывает подсказку при наличии незагруженных документов
  - [x] `upload.html`: текст баннера после сохранения опроса обновлён (документы — опционально)
  - [x] `admin.html`: `renderSurveyData()` оборачивает секции в `<details open>` с `<summary>`
  - [x] Записи в `docs/changelog.md` и `docs/tasktracker.md`
- **Зависимости**: нет

## Задача: UX custom — опросный лист, звёздочки, свёртка, секции в админке
- **Статус**: Завершена
- **Описание**: Улучшения UX custom-пайплайна на странице клиента и в админке.
- **Шаги выполнения**:
  - [x] `upload.html`: опросный лист перемещён над блоками «Необходимые документы» и «Загрузка файлов»
  - [x] `upload.html`: на начальном экране (`status=new`) опросный лист свёрнут (аккордеон), клик раскрывает
  - [x] `upload.html`: обязательные поля опросного листа отмечены звёздочкой `*` в лейбле
  - [x] `admin.html`: «Опросный лист» разбит на секции по группам (как `parsedCard` для express), с фиксированным порядком
  - [x] Записи в `docs/changelog.md` и `docs/tasktracker.md`
- **Зависимости**: нет

## Задача: UX-правки страницы загрузки и админки (апрель 2026)
- **Статус**: Завершена
- **Описание**: Серия UX-улучшений: inline-ошибки опросного листа, переименование поля ВРУ, обновление приветствия экспресс, блокировка кнопки «Одобрить», подсказка инженеру.
- **Шаги выполнения**:
  - [x] `upload.html`: ошибки валидации survey-формы — inline под кнопкой (не вверху)
  - [x] `upload.html`: поле «Расстояние до ВРУ» → обязательное, новое название
  - [x] `upload.html`: экспресс-заявка — приветствие обновляется после отправки документов
  - [x] `admin.html`: `runAction` блокирует кнопки на время запроса, разблокирует при ошибке
  - [x] `admin.html`: подсказка инженеру под формой загрузки файлов
  - [x] `admin.html`: метка `distance_to_vru` в `param_labels` обновлена
  - [x] Запись в `docs/changelog.md` и `docs/tasktracker.md`
- **Зависимости**: нет

## Задача: Отложенный info_request, одноразовые письма, уведомление инженеру, прогресс загрузки PDF
- **Статус**: Завершена
- **Описание**: Реализация плана [`docs/tasktrecker-progrssbar.md`](tasktrecker-progrssbar.md): 24 ч до авто-`info_request`, флаги и 409 для дублей, письмо инженеру после `client-upload-done`, прогресс XHR для `generated_project` в админке.
- **Шаги выполнения**:
  - [x] Модель `waiting_client_info_at`, миграция, `process_due_info_requests` + правки `send_reminders` / `send_info_request_email`
  - [x] `has_successful_email`, `CLIENT_DOCUMENTS_RECEIVED`, шаблон и Celery-уведомление
  - [x] `OrderResponse`: `info_request_sent`, `reminder_sent`; админка и 409 в `emails.py`
  - [x] `docs/changelog.md`, `docs/project.md`, актуализация плана в `tasktrecker-progrssbar.md`
- **Зависимости**: миграция Alembic на PostgreSQL; перезапуск celery-worker и celery-beat после деплоя

## Задача: Валидация файла проекта перед одобрением (pipeline approve)
- **Статус**: Завершена
- **Описание**: Исключить отправку письма «Проект готов» без вложения: раньше `approve` запускал Celery до загрузки PDF администратором.
- **Шаги выполнения**:
  - [x] Проверка `generated_project` в `approve_project` (HTTP 422)
  - [x] Лог-предупреждение в `send_completed_project` при пустых вложениях
  - [x] Блокировка кнопки «Одобрить» в `admin.html` до загрузки PDF
  - [x] Запись в [`docs/changelog.md`](changelog.md)
- **Зависимости**: нет

## Задача: Кодировка UTF-8 в `admin.html`
- **Статус**: Завершена
- **Описание**: После коммита `ec45248` русский текст в [`backend/static/admin.html`](../backend/static/admin.html) в git оказался заменён на `?`. Восстановление из версии до поломки + слияние с актуальной разметкой/JS (тип заявки, опрос, enum файлов).
- **Шаги выполнения**:
  - [x] Слияние строк с `92826c5`, точечные правки (колонки таблицы, даты, `survey_reminder`, эмодзи секций парсера)
  - [x] Запись в [`docs/changelog.md`](changelog.md)
- **Зависимости**: нет

## Задача: «Вернуться на сайт» на странице загрузки документов
- **Статус**: Завершена
- **Описание**: После отправки документов и после сохранения опросного листа клиент может перейти на главную (`/`) со страницы `/upload/{id}`.
- **Шаги выполнения**:
  - [x] Карточка «Все документы получены» + опрос после успешного POST survey
  - [x] Changelog, ревью (a11y `:focus-visible` для кнопок)
- **Зависимости**: нет

## Задача: Умный опросный лист (автозаполнение из ТУ для custom)
- **Статус**: Завершена
- **Описание**: Расширение upload-страницы и API: `parsed_params`/`survey_data` в ответе upload-page, polling парсинга, маппинг ТУ → поля опроса, инициализация по всем статусам, ограничение сохранения опроса по статусу заявки.
- **Шаги выполнения**:
  - [x] Задачи 1–5 по плану [`docs/smart-survey-tasktracker.md`](smart-survey-tasktracker.md)
- **Зависимости**: сегментация `OrderType` custom/express; эндпоинт `POST /landing/orders/{id}/survey`

## Задача: Сегментация клиентов — два варианта заказа (Экспресс / Индивидуальный)
- **Статус**: В работе
- **Описание**: Клиент выбирает тип проекта в калькуляторе. Экспресс — на базе Эско 3Э, скидка 50%. Индивидуальный — полная цена, опросный лист. Подробный план: [`docs/two-option-order-tasktracker.md`](two-option-order-tasktracker.md).
- **Шаги выполнения**:
  - [x] Задача 1: `OrderType` enum, поля `order_type` и `survey_data` в модели и схемах
  - [x] Задача 2: эндпоинт `POST /landing/order` принимает и сохраняет `order_type`
  - [x] Задача 3: две карточки в калькуляторе (фронтенд)
  - [x] Задача 4: форма и сценарии опроса на upload-странице (см. умный опрос, `smart-survey-tasktracker.md`)
  - [x] Задача 5: `order_type` и `survey_data` в админке
  - [x] Задача 6: email-напоминание заполнить опросный лист для custom-заказов
  - [x] Задача 7: changelog и документация
- **Зависимости**: миграция Alembic на сервере (колонки `order_type`, `survey_data`)

## Задача: Регистр значений file_category (BALANCE_ACT / CONNECTION_PLAN)
- **Статус**: Завершена
- **Описание**: Устранение рассинхрона между метками PostgreSQL enum (строчные `balance_act` / `connection_plan` из миграции 20260402) и ожиданиями кода в UPPER_CASE: переименование в БД, миграция `missing_params`, обновление модели и статики.
- **Шаги выполнения**:
  - [x] Alembic `20260403_fc_upper` (rename enum + JSON)
  - [x] `FileCategory`, `param_labels`, `admin.html`, `upload.html`
  - [x] `docs/project.md`, `docs/changelog.md`
- **Зависимости**: миграция `20260402_uute_file_category`

## Задача: Отображение результатов парсинга в админке
- **Статус**: Завершена
- **Описание**: Развёрнутый UI для `parsed_params` в карточке заявки (`admin.html`): `<details>` с таблицами по секциям, пустое состояние, legacy-плоские ключи.
- **Шаги выполнения**:
  - [x] CSS и JS в `backend/static/admin.html`
  - [x] `docs/changelog.md`, `docs/project.md`, [`docs/tasktrecker-otchet-parsing.md`](tasktrecker-otchet-parsing.md)
- **Зависимости**: нет

## Задача: Категории файлов УУТЭ (FileCategory + missing_params)
- **Статус**: Завершена
- **Описание**: Актуальные категории документов для проектирования УУТЭ; миграция БД для старых `floor_plan` и устаревших кодов в `missing_params`; синхронизация `param_labels`, парсера ТУ, `upload.html`, админки. Дополнительно: пересчёт `missing_params` по четырём документам при upload-page и в Celery, чтобы старые заявки не показывали `floor_plan` / `connection_scheme` / `system_type`.
- **Шаги выполнения**:
  - [x] Обновить `FileCategory` и миграцию Alembic
  - [x] `param_labels.py`, `tu_parser.py`, статика
  - [x] `docs/changelog.md`, `docs/project.md`, tasktracker
  - [x] `compute_client_document_missing` + legacy-fix на upload-page + фиксированные 4 пункта в ответе API; `process_client_response`
- **Зависимости**: нет

## Задача: Публичные upload-tu / submit (без 401 на upload.html)
- **Статус**: Завершена
- **Описание**: Эндпоинты в `landing.py` для загрузки ТУ и старта пайплайна при статусе `new`; админские `orders`/`pipeline/start` без изменений по защите.
- **Шаги выполнения**:
  - [x] `POST .../upload-tu`, `POST .../submit`
  - [x] `upload.html` + ограничение «только ТУ» для `new`
  - [x] `PipelineResponse` в `schemas`
- **Зависимости**: задача «upload-page + order_status»

## Задача: Страница upload.html — сценарии new и waiting_client_info
- **Статус**: Завершена
- **Описание**: Расширен ответ upload-page полем `order_status`; на клиенте выбираются URL загрузки и завершения в зависимости от статуса заявки.
- **Шаги выполнения**:
  - [x] Схема `UploadPageInfo` + эндпоинт `landing.py`
  - [x] Логика и категория `tu` в `upload.html`
  - [x] Запись в `docs/changelog.md`
- **Зависимости**: нет
