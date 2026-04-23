/**
 * @file: backend/static/js/admin/utils.js
 * @description: Чистые UI-хелперы: форматтеры, escaper, badge-рендер, alert.
 *   Фаза E3 (минимальный вариант) — вынос из inline <script> в admin.html.
 *   Зависит от констант из config.js (STATUS_LABELS, STATUS_COLORS).
 * @created: 2026-04-22 (E3)
 */

// ── Badges (зависят от STATUS_COLORS / STATUS_LABELS из config.js) ──────────
function statusBadge(status) {
  const color = STATUS_COLORS[status] || '#9e9e9e';
  const label = STATUS_LABELS[status] || status;
  return `<span class="badge" style="background:${color};">${label}</span>`;
}

function orderTypeBadge(type) {
  if (type === 'custom') return '<span class="badge" style="background:#7c3aed;">Индивидуальный</span>';
  return '<span class="badge" style="background:#16a34a;">Экспресс</span>';
}

// ── Number formatting ──────────────────────────────────────────────────────
function formatNum(n) {
  return new Intl.NumberFormat('ru-RU').format(n);
}

function fmtNum(n) {
  if (n === null || n === undefined || n === '') return null;
  if (typeof n === 'number' && !Number.isFinite(n)) return null;
  if (typeof n === 'number') {
    if (Number.isInteger(n)) return String(n);
    return n.toFixed(6).replace(/\.?0+$/, '');
  }
  const p = parseFloat(n);
  return Number.isFinite(p) ? fmtNum(p) : String(n);
}

// ── URL helpers ────────────────────────────────────────────────────────────
function addKeyToUrl(url) {
  const u = new URL(url);
  u.searchParams.set('_k', getKey());
  return u.toString();
}

function isParsedParamsEmpty(params) {
  return !params || typeof params !== 'object' || Object.keys(params).length === 0;
}

// ── Alerts & escaping ──────────────────────────────────────────────────────
function showOrderAlert(type, msg) {
  const el = document.getElementById('orderAlert');
  el.textContent = msg;
  el.className = `alert ${type} visible`;
  if (type === 'success' || type === 'info') {
    setTimeout(() => { el.style.display = 'none'; }, 4000);
  }
}

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Date formatting ────────────────────────────────────────────────────────
function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

function formatDateFull(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' Б';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' КБ';
  return (bytes / (1024 * 1024)).toFixed(1) + ' МБ';
}
