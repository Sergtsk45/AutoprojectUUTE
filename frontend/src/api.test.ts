/**
 * @file: frontend/src/api.test.ts
 * @description: Unit-тесты транспортного слоя лендинга (`./api.ts`).
 *   Фаза E2 roadmap аудита — фиксирует контракт фронта → бэкенд:
 *     • URL + метод + заголовки + сериализация тела;
 *     • разбор FastAPI-ошибок (string detail, validation-массив `[{msg}]`, HTTP fallback);
 *     • multipart-контракт (Content-Type должен ставить браузер, не мы);
 *     • учёт `VITE_API_BASE_URL` из окружения.
 *
 * @dependencies: vitest (environment=node — FormData/URL/fetch уже нативны в Node 20)
 * @created: 2026-04-22 (E2)
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  createOrder,
  requestSample,
  sendKpRequest,
  sendPartnershipRequest,
  type OrderCreatedResponse,
  type OrderRequest,
  type PartnershipRequest,
  type SimpleResponse,
} from './api';

// ── Фикстуры ─────────────────────────────────────────────────────────────────

const SIMPLE_OK: SimpleResponse = { success: true, message: 'ok' };

const ORDER_CREATED: OrderCreatedResponse = {
  order_id: 'ord-123',
  upload_url: 'https://example.test/upload/ord-123',
  message: 'Заявка создана',
};

const ORDER_PAYLOAD: OrderRequest = {
  client_name: 'Иван Иванов',
  client_email: 'ivan@example.test',
  client_phone: '+7 900 000-00-00',
  client_organization: null,
  object_address: 'ул. Строителей, д. 5',
  object_city: 'Москва',
  circuits: 2,
  price: 40000,
  order_type: 'express',
};

const PARTNERSHIP_PAYLOAD: PartnershipRequest = {
  name: 'Пётр Петров',
  company: 'ООО «Ромашка»',
  email: 'petr@partner.test',
  phone: '+7 901 111-11-11',
};

// ── Хелперы ──────────────────────────────────────────────────────────────────

/**
 * Создаёт минималистичный Response-совместимый объект для мока fetch.
 * `Response` в Node 20 поддерживается натично, но конструктор не принимает
 * произвольные status-текст, поэтому проще вернуть объект, совместимый по
 * форме с тем, что читает `api.ts` (ok, status, json()).
 */
function mockResponse<T>(body: T, { ok = true, status = 200 } = {}): Response {
  return {
    ok,
    status,
    json: async () => body,
  } as unknown as Response;
}

function useFetchMock() {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

// ── Теститы ──────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('requestSample', () => {
  it('POSTs JSON на /api/v1/landing/sample-request и возвращает SimpleResponse', async () => {
    const fetchMock = useFetchMock();
    fetchMock.mockResolvedValueOnce(mockResponse(SIMPLE_OK));

    const result = await requestSample('user@example.test');

    expect(result).toEqual(SIMPLE_OK);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('/api/v1/landing/sample-request');
    expect(init).toMatchObject({ method: 'POST' });
    expect((init as RequestInit).headers).toEqual({ 'Content-Type': 'application/json' });
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({ email: 'user@example.test' });
  });

  it('бросает Error с полем detail (строка) при 4xx', async () => {
    const fetchMock = useFetchMock();
    fetchMock.mockResolvedValueOnce(
      mockResponse({ detail: 'email уже в базе' }, { ok: false, status: 400 }),
    );

    await expect(requestSample('dup@example.test')).rejects.toThrow('email уже в базе');
  });

  it('бросает Error по первой валидационной ошибке FastAPI (массив detail)', async () => {
    const fetchMock = useFetchMock();
    fetchMock.mockResolvedValueOnce(
      mockResponse(
        { detail: [{ msg: 'value is not a valid email address' }] },
        { ok: false, status: 422 },
      ),
    );

    await expect(requestSample('broken')).rejects.toThrow('value is not a valid email address');
  });

  it('бросает HTTP-fallback при отсутствии тела ответа', async () => {
    const fetchMock = useFetchMock();
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => {
        throw new Error('not json');
      },
    } as unknown as Response);

    await expect(requestSample('user@example.test')).rejects.toThrow('Ошибка сервера');
  });
});

describe('createOrder', () => {
  it('POSTs payload и возвращает OrderCreatedResponse', async () => {
    const fetchMock = useFetchMock();
    fetchMock.mockResolvedValueOnce(mockResponse(ORDER_CREATED));

    const result = await createOrder(ORDER_PAYLOAD);

    expect(result).toEqual(ORDER_CREATED);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('/api/v1/landing/order');
    expect(init).toMatchObject({ method: 'POST' });
    expect(JSON.parse((init as RequestInit).body as string)).toEqual(ORDER_PAYLOAD);
  });

  it('бросает Error с detail при отказе бэка', async () => {
    const fetchMock = useFetchMock();
    fetchMock.mockResolvedValueOnce(
      mockResponse({ detail: 'order_type must be express|custom' }, { ok: false, status: 422 }),
    );

    await expect(createOrder(ORDER_PAYLOAD)).rejects.toThrow('order_type must be express|custom');
  });
});

describe('sendPartnershipRequest', () => {
  it('POSTs payload и возвращает SimpleResponse', async () => {
    const fetchMock = useFetchMock();
    fetchMock.mockResolvedValueOnce(mockResponse(SIMPLE_OK));

    const result = await sendPartnershipRequest(PARTNERSHIP_PAYLOAD);

    expect(result).toEqual(SIMPLE_OK);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('/api/v1/landing/partnership');
    expect(init).toMatchObject({ method: 'POST' });
    expect(JSON.parse((init as RequestInit).body as string)).toEqual(PARTNERSHIP_PAYLOAD);
  });
});

describe('sendKpRequest', () => {
  it('передаёт FormData без ручного Content-Type (чтобы браузер поставил boundary)', async () => {
    const fetchMock = useFetchMock();
    fetchMock.mockResolvedValueOnce(mockResponse(SIMPLE_OK));

    const fd = new FormData();
    fd.append('organization', 'ООО «КП»');
    fd.append('responsible_name', 'Иванов');
    fd.append('phone', '+7 999 000-00-00');
    fd.append('email', 'kp@example.test');
    fd.append(
      'tu_file',
      new Blob([new Uint8Array([0x25, 0x50, 0x44, 0x46])], { type: 'application/pdf' }),
      'tu.pdf',
    );

    const result = await sendKpRequest(fd);

    expect(result).toEqual(SIMPLE_OK);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('/api/v1/landing/kp-request');
    expect(init).toMatchObject({ method: 'POST' });
    // Ключевая инварианта: нет Content-Type (браузер подставит multipart/form-data; boundary=…)
    expect((init as RequestInit).headers).toBeUndefined();
    expect((init as RequestInit).body).toBe(fd);
  });

  it('пробрасывает detail-ошибку бэка', async () => {
    const fetchMock = useFetchMock();
    fetchMock.mockResolvedValueOnce(
      mockResponse({ detail: 'Файл слишком большой (максимум 20 МБ)' }, { ok: false, status: 413 }),
    );

    await expect(sendKpRequest(new FormData())).rejects.toThrow(
      'Файл слишком большой (максимум 20 МБ)',
    );
  });
});

describe('API_BASE override', () => {
  it('использует VITE_API_BASE_URL, когда он задан', async () => {
    // Важный момент: `API_BASE` читается один раз при импорте модуля.
    // Чтобы проверить override, надо: стабить env → импортировать модуль через
    // динамический импорт с vi.resetModules().
    vi.resetModules();
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v2');

    const fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockResolvedValueOnce(mockResponse(SIMPLE_OK));

    const freshApi = await import('./api');
    await freshApi.requestSample('a@b.test');

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.test/v2/landing/sample-request',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
