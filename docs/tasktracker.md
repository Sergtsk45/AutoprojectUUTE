# Task tracker

## Задача: UX — показывать detail ответа при 422 на `/pipeline/{id}/resend-corrected-project` (2026-04-21)
- **Статус**: Не начата
- **Описание**: При smoke-тесте после деплоя 2026-04-21 инженерный эндпоинт `POST /pipeline/{order_id}/resend-corrected-project` отвечает `422 Unprocessable Entity` в трёх бизнес-сценариях (см. `backend/app/api/pipeline.py:267-314`): нет `RSO_REMARKS`, нет `GENERATED_PROJECT`, либо последний `GENERATED_PROJECT` старше/равен последним `RSO_REMARKS`. Сам код корректен (защищает от отправки клиенту того же файла), но админка показывает только «Unprocessable Entity» без `detail`, из-за чего инженер не понимает, какое условие не выполнено.
- **Шаги выполнения**:
  - [ ] Проверить в `backend/static/admin.html` обработчик ошибки для кнопки «Повторно отправить исправленный проект» — читается ли `response.json().detail` и показывается ли в тосте/алерте
  - [ ] Если нет — вывести `detail` в UI (и для других pipeline-эндпоинтов, где 400/422 несут осмысленный текст)
  - [ ] Добавить короткую подсказку в самой кнопке/секции: «Перед повторной отправкой загрузите новую версию проекта в категорию "Готовый проект"»
  - [ ] Smoke-тест: три сценария 422 → видны три разных сообщения из `detail`
  - [ ] Запись в `docs/changelog.md`
- **Зависимости**: нет; эта задача войдёт в фазу E3 roadmap раздела 3 (декомпозиция `admin.html`) или может быть сделана раньше как точечный UX-фикс.
- **Приоритет**: низкий (не блокирует работу, это UX).

## Задача: Восстановить пропущенную prod-миграцию advance_payment_model (2026-04-20)
- **Статус**: Завершена
- **Описание**: При проверке перед деплоем обнаружено, что миграция `87fcef6f52ff_20260415_uute_advance_payment_model.py` и шаблон `backend/alembic/script.py.mako` существуют только на prod-сервере (`~/uute-project/`) и никогда не коммитились в git. Миграция физически применена в prod-БД (создала колонки `advance_amount`, `advance_paid_at`, `payment_method`, …), но на чистой БД (новый стенд, CI) `alembic upgrade head` их не создаст — модель `Order` при первом запросе упадёт. Восстановлено путём: вставки миграции в репозиторий и корректировки `down_revision` у `20260416_uute_signed_contract_enums`, чтобы цепочка стала линейной.
- **Шаги выполнения**:
  - [x] Получено содержимое миграции и `script.py.mako` с prod (`ubuntu@n8n:~/uute-project`)
  - [x] Проверено, что на prod `alembic_version` = `20260416_uute_tu_parsed_notification`; колонки `advance_amount`/`advance_paid_at` присутствуют в модели `Order`, но ни одна git-миграция их не создаёт
  - [x] Подтверждено отсутствие пересечений с другими миграциями (enum-значения, добавляемые `87fcef6f52ff`, уникальны; все остальные `ALTER TYPE ADD VALUE` идемпотентны за счёт `IF NOT EXISTS` / `DO $body$`)
  - [x] Добавлены `backend/alembic/versions/87fcef6f52ff_20260415_uute_advance_payment_model.py` и `backend/alembic/script.py.mako`
  - [x] В `20260416_uute_signed_contract_enums.py` переключён `down_revision` на `"87fcef6f52ff"`
  - [x] Проверен граф миграций (скриптом Python): одна голова `20260416_uute_tu_parsed_notification`, линейная цепочка из 12 ревизий от `20260402_uute_fc`
  - [x] Записи в `docs/changelog.md` и `docs/tasktracker.md`
- **Риски и mitigation**:
  - На prod `alembic upgrade head` = nothing to do (current = head). Проверено вручную.
  - На dev/CI clean БД вся цепочка применится линейно (12 ревизий).
  - Downgrade миграций теперь проходит через `87fcef6f52ff`; если кто-то делал `alembic downgrade` до `20260412_uute_calc_configs` — теперь придётся откатиться через `87fcef6f52ff` (это снимет и колонки, и index). Для prod это не используется.
- **Зависимости**: блокирует деплой раздела 2 аудита до мерджа. После мерджа — безопасно делать `docker compose up -d --build backend`.
- **Follow-up (раздел 3 аудита)**: в фазе A3 (GitHub Actions CI) обязательно добавить job «alembic upgrade head на пустой Postgres» — это моментально ловило бы такие расхождения.

## Задача: Раздел 3 аудита — roadmap поддерживаемости и архитектуры (2026-04-20)
- **Статус**: В процессе (утверждение плана)
- **Описание**: Составлен подробный roadmap реализации раздела 3 аудита 2026-04-20 (архитектурные проблемы: «толстые» модули, async/sync смешивание, legacy-статусы, нетипизированные JSONB, несогласованный `FileCategory`, захардкоженные пути, отсутствие CI/инструментов, неиспользуемые зависимости, Celery-конфиг, миграции без единого стиля, отсутствие индексов). Документ определяет 6 фаз выполнения, последовательность ~18 PR, критерии готовности и риски.
- **Шаги выполнения**:
  - [x] Написан roadmap и сохранён в [`docs/plans/2026-04-20-audit-section-3-maintainability-roadmap.md`](plans/2026-04-20-audit-section-3-maintainability-roadmap.md)
  - [x] Запись в `docs/changelog.md` и `docs/tasktracker.md`
  - [x] Согласованы ответы на «Открытые вопросы» (§ 13.1 roadmap, 2026-04-21):
    - Legacy-статусы — живых заявок нет, тестовые удаляемы → фаза C упрощается (C1+C2 можно одним PR)
    - FileCategory — через два релиза (non-breaking → breaking)
    - `admin.html` декомпозиция — решение отложено, пока планируем минимальный вариант
    - Sentry, `psycopg3`, GitHub Actions, отсутствие coverage gate — приняты дефолты, ждут финального подтверждения в первом PR фазы A
  - [ ] Фаза A (Фундамент): 4 PR — A1 пути, A2 pyproject+ruff+mypy+pre-commit, A3 GitHub Actions CI, A4 frontend baseline
  - [ ] Фаза B (Типизация данных): 3 PR — B1 Pydantic-схемы для JSONB, B2 нормализация `FileCategory`, B3 миграции + индексы
  - [ ] Фаза C (Упрощение стейт-машины): 2 PR — C1 data-миграция legacy-статусов, C2 удаление legacy из enum
  - [ ] Фаза D (Декомпозиция): 5 PR — D1 `tasks.py`, D2 `email_service.py`, D3 `contract_generator.py`, D4 async/sync граница, D5 Celery hardening
  - [ ] Фаза E (Frontend): 4 PR — E1 typed API, E2 vitest, E3 `admin.html` модули, E4 `upload.html`
  - [ ] Фаза F (Зависимости): 1 PR — F1 унификация на `psycopg[binary] v3`
- **Зависимости**: разделы 1 и 2 аудита закрыты (`chore/audit-cleanup-docs`, `security/audit-hardening`). Строгий порядок фаз: A → B → C → D → F; E параллельно после A.
- **Оценка**: ~35 чел·дней + ~10 дней резерв на ревью/регрессы ≈ 1.5–2 месяца wall-time при 50 % загрузке.

## Задача: Срочные правки безопасности (раздел 2 аудита, 2026-04-20)
- **Статус**: Завершена
- **Описание**: Закрыты пункты 1, 2, 3, 6 раздела «Срочно (безопасность)» из аудита. Пункт 4 (rate-limit `/landing/*`) согласовано вынести на уровень Caddy в отдельной задаче. Пункт 5 (`.gitignore`) уже закрыт в предыдущей задаче 2026-04-20.
- **Шаги выполнения**:
  - [x] CORS: `Settings.cors_origins`, дефолт `["https://constructproject.ru"]`, `main.py` использует whitelist вместо `*`
  - [x] `verify_admin_key`: `secrets.compare_digest`, deprecated `_k` с WARNING в логах и маскированным выводом ключа
  - [x] `config.py`: `admin_api_key` (≥16 симв.), `openrouter_api_key`, `smtp_password` без дефолтов — `Settings()` падает на старте без них
  - [x] `landing.py`: `except Exception: pass` → `logger.exception(...)`
  - [x] `backend/.env.example`: разметка `[REQUIRED]`, `CORS_ORIGINS`, инструкция по генерации `ADMIN_API_KEY`
  - [x] Smoke-тесты: `Settings()` без env падает с ожидаемой ошибкой; с env — стартует; CORS_ORIGINS парсится из JSON; `verify_admin_key` отрабатывает header/`_k`/wrong/missing
  - [x] `python -m compileall backend/app` — без ошибок; `ReadLints` — чисто
  - [x] Обновлены `CLAUDE.md`, `docs/changelog.md`, `docs/tasktracker.md`
- **Зависимости / деплой**:
  - На сервере перед `docker compose up -d --build backend` убедиться, что в `~/uute-project/backend/.env` есть значения `ADMIN_API_KEY`, `OPENROUTER_API_KEY`, `SMTP_PASSWORD` и заполнен `CORS_ORIGINS` (JSON-список с прод-доменом). Без этого backend упадёт на старте.
  - Следующий шаг — раздел 3 аудита (поддерживаемость): декомпозиция `tasks.py` / `email_service.py` / `contract_generator.py`, типизация JSONB, нормализация enum.

## Задача: Уборка документации и репозитория после аудита (2026-04-20)
- **Статус**: Завершена
- **Описание**: По итогам полного аудита проекта закрыт пункт 1 рекомендаций — устранён мусор в репозитории, архивированы завершённые трекеры/планы, переименованы файлы с проблемными именами, синхронизированы ссылки в коде и документации, актуализирован `CLAUDE.md`.
- **Шаги выполнения**:
  - [x] Создан `docs/archive/2026-Q2/` с подкаталогами `plans/`, `superpowers/plans/`, `superpowers/specs/`
  - [x] Перенесены завершённые трекеры: `payment-advance-tasktracker.md`, `smart-survey-tasktracker.md`, `two-option-order-tasktracker.md`, `tasktracker-soprovod.md`, `tasktrecker-otchet-parsing.md`, `tasktrecker-progrssbar.md`, `plan-unified-upload-contract.md`
  - [x] Перенесены реализованные планы: `docs/plans/2026-04-16-*.md` (5 шт), `docs/superpowers/plans/*` (6 шт), `docs/superpowers/specs/*` (3 шт); пустые каталоги удалены
  - [x] Удалены: `backup_20260411.sql`, `frontend/.env`, `cursorrules`, `.cursor/rules/calculator-config-design.md:Zone.Identifier`, дубликат `docs/opros_list_form.pdf`, `docs/rekvizit_acc.md` (с реальными реквизитами; не был в git)
  - [x] Переименованы: `docs/kontrakt_ukute_template (2).md` → `docs/kontrakt_ukute_template.md`; `docs/scheme-generator-roadmap (1).md` → `docs/scheme-generator-roadmap.md`
  - [x] Перенесён `docs/cities_from_table1.md` → `backend/calculator_templates/cities_from_table1.md`
  - [x] Обновлён `.gitignore`: `*.sql`, `*Zone.Identifier`, `docs/rekvizit_acc.md`, `docs/secrets/`, `.secrets/`
  - [x] Обновлены ссылки на переименованные/перенесённые файлы: `docs/project.md`, `docs/changelog.md`, `docs/tasktracker.md`, `backend/app/services/contract_generator.py`
  - [x] `frontend/package.json`: `name` → `uute-landing`, добавлены `description` и `version` `0.1.0`
  - [x] `CLAUDE.md`: актуализирована стейт-машина (`OrderStatus` с веткой оплаты и замечаний РСО), раздел «Текущий статус разработки» под фактический production, структура `docs/` с `archive/`
  - [x] Записи в `docs/changelog.md` и `docs/tasktracker.md`
- **Зависимости**: следующий шаг аудита — раздел 2 (срочные правки безопасности: CORS, `verify_admin_key`, дефолты секретов, rate-limit)

## Задача: SVG библиотека условных обозначений и ГОСТ-рамка для схем УУТЭ (2026-04-20)
- **Статус**: Завершена
- **Описание**: Реализованы чисто строковые генераторы SVG для инженерных схем теплоснабжения и обёртки чертежных форматов A3/A4 с основной надписью; без внешних зависимостей, таблица параметров тепловычислителя на `<rect>`/`<text>`.
- **Шаги выполнения**:
  - [x] Добавить `scheme_svg_elements.py` с элементами и вспомогательными функциями
  - [x] Добавить `scheme_gost_frame.py` с `gost_frame_a3` / `gost_frame_a4`
  - [x] Обновить `docs/project.md`, `docs/changelog.md`, `docs/tasktracker.md`
- **Зависимости**: дальнейшая интеграция с превью/экспортом схем (вне этого коммита)

## Задача: Автоматизация принципиальных схем ИТП — конфиг и маппинг (2026-04-19)
- **Статус**: Завершена
- **Описание**: Заложить основу для генерации принципиальных схем теплового пункта: Pydantic-схемы выбора одной из 8 типовых конфигураций, проверка допустимых сочетаний (зависимая/независимая, клапан, ГВС, вентиляция), русские подписи для UI и извлечение подстановок в SVG из `parsed_params` заявки (`Order.survey_data` / последующая интеграция с `FileCategory.HEAT_SCHEME` — вне этого коммита).
- **Шаги выполнения**:
  - [x] Реализовать `backend/app/schemas/scheme.py` (`SchemeType`, `SchemeConfig`, `SchemeParams`, API-модели)
  - [x] Реализовать `backend/app/services/scheme_service.py` (маппинг, метки, `extract_scheme_params_from_parsed`)
  - [x] Добавить запись в `docs/changelog.md` и `docs/tasktracker.md`
- **Зависимости**: ветка `feature/avtomatizaciya-postroeniya-shem`, структура `TUParsedData` в `backend/app/services/tu_schema.py`

## Задача: DOCX договор — шаблон v2 и компактная вёрстка (2026-04-19)
- **Статус**: Завершена
- **Описание**: Синхронизировать генератор договора с новым шаблоном `kontrakt_ukute_template.md` и сделать компактную вёрстку договора: шрифт 10 pt, минимальные интервалы между строками и абзацами.
- **Шаги выполнения**:
  - [x] Сверить новый шаблон `docs/kontrakt_ukute_template.md` с `contract_generator.py`
  - [x] Обновить тексты разделов 1–15 и приложений 1–3 в генераторе
  - [x] Добавить компактный стиль параграфов для договора и таблиц
  - [x] Обновить `docs/project.md`, `docs/changelog.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/app/services/contract_generator.py`, `docs/kontrakt_ukute_template.md`

## Задача: DOCX договор — вставка ТУ и контроль размера (2026-04-19)
- **Статус**: Завершена
- **Описание**: Встроить страницы PDF ТУ в Приложение 2 договора с лестницей DPI и fallback без растра при превышении ~25 МБ; передавать путь к ТУ и поля из `parsed_params` из Celery-задач.
- **Шаги выполнения**:
  - [x] PyMuPDF в `requirements.txt`, helpers рендера/очистки PNG и цикл `generate_contract`
  - [x] Обновить `process_card_and_contract` и `process_company_card_and_send_contract`
  - [x] Актуализировать `docs/project.md`, `docs/changelog.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/app/services/contract_generator.py`, `backend/app/services/tasks.py`

## Задача: Безопасный predicate миграции статуса замечаний РСО (2026-04-16)
- **Статус**: Завершена
- **Описание**: Сделать безопасной исходную Alembic-миграцию `20260416_uute_rso_remarks_status`, чтобы backfill в `RSO_REMARKS_RECEIVED` выполнялся только для заявок без `final_paid_at` и не возвращал уже обработанные замечания после более нового `GENERATED_PROJECT`.
- **Шаги выполнения**:
  - [x] Усилить регрессионный тест `backend/tests/test_rso_status_migration.py` под итоговый безопасный predicate
  - [x] Добавить в `backend/alembic/versions/20260416_uute_rso_remarks_status.py` guard `o.final_paid_at IS NULL`
  - [x] Сохранить в исходной миграции `autocommit_block()` и хронологию `latest_remarks_at >= latest_project_at`
  - [x] Удалить follow-up backfill-файлы как лишние для финального варианта
  - [x] Обновить `docs/changelog.md`, `docs/project.md`, `docs/tasktracker.md`
- **Зависимости**: `backend/alembic/versions/20260416_uute_rso_remarks_status.py`

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
- **Описание**: Реализация плана [`docs/archive/2026-Q2/tasktrecker-progrssbar.md`](archive/2026-Q2/tasktrecker-progrssbar.md): 24 ч до авто-`info_request`, флаги и 409 для дублей, письмо инженеру после `client-upload-done`, прогресс XHR для `generated_project` в админке.
- **Шаги выполнения**:
  - [x] Модель `waiting_client_info_at`, миграция, `process_due_info_requests` + правки `send_reminders` / `send_info_request_email`
  - [x] `has_successful_email`, `CLIENT_DOCUMENTS_RECEIVED`, шаблон и Celery-уведомление
  - [x] `OrderResponse`: `info_request_sent`, `reminder_sent`; админка и 409 в `emails.py`
  - [x] `docs/changelog.md`, `docs/project.md`, актуализация плана в `archive/2026-Q2/tasktrecker-progrssbar.md`
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
  - [x] Задачи 1–5 по плану [`docs/archive/2026-Q2/smart-survey-tasktracker.md`](archive/2026-Q2/smart-survey-tasktracker.md)
- **Зависимости**: сегментация `OrderType` custom/express; эндпоинт `POST /landing/orders/{id}/survey`

## Задача: Сегментация клиентов — два варианта заказа (Экспресс / Индивидуальный)
- **Статус**: В работе
- **Описание**: Клиент выбирает тип проекта в калькуляторе. Экспресс — на базе Эско 3Э, скидка 50%. Индивидуальный — полная цена, опросный лист. Подробный план: [`docs/archive/2026-Q2/two-option-order-tasktracker.md`](archive/2026-Q2/two-option-order-tasktracker.md).
- **Шаги выполнения**:
  - [x] Задача 1: `OrderType` enum, поля `order_type` и `survey_data` в модели и схемах
  - [x] Задача 2: эндпоинт `POST /landing/order` принимает и сохраняет `order_type`
  - [x] Задача 3: две карточки в калькуляторе (фронтенд)
  - [x] Задача 4: форма и сценарии опроса на upload-странице (см. умный опрос, `archive/2026-Q2/smart-survey-tasktracker.md`)
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
  - [x] `docs/changelog.md`, `docs/project.md`, [`docs/archive/2026-Q2/tasktrecker-otchet-parsing.md`](archive/2026-Q2/tasktrecker-otchet-parsing.md)
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
