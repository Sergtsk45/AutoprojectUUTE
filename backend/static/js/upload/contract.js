/**
 * @file: contract.js
 * @description: Логика экрана «договор и оплата»: метаданные договора,
 *   upload подписанного договора (PDF/JPG), визуальные состояния,
 *   привязка drag&drop/change-обработчиков через bindSignedContractHandlers().
 * @dependencies: config.js, utils.js, survey.js (prefillSurveyFromSaved)
 * @created: 2026-04-22
 */

// ── Contract meta + signed contract UI states ──────────────────────
    function renderContractMeta(data) {
      if (!$contractMeta) return;
      const rows = [
        ['Номер договора', data.contract_number || '—'],
        ['Сумма договора', formatMoneyRub(data.payment_amount)],
      ];
      if (data.advance_amount !== null && data.advance_amount !== undefined && data.advance_amount !== '') {
        rows.push(['Сумма аванса', formatMoneyRub(data.advance_amount)]);
      }
      $contractMeta.innerHTML = rows
        .map(([k, v]) => `<dt>${escapeHtml(String(k))}</dt><dd>${escapeHtml(String(v))}</dd>`)
        .join('');
    }

    function setSignedContractAcceptedState() {
      if ($signedContractSuccess) $signedContractSuccess.style.display = 'block';
      if ($signedContractInput) {
        $signedContractInput.value = '';
        $signedContractInput.disabled = true;
      }
      if ($signedContractDropzone) {
        $signedContractDropzone.style.opacity = '0.65';
        $signedContractDropzone.style.pointerEvents = 'none';
      }
    }

    function resetSignedContractState() {
      if ($signedContractSuccess) $signedContractSuccess.style.display = 'none';
      if ($signedContractInput) {
        $signedContractInput.value = '';
        $signedContractInput.disabled = false;
      }
      if ($signedContractDropzone) {
        $signedContractDropzone.style.opacity = '1';
        $signedContractDropzone.style.pointerEvents = '';
      }
      if ($signedContractQueue) $signedContractQueue.innerHTML = '';
    }

    function showContractSentState() {
      if ($requiredDocsCard) $requiredDocsCard.style.display = 'none';
      $uploadCard.style.display = 'none';
      $surveyCard.style.display = 'none';
      $parsingCard.style.display = 'none';
      $completedCard.style.display = 'none';
      if ($contractSentCard) $contractSentCard.style.display = 'block';
      renderContractMeta(orderData || {});
      const alreadyUploaded = uploadedCategories.has('signed_contract');
      if (alreadyUploaded) {
        setSignedContractAcceptedState();
      } else {
        resetSignedContractState();
      }
    }

// ── Upload alongside survey ────────────────────────────────────────
    /**
     * Показать блок загрузки вместе с опросником (доп. документы после ТУ).
     * @param {object} data — orderData с order_status и missing_params
     */
    function showUploadAlongsideSurveyIfNeeded(data) {
      const st = data.order_status;
      if (st === 'waiting_client_info' || st === 'client_info_received') {
        showUploadCardForDocs();
        return;
      }
      const missing = data.missing_params || [];
      if (missing.length > 0 && ['tu_parsed', 'data_complete', 'generating_project'].includes(st)) {
        showUploadCardForDocs();
      }
    }

// ── Prefill survey from saved snapshot ─────────────────────────────
    /**
     * Плоский JSON survey_data (ключи как в collectSurveyData) → поля s_*.
     * @param {object} surveyData
     */
    function prefillSurveyFromSaved(surveyData) {
      unlockSurveyCard();
      clearSurveyDecorations();
      applySurveyData(surveyData);
      hideSurveyMeta();
      lockFilledSurveyFields(surveyData);
    }

// ── Signed contract file validation & upload ───────────────────────
    function validateSignedContractFile(file) {
      if (!file) return 'Файл не выбран';
      if (file.size > 25 * 1024 * 1024) return `Файл «${file.name}» превышает 25 МБ`;
      const ext = (file.name.split('.').pop() || '').toLowerCase();
      if (!['pdf', 'jpg', 'jpeg', 'png'].includes(ext)) {
        return 'Допустимые форматы: PDF, JPG, JPEG, PNG';
      }
      return '';
    }

    async function uploadSignedContract(file) {
      const err = validateSignedContractFile(file);
      if (err) {
        showBanner('error', err);
        return;
      }

      const item = document.createElement('div');
      item.className = 'upload-item';
      item.innerHTML = `
        <span class="filename">${escapeHtml(file.name)}</span>
        <span class="size">${formatSize(file.size)}</span>
        <div class="progress-bar"><div class="fill" style="width:0%"></div></div>
        <span class="status-text">0%</span>
      `;
      $signedContractQueue.innerHTML = '';
      $signedContractQueue.appendChild(item);

      const fill = item.querySelector('.fill');
      const statusText = item.querySelector('.status-text');

      try {
        const formData = new FormData();
        formData.append('file', file);
        await new Promise((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          xhr.open('POST', `${API_BASE}/landing/orders/${ORDER_ID}/upload-signed-contract`);
          xhr.upload.onprogress = e => {
            if (e.lengthComputable) {
              const pct = Math.round((e.loaded / e.total) * 100);
              fill.style.width = pct + '%';
              statusText.textContent = pct + '%';
            }
          };
          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve();
            } else {
              reject(new Error(`HTTP ${xhr.status}`));
            }
          };
          xhr.onerror = () => reject(new Error('Ошибка сети'));
          xhr.send(formData);
        });

        item.classList.add('success');
        fill.style.width = '100%';
        statusText.className = 'status-text ok';
        statusText.textContent = '✓';
        uploadedCategories.add('signed_contract');
        setSignedContractAcceptedState();
      } catch (e) {
        item.classList.add('error');
        fill.style.width = '100%';
        statusText.className = 'status-text err';
        statusText.textContent = 'Ошибка';
        showBanner('error', `Ошибка загрузки: ${e.message}`);
      }
    }


// ── Bind drag&drop + change handlers for signed contract zone ──────
function bindSignedContractHandlers() {
    if ($signedContractDropzone) {
      $signedContractDropzone.addEventListener('dragover', e => {
        e.preventDefault();
        $signedContractDropzone.classList.add('dragover');
      });
      $signedContractDropzone.addEventListener('dragleave', () => {
        $signedContractDropzone.classList.remove('dragover');
      });
      $signedContractDropzone.addEventListener('drop', e => {
        e.preventDefault();
        $signedContractDropzone.classList.remove('dragover');
        const files = e.dataTransfer && e.dataTransfer.files ? e.dataTransfer.files : null;
        if (!files || files.length === 0) return;
        uploadSignedContract(files[0]);
      });
    }
    if ($signedContractInput) {
      $signedContractInput.addEventListener('change', () => {
        if (!$signedContractInput.files || $signedContractInput.files.length === 0) return;
        uploadSignedContract($signedContractInput.files[0]);
      });
    }
}
