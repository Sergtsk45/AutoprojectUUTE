/**
 * @file: frontend/src/api.ts
 * @description: Типизированный клиент публичного API лендинга.
 *   Типы входа/выхода импортируются из `./api/types.ts`, который
 *   автоматически генерируется из OpenAPI-спеки бэкенда скриптом
 *   `scripts/generate-api-types.sh` (фаза E1 аудита, 2026-04-22).
 *   Любое изменение Pydantic-схем на бэке → перегенерация → frontend-билд
 *   падает с типизированной ошибкой при рассинхроне.
 *
 *   Контракт с компонентами (EmailModal.tsx, KpRequestModal.tsx) сохранён:
 *   те же имена функций и порядок аргументов.
 *
 * @dependencies:
 *   - `./api/types.ts` (генерируется, не редактируется руками)
 *   - `VITE_API_BASE_URL` (ENV, см. `frontend/.env.example`)
 */

import type { components } from './api/types';

// Базовый URL API. Переопределяется через `VITE_API_BASE_URL` (см. `.env.example`).
// По умолчанию — относительный путь; в prod backend отдаёт SPA и API с одного домена.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

// ── Типы (re-export из сгенерированной схемы) ───────────────────────────────
//
// Лёгкие алиасы, чтобы компоненты и тесты могли импортировать привычные имена
// без обращения к `components['schemas'][…]`. Точность типов — как у бэка.
export type OrderRequest = components['schemas']['OrderRequest'];
export type OrderCreatedResponse = components['schemas']['OrderCreatedResponse'];
export type SimpleResponse = components['schemas']['SimpleResponse'];
export type SampleRequest = components['schemas']['SampleRequest'];
export type PartnershipRequest = components['schemas']['PartnershipRequest'];
// KpRequest на бэке — multipart/form-data (Form-параметры + UploadFile),
// в OpenAPI представлен отдельной схемой body; клиент всё равно собирает
// FormData вручную, поэтому типы полей берём напрямую.
export type KpRequestFields = components['schemas']['KpRequest'];

// ── Внутренние утилиты ──────────────────────────────────────────────────────

interface ApiErrorDetail {
  detail?: string | Array<{ msg?: string }>;
}

async function handleJsonResponse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const err: ApiErrorDetail = await resp.json().catch(() => ({ detail: 'Ошибка сервера' }));
    const detail = err.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail) && detail[0]?.msg
          ? detail[0].msg
          : `HTTP ${resp.status}`;
    throw new Error(message);
  }
  return resp.json() as Promise<T>;
}

function jsonRequest<TBody>(path: string, body: TBody): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// ── Публичные эндпоинты лендинга ────────────────────────────────────────────

export async function requestSample(email: SampleRequest['email']): Promise<SimpleResponse> {
  const resp = await jsonRequest<SampleRequest>('/landing/sample-request', { email });
  return handleJsonResponse<SimpleResponse>(resp);
}

export async function createOrder(data: OrderRequest): Promise<OrderCreatedResponse> {
  const resp = await jsonRequest<OrderRequest>('/landing/order', data);
  return handleJsonResponse<OrderCreatedResponse>(resp);
}

export async function sendPartnershipRequest(
  data: PartnershipRequest,
): Promise<SimpleResponse> {
  const resp = await jsonRequest<PartnershipRequest>('/landing/partnership', data);
  return handleJsonResponse<SimpleResponse>(resp);
}

export async function sendKpRequest(formData: FormData): Promise<SimpleResponse> {
  const resp = await fetch(`${API_BASE}/landing/kp-request`, {
    method: 'POST',
    body: formData,
    // Content-Type не указываем — браузер сам ставит multipart/form-data с boundary
  });
  return handleJsonResponse<SimpleResponse>(resp);
}
