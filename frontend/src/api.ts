const API_BASE = '/api/v1';

export interface OrderRequest {
  client_name: string;
  client_email: string;
  client_phone?: string;
  client_organization?: string;
  object_address?: string;
  object_city: string;
  circuits?: number;
  price?: number;
  order_type?: string;
}

export interface OrderCreatedResponse {
  order_id: string;
  upload_url: string;
  message: string;
}

export interface SimpleResponse {
  success: boolean;
  message: string;
}

export async function requestSample(email: string): Promise<SimpleResponse> {
  const resp = await fetch(`${API_BASE}/landing/sample-request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Ошибка сервера' }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function createOrder(data: OrderRequest): Promise<OrderCreatedResponse> {
  const resp = await fetch(`${API_BASE}/landing/order`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Ошибка сервера' }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function sendPartnershipRequest(data: {
  name: string;
  company: string;
  email: string;
  phone: string;
}): Promise<SimpleResponse> {
  const resp = await fetch(`${API_BASE}/landing/partnership`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Ошибка сервера' }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function sendKpRequest(formData: FormData): Promise<SimpleResponse> {
  const resp = await fetch(`${API_BASE}/landing/kp-request`, {
    method: 'POST',
    body: formData,
    // Content-Type не указываем — браузер сам ставит multipart/form-data с boundary
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Ошибка сервера' }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}
