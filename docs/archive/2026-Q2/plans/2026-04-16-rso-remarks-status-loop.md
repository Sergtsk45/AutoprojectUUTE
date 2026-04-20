# RSO Remarks Status Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated post-project status for RSO remarks so engineers clearly see when a project returned for correction and can resend the corrected package with a new cover letter.

**Architecture:** Keep the existing post-project payment flow, but insert a focused status `rso_remarks_received` between `awaiting_final_payment` and the resend action. The backend owns the transition loop, while API-derived flags keep `admin.html` and `payment.html` consistent even after older remark files remain attached to the order.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, static admin/payment HTML, stdlib `unittest`

---

### Task 1: Post-project state model

**Files:**
- Modify: `backend/app/models/models.py`
- Create: `backend/alembic/versions/20260416_uute_rso_remarks_status.py`
- Test: `backend/tests/test_post_project_status.py`

- [ ] Add failing tests for the new status loop and derived flag semantics.
- [ ] Extend `OrderStatus` and `ALLOWED_TRANSITIONS` with `rso_remarks_received`.
- [ ] Add Alembic migration for the new `order_status` enum label.

### Task 2: Backend flow transitions

**Files:**
- Modify: `backend/app/api/landing.py`
- Modify: `backend/app/api/pipeline.py`
- Modify: `backend/app/services/tasks.py`
- Modify: `backend/app/schemas/schemas.py`
- Test: `backend/tests/test_post_project_status.py`

- [ ] Make `upload-rso-remarks` move the order into `rso_remarks_received`.
- [ ] Make `resend_corrected_project` available only from `rso_remarks_received`.
- [ ] Return the order back to `awaiting_final_payment` after a successful resend.
- [ ] Recompute post-project flags from status plus file chronology so stale remark files do not keep the order “stuck”.

### Task 3: Admin and client UI

**Files:**
- Modify: `backend/static/admin.html`
- Modify: `backend/static/payment.html`

- [ ] Add the new status label/color and action rules in the admin UI.
- [ ] Keep the payment page on the same post-project screen for `rso_remarks_received`, but show a clear “remarks received, engineer is updating the project” state.

### Task 4: Documentation and verification

**Files:**
- Modify: `docs/project.md`
- Modify: `docs/changelog.md`
- Modify: `docs/tasktracker.md`

- [ ] Update architecture docs for the new post-project status loop.
- [ ] Run focused tests and Python syntax checks.
