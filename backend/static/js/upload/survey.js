/**
 * @file: survey.js
 * @description: Опросный лист клиента: collapse/lock/prefill/validate/collect,
 *   маппинг parsed TU → survey, hydrate из сохранённого snapshot.
 *   Функция toggleSurveyCollapse экспортируется на window для inline onclick.
 * @dependencies: config.js, utils.js
 * @created: 2026-04-22
 */

// ── Survey collapse / lock / visibility ────────────────────────────
    function collapseSurveyCard() {
      const body = document.getElementById('surveyBody');
      if (body) body.style.display = 'none';
      if ($surveyCard) $surveyCard.classList.add('collapsed');
    }

    function expandSurveyCard() {
      const body = document.getElementById('surveyBody');
      if (body) body.style.display = '';
      if ($surveyCard) $surveyCard.classList.remove('collapsed');
    }

    function toggleSurveyCollapse() {
      const body = document.getElementById('surveyBody');
      if (!body) return;
      if (body.style.display === 'none') {
        expandSurveyCard();
      } else {
        collapseSurveyCard();
      }
    }

    function lockSurveyCard(locked) {
      const ov = document.getElementById('surveyLockedOverlay');
      document.querySelectorAll('#surveyCard input, #surveyCard select, #surveyCard textarea, #surveyCard button').forEach(el => {
        if (locked) el.setAttribute('disabled', 'disabled');
        else el.removeAttribute('disabled');
      });
      if (ov) {
        ov.style.display = locked ? 'flex' : 'none';
        ov.setAttribute('aria-hidden', locked ? 'false' : 'true');
      }
    }

    function unlockSurveyCard() {
      lockSurveyCard(false);
    }

    /**
     * Блокирует поля опросного листа, в которых уже есть сохранённые значения.
     * Незаполненные поля остаются редактируемыми.
     * @param {object} surveyData — плоский объект ключ→значение из survey_data
     */
    function lockFilledSurveyFields(surveyData) {
      if (!surveyData) return;
      Object.entries(surveyData).forEach(([key, value]) => {
        if (value === null || value === undefined || value === '') return;
        const el = document.getElementById('s_' + key);
        if (!el) return;
        el.classList.add('survey-field-locked');
        if (el.tagName !== 'SELECT') {
          el.setAttribute('readonly', 'readonly');
        }
      });
    }

    function hideSurveyMeta() {
      const block = document.getElementById('surveyMetaBlock');
      const conf = document.getElementById('surveyConfidence');
      const warn = document.getElementById('surveyWarnings');
      if (block) block.style.display = 'none';
      if (conf) { conf.style.display = 'none'; conf.textContent = ''; }
      if (warn) { warn.style.display = 'none'; warn.innerHTML = ''; }
    }

    function showUploadWithLockedSurvey() {
      if ($contractSentCard) $contractSentCard.style.display = 'none';
      $parsingCard.style.display = 'none';
      $completedCard.style.display = 'none';
      $uploadCard.style.display = 'block';
      $surveyCard.style.display = 'block';
      lockSurveyCard(true);
      collapseSurveyCard();
    }

    function showSurveyCard() {
      if ($contractSentCard) $contractSentCard.style.display = 'none';
      $surveyCard.style.display = 'block';
      $parsingCard.style.display = 'none';
      $uploadCard.style.display = 'none';
      $completedCard.style.display = 'none';
      expandSurveyCard();
    }

    function showUploadCardForDocs() {
      if ($contractSentCard) $contractSentCard.style.display = 'none';
      $uploadCard.style.display = 'block';
    }

// ── Survey metadata & hydration ────────────────────────────────────
    function getNestedValue(obj, path) {
      if (obj == null || typeof obj !== 'object' || !path) return null;
      const parts = path.split('.');
      let cur = obj;
      for (const p of parts) {
        if (cur == null || typeof cur !== 'object' || !Object.prototype.hasOwnProperty.call(cur, p)) {
          return null;
        }
        cur = cur[p];
      }
      return cur === undefined ? null : cur;
    }

    function normalizeConnectionType(raw) {
      const s = String(raw || '').toLowerCase();
      if (s.includes('зависим')) return 'dependent';
      if (s.includes('независим')) return 'independent';
      return null;
    }

    function normalizeSystemType(raw) {
      const s = String(raw || '').toLowerCase();
      if (s.includes('открыт')) return 'open';
      if (s.includes('закрыт')) return 'closed';
      return null;
    }

    function normalizeBuildingType(raw) {
      const s = String(raw || '').toLowerCase();
      if (s.includes('мкд') || s.includes('жил')) return 'residential';
      if (s.includes('нежил') || s.includes('обществен')) return 'public';
      if (s.includes('промыш')) return 'industrial';
      return null;
    }

    function surveyFieldId(surveyKey) {
      return 's_' + surveyKey;
    }

    function clearSurveyDecorations() {
      const card = document.getElementById('surveyCard');
      if (!card) return;
      card.querySelectorAll('[data-survey-badge]').forEach(el => el.remove());
      card.querySelectorAll('.prefilled, .needs-input').forEach(el => {
        el.classList.remove('prefilled', 'needs-input');
      });
      hideSurveyMeta();
    }

    function appendSurveyBadge(fieldId, badgeClass, text) {
      const el = document.getElementById(fieldId);
      if (!el) return;
      const row = el.closest('.form-row');
      if (!row) return;
      const label = row.querySelector('label[for="' + fieldId + '"]');
      if (!label) return;
      label.querySelectorAll('[data-survey-badge]').forEach(n => n.remove());
      const span = document.createElement('span');
      span.className = badgeClass;
      span.setAttribute('data-survey-badge', '1');
      span.textContent = text;
      label.appendChild(document.createTextNode('\u00a0'));
      label.appendChild(span);
    }

    function markFieldPrefilled(fieldId, badgeText) {
      const el = document.getElementById(fieldId);
      if (!el) return;
      el.classList.remove('needs-input');
      el.classList.add('prefilled');
      appendSurveyBadge(fieldId, 'prefilled-badge', badgeText || 'из ТУ');
    }

    function markFieldNeedsInput(fieldId, badgeText) {
      const el = document.getElementById(fieldId);
      if (!el) return;
      el.classList.remove('prefilled');
      el.classList.add('needs-input');
      appendSurveyBadge(fieldId, 'needs-badge', badgeText || 'заполните');
    }

    function setSurveyControlValue(fieldId, value) {
      if (value == null || value === '') return false;
      const el = document.getElementById(fieldId);
      if (!el) return false;
      const str = typeof value === 'number' ? String(value) : String(value);
      if (el.tagName === 'SELECT') {
        const ok = [...el.options].some(o => o.value === str);
        if (!ok) return false;
      }
      el.value = str;
      return true;
    }

    function showSurveyMeta(parsed) {
      const block = document.getElementById('surveyMetaBlock');
      const confEl = document.getElementById('surveyConfidence');
      const warnEl = document.getElementById('surveyWarnings');
      if (!block || !confEl || !warnEl || !parsed || typeof parsed !== 'object') return;

      let show = false;
      if (typeof parsed.parse_confidence === 'number' && !Number.isNaN(parsed.parse_confidence)) {
        const pct = Math.round(Math.min(1, Math.max(0, parsed.parse_confidence)) * 100);
        confEl.textContent = 'Уверенность анализа: ' + pct + '%';
        confEl.style.display = 'block';
        show = true;
      } else {
        confEl.style.display = 'none';
        confEl.textContent = '';
      }

      if (Array.isArray(parsed.warnings) && parsed.warnings.length) {
        const items = parsed.warnings.filter(Boolean).map(w => '<li>' + escapeHtml(String(w)) + '</li>').join('');
        warnEl.innerHTML = '<strong>Замечания по ТУ:</strong><ul>' + items + '</ul>';
        warnEl.style.display = 'block';
        show = true;
      } else {
        warnEl.style.display = 'none';
        warnEl.innerHTML = '';
      }

      block.style.display = show ? 'block' : 'none';
    }

    function hasMeaningfulSurveyData(sd) {
      if (sd == null || typeof sd !== 'object') return false;
      return Object.values(sd).some(v => {
        if (v === null || v === undefined) return false;
        if (typeof v === 'boolean') return true;
        if (typeof v === 'number') return !Number.isNaN(v);
        if (typeof v === 'string') return v.trim() !== '';
        if (Array.isArray(v)) return v.length > 0;
        if (typeof v === 'object') return false;
        return false;
      });
    }

    /**
     * Приоритет: сохранённый survey_data; иначе автозаполнение из parsed_params.
     * @param {object} data — ответ upload-page
     */
    function hydrateSurveyFromOrder(data) {
      if (!data || data.order_type !== 'custom') return;
      unlockSurveyCard();
      clearSurveyDecorations();

      const parsed = data.parsed_params;
      const sd = data.survey_data;

      if (hasMeaningfulSurveyData(sd)) {
        applySurveyData(sd);
        hideSurveyMeta();
        return;
      }

      applyParsedParamsToSurvey(parsed);
    }

    /**
     * Заполняет опросник из parsed_params (структура парсера ТУ).
     * @param {object|null|undefined} parsedParams
     */
    function prefillSurvey(parsedParams) {
      if (!parsedParams || typeof parsedParams !== 'object') return;

      for (const [jsonPath, surveyKey] of Object.entries(PARAM_TO_SURVEY)) {
        const raw = getNestedValue(parsedParams, jsonPath);
        const fieldId = surveyFieldId(surveyKey);
        let normalized = raw;

        if (surveyKey === 'connection_type') normalized = normalizeConnectionType(raw);
        else if (surveyKey === 'system_type') normalized = normalizeSystemType(raw);
        else if (surveyKey === 'building_type') normalized = normalizeBuildingType(raw);
        else if (surveyKey === 'accuracy_class' && raw != null) normalized = String(raw);

        if (normalized != null && normalized !== '') {
          if (setSurveyControlValue(fieldId, normalized)) {
            markFieldPrefilled(fieldId, 'из ТУ');
          }
        }
      }

      const pipe = parsedParams.pipeline || {};
      const dnAny = pipe.pipe_outer_diameter_mm ?? pipe.pipe_inner_diameter_mm;
      const supId = surveyFieldId('pipe_dn_supply');
      const supEl = document.getElementById(supId);
      if (dnAny != null && supEl && !String(supEl.value).trim()) {
        if (setSurveyControlValue(supId, dnAny)) {
          markFieldPrefilled(supId, 'из ТУ');
        }
      }
      const retId = surveyFieldId('pipe_dn_return');
      const retEl = document.getElementById(retId);
      if (dnAny != null && retEl && supEl && !String(retEl.value).trim() && String(supEl.value).trim()) {
        if (setSurveyControlValue(retId, dnAny)) {
          markFieldPrefilled(retId, 'из ТУ');
        }
      }

      const metering = parsedParams.metering || {};
      const fmRaw = String(metering.flowmeter_model || '').toLowerCase();
      const flowId = surveyFieldId('flow_meter_type');
      if (fmRaw.includes('ультразвук')) {
        if (setSurveyControlValue(flowId, 'ultrasonic')) {
          markFieldPrefilled(flowId, 'из ТУ');
        }
      } else if (fmRaw.includes('электро')) {
        if (setSurveyControlValue(flowId, 'electromagnetic')) {
          markFieldPrefilled(flowId, 'из ТУ');
        }
      }

      const add = parsedParams.additional || {};
      if (Array.isArray(add.notes) && add.notes.length) {
        const cur = document.getElementById('s_comments');
        if (cur && !String(cur.value).trim()) {
          cur.value = add.notes.filter(Boolean).join('\n');
          markFieldPrefilled('s_comments', 'из ТУ');
        }
      }

      const manuId = surveyFieldId('manufacturer');
      const manuEl = document.getElementById(manuId);
      if (manuEl && !String(manuEl.value).trim()) {
        markFieldNeedsInput(manuId, 'выберите производителя');
      }

      const flowEl = document.getElementById(flowId);
      if (flowEl && !String(flowEl.value).trim()) {
        markFieldNeedsInput(flowId, 'заполните');
      }
    }

    /**
     * Данные парсера ТУ → поля формы + блок уверенности/предупреждений.
     * @param {object|null|undefined} parsed
     */

// ── Apply parsed/saved data to survey form ─────────────────────────
    function applyParsedParamsToSurvey(parsed) {
      prefillSurvey(parsed);
      showSurveyMeta(parsed);
    }

    /**
     * Подставляет сохранённые ранее ответы опроса (ключи как в collectSurveyData).
     * @param {object|null|undefined} data
     */
    function applySurveyData(data) {
      if (!data || typeof data !== 'object') return;
      for (const [key, val] of Object.entries(data)) {
        if (val === null || val === undefined) continue;
        const id = 's_' + key;
        const el = document.getElementById(id);
        if (!el) continue;
        if (el.type === 'checkbox') {
          el.checked = !!val;
        } else if (el.tagName === 'SELECT') {
          const str = String(val);
          if ([...el.options].some(o => o.value === str)) el.value = str;
        } else {
          el.value = String(val);
        }
      }
      const otherRow = document.getElementById('s_manufacturer_other_row');
      const manu = document.getElementById('s_manufacturer');
      if (otherRow && manu && manu.value === 'other') {
        otherRow.style.display = 'block';
      }
    }

// ── Survey collection ──────────────────────────────────────────────
    function collectSurveyData() {
      const manufacturer = strVal('s_manufacturer');
      return {
        building_type: strVal('s_building_type') || null,
        floors: numVal('s_floors'),
        construction_year: numVal('s_construction_year'),
        heat_supply_source: strVal('s_heat_supply_source') || null,
        city: strVal('s_city') || null,
        connection_type: strVal('s_connection_type') || null,
        system_type: strVal('s_system_type') || null,
        supply_temp: numVal('s_supply_temp'),
        return_temp: numVal('s_return_temp'),
        pressure_supply: numVal('s_pressure_supply'),
        pressure_return: numVal('s_pressure_return'),
        heat_load_total: numVal('s_heat_load_total'),
        heat_load_heating: numVal('s_heat_load_heating'),
        heat_load_hw: numVal('s_heat_load_hw'),
        heat_load_vent: numVal('s_heat_load_vent'),
        heat_load_tech: numVal('s_heat_load_tech'),
        pipe_dn_supply: numVal('s_pipe_dn_supply'),
        pipe_dn_return: numVal('s_pipe_dn_return'),
        has_mud_separators: strVal('s_has_mud_separators') || null,
        has_filters: strVal('s_has_filters') || null,
        manufacturer: manufacturer || null,
        manufacturer_other: manufacturer === 'other' ? strVal('s_manufacturer_other') : null,
        flow_meter_type: strVal('s_flow_meter_type') || null,
        accuracy_class: strVal('s_accuracy_class') || null,
        meter_location: strVal('s_meter_location') || null,
        distance_to_vru: numVal('s_distance_to_vru'),
        rso_requirements: strVal('s_rso_requirements') || null,
        comments: strVal('s_comments') || null,
      };
    }

// ── Survey validation & submit handler ─────────────────────────────
    function validateSurveyFields() {
      let firstInvalid = null;
      let hasErrors = false;
      for (const [id, type] of SURVEY_REQUIRED_FIELDS) {
        const el = document.getElementById(id);
        if (!el) continue;
        const empty = type === 'num'
          ? (numVal(id) === null)
          : (strVal(id) === '' || strVal(id) === null);
        if (empty) {
          el.classList.add('field-invalid');
          if (!firstInvalid) firstInvalid = el;
          hasErrors = true;
        } else {
          el.classList.remove('field-invalid');
        }
      }
      return { hasErrors, firstInvalid };
    }

    if ($surveySubmitBtn) $surveySubmitBtn.addEventListener('click', async () => {
      hideSurveyError();

      const { hasErrors, firstInvalid } = validateSurveyFields();
      if (hasErrors) {
        showSurveyError('Заполните все обязательные поля');
        if (firstInvalid) firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }

      $surveySubmitBtn.disabled = true;
      $surveySubmitBtn.innerHTML = '<span class="spinner"></span> Сохранение…';

      try {
        const resp = await fetch(`${API_BASE}/landing/orders/${ORDER_ID}/survey`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(collectSurveyData()),
        });
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          throw new Error(formatHttpDetail(data.detail) || `HTTP ${resp.status}`);
        }
        orderData.survey_data = collectSurveyData();
        surveySavedCustom = true;
        applySurveySavedVisuals(true);
        syncSubmitButtonState();
        if (typeof showSchemeConfiguratorIfNeeded === 'function') {
          showSchemeConfiguratorIfNeeded();
        }
        if ($surveyCard) {
          $surveyCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        showBanner('success', 'Опросный лист сохранён. Вы можете отправить заявку сейчас или дополнительно загрузить документы из списка выше.', 12000);
      } catch (err) {
        showSurveyError(`Ошибка: ${err.message}`);
        $surveySubmitBtn.disabled = false;
        $surveySubmitBtn.innerHTML = 'Сохранить опросный лист';
        if ($surveyBackActions) $surveyBackActions.style.display = 'none';
      }
    });

    // Снимаем подсветку ошибки при изменении поля
    SURVEY_REQUIRED_FIELDS.forEach(([id]) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('input', () => el.classList.remove('field-invalid'));
    });

// ── Inline-handler export ──────────────────────────────────────────
window.toggleSurveyCollapse = toggleSurveyCollapse;
