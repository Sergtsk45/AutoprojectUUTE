/**
 * @file: backend/static/js/admin/views-calc.js
 * @description: Настроечная БД вычислителя (calc config) — инициализация, рендер,
 *   редактирование, сохранение, экспорт PDF.
 *   Фаза E3 (минимальный вариант) — вынос из inline <script> в admin.html.
 *   Зависит от: API_BASE/getKey() (config.js/admin.js). Функции
 *   initCalcConfig, initCalcConfigExpress, saveCalcConfig, exportCalcConfigPdf,
 *   calcParamChanged вызываются из HTML через inline onclick/onchange — их
 *   надо держать в глобальной области (обычный <script>, не ES-модуль).
 * @created: 2026-04-22 (E3)
 */

    let calcConfigState = { config: null, template: null, calcType: null };
    let calcPendingChanges = {};
    let calcSaveInFlight = false;
    let calcInitialValues = {};
    const calcConfigUiStateByOrder = {};
    const calcGroupUiStateByOrder = {};

    function normalizeCalcValue(value) {
      return value == null ? '' : String(value);
    }

    function buildCalcInitialValues(template, cfgData) {
      const initial = {};
      if (!template || !Array.isArray(template.groups)) return initial;
      for (const group of template.groups) {
        if (!group || !Array.isArray(group.params)) continue;
        for (const param of group.params) {
          const baseVal = cfgData[param.id] !== undefined ? cfgData[param.id] : (param.default ?? '');
          initial[param.id] = normalizeCalcValue(baseVal);
        }
      }
      return initial;
    }

    function syncCalcSaveButtonState() {
      const saveBtn = document.getElementById('calcSaveBtn');
      if (!saveBtn) return;
      const hasPendingChanges = Object.keys(calcPendingChanges).length > 0;
      saveBtn.disabled = calcSaveInFlight || !hasPendingChanges;
      saveBtn.textContent = calcSaveInFlight ? 'Сохранение…' : 'Сохранить';
    }

    function bindCalcConfigDetailsToggle() {
      const details = document.getElementById('calcConfigDetails');
      if (!details || details.dataset.toggleBound === '1') return;
      details.addEventListener('toggle', () => {
        const orderId = details.dataset.orderId;
        if (!orderId) return;
        calcConfigUiStateByOrder[orderId] = details.open;
      });
      details.dataset.toggleBound = '1';
    }

    function applyCalcConfigDetailsState(orderId) {
      const details = document.getElementById('calcConfigDetails');
      if (!details) return;
      details.dataset.orderId = orderId || '';
      const isOpen = calcConfigUiStateByOrder[orderId] === true;
      if (details.open !== isOpen) {
        details.open = isOpen;
      }
    }

    function bindCalcGroupToggles(orderId) {
      const content = document.getElementById('calcConfigContent');
      if (!content) return;
      content.querySelectorAll('details[data-group-idx]').forEach(det => {
        det.addEventListener('toggle', () => {
          if (!calcGroupUiStateByOrder[orderId]) calcGroupUiStateByOrder[orderId] = {};
          calcGroupUiStateByOrder[orderId][det.dataset.groupIdx] = det.open;
        });
      });
    }

    function applyCalcGroupStates(orderId) {
      const content = document.getElementById('calcConfigContent');
      if (!content) return;
      const saved = calcGroupUiStateByOrder[orderId];
      content.querySelectorAll('details[data-group-idx]').forEach(det => {
        // Default: open; закрыто только если явно сохранено как false
        const isOpen = !saved || saved[det.dataset.groupIdx] !== false;
        if (det.open !== isOpen) det.open = isOpen;
      });
    }

    async function loadCalcConfig(orderId) {
      const card = document.getElementById('calcConfigCard');
      const content = document.getElementById('calcConfigContent');
      const _det = document.getElementById('calcConfigDetails');
      const isOrderChange = !_det || _det.dataset.orderId !== String(orderId);
      bindCalcConfigDetailsToggle();
      try {
        const resp = await fetch(`${API_BASE}/admin/orders/${orderId}/calc-config`, {
          headers: { 'X-Admin-Key': getKey() }
        });
        if (!resp.ok) {
          card.style.display = 'none';
          return;
        }
        const data = await resp.json();
        calcConfigState = { config: data.config, template: data.template, calcType: data.calculator_type };
        calcPendingChanges = {};
        calcSaveInFlight = false;
        calcInitialValues = buildCalcInitialValues(
          data.template || {},
          (data.config && data.config.config_data) || {},
        );
        renderCalcConfig(data, orderId);
        // Restore open/close state only when switching to a different order.
        // On poll refreshes for the same order we must NOT touch details.open —
        // otherwise a completing fetch races with the user's click and
        // re-opens the panel they just closed.
        if (isOrderChange) {
          applyCalcConfigDetailsState(orderId);
        } else {
          const d = document.getElementById('calcConfigDetails');
          if (d) d.dataset.orderId = String(orderId);
        }
        card.style.display = 'block';
      } catch (e) {
        card.style.display = 'none';
      }
    }

    function renderCalcConfig(data, orderId) {
      const content = document.getElementById('calcConfigContent');
      const { config, template, status } = data;

      // Express: вычислитель не обнаружен автоматически — показываем сообщение + кнопку ручной инициализации
      if (status === 'not_supported_for_express') {
        content.innerHTML = `
          <div style="padding:12px 0; color:var(--c-warn); font-size:13px;">
            ⚠️ ${data.message || 'Вычислитель Эско-Терра не обнаружен в ТУ автоматически.'}
          </div>
          <div class="calc-actions">
            <button class="btn btn-primary" onclick="initCalcConfigExpress('${orderId}')">Инициализировать как Эско 3Э</button>
          </div>`;
        return;
      }

      if (!template && !config) {
        content.innerHTML = `<div class="empty-state" style="padding:16px 0;">${data.message || 'Производитель не поддерживается'}</div>`;
        return;
      }

      const tpl = template || {};
      const calcName = tpl.calculator_name || (config && config.calculator_type) || '—';
      const hasDual = tpl.has_dual_db || false;
      const cfgData = (config && config.config_data) || {};
      const total = (config && config.total_params) || 0;
      const filled = (config && config.filled_params) || 0;
      const missing = (config && config.missing_required) || [];
      const pct = total > 0 ? Math.round(filled / total * 100) : 0;

      let html = `<div style="margin-bottom:8px;">`;
      html += `<div style="font-weight:600; font-size:14px;">${calcName}</div>`;

      if (config) {
        html += `<div style="font-size:12px; color:var(--c-text-secondary);">Заполнено: ${filled} / ${total} (${pct}%)</div>`;
        html += `<div class="calc-progress-bar"><div class="calc-progress-fill" style="width:${pct}%"></div></div>`;
      }

      html += `<div class="calc-legend">
        <span class="calc-legend-item"><span class="calc-legend-dot" style="background:#27ae60;"></span>из ТУ (авто)</span>
        <span class="calc-legend-item"><span class="calc-legend-dot" style="background:#2980b9;"></span>по умолч.</span>
        <span class="calc-legend-item"><span class="calc-legend-dot" style="background:#f39c12;"></span>запрос</span>
        <span class="calc-legend-item"><span class="calc-legend-dot" style="background:#ccc; border:1px solid #ddd;"></span>инженер</span>
      </div></div>`;

      if (missing.length > 0) {
        html += `<div class="calc-missing-warning">⚠️ Незаполненные обязательные поля: ${missing.join(', ')}</div>`;
      }

      if (!config) {
        html += `<div class="calc-actions">
          <button class="btn btn-primary" onclick="initCalcConfig('${orderId}')">Инициализировать БД</button>
        </div>`;
        if (tpl.groups) {
          html += renderCalcGroups(tpl, {}, hasDual, orderId, false);
        }
        content.innerHTML = html;
        bindCalcGroupToggles(orderId);
        applyCalcGroupStates(orderId);
        return;
      }

      html += renderCalcGroups(tpl, cfgData, hasDual, orderId, true);

      html += `<div class="calc-actions">
        <button class="btn btn-primary" id="calcSaveBtn" onclick="saveCalcConfig('${orderId}')" disabled>Сохранить</button>
        <button class="btn" onclick="exportCalcConfigPdf('${orderId}')">📄 Экспорт PDF</button>
      </div>`;

      content.innerHTML = html;
      bindCalcGroupToggles(orderId);
      applyCalcGroupStates(orderId);
      syncCalcSaveButtonState();
    }

    function renderCalcGroups(template, cfgData, hasDual, orderId, editable) {
      if (!template.groups) return '';
      let html = '';
      for (let groupIdx = 0; groupIdx < template.groups.length; groupIdx++) {
        const group = template.groups[groupIdx];
        html += `<details data-group-idx="${groupIdx}" style="margin-bottom:8px;">
          <summary style="cursor:pointer; font-weight:600; font-size:13px; padding:6px 0; color:var(--c-text);">${group.title}</summary>
          <table class="calc-table">
            <thead><tr>
              <th style="width:60px;">Обозн.</th>
              <th>Параметр</th>
              <th style="width:${hasDual ? '160px' : '200px'};">${hasDual ? 'БД1 (зима)' : 'Значение'}</th>
              ${hasDual ? '<th style="width:160px;">БД2 (лето)</th>' : ''}
              <th style="width:70px;">Источник</th>
            </tr></thead>
            <tbody>`;
        for (const param of group.params) {
          const src = param.source || 'engineer';
          const val = cfgData[param.id] !== undefined ? cfgData[param.id] : (param.default || '');
          const srcLabel = { auto: '🟢 авто', default: '🔵 умолч.', client: '🟡 запрос', engineer: '⬜ инженер' }[src] || src;
          const srcClass = { auto: 'calc-source-auto', default: 'calc-source-default', client: 'calc-source-client', engineer: 'calc-source-engineer' }[src] || '';
          const isEditable = editable && (src === 'engineer' || src === 'client');
          const isRequired = param.required ? ' *' : '';

          let valCell = '';
          if (isEditable) {
            if (param.type === 'select' && param.options && param.options.length) {
              valCell = `<select data-param-id="${param.id}" onchange="calcParamChanged(this, '${orderId}')">`;
              for (const opt of param.options) {
                valCell += `<option value="${opt.value}"${String(opt.value) === String(val) ? ' selected' : ''}>${opt.text}</option>`;
              }
              valCell += '</select>';
            } else {
              const minAttr = param.min != null ? ` min="${param.min}"` : '';
              const maxAttr = param.max != null ? ` max="${param.max}"` : '';
              const stepAttr = param.step != null ? ` step="${param.step}"` : '';
              valCell = `<input type="${param.type === 'number' ? 'number' : 'text'}" data-param-id="${param.id}" value="${val}"${minAttr}${maxAttr}${stepAttr} onchange="calcParamChanged(this, '${orderId}')" placeholder="${param.hint || ''}">`;
            }
          } else {
            let displayVal = val !== '' && val != null ? String(val) : '—';
            if (param.type === 'select' && param.options) {
              const opt = param.options.find(o => String(o.value) === String(val));
              if (opt) displayVal = `${val} — ${opt.text}`;
            }
            valCell = `<span class="${srcClass}" style="padding:2px 4px; border-radius:3px;">${displayVal}</span>`;
          }

          html += `<tr>
            <td style="font-family:monospace; font-size:12px;">${param.label}${isRequired}</td>
            <td title="${param.hint || ''}">${param.full_label || param.label}</td>
            <td>${valCell}</td>
            ${hasDual ? '<td>—</td>' : ''}
            <td style="font-size:11px; white-space:nowrap;">${srcLabel}</td>
          </tr>`;
        }
        html += `</tbody></table></details>`;
      }
      return html;
    }

    async function initCalcConfig(orderId) {
      try {
        const resp = await fetch(`${API_BASE}/admin/orders/${orderId}/calc-config/init`, {
          method: 'POST',
          headers: { 'X-Admin-Key': getKey(), 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        if (!resp.ok) {
          const err = await resp.json();
          alert('Ошибка: ' + (err.detail || resp.statusText));
          return;
        }
        await loadCalcConfig(orderId);
      } catch (e) {
        alert('Ошибка инициализации: ' + e.message);
      }
    }

    async function initCalcConfigExpress(orderId) {
      try {
        const resp = await fetch(`${API_BASE}/admin/orders/${orderId}/calc-config/init`, {
          method: 'POST',
          headers: { 'X-Admin-Key': getKey(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ calculator_type: 'esko_terra' })
        });
        if (!resp.ok) {
          const err = await resp.json();
          alert('Ошибка: ' + (err.detail || resp.statusText));
          return;
        }
        await loadCalcConfig(orderId);
      } catch (e) {
        alert('Ошибка инициализации: ' + e.message);
      }
    }

    function calcParamChanged(el, orderId) {
      const paramId = el.dataset.paramId;
      const currentValue = normalizeCalcValue(el.value);
      const initialValue = calcInitialValues[paramId] ?? '';
      if (currentValue === initialValue) {
        delete calcPendingChanges[paramId];
      } else {
        calcPendingChanges[paramId] = el.value;
      }
      syncCalcSaveButtonState();
    }

    async function saveCalcConfig(orderId) {
      if (calcSaveInFlight || Object.keys(calcPendingChanges).length === 0) {
        return;
      }
      calcSaveInFlight = true;
      syncCalcSaveButtonState();
      try {
        const resp = await fetch(`${API_BASE}/admin/orders/${orderId}/calc-config`, {
          method: 'PATCH',
          headers: { 'X-Admin-Key': getKey(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ params: calcPendingChanges })
        });
        if (!resp.ok) {
          const err = await resp.json();
          alert('Ошибка: ' + (err.detail || resp.statusText));
          return;
        }
        calcPendingChanges = {};
        syncCalcSaveButtonState();
        await loadCalcConfig(orderId);
      } catch (e) {
        alert('Ошибка сохранения: ' + e.message);
      } finally {
        calcSaveInFlight = false;
        syncCalcSaveButtonState();
      }
    }

    async function exportCalcConfigPdf(orderId) {
      try {
        const resp = await fetch(`${API_BASE}/admin/orders/${orderId}/calc-config/export-pdf`, {
          method: 'POST',
          headers: { 'X-Admin-Key': getKey() }
        });
        if (!resp.ok) {
          const err = await resp.json();
          alert('Ошибка: ' + (err.detail || resp.statusText));
          return;
        }
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `calc_config_${orderId}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (e) {
        alert('Ошибка экспорта PDF: ' + e.message);
      }
    }
