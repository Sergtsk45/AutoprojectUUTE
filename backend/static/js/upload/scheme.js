/**
 * @file: scheme.js
 * @description: Модуль конфигуратора принципиальной схемы теплового пункта.
 *   Управляет опросником (тип присоединения, клапан, ГВС, вентиляция),
 *   и демонстрационным превью SVG. Показывается для custom-заявок после
 *   сохранения опросного листа.
 * @dependencies: config.js, utils.js, upload.js (ORDER_ID, orderData,
 *   surveySavedCustom, CUSTOM_EDITABLE_STATUSES, fetchOrder)
 * @created: 2026-04-23
 */

// ── Scheme Configurator ─────────────────────────────────────────────────────

    const $schemeConfiguratorCard = document.getElementById('schemeConfiguratorCard');
    const $schemeValveQuestion = document.getElementById('schemeValveQuestion');
    const $schemeVentQuestion = document.getElementById('schemeVentQuestion');
    const $schemeConfigSummary = document.getElementById('schemeConfigSummary');
    const $schemeSummaryText = document.getElementById('schemeSummaryText');
    const $schemePreviewBlock = document.getElementById('schemePreviewBlock');
    const $schemePreviewContainer = document.getElementById('schemePreviewContainer');
    const $schemeRefreshBtn = document.getElementById('schemeRefreshBtn');

    let currentSchemeConfig = null;

    function getSchemeConfig() {
      const connectionType = document.querySelector('input[name="connection_type"]:checked')?.value;
      if (!connectionType || connectionType === 'unknown') return null;

      const config = {
        connection_type: connectionType,
        has_valve: connectionType === 'independent',
        has_gwp: document.getElementById('has_gwp')?.checked || false,
        has_ventilation: document.getElementById('has_ventilation')?.checked || false,
      };

      if (connectionType === 'dependent') {
        const valveValue = document.querySelector('input[name="has_valve"]:checked')?.value;
        config.has_valve = valveValue === 'yes';
      }

      return config;
    }

    function handleConnectionTypeChange() {
      const connectionType = document.querySelector('input[name="connection_type"]:checked')?.value;
      if (connectionType === 'dependent') {
        $schemeValveQuestion.style.display = '';
      } else {
        $schemeValveQuestion.style.display = 'none';
        document.querySelectorAll('input[name="has_valve"]').forEach(el => el.checked = false);
      }
      updateSchemeUI();
    }

    function handleGwpChange() {
      const hasGwp = document.getElementById('has_gwp')?.checked;
      if (hasGwp) {
        $schemeVentQuestion.style.display = '';
      } else {
        $schemeVentQuestion.style.display = 'none';
        const ventCheckbox = document.getElementById('has_ventilation');
        if (ventCheckbox) ventCheckbox.checked = false;
      }
      updateSchemeUI();
    }

    function updateSchemeUI() {
      const config = getSchemeConfig();
      currentSchemeConfig = config;

      if (!config) {
        $schemeConfigSummary.style.display = 'none';
        $schemePreviewBlock.style.display = 'none';
        return;
      }

      const summaryParts = [config.connection_type === 'dependent' ? 'Зависимая' : 'Независимая'];
      if (config.has_valve) summaryParts.push(config.connection_type === 'dependent' ? '3-ходовой клапан' : '2-ходовой клапан');
      if (config.has_gwp) summaryParts.push('ГВС');
      if (config.has_ventilation) summaryParts.push('Вентиляция');
      $schemeSummaryText.textContent = summaryParts.join(', ');
      $schemeConfigSummary.style.display = '';

      loadSchemePreview(config);
    }

    async function loadSchemePreview(config) {
      if (!config) return;
      $schemePreviewBlock.style.display = '';
      $schemePreviewContainer.innerHTML = '<div class="scheme-preview-loading"><div class="spinner"></div><p>Загрузка схемы...</p></div>';
      try {
        const response = await fetch(`${API_BASE}/schemes/preview`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ config }),
        });
        if (!response.ok) throw new Error('Ошибка генерации превью');
        const data = await response.json();
        $schemePreviewContainer.innerHTML = data.svg_content;
      } catch (error) {
        console.error('Scheme preview error:', error);
        $schemePreviewContainer.innerHTML = '<p style="color: var(--c-error);">Ошибка загрузки превью. Попробуйте обновить.</p>';
      }
    }

    function prefillSchemeConfig(config) {
      if (!config) return;
      const connectionType = config.connection_type === 'independent' ? 'independent' : 'dependent';
      const connectionRadio = document.querySelector(`input[name="connection_type"][value="${connectionType}"]`);
      if (connectionRadio) { connectionRadio.checked = true; handleConnectionTypeChange(); }
      if (connectionType === 'dependent') {
        const valveRadio = document.querySelector(`input[name="has_valve"][value="${config.has_valve ? 'yes' : 'no'}"]`);
        if (valveRadio) valveRadio.checked = true;
      }
      const gwpCheckbox = document.getElementById('has_gwp');
      if (gwpCheckbox) { gwpCheckbox.checked = config.has_gwp || false; handleGwpChange(); }
      const ventCheckbox = document.getElementById('has_ventilation');
      if (ventCheckbox && config.has_ventilation) ventCheckbox.checked = true;
      updateSchemeUI();
    }

    function suggestSchemeFromParsedParams() {
      if (!orderData || !orderData.parsed_params) return;
      const parsed = orderData.parsed_params;
      if (parsed.connection && parsed.connection.connection_type) {
        const connType = parsed.connection.connection_type.toLowerCase();
        const val = (connType.includes('зависим') || connType.includes('dependent')) ? 'dependent'
          : (connType.includes('независим') || connType.includes('independent')) ? 'independent' : null;
        if (val) {
          const radio = document.querySelector(`input[name="connection_type"][value="${val}"]`);
          if (radio) { radio.checked = true; handleConnectionTypeChange(); }
        }
      }
      if (parsed.connection && parsed.connection.heating_system) {
        const hs = parsed.connection.heating_system.toLowerCase();
        if (hs.includes('гвс') || hs.includes('горяч')) {
          const cb = document.getElementById('has_gwp');
          if (cb) { cb.checked = true; handleGwpChange(); }
        }
      }
    }

    function showSchemeConfiguratorIfNeeded() {
      if (!orderData || !$schemeConfiguratorCard) return;
      const shouldShow = orderData.order_type === 'custom'
        && CUSTOM_EDITABLE_STATUSES.includes(orderData.order_status)
        && surveySavedCustom;
      if (shouldShow) {
        $schemeConfiguratorCard.style.display = 'block';
        if (orderData.survey_data && orderData.survey_data.scheme_config) {
          prefillSchemeConfig(orderData.survey_data.scheme_config);
        } else {
          suggestSchemeFromParsedParams();
        }
      } else {
        $schemeConfiguratorCard.style.display = 'none';
      }
    }

    if ($schemeConfiguratorCard) {
      document.querySelectorAll('input[name="connection_type"]').forEach(r => r.addEventListener('change', handleConnectionTypeChange));
      document.querySelectorAll('input[name="has_valve"]').forEach(r => r.addEventListener('change', updateSchemeUI));
      const gwpCb = document.getElementById('has_gwp');
      if (gwpCb) gwpCb.addEventListener('change', handleGwpChange);
      const ventCb = document.getElementById('has_ventilation');
      if (ventCb) ventCb.addEventListener('change', updateSchemeUI);
      if ($schemeRefreshBtn) $schemeRefreshBtn.addEventListener('click', () => { if (currentSchemeConfig) loadSchemePreview(currentSchemeConfig); });
    }
