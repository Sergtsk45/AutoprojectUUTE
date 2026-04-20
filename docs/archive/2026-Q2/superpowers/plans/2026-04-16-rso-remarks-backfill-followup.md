# RSO Remarks Backfill Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Догнать исторические post-project заявки с уже загруженными замечаниями РСО и перевести их в `rso_remarks_received`, чтобы статусная логика и UI больше не расходились.

**Architecture:** Не переписывать уже выпущенную миграцию `20260416_uute_rso_remarks_status.py`, а добавить отдельную идемпотентную Alembic-миграцию-догонялку. UI fallback по `order.has_rso_remarks` остаётся как защитный слой, а источником истины для новых и исторических заявок снова становится корректный статус в БД.

**Tech Stack:** Python 3.12, Alembic, SQLAlchemy, PostgreSQL enums, unittest, static admin UI docs

---

### Task 1: Backfill historical RSO remarks statuses

**Files:**
- Create: `backend/alembic/versions/20260416_uute_rso_remarks_status_backfill.py`
- Create: `backend/tests/test_rso_status_backfill_migration.py`
- Modify: `docs/changelog.md`
- Modify: `docs/tasktracker.md`
- Modify: `docs/project.md`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260416_uute_rso_remarks_status_backfill.py"
)


class RsoStatusBackfillMigrationTests(unittest.TestCase):
    def test_backfill_targets_historical_orders_with_rso_remarks(self) -> None:
        source = MIGRATION_PATH.read_text(encoding="utf-8")
        normalized = " ".join(source.replace('"', "'").split())

        self.assertIn("o.status = 'AWAITING_FINAL_PAYMENT'", normalized)
        self.assertIn("o.final_paid_at IS NULL", normalized)
        self.assertIn("WHERE f.order_id = o.id", normalized)
        self.assertIn("f.category = 'RSO_REMARKS'", normalized)
        self.assertIn("SET status = 'RSO_REMARKS_RECEIVED'", normalized)
        self.assertNotIn("latest_project_at", normalized)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest backend.tests.test_rso_status_backfill_migration -v`

Expected: FAIL because `backend/tests/test_rso_status_backfill_migration.py` and the new migration file do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
"""backfill historical rso remarks statuses

Revision ID: 20260416_uute_rso_remarks_status_backfill
Revises: 20260416_uute_rso_remarks_status
Create Date: 2026-04-16
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "20260416_uute_rso_remarks_status_backfill"
down_revision: Union[str, None] = "20260416_uute_rso_remarks_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        text(
            """
            UPDATE orders AS o
            SET status = 'RSO_REMARKS_RECEIVED'
            WHERE o.status = 'AWAITING_FINAL_PAYMENT'
              AND o.final_paid_at IS NULL
              AND EXISTS (
                SELECT 1
                FROM order_files AS f
                WHERE f.order_id = o.id
                  AND f.category = 'RSO_REMARKS'
              );
            """
        )
    )


def downgrade() -> None:
    pass
```

```markdown
## [2026-04-16] — Fix: догоняющий backfill статусов замечаний РСО

### Исправлено
- В [`backend/alembic/versions/20260416_uute_rso_remarks_status_backfill.py`](../backend/alembic/versions/20260416_uute_rso_remarks_status_backfill.py): добавлена отдельная миграция, которая переводит исторические заявки из `awaiting_final_payment` в `rso_remarks_received`, если замечания РСО уже загружены и финальная оплата ещё не подтверждена.
- В [`backend/tests/test_rso_status_backfill_migration.py`](../backend/tests/test_rso_status_backfill_migration.py): добавлен регрессионный тест на SQL-условия backfill без привязки к датам последнего проекта.
```

```markdown
## Задача: Догоняющий backfill статусов замечаний РСО (2026-04-16)
- **Статус**: Завершена
- **Описание**: Закрыть рассинхрон между историческими заказами с `RSO_REMARKS` и новым статусом `rso_remarks_received`, не переписывая уже выпущенную enum-миграцию.
- **Шаги выполнения**:
  - [x] Проверить текущую миграцию `20260416_uute_rso_remarks_status.py` и подтвердить, что она пропускает часть старых заказов по условию дат
  - [x] Добавить отдельную Alembic-миграцию для `AWAITING_FINAL_PAYMENT` + `RSO_REMARKS` + `final_paid_at IS NULL`
  - [x] Добавить регрессионный тест на SQL backfill
  - [x] Обновить `docs/changelog.md`, `docs/tasktracker.md`, `docs/project.md`
- **Зависимости**: `backend/alembic/versions/20260416_uute_rso_remarks_status.py`, `backend/static/admin.html`
```

```markdown
- в post-project ветке нельзя одновременно убирать legacy-derived ветку UI и переводить логику только на новый статус без полного data backfill для уже существующих заказов;
- если новый статус заменяет старое поведение, в том же PR должны идти и миграция данных, и временный UI fallback (`status || derived-flag`) до полной консистентности исторических записей.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest backend.tests.test_rso_status_backfill_migration backend.tests.test_rso_status_migration backend.tests.test_admin_post_project_actions -v`

Expected: PASS, including the new backfill regression and the existing admin fallback regression.

- [ ] **Step 5: Verify docs and lints**

Run: `python3 -m unittest backend.tests.test_rso_status_backfill_migration -v`

Run: `python3 -m compileall backend/app`

Expected: unittest passes; `compileall` exits 0.

- [ ] **Step 6: Commit**

```bash
git add \
  backend/alembic/versions/20260416_uute_rso_remarks_status_backfill.py \
  backend/tests/test_rso_status_backfill_migration.py \
  docs/changelog.md \
  docs/tasktracker.md \
  docs/project.md
git commit -m "fix(migration): backfill historical rso remarks status"
```
