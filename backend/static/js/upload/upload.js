/**
 * @file: upload.js
 * @description: Entry-модуль страницы /upload/<id>. Отвечает за первичную
 *   загрузку данных (init), отрисовку чеклиста и селектора категорий,
 *   drag&drop + XHR-загрузку файлов, submit-хендлер «Всё загружено»,
 *   finalize (showCompleted), polling статуса парсинга ТУ и переход
 *   к initCustomOrderUi. Привязывает обработчик подписанного договора.
 * @dependencies: config.js, utils.js, survey.js, contract.js
 * @created: 2026-04-22
 */

// ── Init custom-order UI by order_status ───────────────────────────
    function initCustomOrderUi() {
      const status = orderData.order_status || 'new';

      if (status === 'contract_sent') {
        showContractSentState();
        return true;
      }

      if (status === 'new') {
        $surveyCard.style.display = 'none';
        if ($submitBtn) $submitBtn.innerHTML = 'Загрузить';
        return true;
      }
      if (status === 'tu_parsing') {
        showParsingState();
        startParsingPoll();
        return true;
      }
      if (CUSTOM_EDITABLE_STATUSES.includes(status)) {
        showSurveyCard();
        if (hasMeaningfulSurveyData(orderData.survey_data)) {
          prefillSurveyFromSaved(orderData.survey_data);
          applySurveySavedVisuals(true);
        } else if (orderData.parsed_params && Object.keys(orderData.parsed_params).length > 0) {
          unlockSurveyCard();
          clearSurveyDecorations();
          applyParsedParamsToSurvey(orderData.parsed_params);
          applySurveySavedVisuals(false);
        } else {
          unlockSurveyCard();
          clearSurveyDecorations();
          applySurveySavedVisuals(false);
        }
        showUploadAlongsideSurveyIfNeeded(orderData);
        return true;
      }
      if (status === 'advance_paid' || status === 'awaiting_final_payment' || status === 'review' || status === 'completed') {
        showCompleted();
        return true;
      }
      if (status === 'error') {
        showBanner('error', 'Произошла ошибка. Свяжитесь с нами.');
        $surveyCard.style.display = 'none';
        $parsingCard.style.display = 'none';
        $completedCard.style.display = 'none';
        $uploadCard.style.display = 'block';
        unlockSurveyCard();
        return true;
      }
      return false;
    }

// ── Init (fetch order + kickoff UI) ────────────────────────────────
    async function init() {
      try {
        const resp = await fetch(`${API_BASE}/landing/orders/${ORDER_ID}/upload-page`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        orderData = await resp.json();
        isNewOrder = !orderData.order_status || orderData.order_status === 'new';

        $badge.textContent = `Заявка №${ORDER_ID.slice(0, 8)}`;
        $greeting.innerHTML = `<strong>${orderData.client_name}</strong>, здравствуйте! Загрузите документы, необходимые для проектирования узла учёта.`;
        if ($requiredDocsCard) $requiredDocsCard.style.display = '';

        // Track already uploaded
        (orderData.files_uploaded || []).forEach(f => uploadedCategories.add(f.category));

        renderChecklist();
        renderCategoryOptions();

        if (orderData.order_status === 'contract_sent') {
          showContractSentState();
        } else if (orderData.order_type === 'custom') {
          if (!initCustomOrderUi()) {
            $surveyCard.style.display = 'none';
          }
        } else {
          $surveyCard.style.display = 'none';
          if (['advance_paid', 'awaiting_final_payment', 'review', 'completed'].includes(orderData.order_status)) {
            showCompleted();
          }
        }

        $loading.style.display = 'none';
        $main.style.display = 'block';

        const mp = orderData.missing_params || [];
        const still = mp.filter(p => !uploadedCategories.has(p));
        if (still.length === 0 && mp.length > 0) {
          const st = orderData.order_status;
          const customKeepUploadPage =
            orderData.order_type === 'custom' &&
            (st === 'new' ||
              st === 'tu_parsing' ||
              CUSTOM_EDITABLE_STATUSES.includes(st));
          if (!customKeepUploadPage) {
            showCompleted();
          }
        }

        surveySavedCustom =
          orderData.order_type === 'custom' && hasMeaningfulSurveyData(orderData.survey_data);
        syncSubmitButtonState();
      } catch (err) {
        $loading.style.display = 'none';
        $error.style.display = 'block';
        $errorText.textContent = 'Не удалось загрузить данные заявки. Проверьте ссылку или обратитесь в поддержку.';
        console.error(err);
      }
    }

// ── Render checklist ───────────────────────────────────────────────
    function renderChecklist() {
      $checklist.innerHTML = '';
      const rawCodes = orderData.missing_params || [];
      const isWaitingFlow = ['waiting_client_info', 'client_info_received'].includes(orderData.order_status);
      const hasCompanyCard = rawCodes.includes('company_card');
      const codes = isWaitingFlow && hasCompanyCard
        ? rawCodes.filter(c => c !== 'company_card').concat('company_card')
        : rawCodes.slice();

      const appendItem = (code, extraClass) => {
        const info = PARAM_LABELS[code] || { label: code, hint: '' };
        const done = uploadedCategories.has(code);
        const li = document.createElement('li');
        const classes = [done ? 'done' : 'pending'];
        if (extraClass) classes.push(extraClass);
        li.className = classes.join(' ');
        li.innerHTML = `
          <svg class="status-icon" viewBox="0 0 20 20" fill="currentColor">
            ${done
              ? '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>'
              : '<circle cx="10" cy="10" r="7.5" fill="none" stroke="#d97706" stroke-width="1.5"/><circle cx="10" cy="10" r="2" fill="#d97706"/>'
            }
          </svg>
          <span class="label">
            ${info.label}
            ${info.hint ? `<span class="hint">${info.hint}</span>` : ''}
          </span>
        `;
        $checklist.appendChild(li);
      };

      codes.forEach(code => {
        if (isWaitingFlow && code === 'company_card') {
          const sep = document.createElement('li');
          sep.className = 'checklist-separator';
          sep.textContent = 'Реквизиты для договора';
          $checklist.appendChild(sep);
          appendItem(code, 'company-card-item');
          return;
        }
        appendItem(code, '');
      });
    }

// ── Render category dropdown ───────────────────────────────────────
    function renderCategoryOptions() {
      $catSelect.innerHTML = '';
      const optPlaceholder = document.createElement('option');
      optPlaceholder.value = '';
      optPlaceholder.textContent = '— Выберите тип документа —';
      $catSelect.appendChild(optPlaceholder);

      const codes = [];
      if (isNewOrder && !uploadedCategories.has('tu')) {
        codes.push('tu');
      }
      (orderData.missing_params || []).forEach(code => {
        if (uploadedCategories.has(code)) return;
        if (code === 'tu' && codes.includes('tu')) return;
        codes.push(code);
      });

      codes.forEach(code => {
        const info =
          code === 'tu'
            ? { label: 'Технические условия' }
            : PARAM_LABELS[code] || { label: code };
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = info.label;
        $catSelect.appendChild(opt);
      });

      const optOther = document.createElement('option');
      optOther.value = 'other';
      optOther.textContent = 'Другой документ';
      $catSelect.appendChild(optOther);

      if (isNewOrder && codes.includes('tu')) {
        $catSelect.value = 'tu';
      }
    }

// ── Drag & drop + file input listeners ─────────────────────────────
    $dropzone.addEventListener('dragover', e => {
      e.preventDefault();
      $dropzone.classList.add('dragover');
    });
    $dropzone.addEventListener('dragleave', () => {
      $dropzone.classList.remove('dragover');
    });
    $dropzone.addEventListener('drop', e => {
      e.preventDefault();
      $dropzone.classList.remove('dragover');
      handleFiles(e.dataTransfer.files);
    });
    $fileInput.addEventListener('change', () => {
      handleFiles($fileInput.files);
      $fileInput.value = '';
    });

// ── Handle file selection ──────────────────────────────────────────
    function handleFiles(fileList) {
      const category = $catSelect.value;
      if (!category) {
        showBanner('error', 'Сначала выберите тип документа');
        return;
      }
      if (isNewOrder && category !== 'tu') {
        showBanner('error', 'На этом этапе можно загрузить только технические условия');
        return;
      }

      for (const file of fileList) {
        if (file.size > 25 * 1024 * 1024) {
          showBanner('error', `Файл «${file.name}» превышает 25 МБ`);
          continue;
        }
        uploadFile(file, category);
      }
    }

// ── Upload single file (XHR + progress) ────────────────────────────
    async function uploadFile(file, category) {
      const item = document.createElement('div');
      item.className = 'upload-item';
      item.innerHTML = `
        <span class="filename">${file.name}</span>
        <span class="size">${formatSize(file.size)}</span>
        <div class="progress-bar"><div class="fill" style="width:0%"></div></div>
        <span class="status-text">0%</span>
      `;
      $queue.appendChild(item);

      const fill = item.querySelector('.fill');
      const statusText = item.querySelector('.status-text');

      try {
        const formData = new FormData();
        formData.append('file', file);

        // Use XMLHttpRequest for progress tracking
        await new Promise((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          const uploadUrl = isNewOrder
            ? `${API_BASE}/landing/orders/${ORDER_ID}/upload-tu`
            : `${API_BASE}/pipeline/${ORDER_ID}/client-upload?category=${encodeURIComponent(category)}`;
          xhr.open('POST', uploadUrl);

          xhr.upload.onprogress = e => {
            if (e.lengthComputable) {
              const pct = Math.round((e.loaded / e.total) * 100);
              fill.style.width = pct + '%';
              statusText.textContent = pct + '%';
            }
          };

          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve(JSON.parse(xhr.responseText));
            } else {
              reject(new Error(`HTTP ${xhr.status}`));
            }
          };

          xhr.onerror = () => reject(new Error('Ошибка сети'));
          xhr.send(formData);
        });

        // Success
        item.classList.add('success');
        fill.style.width = '100%';
        statusText.className = 'status-text ok';
        statusText.textContent = '✓';
        uploadedCategories.add(category);
        renderChecklist();
        renderCategoryOptions();

        syncSubmitButtonState();

      } catch (err) {
        item.classList.add('error');
        fill.style.width = '100%';
        statusText.className = 'status-text err';
        statusText.textContent = 'Ошибка';
        console.error('Upload failed:', err);
      }
    }

// ── Submit (all done) listener ─────────────────────────────────────
    $submitBtn.addEventListener('click', async () => {
      $submitBtn.disabled = true;
      $submitBtn.innerHTML = '<span class="spinner"></span> Отправка…';

      try {
        const doneUrl = isNewOrder
          ? `${API_BASE}/landing/orders/${ORDER_ID}/submit`
          : `${API_BASE}/pipeline/${ORDER_ID}/client-upload-done`;
        const resp = await fetch(doneUrl, { method: 'POST' });
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          throw new Error(formatHttpDetail(data.detail) || `HTTP ${resp.status}`);
        }

        const customNewParsing =
          orderData.order_type === 'custom' && isNewOrder;

        if (customNewParsing) {
          showParsingState();
          startParsingPoll();
          showBanner('success', 'Документы отправлены! Мы начали обработку вашей заявки.');
        } else {
          showCompleted();
          showBanner('success', 'Документы отправлены! Мы начали обработку вашей заявки.');
        }

      } catch (err) {
        showBanner('error', `Ошибка: ${err.message}`);
        $submitBtn.innerHTML = 'Всё загружено — отправить';
        syncSubmitButtonState();
      }
    });

// ── Completed state ────────────────────────────────────────────────
    function showCompleted() {
      if ($requiredDocsCard) $requiredDocsCard.style.display = '';
      if ($contractSentCard) $contractSentCard.style.display = 'none';
      $uploadCard.style.display = 'none';
      $surveyCard.style.display = 'none';
      $parsingCard.style.display = 'none';
      unlockSurveyCard();
      $completedCard.style.display = 'block';
      if (orderData && orderData.order_type !== 'custom' && $greeting) {
        $greeting.innerHTML = `<strong>${orderData.client_name}</strong>, спасибо! Документы загружены, ждите готовый проект или запрос на уточнения.`;
      }
    }

// ── Parsing state / polling ────────────────────────────────────────
    function showParsingState() {
      if ($requiredDocsCard) $requiredDocsCard.style.display = '';
      if ($contractSentCard) $contractSentCard.style.display = 'none';
      $uploadCard.style.display = 'none';
      $parsingCard.style.display = 'block';
      $surveyCard.style.display = 'none';
    }

    function stopParsingPoll() {
      if (parsingPollTimer !== null) {
        clearInterval(parsingPollTimer);
        parsingPollTimer = null;
      }
      parsingPollCount = 0;
    }

    function showParsingTimeout() {
      $parsingCard.style.display = 'none';
      $uploadCard.style.display = 'block';
      showBanner('error', 'Анализ занимает больше времени, чем обычно. Обновите страницу через несколько минут или обратитесь в поддержку.');
    }

    let parsingPollBusy = false;

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
            showParsingTimeout();
            return;
          }

          const resp = await fetch(`${API_BASE}/landing/orders/${ORDER_ID}/upload-page`);
          if (!resp.ok) return;

          const data = await resp.json();
          const st = data.order_status;

          if (st === 'error') {
            stopParsingPoll();
            $parsingCard.style.display = 'none';
            $uploadCard.style.display = 'block';
            showBanner('error', 'Ошибка анализа ТУ. Попробуйте загрузить файл снова.');
            return;
          }

          if (POST_PARSE_STATUSES.has(st)) {
            stopParsingPoll();
            orderData = data;
            isNewOrder = false;
            uploadedCategories.clear();
            (data.files_uploaded || []).forEach(f => uploadedCategories.add(f.category));
            renderChecklist();
            renderCategoryOptions();
            $parsingCard.style.display = 'none';

            if (st === 'review' || st === 'completed') {
              showCompleted();
              showBanner('success', 'Заявка обновлена.');
              return;
            }

            hydrateSurveyFromOrder(data);
            showSurveyCard();
            showUploadAlongsideSurveyIfNeeded(data);
            $submitBtn.innerHTML = 'Всё загружено — отправить';
            surveySavedCustom =
              data.order_type === 'custom' && hasMeaningfulSurveyData(data.survey_data);
            if (data.order_type === 'custom' && hasMeaningfulSurveyData(data.survey_data)) {
              applySurveySavedVisuals(true);
            } else {
              applySurveySavedVisuals(false);
            }
            syncSubmitButtonState();
            showBanner('success', 'Анализ завершён! Проверьте и дополните данные.');
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

// ── Signed contract handlers + Start ───────────────────────────────
bindSignedContractHandlers();
init();
