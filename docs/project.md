# УУТЭ Проектировщик — архитектура (фрагмент)

## Публичный фронтенд (React SPA)

Контактные данные и юридические реквизиты на лэндинге задаются в [`frontend/src/constants/siteLegal.ts`](../frontend/src/constants/siteLegal.ts): `SITE_CONTACT` используется в подвале и в секции «Свяжитесь с нами» (`Footer`, `PartnerFormSection`), `SITE_REQUISITES` — только в подвале.

Сборка Vite кладётся в `frontend/dist`; в production образ монтируется в контейнер как `/app/frontend-dist` (`docker-compose.prod.yml`). FastAPI в [`backend/app/main.py`](../backend/app/main.py) отдаёт `index.html` для путей вне зарегистрированных маршрутов (`/{full_path:path}` регистрируется последним) и статику `/assets` из той же папки. Явные маршруты `/api/v1/*`, `/health`, `/upload/{id}`, `/admin`, `/static` имеют приоритет.

Файлы из [`frontend/public/`](../frontend/public/) попадают в корень статики: опросный лист для скачивания с лендинга — [`/downloads/opros_list_form.pdf`](../frontend/public/downloads/opros_list_form.pdf) (единственная копия PDF; ранее дубль лежал в `docs/` и был удалён, чтобы не плодить расхождения). В production [`backend/app/main.py`](../backend/app/main.py) для путей вне `/api`, `/upload`, `/admin`, `/static`, `/assets` сначала проверяет наличие **реального файла** в `frontend-dist` (`_safe_dist_file`) и отдаёт его через `FileResponse`; иначе — `index.html` SPA. Без этого запрос к PDF попадал бы в SPA и отдавал бы HTML под именем `.pdf`.

## Админка (`/admin`, `backend/static/admin.html`)

Статический интерфейс инженера: список заявок, карточка заявки, файлы, действия по пайплайну. Результат парсинга ТУ (`orders.parsed_params`, JSON из `TUParsedData`) отображается в блоке «Результат парсинга ТУ»: уверенность, раскрываемые таблицы параметров по группам, `missing_params`, `warnings`. Данные подгружаются из `GET /api/v1/orders/{id}` без отдельного эндпоинта.

Ответ `GET /api/v1/orders/{id}` дополняется флагами `info_request_sent` и `reminder_sent` (успешная отправка по записям в `email_log` с `sent_at`). Кнопки «Отправить запрос клиенту» и «Отправить напоминание» в админке одноразовые; повторный вызов `POST /emails/{id}/send` с тем же типом даёт **409**. Загрузка файла категории «Готовый проект» показывает линейный прогресс отправки (XHR `upload.onprogress`).

Карточка «Настроечная БД вычислителя» в админке свёрнута по умолчанию при первом открытии конкретной заявки. Дальше её ручное раскрытие/сворачивание запоминается отдельно для каждой заявки в рамках текущей сессии страницы `/admin`, включая перерисовки после сохранения. При poll-обновлениях той же заявки `loadCalcConfig()` больше не трогает `details.open`: восстановление open/close состояния допустимо только при смене заявки, чтобы завершившийся `fetch` не переоткрывал панель поверх пользовательского клика. Кнопка `Сохранить` в этом блоке активна только при наличии несохранённых изменений и после успешного `PATCH` снова становится неактивной до следующего редактирования.

Защищённые админские API: заголовок `X-Admin-Key` или query `?_k=…` (см. `app.core.auth.verify_admin_key`).

## Категории файлов (`FileCategory`)

Значения хранятся в PostgreSQL как тип `file_category` и в коде как `app.models.FileCategory`.

**Документы от клиента (после ТУ):**

| Значение | Назначение |
|----------|------------|
| `tu` | Технические условия |
| `BALANCE_ACT` | Акт разграничения балансовой принадлежности (действующие объекты) |
| `CONNECTION_PLAN` | План подключения потребителя к тепловой сети |
| `heat_point_plan` | План теплового пункта с указанием мест установки узла учёта и ШУ |
| `heat_scheme` | Принципиальная схема теплового пункта с узлом учёта |

**Post-project / служебные:** `generated_excel`, `generated_project`, `invoice`, `final_invoice`, `signed_contract`, `rso_scan`, `rso_remarks`, `other`.

Список того, что ещё нужно от клиента, задаётся в `orders.missing_params` (JSON-массив строк). Коды документов совпадают с `FileCategory` для сопоставления с загруженными файлами в `process_client_response` (сравнение с `OrderFile.category`). Подписи для писем и страницы загрузки — `app/services/param_labels.py`.

Миграция `20260402_uute_file_category` добавляет значения перечисления в БД (изначально `balance_act` / `connection_plan`), переносит файлы `floor_plan` → `other` и нормализует устаревшие коды в `missing_params`. Миграция `20260403_fc_upper` переименовывает метки enum в `BALANCE_ACT` / `CONNECTION_PLAN` и обновляет соответствующие строки в `orders.missing_params`.

На странице загрузки (`GET .../upload-page`) в ответе для статусов ожидания клиента в `missing_params` приходят коды из `CLIENT_DOCUMENT_PARAM_CODES` (технические документы + `company_card`), а UI строит чеклист с галочками по факту загруженных файлов. Устаревшие значения в БД подменяются на канонические при первом открытии (`fix_legacy_client_document_params`). После нажатия «Готово» Celery записывает в БД только ещё не закрытые позиции: `compute_client_document_missing`. Для заявок `order_type=custom` в том же ответе приходят `parsed_params` (если не пустой JSON после парсинга ТУ) и `survey_data` (если уже сохранён), для `express` эти поля `null`. На `upload.html` для custom после отправки ТУ страница показывает ожидание парсинга и опрашивает этот эндпоинт до статуса `tu_parsed` (или далее), затем открывает опросный лист с предзаполнением из `parsed_params`. Если клиент уже сохранял опрос (`survey_data`), при загрузке страницы подставляются сохранённые значения; иначе поля заполняются из ТУ по таблице `PARAM_TO_SURVEY`, с подсветкой источника и блоком уверенности/предупреждений парсера. Для custom-заявок `init()` ветвится по `order_status`: `new` — загрузка ТУ и заблокированный опрос (overlay); `tu_parsing` — экран ожидания и polling; после парсинга — редактируемый опрос и при необходимости блок догрузки документов; для custom после парсинга кнопка «Всё загружено — отправить» включается только после сохранения опроса (`POST .../survey`) и загрузки файлов по всем позициям `missing_params`; `review`/`completed` — экран «готово»; `error` — сообщение и возможность снова обратиться к загрузке. Публичный `POST /landing/orders/{id}/survey` записывает `survey_data` только в статусах, где клиенту разрешено редактировать опрос на upload-странице (`tu_parsed` … `generating_project`), не в `review`/`completed`/`new` и т.п.

Подробный трекер (в архиве): [`docs/archive/2026-Q2/smart-survey-tasktracker.md`](archive/2026-Q2/smart-survey-tasktracker.md).

## Celery-задачи (`app.services.tasks`)

С **фазы D1.b (2026-04-22)** код вынесен из одного файла в пакет [`backend/app/services/tasks/`](../backend/app/services/tasks/): `_common` (синхронная сессия, хелперы вложений), `tu_parsing`, `client_response`, `contract_flow`, `post_project_flow`, `reminders`. Публичный импорт прежний: `from app.services.tasks import start_tu_parsing`, `SyncSession`, `_get_order`. У каждой задачи в декораторе зафиксировано явное `name="app.services.tasks.<funcname>"` (фаза D1.a) — смена файла в пакете не меняет имя в Redis/beat.

## Email-сервис (`app.services.email`)

С **фазы D2 (2026-04-22)** отправка писем разбита на пакет [`backend/app/services/email/`](../backend/app/services/email/): `renderers` (Jinja2 и все `render_*`), `smtp` (сборка MIME, `send_email`, общий `send_smtp_message` для нестандартных писем, например с `Reply-To` и вложениями), `idempotency` (`has_successful_email`, `log_email` для писем клиенту с логом по `order_id`), `service` (все `send_*`). Обратная совместимость: `from app.services.email_service import …` (модуль-обёртка re-export'ит пакет); допустим также `from app.services.email import …`.

## Генерация договора (DOCX)

Сервис [`backend/app/services/contract_generator.py`](../backend/app/services/contract_generator.py) формирует договор по тексту шаблона [`docs/kontrakt_ukute_template.md`](kontrakt_ukute_template.md): разделы 1–15, приложения 1–3 (состав документации, ТУ РСО, лист согласования). Для договора используется компактная вёрстка: базовый шрифт `10 pt`, нулевые интервалы до/после абзацев и минимальный межстрочный интервал, чтобы DOCX оставался плотным и ближе к согласованному шаблону.

PDF технических условий (`FileCategory.TU`, путь вычисляется как `upload_dir / OrderFile.storage_path`) опционально встраивается в Приложение №2: страницы раструются через PyMuPDF в PNG во временный каталог под `/tmp`, в документ вставляются с шириной 16.5 см. Чтобы вложение письма укладывалось в лимит SMTP (~25 МБ целевой запас к 30 МБ), при превышении порога размер снижается за счёт DPI 150 → 120 → 100; если и на минимальном DPI файл слишком велик — генерируется версия без встроенных страниц ТУ (текст-заглушка) и пишется ERROR в лог. Счёт `generate_invoice` и номер `generate_contract_number` не затрагиваются.

## Unified upload + contract flow

Актуальный основной поток заявки для клиентского/админского UI: `new → tu_parsing → tu_parsed → waiting_client_info → client_info_received → contract_sent → advance_paid → awaiting_final_payment → completed`, с дополнительной post-project петлёй `awaiting_final_payment → rso_remarks_received → awaiting_final_payment`, если РСО вернула замечания. Legacy-статусы (`data_complete`, `generating_project`, `review`, `awaiting_contract`) поддерживаются для обратной совместимости старых заявок и отображаются в интерфейсах как дополнительные.

Роль страницы `/upload/{id}`:
- в `waiting_client_info` и `client_info_received` клиент догружает недостающие документы из `missing_params`, при этом `company_card` выделяется отдельным блоком как реквизитный документ для договора/счёта;
- в `contract_sent` клиент видит отдельный экран подписания: номер договора, суммы (`payment_amount`, `advance_amount`) и отдельную загрузку скана подписанного договора через `POST /api/v1/landing/orders/{id}/upload-signed-contract` (PDF/JPG/JPEG/PNG);
- после успешной загрузки `signed_contract` показывается подтверждение приёма и сообщение о сроке подготовки проекта (3 рабочих дня после подтверждения аванса).

## Post-project flow (`awaiting_final_payment` / `rso_remarks_received`)

Post-project ветка теперь состоит из двух статусов:

- `awaiting_final_payment` — клиенту уже отправлен проект, ждём скан из РСО, замечания или оплату остатка;
- `rso_remarks_received` — клиент загрузил замечания РСО, и заявка явно возвращена инженеру на исправление.

При этом детализация сценария по-прежнему опирается на артефакты и derived-флаги:

- `orders.rso_scan_received_at` — когда клиент загрузил скан сопроводительного письма с входящим номером РСО;
- `order_files.category = final_invoice` — сохранённый счёт на остаток, который повторно отправляется без регенерации;
- `order_files.category = rso_remarks` — замечания РСО, загруженные клиентом;
- derived-флаги API: `has_rso_scan`, `has_rso_remarks`, `awaiting_rso_feedback`, `final_invoice_available`.

Для исторических заявок, попавших в рассинхрон между статусом и уже загруженными замечаниями РСО, безопасный remediation встроен прямо в исходную миграцию `20260416_uute_rso_remarks_status`: после `autocommit_block()` для добавления enum она переводит заказ в `RSO_REMARKS_RECEIVED` только если в БД он всё ещё `AWAITING_FINAL_PAYMENT`, `final_paid_at IS NULL`, существуют последние `RSO_REMARKS` и после них нет более нового `GENERATED_PROJECT`. Этот predicate намеренно повторяет текущую доменную логику `derive_post_project_flags()` из [`backend/app/post_project_state.py`](../backend/app/post_project_state.py), чтобы не возвращать в статус замечаний уже обработанные заявки, по которым инженер успел повторно отправить исправленный проект.

Страница `/payment/{id}` в этом статусе показывает два реальных сценария варианта A:

- до загрузки скана РСО: клиент может либо загрузить скан письма с входящим номером, либо открыть блок оплаты по счёту и реквизитам;
- после загрузки скана: UI явно подтверждает приём документа, показывает ожидание замечаний/оплаты и даёт отдельную загрузку `rso_remarks`;
- после загрузки замечаний: заявка переходит в `rso_remarks_received`, клиент видит устойчивое подтверждение, а инженер получает email-уведомление и кнопку повторной отправки исправленного проекта; в админке показ этих post-project действий дополнительно страхуется derived-флагом `has_rso_remarks`, чтобы кнопки не пропадали при рассинхроне статуса и уже загруженных замечаний;
- после повторной отправки исправленного проекта заявка возвращается в `awaiting_final_payment`, а клиент получает новый PDF проекта и новое сопроводительное письмо с тем же счётом на остаток.

## Письма и Celery (фрагмент)

- Письмо `project_delivery` (отправка готового проекта) теперь содержит ссылку на страницу `/payment/{order_id}` для оплаты по счёту / загрузки post-project документов и отправляется с вложениями: PDF проекта, DOCX сопроводительного письма и сохранённый счёт на остаток `final_invoice`.
- `send_completed_project` при первой отправке сохраняет счёт на остаток как `OrderFile(final_invoice)`; при повторной отправке исправленного проекта (`resend_corrected_project`) переиспользуется тот же файл счёта, а клиент получает новый PDF проекта и обновлённое сопроводительное письмо.
- После загрузки клиентом скана сопроводительного через `POST /landing/orders/{id}/upload-rso-scan` записывается `rso_scan_received_at` и запускаются два уведомления: инженеру (`notify_engineer_rso_scan_received`) и клиенту (`notify_client_after_rso_scan`). Клиент получает письмо со сроками по ПП РФ №1034 (п.51 и п.50) и кнопкой перехода на страницу замечаний/реквизитов.
- После загрузки `rso_remarks` через `POST /landing/orders/{id}/upload-rso-remarks` заявка переводится в `rso_remarks_received`, а инженер получает отдельное email-уведомление.
- Повторная отправка исправленного проекта (`POST /pipeline/{id}/resend-corrected-project`) доступна только из `rso_remarks_received`; после успешной отправки заявка возвращается в `awaiting_final_payment`.
- Подтверждение финальной оплаты (`POST /pipeline/{id}/confirm-final`) разрешено как в `awaiting_final_payment`, так и в `rso_remarks_received`, чтобы замечания РСО не блокировали ручное закрытие уже оплаченной заявки.
- Напоминание о финальной оплате после РСО отправляется периодической задачей `send_final_payment_reminders_after_rso_scan`: кандидат — заявка в `awaiting_final_payment` со значением `rso_scan_received_at` старше 15 дней и без `final_paid_at`; идемпотентность обеспечивается по `email_log` через тип `final_payment_request` и маркер `reminder_kind:rso_scan_15d`.
- После `check_data_completeness` при непустых `missing_params` заявка переходит в `waiting_client_info`, в `orders.waiting_client_info_at` пишется UTC; в этот же момент ставится отдельное письмо инженеру `notify_engineer_tu_parsed`, чтобы инженер получал email сразу после успешной загрузки и парсинга ТУ, когда в админке уже доступны `parsed_params` и список недостающих документов. **Автоотправка** `info_request` клиенту по-прежнему не раньше чем через 24 ч: отложенная задача Celery `send_info_request_email` с `countdown` 24 ч плюс резерв `process_due_info_requests` (Beat каждые 15 минут). Ручная отправка из админки возможна сразу; дубликат блокируется по `email_log`. В ответе `GET /orders/{id}` поле `info_request_earliest_auto_at` (UTC) подсказывает момент ближайшей автоотправки, пока запрос ещё не уходил.
- Напоминание (`reminder`): не чаще одного успешного на заявку; периодика `send_reminders` (ежедневно 10:00 МСК) шлёт только если уже был успешный `info_request` и с его `sent_at` прошло ≥ 3 суток.
- После `POST /pipeline/{id}/client-upload-done` в очередь ставится `notify_engineer_client_documents_received` — отдельное письмо на `admin_email` для более позднего события "клиент завершил загрузку документов" (тип `client_documents_received`, идемпотентность по логу). Событие раннего парсинга ТУ логируется отдельно как `tu_parsed_notification`.
