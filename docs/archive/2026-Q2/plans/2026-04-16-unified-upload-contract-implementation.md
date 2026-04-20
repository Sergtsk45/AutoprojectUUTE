# Plan: Unified Upload + Contract Flow

**Created:** 2026-04-16  
**Orchestration:** orch-2026-04-16-04-49-unified-upload-contract  
**Status:** Ready  
**Goal:** Перевести новые заявки на единый путь `new → ... → completed` с общим сбором документов/реквизитов, отправкой договора до проекта, раздельными `confirm-advance` и отправкой проекта, добавлением `signed_contract`.

## Critical Path Tasks

1. **UPC-001 — State machine and enum migration** (Critical)
   - Files: `backend/app/models/models.py`, `backend/alembic/versions/<new_migration>.py`
   - Add `FileCategory.SIGNED_CONTRACT`, `EmailType.SIGNED_CONTRACT_NOTIFICATION`
   - Update transitions for new path (`CLIENT_INFO_RECEIVED -> CONTRACT_SENT`), keep legacy transitions

2. **UPC-002 — company_card in mandatory docs** (Critical, depends on UPC-001)
   - Files: `backend/app/services/param_labels.py`
   - Include `company_card` in `CLIENT_DOCUMENT_PARAM_CODES` and labels
   - Keep migration helper behavior stable for old `missing_params`

3. **UPC-003 — completeness always to waiting_client_info** (Critical, depends on UPC-002)
   - Files: `backend/app/services/tasks.py` (`check_data_completeness`)
   - Stop routing new flow through `DATA_COMPLETE`
   - Ensure no backward status regression for orders already past this stage

4. **UPC-004 — unified process_card_and_contract chain** (Critical, depends on UPC-003)
   - Files: `backend/app/services/tasks.py`
   - Refactor `process_client_response` and add `process_card_and_contract`
   - Combine parse requisites + generate docs + send contract + transition + engineer notification

5. **UPC-005 — landing API extension for contract_sent and signed upload** (High, depends on UPC-004)
   - Files: `backend/app/api/landing.py`, `backend/app/schemas/schemas.py`
   - Extend `GET /upload-page` payload for `contract_sent`
   - Add `POST /orders/{id}/upload-signed-contract` (public)

6. **UPC-006 — email contract flow updates** (High, depends on UPC-004)
   - Files: `backend/app/services/email_service.py`, `backend/templates/emails/contract_delivery.html`, `backend/templates/emails/info_request.html`, `backend/templates/emails/client_documents_received.html`
   - Add `upload_url` and revised contract instructions
   - Add engineer notification for signed contract upload

7. **UPC-007 — split confirm-advance from project delivery** (High, depends on UPC-004)
   - Files: `backend/app/api/pipeline.py`, `backend/app/services/tasks.py`
   - Keep `confirm-advance` only as `CONTRACT_SENT -> ADVANCE_PAID`
   - Move final project send to explicit approve action from `ADVANCE_PAID`

8. **UPC-008 — upload page scenarios** (High, depends on UPC-005, UPC-006)
   - Files: `backend/static/upload.html`
   - `waiting_client_info`: enforce `company_card`
   - `contract_sent`: separate signed-contract upload UI and post-upload state message

9. **UPC-009 — backward compatibility and safe migration** (High, depends on UPC-001, UPC-005, UPC-007)
   - Files: `backend/app/models/models.py`, `backend/app/api/landing.py`, `backend/static/payment.html`, `backend/static/admin.html`, `backend/app/services/tasks.py`
   - Keep legacy statuses/routes usable for old orders (`awaiting_contract`, `data_complete`, `review`, etc.)
   - Guard new logic by order status/versioned branch conditions

10. **UPC-010 — docs and release notes** (Medium, depends on UPC-008, UPC-009)
    - Files: `docs/changelog.md`, `docs/tasktracker.md`, `docs/project.md`
    - Record behavior/API changes and migration notes

## Compatibility and Migration Risks

- Legacy orders in `AWAITING_CONTRACT` can break if payment page endpoints are removed too early.
- Existing Celery retries for `process_company_card_and_send_contract` can conflict with new unified task and create duplicate emails.
- Admin UX assumptions around `approve` currently tied to early statuses will regress if backend logic changes first.
- Old `missing_params` payloads may still contain deprecated codes and produce wrong client prompts.
- Enum migration errors in Postgres (`ALTER TYPE`) can block deploy if value casing mismatches existing enum persistence strategy.

## Safe Migration Strategy

- Deploy backend changes in two phases:
  1) Additive (new enums/endpoints/tasks, no removals)
  2) Switch defaults for new orders only, then cleanup
- Keep `payment` flow and old status transitions intact for in-flight orders.
- Add idempotency check on contract email send (existing `EmailLog`) before every retry.
- Feature-guard UI branch for `contract_sent` while preserving previous screens.
- Run data repair script for legacy `missing_params` before forcing `company_card` requirement.

## Verification Matrix (minimum)

- **UPC-001..003**
  - Unit: transition guards and enum serialization in ORM
  - DB: migration apply on staging clone and rollback smoke check
  - API smoke: create order -> TU parse -> reaches `waiting_client_info`

- **UPC-004..006**
  - Integration: `client-upload-done` with/without `company_card`
  - Celery: happy path and retry path for unified task; no duplicate `contract_delivery`
  - Email render snapshot: `info_request`, `contract_delivery`, signed-contract notification

- **UPC-005 & UPC-008**
  - Contract_sent payload contract fields in `GET /upload-page`
  - Public upload of signed contract validates type/size and persists `SIGNED_CONTRACT`
  - Browser test: user can complete both `waiting_client_info` and `contract_sent` scenarios

- **UPC-007**
  - API: `confirm-advance` only changes status/time markers
  - API: `approve` requires `ADVANCE_PAID` and `generated_project`
  - Regression: `confirm-final` path unchanged

- **UPC-009..010**
  - Regression matrix for legacy statuses (`awaiting_contract`, `review`, `awaiting_final_payment`)
  - Manual admin flow for old and new orders in parallel
  - Docs consistency check with final status diagram
