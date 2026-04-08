# УУТЭ Проектировщик — архитектура (фрагмент)

## Публичный фронтенд (React SPA)

Сборка Vite кладётся в `frontend/dist`; в production образ монтируется в контейнер как `/app/frontend-dist` (`docker-compose.prod.yml`). FastAPI в [`backend/app/main.py`](../backend/app/main.py) отдаёт `index.html` для путей вне зарегистрированных маршрутов (`/{full_path:path}` регистрируется последним) и статику `/assets` из той же папки. Явные маршруты `/api/v1/*`, `/health`, `/upload/{id}`, `/admin`, `/static` имеют приоритет.

## Админка (`/admin`, `backend/static/admin.html`)

Статический интерфейс инженера: список заявок, карточка заявки, файлы, действия по пайплайну. Результат парсинга ТУ (`orders.parsed_params`, JSON из `TUParsedData`) отображается в блоке «Результат парсинга ТУ»: уверенность, раскрываемые таблицы параметров по группам, `missing_params`, `warnings`. Данные подгружаются из `GET /api/v1/orders/{id}` без отдельного эндпоинта.

Ответ `GET /api/v1/orders/{id}` дополняется флагами `info_request_sent` и `reminder_sent` (успешная отправка по записям в `email_log` с `sent_at`). Кнопки «Отправить запрос клиенту» и «Отправить напоминание» в админке одноразовые; повторный вызов `POST /emails/{id}/send` с тем же типом даёт **409**. Загрузка файла категории «Готовый проект» показывает линейный прогресс отправки (XHR `upload.onprogress`).

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

**Служебные:** `generated_excel`, `generated_project`, `other`.

Список того, что ещё нужно от клиента, задаётся в `orders.missing_params` (JSON-массив строк). Коды документов совпадают с `FileCategory` для сопоставления с загруженными файлами в `process_client_response` (сравнение с `OrderFile.category`). Подписи для писем и страницы загрузки — `app/services/param_labels.py`.

Миграция `20260402_uute_file_category` добавляет значения перечисления в БД (изначально `balance_act` / `connection_plan`), переносит файлы `floor_plan` → `other` и нормализует устаревшие коды в `missing_params`. Миграция `20260403_fc_upper` переименовывает метки enum в `BALANCE_ACT` / `CONNECTION_PLAN` и обновляет соответствующие строки в `orders.missing_params`.

На странице загрузки (`GET .../upload-page`) в ответе для статусов ожидания клиента в `missing_params` всегда приходят все четыре кода из `CLIENT_DOCUMENT_PARAM_CODES` (чеклист с галочками по факту загруженных файлов). Устаревшие значения в БД подменяются на канонические четыре при первом открытии (`fix_legacy_client_document_params`). После нажатия «Готово» Celery записывает в БД только ещё не закрытые позиции: `compute_client_document_missing`. Для заявок `order_type=custom` в том же ответе приходят `parsed_params` (если не пустой JSON после парсинга ТУ) и `survey_data` (если уже сохранён), для `express` эти поля `null`. На `upload.html` для custom после отправки ТУ страница показывает ожидание парсинга и опрашивает этот эндпоинт до статуса `tu_parsed` (или далее), затем открывает опросный лист с предзаполнением из `parsed_params`. Если клиент уже сохранял опрос (`survey_data`), при загрузке страницы подставляются сохранённые значения; иначе поля заполняются из ТУ по таблице `PARAM_TO_SURVEY`, с подсветкой источника и блоком уверенности/предупреждений парсера. Для custom-заявок `init()` ветвится по `order_status`: `new` — загрузка ТУ и заблокированный опрос (overlay); `tu_parsing` — экран ожидания и polling; после парсинга — редактируемый опрос и при необходимости блок догрузки документов; `review`/`completed` — экран «готово»; `error` — сообщение и возможность снова обратиться к загрузке. Публичный `POST /landing/orders/{id}/survey` записывает `survey_data` только в статусах, где клиенту разрешено редактировать опрос на upload-странице (`tu_parsed` … `generating_project`), не в `review`/`completed`/`new` и т.п.

Подробный трекер: [`docs/smart-survey-tasktracker.md`](smart-survey-tasktracker.md).

## Письма и Celery (фрагмент)

- После `check_data_completeness` при непустых `missing_params` заявка переходит в `waiting_client_info`, в `orders.waiting_client_info_at` пишется UTC; **автоотправка** `info_request` клиенту — не раньше чем через 24 ч: отложенная задача Celery `send_info_request_email` с `countdown` 24 ч плюс резерв `process_due_info_requests` (Beat каждые 15 минут). Ручная отправка из админки возможна сразу; дубликат блокируется по `email_log`. В ответе `GET /orders/{id}` поле `info_request_earliest_auto_at` (UTC) подсказывает момент ближайшей автоотправки, пока запрос ещё не уходил.
- Напоминание (`reminder`): не чаще одного успешного на заявку; периодика `send_reminders` (ежедневно 10:00 МСК) шлёт только если уже был успешный `info_request` и с его `sent_at` прошло ≥ 3 суток.
- После `POST /pipeline/{id}/client-upload-done` в очередь ставится `notify_engineer_client_documents_received` — одно письмо на `admin_email` (тип `client_documents_received`, идемпотентность по логу).
