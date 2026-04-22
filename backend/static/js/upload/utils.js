/**
 * @file: utils.js
 * @description: Утилиты страницы upload: экранирование, форматирование,
 *   банер, HTTP-детали, вспомогательные strVal/numVal, syncSubmitButtonState,
 *   showDocsOptionalHint, applySurveySavedVisuals, DOM-refs (глобальные $*).
 * @dependencies: config.js
 * @created: 2026-04-22
 */

// ── HTTP helpers ────────────────────────────────────────────────────
    function formatHttpDetail(detail) {
      if (detail == null) return '';
      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail)) {
        return detail.map(x => (x && typeof x === 'object' && x.msg ? x.msg : JSON.stringify(x))).join('; ');
      }
      if (typeof detail === 'object' && detail.msg) return String(detail.msg);
      try {
        return JSON.stringify(detail);
      } catch (e) {
        return String(detail);
      }
    }

// ── Submit button state / hints / badges ───────────────────────────
    function syncSubmitButtonState() {
      if (!$submitBtn) return;
      if (isNewOrder) {
        $submitBtn.disabled = uploadedCategories.size === 0;
        showDocsOptionalHint(false);
        return;
      }
      const customPost =
        orderData &&
        orderData.order_type === 'custom' &&
        CUSTOM_EDITABLE_STATUSES.includes(orderData.order_status);
      if (customPost) {
        if (!surveySavedCustom) {
          $submitBtn.disabled = true;
          $submitBtn.title = 'Сначала сохраните опросный лист внизу страницы';
          showDocsOptionalHint(false);
          return;
        }
        $submitBtn.disabled = false;
        $submitBtn.title = '';
        const mp = orderData.missing_params || [];
        const allDone = mp.length === 0 || mp.every(code => uploadedCategories.has(code));
        showDocsOptionalHint(!allDone);
        return;
      }
      $submitBtn.title = '';
      $submitBtn.disabled = uploadedCategories.size === 0;
      showDocsOptionalHint(false);
    }

    function showDocsOptionalHint(show) {
      const el = document.getElementById('docsOptionalHint');
      if (el) el.style.display = show ? 'block' : 'none';
    }

    function applySurveySavedVisuals(saved) {
      if (!$surveySubmitBtn || !$surveyDoneBadge) return;
      if (saved) {
        $surveySubmitBtn.style.display = 'none';
        $surveyDoneBadge.style.display = 'inline-flex';
        if ($surveyBackActions) $surveyBackActions.style.display = 'flex';
      } else {
        $surveySubmitBtn.style.display = '';
        $surveySubmitBtn.disabled = false;
        $surveySubmitBtn.innerHTML = 'Сохранить опросный лист';
        $surveyDoneBadge.style.display = 'none';
        if ($surveyBackActions) $surveyBackActions.style.display = 'none';
      }
    }

// ── DOM refs ────────────────────────────────────────────────────────
    const $loading     = document.getElementById('loadingScreen');
    const $error       = document.getElementById('errorScreen');
    const $errorText   = document.getElementById('errorText');
    const $main        = document.getElementById('mainContent');
    const $badge       = document.getElementById('orderBadge');
    const $greeting    = document.getElementById('greetingText');
    const $checklist   = document.getElementById('checklist');
    const $requiredDocsCard = document.getElementById('requiredDocsCard');
    const $catSelect   = document.getElementById('categorySelect');
    const $dropzone    = document.getElementById('dropzone');
    const $fileInput   = document.getElementById('fileInput');
    const $queue       = document.getElementById('uploadQueue');
    const $submitBtn   = document.getElementById('submitBtn');
    const $uploadCard  = document.getElementById('uploadCard');
    const $parsingCard = document.getElementById('parsingCard');
    const $surveyCard  = document.getElementById('surveyCard');
    const $completedCard = document.getElementById('completedCard');
    const $contractSentCard = document.getElementById('contractSentCard');
    const $contractMeta = document.getElementById('contractMeta');
    const $signedContractDropzone = document.getElementById('signedContractDropzone');
    const $signedContractInput = document.getElementById('signedContractInput');
    const $signedContractQueue = document.getElementById('signedContractQueue');
    const $signedContractSuccess = document.getElementById('signedContractSuccess');
    const $surveyBackActions = document.getElementById('surveyBackActions');
    const $surveySubmitBtn = document.getElementById('surveySubmitBtn');
    const $surveyDoneBadge = document.getElementById('surveyDoneBadge');
    const $banner      = document.getElementById('banner');
    const $bannerText  = document.getElementById('bannerText');

// ── Formatting helpers ─────────────────────────────────────────────
    function formatMoneyRub(amount) {
      if (amount === null || amount === undefined || amount === '') return '—';
      const n = Number(amount);
      if (Number.isNaN(n)) return String(amount);
      return n.toLocaleString('ru-RU') + ' ₽';
    }

    function escapeHtml(s) {
      const d = document.createElement('div');
      d.textContent = s;
      return d.innerHTML;
    }

// ── Banner ─────────────────────────────────────────────────────────
    function showBanner(type, text, durationMs) {
      const ms = typeof durationMs === 'number' ? durationMs : 6000;
      $banner.className = `banner visible ${type}`;
      $bannerText.textContent = text;
      setTimeout(() => { $banner.classList.remove('visible'); }, ms);
    }

// ── Size formatting ────────────────────────────────────────────────
    function formatSize(bytes) {
      if (bytes < 1024) return bytes + ' Б';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' КБ';
      return (bytes / (1024 * 1024)).toFixed(1) + ' МБ';
    }

// ── Survey form input helpers ──────────────────────────────────────
    function strVal(id) {
      const el = document.getElementById(id);
      return el ? el.value.trim() : '';
    }
    function numVal(id) {
      const v = strVal(id);
      return v === '' ? null : parseFloat(v);
    }

// ── Survey error banner ────────────────────────────────────────────
    const $surveyError = document.getElementById('surveyError');
    function showSurveyError(msg) {
      if (!$surveyError) return;
      $surveyError.textContent = msg;
      $surveyError.style.display = 'block';
      $surveyError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    function hideSurveyError() {
      if ($surveyError) $surveyError.style.display = 'none';
    }

