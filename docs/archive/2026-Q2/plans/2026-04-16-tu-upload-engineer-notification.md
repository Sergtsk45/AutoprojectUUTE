# Возврат email-уведомления инженеру после парсинга ТУ

**Goal:** Вернуть письмо инженеру сразу после успешного парсинга загруженного ТУ, когда в админке уже доступны распарсенные данные и заявка переведена в `waiting_client_info`.

**Architecture:** Точка постановки уведомления остаётся в Celery-цепочке после `check_data_completeness`, чтобы письмо уходило только после успешного завершения парсинга и записи `missing_params`. Для различения события "ТУ распарсено" и существующего события "клиент завершил загрузку документов" добавляется отдельный `EmailType` и отдельный шаблон письма инженеру.

**Tech Stack:** FastAPI, Celery, SQLAlchemy, Jinja2, Alembic, unittest/pytest-compatible backend tests.

---

### Task 1: Регрессионный тест на очередь уведомления

**Files:**
- Create: `backend/tests/test_tu_parsed_engineer_notification.py`
- Modify: `backend/app/services/tasks.py`
- Test: `backend/tests/test_tu_parsed_engineer_notification.py`

- [ ] Написать падающий тест на то, что `check_data_completeness` после перехода в `waiting_client_info` ставит в очередь отдельное уведомление инженеру.
- [ ] Запустить тест и убедиться, что он падает по отсутствию вызова новой задачи.
- [ ] Реализовать минимальную правку в `tasks.py`.
- [ ] Снова запустить тест и убедиться, что он проходит.

### Task 2: Отдельный email-тип и письмо инженеру

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/services/email_service.py`
- Create: `backend/templates/emails/tu_parsed_notification.html`
- Create: `backend/alembic/versions/20260416_uute_tu_parsed_notification_enum.py`

- [ ] Добавить отдельный `EmailType` для события "ТУ распарсено".
- [ ] Добавить render/send-хелперы письма инженеру с `missing_params`, статусом ожидания документов и ссылкой на админку.
- [ ] Добавить шаблон письма.
- [ ] Добавить Alembic-миграцию для нового enum-label в PostgreSQL.

### Task 3: Документация и верификация

**Files:**
- Modify: `docs/project.md`
- Modify: `docs/changelog.md`
- Modify: `docs/tasktracker.md`

- [ ] Обновить архитектурное описание email/Celery-цепочки.
- [ ] Добавить запись в changelog и tasktracker.
- [ ] Запустить релевантные тесты/проверки и зафиксировать результат.
