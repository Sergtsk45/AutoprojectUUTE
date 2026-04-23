/**
 * @file: backend/static/js/admin/admin.js
 * @description: Entry-скрипт админки: авторизация, fetch-хелперы, навигация,
 *   поллинги, список заявок, карточка заявки, действия над заявкой и email-log.
 *   Фаза E3 (минимальный вариант) — вынос из inline <script> в admin.html.
 *   Подключается последним: config.js → utils.js → views-parsed.js →
 *   views-calc.js → admin.js. Функции doLogin/doLogout/refreshList/showList/
 *   showOrderScreen/uploadAdminFile вызываются из HTML через inline
 *   onclick/onchange — они остаются в глобальной области (обычный <script>).
 * @created: 2026-04-22 (E3)
 */

// ── Auth ────────────────────────────────────────────────────────────────────
    function getKey() {
      return sessionStorage.getItem('admin_key') || '';
    }

    function setKey(k) {
      sessionStorage.setItem('admin_key', k);
    }

    function consumeOrderIdFromUrl() {
      const raw = new URLSearchParams(window.location.search).get('order');
      if (!raw || !ORDER_ID_URL_RE.test(raw.trim())) return null;
      const id = raw.trim();
      history.replaceState({}, '', window.location.pathname);
      return id;
    }

    function doLogout() {
      sessionStorage.removeItem('admin_key');
      showLoginScreen();
    }

    async function doLogin() {
      const input = document.getElementById('apiKeyInput');
      const key = input.value.trim();
      if (!key) return;

      const alert = document.getElementById('loginAlert');
      alert.className = 'alert';
      alert.style.display = 'none';

      try {
        const resp = await fetch(`${API_BASE}/orders?limit=1`, {
          headers: { 'X-Admin-Key': key }
        });
        if (resp.status === 401) {
          alert.textContent = 'Неверный API-ключ';
          alert.className = 'alert error visible';
          return;
        }
        setKey(key);
        const pending = sessionStorage.getItem('admin_pending_order_id');
        if (pending && ORDER_ID_URL_RE.test(pending)) {
          sessionStorage.removeItem('admin_pending_order_id');
          showOrderScreen(pending);
        } else {
          sessionStorage.removeItem('admin_pending_order_id');
          showListScreen();
        }
      } catch (e) {
        alert.textContent = 'Ошибка соединения с сервером';
        alert.className = 'alert error visible';
      }
    }

    document.addEventListener('DOMContentLoaded', () => {
      document.getElementById('apiKeyInput').addEventListener('keydown', e => {
        if (e.key === 'Enter') doLogin();
      });

      const orderFromUrl = consumeOrderIdFromUrl();
      if (!getKey() && orderFromUrl) {
        sessionStorage.setItem('admin_pending_order_id', orderFromUrl);
      }

      if (getKey()) {
        if (orderFromUrl) {
          showOrderScreen(orderFromUrl);
        } else {
          showListScreen();
        }
      } else {
        showLoginScreen();
      }
    });

// ── API helpers ─────────────────────────────────────────────────────────────
    async function apiFetch(path, opts = {}) {
      const resp = await fetch(API_BASE + path, {
        ...opts,
        headers: {
          'X-Admin-Key': getKey(),
          ...(opts.headers || {}),
        },
      });
      if (resp.status === 401) {
        sessionStorage.removeItem('admin_key');
        showLoginScreen();
        throw new Error('Требуется авторизация');
      }
      return resp;
    }

    async function apiJSON(path, opts = {}) {
      const resp = await apiFetch(path, opts);
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${resp.status}`);
      }
      return resp.json();
    }

// ── Navigation ──────────────────────────────────────────────────────────────
    function showLoginScreen() {
      document.getElementById('loginScreen').style.display = 'block';
      document.getElementById('listScreen').style.display = 'none';
      document.getElementById('orderScreen').style.display = 'none';
      clearInterval(refreshTimer);
    }

    function showListScreen() {
      document.getElementById('loginScreen').style.display = 'none';
      document.getElementById('listScreen').style.display = 'block';
      document.getElementById('orderScreen').style.display = 'none';
      stopWaitingEmailPoll();
      stopSendingProjectPoll();
      refreshList();
      clearInterval(refreshTimer);
      refreshTimer = setInterval(refreshList, 30000);
    }

    function showList() {
      showListScreen();
    }

    function showOrderScreen(orderId) {
      document.getElementById('loginScreen').style.display = 'none';
      document.getElementById('listScreen').style.display = 'none';
      document.getElementById('orderScreen').style.display = 'block';
      clearInterval(refreshTimer);
      stopParsingPoll();
      loadOrder(orderId);
    }

// ── Polls (waiting email / sending project / payment / parsing) ────────────
    function stopWaitingEmailPoll() {
      if (waitingEmailPollTimer !== null) {
        clearInterval(waitingEmailPollTimer);
        waitingEmailPollTimer = null;
      }
    }

    function startWaitingEmailPoll() {
      stopWaitingEmailPoll();
      waitingEmailPollTimer = setInterval(async () => {
        try {
          const order = await apiJSON(`/orders/${currentOrderId}`);
          renderOrder(order);
          if (order.status !== 'waiting_client_info') {
            stopWaitingEmailPoll();
          }
        } catch (e) {
          console.error('waitingEmailPoll:', e);
        }
      }, 30000); // каждые 30 сек
    }

    // ─────────────────────────────────────────────────────────────────────
    // Sending-project poll helpers
    // ─────────────────────────────────────────────────────────────────────
    function stopSendingProjectPoll() {
      if (sendingProjectPollTimer !== null) {
        clearInterval(sendingProjectPollTimer);
        sendingProjectPollTimer = null;
      }
    }

    function startSendingProjectPoll() {
      stopSendingProjectPoll();
      sendingProjectPollTimer = setInterval(async () => {
        try {
          const order = await apiJSON(`/orders/${currentOrderId}`);
          if (order.status !== 'advance_paid') {
            stopSendingProjectPoll();
            renderOrder(order);
          }
          // пока статус ещё advance_paid — не перерисовываем: кнопки остаются заблокированы
        } catch (e) {
          console.error('sendingProjectPoll:', e);
        }
      }, 5000); // каждые 5 сек
    }

    function startPaymentFlowPoll(fromStatus) {
      stopSendingProjectPoll();
      sendingProjectPollTimer = setInterval(async () => {
        try {
          const order = await apiJSON(`/orders/${currentOrderId}`);
          if (order.status !== fromStatus) {
            clearInterval(sendingProjectPollTimer);
            sendingProjectPollTimer = null;
            renderOrder(order);
          }
        } catch (e) {
          console.error('paymentFlowPoll:', e);
        }
      }, 5000);
    }

    async function approveProject(orderId, currentStatus) {
      if (!confirm('Отправить клиенту готовый проект? Действие доступно только после подтверждения аванса.')) return;
      const actionBtns = document.querySelectorAll('[id^="action_btn_"]');
      actionBtns.forEach(b => { b.disabled = true; });
      showOrderAlert('info', 'Выполняется…');
      try {
        await apiJSON(`/pipeline/${orderId}/approve`, { method: 'POST' });
        showOrderAlert('success', 'Готовый проект отправлен клиенту. Ожидаем перехода в следующий статус.');
        startPaymentFlowPoll(currentStatus);
      } catch (e) {
        showOrderAlert('error', 'Ошибка: ' + e.message);
        actionBtns.forEach(b => { b.disabled = false; });
      }
    }

    // ─────────────────────────────────────────────────────────────────────
    // Parsing poll helpers
    // ─────────────────────────────────────────────────────────────────────
    function stopParsingPoll() {
      if (parsingPollTimer !== null) {
        clearInterval(parsingPollTimer);
        parsingPollTimer = null;
      }
      parsingPollCount = 0;
    }

    function startParsingPoll() {
      stopParsingPoll();
      parsingPollBusy = false;

      const tick = async () => {
        if (parsingPollBusy) return;
        parsingPollBusy = true;
        try {
          parsingPollCount += 1;
          if (parsingPollCount > 60) {
            stopParsingPoll();
            showOrderAlert('error', 'Анализ занимает больше времени, чем обычно. Обновите страницу через несколько минут.');
            return;
          }

          const order = await apiJSON(`/orders/${currentOrderId}`);
          const st = order.status;

          if (st === 'error') {
            stopParsingPoll();
            showOrderAlert('error', 'Ошибка анализа ТУ.');
            renderOrder(order);
            return;
          }

          if (POST_PARSE_STATUSES.has(st)) {
            stopParsingPoll();
            renderOrder(order);
            showOrderAlert('success', 'Анализ завершён!');
          }
        } catch (e) {
          console.error('parsing poll:', e);
        } finally {
          parsingPollBusy = false;
        }
      };

      tick();
      parsingPollTimer = setInterval(tick, 5000);
    }

// ── List screen ─────────────────────────────────────────────────────────────
    async function refreshList() {
      const statusFilter = document.getElementById('statusFilter').value;
      const loading = document.getElementById('listLoading');
      const content = document.getElementById('listContent');
      const alertEl = document.getElementById('listAlert');

      loading.style.display = 'block';
      content.style.display = 'none';
      alertEl.style.display = 'none';

      try {
        const qs = statusFilter ? `?status=${statusFilter}&limit=100` : '?limit=100';
        const [orders, stats] = await Promise.all([
          apiJSON(`/orders${qs}`),
          apiJSON('/admin/stats').catch(() => null),
        ]);

        renderStats(stats);
        renderOrdersTable(orders);

        const now = new Date();
        document.getElementById('lastRefresh').textContent =
          'Обновлено: ' + now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      } catch (e) {
        alertEl.textContent = 'Ошибка загрузки: ' + e.message;
        alertEl.className = 'alert error visible';
      } finally {
        loading.style.display = 'none';
        content.style.display = 'block';
      }
    }

    function renderStats(stats) {
      const row = document.getElementById('statsRow');
      if (!stats) { row.innerHTML = ''; return; }

      const items = [
        { label: 'Всего заявок', value: stats.total, color: '#2563eb' },
        { label: 'Новых', value: stats.by_status?.new || 0, color: '#9e9e9e' },
        { label: 'Договор отправлен', value: stats.by_status?.contract_sent || 0, color: '#f57c00' },
        { label: 'Ошибки', value: stats.by_status?.error || 0, color: '#f44336' },
        { label: 'Завершены', value: stats.by_status?.completed || 0, color: '#4caf50' },
      ];

      row.innerHTML = items.map(it => `
        <div class="stat-card">
          <div class="stat-value" style="color:${it.color};">${it.value}</div>
          <div class="stat-label">${it.label}</div>
        </div>
      `).join('');
    }

    function renderOrdersTable(orders) {
      const tbody = document.getElementById('ordersBody');
      const empty = document.getElementById('emptyOrders');

      if (!orders || orders.length === 0) {
        tbody.innerHTML = '';
        empty.style.display = 'block';
        return;
      }
      empty.style.display = 'none';

      tbody.innerHTML = orders.map(o => `
        <tr onclick="showOrderScreen('${o.id}')">
          <td class="td-id">${o.id.slice(0,8)}</td>
          <td class="td-name">${esc(o.client_name)}</td>
          <td>${esc(o.client_email)}</td>
          <td>${esc(o.object_address || '—')}</td>
          <td>${esc(o.object_city || '—')}</td>
          <td>${statusBadge(o.status)}</td>
          <td>${orderTypeBadge(o.order_type)}</td>
          <td class="td-date">${formatDate(o.created_at)}</td>
        </tr>
      `).join('');
    }

// ── Order detail screen ─────────────────────────────────────────────────────
    async function loadOrder(orderId) {
      currentOrderId = orderId;

      const loading = document.getElementById('orderLoading');
      const content = document.getElementById('orderContent');
      const alertEl = document.getElementById('orderAlert');

      loading.style.display = 'block';
      content.style.display = 'none';
      alertEl.style.display = 'none';

      try {
        const order = await apiJSON(`/orders/${orderId}`);
        renderOrder(order);
        loading.style.display = 'none';
        content.style.display = 'block';
      } catch (e) {
        loading.style.display = 'none';
        showOrderAlert('error', 'Ошибка загрузки заявки: ' + e.message);
      }
    }

    function renderPaymentCard(order) {
      let card = document.getElementById('paymentCard');
      if (!card) {
        const emailCard = document.getElementById('emailLog').closest('.card');
        card = document.createElement('div');
        card.className = 'card';
        card.id = 'paymentCard';
        card.innerHTML = `
          <div class="card-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
              <line x1="1" y1="10" x2="23" y2="10"/>
            </svg>
            Оплата
          </div>
          <div id="paymentContent"></div>
        `;
        emailCard.after(card);
      }

      const content = document.getElementById('paymentContent');

      if (!order.payment_amount && !order.contract_number) {
        card.style.display = 'none';
        return;
      }
      card.style.display = 'block';

      const pm = order.payment_method;
      const pmLabel = {
        bank_transfer: 'Безналичная',
        online_card: 'Онлайн картой',
      }[pm] || '—';

      const advanceStatus = order.advance_paid_at
        ? `<span style="color:#16a34a;">✓ Получен ${formatDate(order.advance_paid_at)}</span>`
        : '<span style="color:#f57c00;">Ожидание</span>';

      const finalAmount = (order.payment_amount || 0) - (order.advance_amount || 0);
      const finalStatus = order.final_paid_at
        ? `<span style="color:#16a34a;">✓ Получен ${formatDate(order.final_paid_at)}</span>`
        : '<span style="color:#f57c00;">Ожидание</span>';

      const rub = '₽';
      const hasActiveRsoRemarks = order.status === 'rso_remarks_received' || order.has_rso_remarks;
      const postProjectState = hasActiveRsoRemarks
        ? '<span style="color:#2563eb;">Замечания РСО получены</span>'
        : (order.awaiting_rso_feedback
          ? '<span style="color:#2563eb;">Ожидаем замечания РСО</span>'
          : (order.has_rso_scan
            ? '<span style="color:#0f766e;">Скан РСО получен</span>'
            : '<span style="color:#f57c00;">Ожидаем скан РСО или оплату</span>'));
      let html = `
        <dl class="detail-grid">
          <dt>Договор</dt><dd>${esc(order.contract_number || '—')}</dd>
          <dt>Метод оплаты</dt><dd>${pmLabel}</dd>
          <dt>Полная сумма</dt><dd>${order.payment_amount ? formatNum(order.payment_amount) + ' ' + rub : '—'}</dd>
          <dt>Аванс (50%)</dt><dd>${order.advance_amount ? formatNum(order.advance_amount) + ' ' + rub : '—'} — ${advanceStatus}</dd>
          <dt>Остаток (50%)</dt><dd>${finalAmount ? formatNum(finalAmount) + ' ' + rub : '—'} — ${finalStatus}</dd>
          <dt>Счёт на остаток</dt><dd>${order.final_invoice_available ? '<span style="color:#16a34a;">✓ Сохранён</span>' : '—'}</dd>
          <dt>Скан РСО получен</dt><dd>${order.rso_scan_received_at ? formatDateFull(order.rso_scan_received_at) : '—'}</dd>
          <dt>Post-project этап</dt><dd>${postProjectState}</dd>
        </dl>
      `;


      const r = order.company_requisites;
      if (r && typeof r === 'object' && !r.error) {
        const reqLabels = {
          full_name: 'Наименование', inn: 'ИНН', kpp: 'КПП',
          legal_address: 'Юр. адрес', bank_name: 'Банк',
          bik: 'БИК', settlement_account: 'Р/с',
          director_name: 'Руководитель',
        };
        html += `<details style="margin-top:12px;"><summary style="cursor:pointer; font-weight:600; font-size:13px;">Реквизиты клиента</summary>
          <dl class="detail-grid" style="margin-top:8px;">
            ${Object.entries(reqLabels)
              .filter(([k]) => r[k])
              .map(([k, label]) => `<dt>${label}</dt><dd>${esc(String(r[k]))}</dd>`)
              .join('')}
          </dl>
        </details>`;
      }

      html += `<div style="margin-top:12px; font-size:13px;">
        <a href="/payment/${order.id}" target="_blank" style="color:var(--c-primary);">
          Страница оплаты клиента \u2197
        </a>
      </div>`;

      content.innerHTML = html;
    }

    function renderOrder(order) {
      // ID badge
      document.getElementById('orderIdBadge').textContent = 'Заявка №' + order.id.slice(0,8);

      // Contacts
      const grid = document.getElementById('contactsGrid');
      const fields = [
        ['Имя клиента', order.client_name],
        ['Email', order.client_email],
        ['Телефон', order.client_phone || '—'],
        ['Организация', order.client_organization || '—'],
        ['Почтовый адрес для отправки проекта', order.object_address || '—'],
        ['Город объекта', order.object_city || '—'],
        ['Адрес объекта (из ТУ)', (() => { const p = order.parsed_params; if (!p) return '—'; const o = p.object || {}; const d = p.document || {}; return o.object_address ?? d.object_address ?? '—'; })()],
        ['Дата создания', formatDateFull(order.created_at)],
        ['Обновлена', formatDateFull(order.updated_at)],
        ['Повторных запросов', order.retry_count],
      ];
      grid.innerHTML = fields.map(([k,v]) =>
        `<dt>${k}</dt><dd>${esc(String(v))}</dd>`
      ).join('');

      // Status badge
      document.getElementById('statusBadge').innerHTML = statusBadge(order.status).replace('class="badge"', 'class="badge"');
      document.getElementById('statusBadge').style.background = STATUS_COLORS[order.status] || '#9e9e9e';
      document.getElementById('statusBadge').textContent = STATUS_LABELS[order.status] || order.status;
      document.getElementById('orderTypeBadgeEl').outerHTML = orderTypeBadge(order.order_type).replace('class="badge"', 'id="orderTypeBadgeEl" class="badge"');
      document.getElementById('statusDates').textContent =
        order.reviewer_comment ? 'Комментарий: ' + order.reviewer_comment : '';

      // Progress
      renderProgress(order.status);

      // Files
      renderFiles(order.files || [], order.id);

      // Parsed params + Survey data
      const hasParsed = !isParsedParamsEmpty(order.parsed_params);
      const hasSurvey = order.survey_data && typeof order.survey_data === 'object' && Object.keys(order.survey_data).length > 0;

      if (hasParsed && hasSurvey) {
        // Показываем единую таблицу сравнения
        document.getElementById('parsedCard').style.display = 'none';
        document.getElementById('surveyCard').style.display = 'none';
        renderComparisonTable(order.parsed_params, order.survey_data);
      } else {
        document.getElementById('comparisonCard').style.display = 'none';
        renderParsedParams(order.parsed_params, order.missing_params, order.survey_data, order.files);
        renderSurveyData(order.survey_data);
      }

      // Настроечная БД — для custom всегда, для express если определена Эско-Терра
      if (order.order_type === 'custom' || order.order_type === 'express') {
        loadCalcConfig(order.id);
      } else {
        document.getElementById('calcConfigCard').style.display = 'none';
      }

      // Email log
      renderEmailLog(order.emails || []);

      renderPaymentCard(order);

      // Actions
      renderActions(order);

      // Start polling if parsing in progress
      if (order.status === 'tu_parsing') {
        startParsingPoll();
      } else {
        stopParsingPoll();
      }

      // Poll пока заявка ждёт ответа клиента: обновляем карточку при смене статуса или файлов
      if (order.status === 'waiting_client_info') {
        startWaitingEmailPoll();
      } else {
        stopWaitingEmailPoll();
      }
    }

    function renderProgress(currentStatus) {
      const steps = document.getElementById('progressSteps');
      const isError = currentStatus === 'error';
      const progressOrder = STATUS_ORDER;
      const curIdx = progressOrder.indexOf(currentStatus);

      steps.innerHTML = progressOrder.map((s, idx) => {
        let cls = '';
        if (isError) cls = curIdx >= 0 && idx <= curIdx ? 'error-step' : '';
        else if (idx < curIdx) cls = 'done';
        else if (idx === curIdx) cls = 'active';
        return `<div class="step ${cls}"><div class="step-label">${STATUS_LABELS[s]}</div></div>`;
      }).join('');
    }

    function renderFiles(files, orderId) {
      const el = document.getElementById('filesList');
      if (!files.length) {
        el.innerHTML = '<div class="empty-state" style="padding:16px 0;">Нет файлов</div>';
        return;
      }

      const catLabels = {
        tu: 'Технические условия',
        company_card: 'Карточка организации (реквизиты)',
        balance_act: 'Акт разграничения балансовой принадлежности',
        connection_plan: 'План подключения потребителя к тепловой сети',
        heat_point_plan: 'План теплового пункта (УУТЭ, ШУ)',
        heat_scheme: 'Принципиальная схема теплового пункта с УУТЭ',
        contract: 'Договор',
        invoice: 'Счёт',
        final_invoice: 'Счёт на остаток',
        signed_contract: 'Подписанный договор',
        rso_scan: 'Скан письма в РСО',
        rso_remarks: 'Замечания РСО',
        generated_excel: 'Excel (расчёты)',
        generated_project: 'Готовый проект',
        other: 'Другое',
      };

      el.innerHTML = files.map(f => `
        <div class="file-item">
          <svg class="file-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <span class="file-name">${esc(f.original_filename)}</span>
          <span class="file-meta">${catLabels[f.category] || f.category}</span>
          <span class="file-meta">${f.file_size ? formatSize(f.file_size) : ''}</span>
          <a href="${API_BASE}/admin/files/${f.id}/download"
             class="btn btn-ghost btn-sm"
             style="font-size:12px; padding:4px 10px;"
             target="_blank"
             onclick="this.href = addKeyToUrl(this.href)">
            ↓ Скачать
          </a>
        </div>
      `).join('');
    }

// ── Actions, email, uploads ─────────────────────────────────────────────────
    function renderActions(order) {
      const row = document.getElementById('actionsRow');
      const note = document.getElementById('actionsNote');
      const status = order.status;
      const infoSent = order.info_request_sent === true;
      const reminderSent = order.reminder_sent === true;

      let buttons = [];
      let noteText = '';

      // Show spinner during parsing
      if (status === 'tu_parsing') {
        row.innerHTML = `
          <div style="display:flex; align-items:center; gap:10px; color:var(--c-text-secondary); font-size:14px;">
            <svg class="spinner spinner-dark" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
              <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/>
            </svg>
            <span>Выполняется анализ ТУ…</span>
          </div>
        `;
        note.textContent = 'Страница обновится автоматически после завершения';
        return;
      }

      if (status === 'new') {
        buttons.push({
          label: '▶ Запустить парсинг ТУ',
          cls: 'btn-primary',
          action: () => runAction(`/pipeline/${order.id}/start`, 'POST', 'Парсинг запущен'),
        });
        noteText = 'Убедитесь, что файл ТУ загружен перед запуском';
      }

      if (status === 'tu_parsed' || status === 'waiting_client_info' || status === 'client_info_received') {
        buttons.push({
          label: '✉ Отправить запрос клиенту',
          cls: 'btn-warn',
          disabled: infoSent,
          title: infoSent ? 'Запрос уже отправлялся' : '',
          action: () => sendEmail(order.id, 'info_request', 'Запрос отправлен'),
        });
      }

      if (status === 'waiting_client_info') {
        buttons.push({
          label: '✉ Отправить напоминание',
          cls: 'btn-warn',
          disabled: reminderSent || !infoSent,
          title: reminderSent
            ? 'Напоминание уже отправлялось'
            : (!infoSent ? 'Сначала отправьте запрос документов (или дождитесь автоотправки)' : ''),
          action: () => sendEmail(order.id, 'reminder', 'Напоминание отправлено'),
        });
      }

      const approveAllowed = status === 'advance_paid';
      if (approveAllowed) {
        const hasProjectPdf = (order.files || []).some(
          f => f.category === 'generated_project'
        );
        buttons.push({
          label: '✓ Отправить готовый проект',
          cls: 'btn-success',
          disabled: !hasProjectPdf,
          title: hasProjectPdf
            ? ''
            : 'Сначала загрузите готовый проект (PDF) в блоке файлов ниже',
          action: () => approveProject(order.id, status),
        });
        if (!hasProjectPdf) {
          noteText = noteText
            ? noteText + ' Загрузите файл проекта (категория «Готовый проект»), затем нажмите кнопку одобрения.'
            : 'Загрузите файл проекта (категория «Готовый проект»), затем нажмите кнопку одобрения.';
        }
      }

      if (status === 'error') {
        buttons.push({
          label: '↻ Перезапустить парсинг',
          cls: 'btn-danger',
          action: () => {
            if (confirm('Сбросить статус и перезапустить парсинг?')) {
              runAction(`/parsing/${order.id}/retrigger`, 'POST', 'Парсинг перезапущен');
            }
          },
        });
      }


      if (status === 'awaiting_contract') {
        noteText = 'Клиенту отправлено уведомление. Ожидаем загрузку реквизитов и выбор метода оплаты.';
      }

      if (status === 'contract_sent') {
        const hasSignedContract = (order.files || []).some(f => f.category === 'signed_contract');
        const signedContractLine = hasSignedContract
          ? 'Подписанный договор: загружен.'
          : 'Подписанный договор: не загружен.';
        buttons.push({
          label: '\uD83D\uDCB0 Аванс получен',
          cls: 'btn-success',
          disabled: !hasSignedContract,
          title: hasSignedContract ? '' : 'Сначала должен быть загружен подписанный договор',
          action: () => {
            if (confirm('Подтвердить получение аванса?')) {
              runAction(`/pipeline/${order.id}/confirm-advance`, 'POST', 'Аванс подтверждён');
            }
          },
        });
        noteText = 'Ожидаем оплату аванса от клиента. После получения — нажмите «Аванс получен». ' + signedContractLine;
      }

      if (status === 'advance_paid') {
        noteText = 'Проект в работе. Срок: 3 рабочих дня. Загрузите файл проекта и нажмите «Отправить готовый проект».';
      }

      if (status === 'awaiting_final_payment') {
        buttons.push({
          label: '\uD83D\uDCB0 Остаток получен',
          cls: 'btn-success',
          action: () => {
            if (confirm('Подтвердить получение остатка? Заявка будет завершена.')) {
              runAction(`/pipeline/${order.id}/confirm-final`, 'POST', 'Оплата подтверждена — заявка завершена');
            }
          },
        });
        if (order.awaiting_rso_feedback) {
          noteText = 'Скан из РСО получен. Ожидаем замечания РСО или оплату остатка.';
        } else if (order.has_rso_scan) {
          noteText = 'Клиент загрузил скан из РСО. Проверьте статус согласования и ожидайте замечания или оплату.';
        } else {
          noteText = 'Ожидаем скан из РСО или оплату остатка от клиента.';
        }
      }

      if (status === 'rso_remarks_received' || order.has_rso_remarks) {
        buttons.push({
          label: '\uD83D\uDCB0 Остаток получен',
          cls: 'btn-success',
          action: () => {
            if (confirm('Подтвердить получение остатка? Заявка будет завершена.')) {
              runAction(`/pipeline/${order.id}/confirm-final`, 'POST', 'Оплата подтверждена — заявка завершена');
            }
          },
        });
        buttons.push({
          label: '\u2709 Отправить исправленный проект',
          cls: 'btn-primary',
          action: () => {
            if (confirm('Отправить клиенту исправленный проект с новым сопроводительным письмом и тем же счётом на остаток?')) {
              runAction(
                `/pipeline/${order.id}/resend-corrected-project`,
                'POST',
                'Исправленный проект отправлен клиенту'
              );
            }
          },
        });
        noteText = 'Клиент загрузил замечания РСО. Загрузите новую версию PDF проекта и отправьте исправленный комплект клиенту, либо подтвердите оплату остатка, если вопрос уже закрыт.';
      }

      if (status === 'waiting_client_info' && !infoSent && order.info_request_earliest_auto_at) {
        const d = new Date(order.info_request_earliest_auto_at);
        const msk = d.toLocaleString('ru-RU', { timeZone: 'Europe/Moscow' });
        const autoLine =
          '\u0410\u0432\u0442\u043e\u043e\u0442\u043f\u0440\u0430\u0432\u043a\u0430 \u0437\u0430\u043f\u0440\u043e\u0441\u0430 \u043a\u043b\u0438\u0435\u043d\u0442\u0443 \u043d\u0435 \u0440\u0430\u043d\u0435\u0435: '
          + msk
          + ' (\u041c\u0421\u041a). \u0420\u0430\u043d\u044c\u0448\u0435 \u2014 \u043a\u043d\u043e\u043f\u043a\u0430 \u00ab\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0437\u0430\u043f\u0440\u043e\u0441 \u043a\u043b\u0438\u0435\u043d\u0442\u0443\u00bb.';
        noteText = noteText ? noteText + ' ' + autoLine : autoLine;
      }

      if (buttons.length === 0) {
        row.innerHTML = '<span style="color:var(--c-text-secondary); font-size:14px;">Нет доступных действий для текущего статуса</span>';
      } else {
        row.innerHTML = buttons.map((b, i) => `
          <button class="btn ${b.cls}" id="action_btn_${i}"
            ${b.disabled ? 'disabled' : ''}
            ${b.title ? `title="${esc(b.title)}"` : ''}
            onclick="actionBtns[${i}]()">${b.label}</button>
        `).join('');
        window.actionBtns = buttons.map(b => b.action);
      }

      note.textContent = noteText;
    }

    async function runAction(path, method, successMsg) {
      const actionBtns = document.querySelectorAll('[id^="action_btn_"]');
      actionBtns.forEach(b => { b.disabled = true; });
      showOrderAlert('info', 'Выполняется…');
      try {
        await apiJSON(path, { method });
        showOrderAlert('success', successMsg);
        setTimeout(() => loadOrder(currentOrderId), 1200);
      } catch (e) {
        showOrderAlert('error', 'Ошибка: ' + e.message);
        actionBtns.forEach(b => { b.disabled = false; });
      }
    }

    function formatApiDetail(detail) {
      if (detail == null) return '';
      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail)) {
        return detail.map(x => (x.msg || JSON.stringify(x))).join('; ');
      }
      return String(detail);
    }

    async function sendEmail(orderId, emailType, successMsg) {
      const actionBtns = document.querySelectorAll('[id^="action_btn_"]');
      actionBtns.forEach(b => { b.disabled = true; });
      showOrderAlert('info', 'Отправка…');
      try {
        const resp = await apiFetch(`/emails/${orderId}/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email_type: emailType }),
        });
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          throw new Error(formatApiDetail(data.detail) || `HTTP ${resp.status}`);
        }
        await resp.json();
        showOrderAlert('success', successMsg);
        setTimeout(() => loadOrder(currentOrderId), 1200);
      } catch (e) {
        showOrderAlert('error', 'Ошибка отправки: ' + e.message);
        actionBtns.forEach(b => { b.disabled = false; });
      }
    }

    async function uploadAdminFile() {
      const category = document.getElementById('uploadCategory').value;
      const fileInput = document.getElementById('uploadFileInput');
      const file = fileInput.files[0];
      if (!file) { showOrderAlert('error', 'Выберите файл'); return; }

      const progressWrap = document.getElementById('adminUploadProgressWrap');
      const progressEl = document.getElementById('adminUploadProgress');
      const progressLabel = document.getElementById('adminUploadProgressLabel');
      const uploadBtn = document.getElementById('adminUploadBtn');

      if (category === 'generated_project') {
        showOrderAlert('info', 'Загрузка файла…');
        progressWrap.style.display = 'block';
        progressEl.value = 0;
        progressLabel.textContent = '0%';
        uploadBtn.disabled = true;

        const xhr = new XMLHttpRequest();
        const url = `${API_BASE}/orders/${currentOrderId}/files?category=${encodeURIComponent(category)}`;

        try {
          await new Promise((resolve, reject) => {
            xhr.open('POST', url);
            xhr.setRequestHeader('X-Admin-Key', getKey());
            xhr.upload.onprogress = (ev) => {
              if (ev.lengthComputable && ev.total > 0) {
                const pct = Math.round((ev.loaded / ev.total) * 100);
                progressEl.value = pct;
                progressLabel.textContent = pct + '%';
              }
            };
            xhr.onload = () => {
              if (xhr.status === 401) {
                sessionStorage.removeItem('admin_key');
                showLoginScreen();
                reject(new Error('Требуется авторизация'));
                return;
              }
              if (xhr.status < 200 || xhr.status >= 300) {
                let msg = `HTTP ${xhr.status}`;
                try {
                  const d = JSON.parse(xhr.responseText || '{}');
                  msg = formatApiDetail(d.detail) || msg;
                } catch (_) {}
                reject(new Error(msg));
                return;
              }
              resolve();
            };
            xhr.onerror = () => reject(new Error('Ошибка сети'));
            const formData = new FormData();
            formData.append('file', file);
            xhr.send(formData);
          });
          fileInput.value = '';
          showOrderAlert('success', 'Файл загружен');
          setTimeout(() => loadOrder(currentOrderId), 800);
        } catch (e) {
          showOrderAlert('error', 'Ошибка загрузки: ' + e.message);
        } finally {
          progressWrap.style.display = 'none';
          uploadBtn.disabled = false;
        }
        return;
      }

      progressWrap.style.display = 'none';
      showOrderAlert('info', 'Загрузка файла…');
      const formData = new FormData();
      formData.append('file', file);

      try {
        const resp = await apiFetch(`/orders/${currentOrderId}/files?category=${category}`, {
          method: 'POST',
          body: formData,
        });
        if (!resp.ok) {
          const d = await resp.json().catch(() => ({}));
          throw new Error(formatApiDetail(d.detail) || `HTTP ${resp.status}`);
        }
        fileInput.value = '';
        showOrderAlert('success', 'Файл загружен');
        setTimeout(() => loadOrder(currentOrderId), 800);
      } catch (e) {
        showOrderAlert('error', 'Ошибка загрузки: ' + e.message);
      }
    }

    function renderEmailLog(emails) {
      const el = document.getElementById('emailLog');
      if (!emails.length) {
        el.innerHTML = '<div class="empty-state" style="padding:16px 0;">Писем не отправлялось</div>';
        return;
      }

      const typeLabels = {
        info_request: 'Запрос документов',
        reminder: 'Напоминание',
        project_delivery: 'Проект готов',
        error_notification: 'Ошибка',
        sample_delivery: 'Образец проекта',
        new_order_notification: 'Новая заявка (инженеру)',
        client_documents_received: 'Документы от клиента (инженеру)',
        partnership_request: 'Запрос партнёрства',
        survey_reminder: 'Напоминание об опросе (клиенту)',
        project_ready_payment: 'Проект готов (оплата)',
        contract_delivery: 'Договор и счёт',
        advance_received: 'Аванс получен (проект)',
        final_payment_request: 'Напоминание об оплате',
        final_payment_received: 'Оплата завершена',
      };

      el.innerHTML = `
        <table class="email-log-table" style="width:100%;">
          <thead>
            <tr>
              <th>Тип</th>
              <th>Получатель</th>
              <th>Тема</th>
              <th>Отправлено</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            ${emails.map(e => `
              <tr>
                <td>${typeLabels[e.email_type] || e.email_type}</td>
                <td style="font-size:13px;">${esc(e.recipient)}</td>
                <td style="font-size:12px; color:var(--c-text-secondary);">${esc(e.subject)}</td>
                <td class="td-date">${e.sent_at ? formatDate(e.sent_at) : '—'}</td>
                <td>${e.sent_at
                  ? '<span style="color:#16a34a; font-size:13px; font-weight:600;">✓ OK</span>'
                  : '<span style="color:#dc2626; font-size:13px; font-weight:600;">✗ Ошибка</span>'
                }</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }
