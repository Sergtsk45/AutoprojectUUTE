/**
 * @file: backend/static/js/admin/views-parsed.js
 * @description: Рендер разобранных параметров ТУ, опросного листа и сравнительной
 *   таблицы parsed vs survey.
 *   Фаза E3 (минимальный вариант) — вынос из inline <script> в admin.html.
 *   Зависит от констант/хелперов из config.js (SURVEY_*) и utils.js (esc,
 *   fmtNum, isParsedParamsEmpty).
 * @created: 2026-04-22 (E3)
 */

// ── Survey (опросный лист) ─────────────────────────────────────────────────
    function renderSurveyData(survey) {
      const card = document.getElementById('surveyCard');
      const content = document.getElementById('surveyContent');
      if (!survey || typeof survey !== 'object' || Object.keys(survey).length === 0) {
        card.style.display = 'none';
        return;
      }
      card.style.display = 'block';

      const sections = SURVEY_SECTIONS.map(section => {
        const rows = section.keys
          .filter(k => survey[k] !== undefined && survey[k] !== null && survey[k] !== '')
          .map(k => {
            const label = SURVEY_LABELS[k] || k;
            const v = survey[k];
            let val;
            if (typeof v === 'boolean') {
              val = v ? 'Да' : 'Нет';
            } else {
              const strV = String(v ?? '');
              const map = SURVEY_VALUE_MAP[k];
              val = esc(map && map[strV] ? map[strV] : strV || '—');
            }
            return parsedTableRow(label, `<td class="parsed-value-cell"><span class="parsed-value">${val}</span></td>`);
          });
        if (rows.length === 0) return '';
        return parsedSectionHtml(section.title, rows);
      }).filter(Boolean);

      const sectionsHtml = sections.length > 0
        ? sections.join('')
        : '<p class="parsed-empty-msg">Опросный лист не заполнен</p>';
      content.innerHTML = `<details class="parsed-params-details">
        <summary>Данные опросного листа &#9654;</summary>
        <div class="parsed-details-body">${sectionsHtml}</div>
      </details>`;
    }

// ── Comparison table: parsed ТУ vs survey ──────────────────────────────────
    /** Форматирует значение из parsed_params в <td>. */
    function cmpParsedCell(raw, unit, fmt) {
      if (raw === null || raw === undefined || (typeof raw === 'string' && raw.trim() === '')) {
        return '<td class="parsed-value-cell cmp-parsed-cell"><span class="parsed-null">—</span></td>';
      }
      const inner = fmt ? fmt(raw) : (typeof raw === 'number' ? fmtNum(raw) : esc(String(raw)));
      return `<td class="parsed-value-cell cmp-parsed-cell"><span class="parsed-value">${inner}${unit || ''}</span></td>`;
    }

    /** Форматирует значение из survey_data в <td>. */
    function cmpSurveyCell(key, raw) {
      if (raw === null || raw === undefined || raw === '') {
        return '<td class="parsed-value-cell cmp-survey-cell"><span class="parsed-null">—</span></td>';
      }
      const map = SURVEY_VALUE_MAP[key];
      const strV = String(raw);
      const display = (map && map[strV]) ? map[strV] : strV;
      return `<td class="parsed-value-cell cmp-survey-cell"><span class="parsed-value">${esc(display)}</span></td>`;
    }

    /**
     * Строит строку сравнительной таблицы.
     * mismatch=true подсвечивает строку жёлтым если оба значения есть, но не равны.
     */
    function cmpRow(label, parsedCell, surveyCell, parsedRaw, surveyRaw) {
      const bothExist = (parsedRaw !== null && parsedRaw !== undefined && parsedRaw !== '')
                     && (surveyRaw !== null && surveyRaw !== undefined && surveyRaw !== '');
      const differ = bothExist && String(parsedRaw).trim() !== String(surveyRaw).trim();
      const cls = differ ? ' class="cmp-mismatch"' : '';
      return `<tr${cls}><td class="parsed-label-cell cmp-label-cell">${esc(label)}</td>${parsedCell}${surveyCell}</tr>`;
    }

    /** Строит секцию сравнительной таблицы. */
    function cmpSectionHtml(title, rows) {
      return `
        <div class="parsed-section">
          <div class="parsed-section-title">${title}</div>
          <table class="parsed-params-table">
            <thead><tr>
              <th style="width:32%">Поле</th>
              <th style="width:34%">Парсинг ТУ</th>
              <th style="width:34%">Опросный лист</th>
            </tr></thead>
            <tbody>${rows.join('')}</tbody>
          </table>
        </div>`;
    }

    function renderComparisonTable(params, survey) {
      const card = document.getElementById('comparisonCard');
      const content = document.getElementById('comparisonContent');
      card.style.display = 'block';

      const hl   = heatLoadsFromParams(params);
      const cool = coolantFromParams(params);
      const pipe = pipelineFromParams(params);
      const conn = connectionFromParams(params);
      const met  = meteringFromParams(params);
      const { doc, rsoName, obj, validTo } = documentBlockSources(params);

      // Confidence badge
      let header = '';
      const confidence = params.parse_confidence;
      if (confidence !== undefined && confidence !== null) {
        const pct = Math.round(Number(confidence) * 100);
        const color = pct >= 80 ? '#16a34a' : pct >= 60 ? '#d97706' : '#dc2626';
        header = `<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
          <span style="font-size:13px;color:var(--c-text-secondary);">Уверенность парсинга:</span>
          <span style="font-size:18px;font-weight:700;color:${color};">${pct}%</span>
        </div>`;
      }

      // Document block (только из парсинга — survey-аналога нет)
      const docSection = cmpSectionHtml('📄 Документ (только из ТУ)', [
        parsedTableRow('РСО', fmtParsedValueCell(rsoName, '')),
        parsedTableRow('Номер ТУ', fmtParsedValueCell(doc.tu_number, '')),
        parsedTableRow('Дата ТУ', fmtParsedValueCell(doc.tu_date, '')),
        parsedTableRow('Действует до', fmtParsedValueCell(validTo, '')),
        parsedTableRow('Адрес объекта', fmtParsedValueCell(obj.object_address ?? doc.object_address, '')),
      ].map(r => r.replace('<thead><tr><th>Поле</th><th>Значение</th></tr></thead>', '')));

      // Для секции «Документ» используем обычную 2-колоночную таблицу
      const docSection2col = `
        <div class="parsed-section">
          <div class="parsed-section-title">📄 Документ (только из ТУ)</div>
          <table class="parsed-params-table">
            <thead><tr><th>Поле</th><th>Значение</th></tr></thead>
            <tbody>
              ${parsedTableRow('РСО', fmtParsedValueCell(rsoName, ''))}
              ${parsedTableRow('Номер ТУ', fmtParsedValueCell(doc.tu_number, ''))}
              ${parsedTableRow('Дата ТУ', fmtParsedValueCell(doc.tu_date, ''))}
              ${parsedTableRow('Действует до', fmtParsedValueCell(validTo, ''))}
              ${parsedTableRow('Адрес объекта', fmtParsedValueCell(obj.object_address ?? doc.object_address, ''))}
            </tbody>
          </table>
        </div>`;

      // Секция «Объект» — только из опросника
      const objSection = cmpSectionHtml('🏢 Объект (из опросного листа)', [
        cmpRow('Город',           cmpParsedCell(obj.city), cmpSurveyCell('city', survey.city), obj.city, survey.city),
        cmpRow('Тип здания',           cmpParsedCell(null), cmpSurveyCell('building_type', survey.building_type), null, survey.building_type),
        cmpRow('Этажность',            cmpParsedCell(null), cmpSurveyCell('floors', survey.floors), null, survey.floors),
        cmpRow('Год постройки',        cmpParsedCell(null), cmpSurveyCell('construction_year', survey.construction_year), null, survey.construction_year),
        cmpRow('Источник теплоснабжения', cmpParsedCell(null), cmpSurveyCell('heat_supply_source', survey.heat_supply_source), null, survey.heat_supply_source),
      ]);

      // Теплоснабжение
      const heatSection = cmpSectionHtml('⚡ Теплоснабжение', [
        cmpRow('Схема подключения', cmpParsedCell(conn.connection_type), cmpSurveyCell('connection_type', survey.connection_type), conn.connection_type, survey.connection_type),
        cmpRow('Тип системы',       cmpParsedCell(conn.system_type, '', fmtSystemTypeDisplay), cmpSurveyCell('system_type', survey.system_type), conn.system_type, survey.system_type),
        cmpRow('Температура подачи, °C',   cmpParsedCell(cool.supply_temp, ' °C'), cmpSurveyCell('supply_temp', survey.supply_temp), cool.supply_temp, survey.supply_temp),
        cmpRow('Температура обратки, °C',  cmpParsedCell(cool.return_temp, ' °C'), cmpSurveyCell('return_temp', survey.return_temp), cool.return_temp, survey.return_temp),
        cmpRow('Давление подачи, кгс/см²', cmpParsedCell(cool.supply_pressure_kgcm2, ' кгс/см²'), cmpSurveyCell('pressure_supply', survey.pressure_supply), cool.supply_pressure_kgcm2, survey.pressure_supply),
        cmpRow('Давление обратки, кгс/см²',cmpParsedCell(cool.return_pressure_kgcm2, ' кгс/см²'), cmpSurveyCell('pressure_return', survey.pressure_return), cool.return_pressure_kgcm2, survey.pressure_return),
      ]);

      // Нагрузки
      const loadsSection = cmpSectionHtml('🔥 Тепловые нагрузки, Гкал/ч', [
        cmpRow('Суммарная',   cmpParsedCell(hl.total_load, ' Гкал/ч'), cmpSurveyCell('heat_load_total', survey.heat_load_total), hl.total_load, survey.heat_load_total),
        cmpRow('Отопление',   cmpParsedCell(hl.heating_load, ' Гкал/ч'), cmpSurveyCell('heat_load_heating', survey.heat_load_heating), hl.heating_load, survey.heat_load_heating),
        cmpRow('ГВС',         cmpParsedCell(hl.hot_water_load, ' Гкал/ч'), cmpSurveyCell('heat_load_hw', survey.heat_load_hw), hl.hot_water_load, survey.heat_load_hw),
        cmpRow('Вентиляция',  cmpParsedCell(hl.ventilation_load, ' Гкал/ч'), cmpSurveyCell('heat_load_vent', survey.heat_load_vent), hl.ventilation_load, survey.heat_load_vent),
      ]);

      // Трубопроводы
      const pipeSection = cmpSectionHtml('🔧 Трубопроводы', [
        cmpRow('Ду подачи, мм',   cmpParsedCell(pipe.pipe_outer_diameter_mm, ' мм'), cmpSurveyCell('pipe_dn_supply', survey.pipe_dn_supply), pipe.pipe_outer_diameter_mm, survey.pipe_dn_supply),
        cmpRow('Ду обратки, мм',  cmpParsedCell(null), cmpSurveyCell('pipe_dn_return', survey.pipe_dn_return), null, survey.pipe_dn_return),
        cmpRow('Грязевики',       cmpParsedCell(null), cmpSurveyCell('has_mud_separators', survey.has_mud_separators), null, survey.has_mud_separators),
        cmpRow('Фильтры',         cmpParsedCell(null), cmpSurveyCell('has_filters', survey.has_filters), null, survey.has_filters),
      ]);

      // Приборы учёта
      const metSection = cmpSectionHtml('📊 Приборы учёта', [
        cmpRow('Производитель',     cmpParsedCell(null), cmpSurveyCell('manufacturer', survey.manufacturer), null, survey.manufacturer),
        cmpRow('Тип расходомера',   cmpParsedCell(null), cmpSurveyCell('flow_meter_type', survey.flow_meter_type), null, survey.flow_meter_type),
        cmpRow('Класс точности',    cmpParsedCell(met.heat_meter_class), cmpSurveyCell('accuracy_class', survey.accuracy_class), met.heat_meter_class, survey.accuracy_class),
        cmpRow('Место установки',   cmpParsedCell(met.meter_location), cmpSurveyCell('meter_location', survey.meter_location), met.meter_location, survey.meter_location),
      ]);

      // Дополнительно
      const extraSection = cmpSectionHtml('➕ Дополнительно (из опросного листа)', [
        cmpRow('Расстояние до ВРУ, м', cmpParsedCell(null), cmpSurveyCell('distance_to_vru', survey.distance_to_vru), null, survey.distance_to_vru),
        cmpRow('Требования РСО',       cmpParsedCell(null), cmpSurveyCell('rso_requirements', survey.rso_requirements), null, survey.rso_requirements),
        cmpRow('Комментарии',          cmpParsedCell(null), cmpSurveyCell('comments', survey.comments), null, survey.comments),
      ]);

      // Warnings
      let warningsHtml = '';
      if (params.warnings && params.warnings.length > 0) {
        warningsHtml = `<div class="warnings-list" style="margin-top:14px;">
          <div style="font-size:13px;font-weight:600;color:var(--c-warn);margin-bottom:6px;">Предупреждения парсинга:</div>
          ${params.warnings.map(w => `<div class="warning-item">${esc(w)}</div>`).join('')}
        </div>`;
      }

      content.innerHTML = `<details class="parsed-params-details">
        <summary>Данные ТУ и опросного листа &#9654;</summary>
        <div class="parsed-details-body">
          ${header}
          <p style="font-size:12px;color:var(--c-text-secondary);margin:0 0 10px;">
            🟡 Жёлтым выделены строки, где значения из ТУ и опросного листа расходятся.
          </p>
          ${docSection2col}
          ${objSection}
          ${heatSection}
          ${loadsSection}
          ${pipeSection}
          ${metSection}
          ${extraSection}
          ${warningsHtml}
        </div>
      </details>`;
    }

// ── Parsed params helpers и рендер ─────────────────────────────────────────
    function fmtParsedValueCell(raw, unitSuffix, formatValue) {
      if (raw === null || raw === undefined) {
        return '<td class="parsed-value-cell"><span class="parsed-null">\u2014</span></td>';
      }
      if (typeof raw === 'string' && raw.trim() === '') {
        return '<td class="parsed-value-cell"><span class="parsed-null">\u2014</span></td>';
      }
      const inner = formatValue ? formatValue(raw) : (typeof raw === 'number' ? fmtNum(raw) : esc(String(raw)));
      const suf = unitSuffix || '';
      return `<td class="parsed-value-cell"><span class="parsed-value">${inner}${suf}</span></td>`;
    }

    function fmtSystemTypeDisplay(raw) {
      return esc(String(raw).replace(/_/g, ' '));
    }

    function parsedTableRow(label, valueCellHtml) {
      return `<tr><td class="parsed-label-cell">${esc(label)}</td>${valueCellHtml}</tr>`;
    }

    function parsedSectionHtml(title, rows) {
      const body = rows.join('');
      return `
        <div class="parsed-section">
          <div class="parsed-section-title">${title}</div>
          <table class="parsed-params-table">
            <thead><tr><th>Поле</th><th>Значение</th></tr></thead>
            <tbody>${body}</tbody>
          </table>
        </div>`;
    }

    function hasNestedParsingShape(p) {
      if (!p || typeof p !== 'object') return false;
      return !!(p.heat_loads || p.coolant || p.pipeline || p.connection || p.metering
        || p.document || p.rso || p.object || p.applicant || p.additional);
    }

    function heatLoadsFromParams(p) {
      if (p.heat_loads && typeof p.heat_loads === 'object') return p.heat_loads;
      return {
        total_load: p.total_load,
        heating_load: p.heating_load ?? p.heat_load_ot,
        hot_water_load: p.hot_water_load ?? p.heat_load_gvs,
        ventilation_load: p.ventilation_load ?? p.heat_load_vent,
      };
    }

    function coolantFromParams(p) {
      if (p.coolant && typeof p.coolant === 'object') return p.coolant;
      return {
        supply_temp: p.supply_temp ?? p.t_supply,
        return_temp: p.return_temp ?? p.t_return,
        supply_pressure_kgcm2: p.supply_pressure_kgcm2 ?? p.p_supply,
        return_pressure_kgcm2: p.return_pressure_kgcm2 ?? p.p_return,
      };
    }

    function pipelineFromParams(p) {
      if (p.pipeline && typeof p.pipeline === 'object') return p.pipeline;
      const d = p.pipe_diameter_supply ?? p.pipe_diameter_return;
      return {
        pipe_outer_diameter_mm: p.pipe_outer_diameter_mm ?? d,
        pipe_wall_thickness_mm: p.pipe_wall_thickness_mm,
        pipe_inner_diameter_mm: p.pipe_inner_diameter_mm,
      };
    }

    function connectionFromParams(p) {
      if (p.connection && typeof p.connection === 'object') return p.connection;
      return {
        system_type: p.system_type,
        scheme: p.connection_scheme,
        connection_type: p.connection_type,
        heating_system: p.heating_system,
      };
    }

    function meteringFromParams(p) {
      if (p.metering && typeof p.metering === 'object') {
        const m = p.metering;
        return {
          ...m,
          data_interface: m.data_interface ?? m.communication_interface ?? p.communication_interface,
        };
      }
      return {
        heat_meter_class: p.heat_meter_class,
        data_interface: p.data_interface ?? p.communication_interface,
        meter_brand: p.meter_brand,
      };
    }

    function documentBlockSources(p) {
      const doc = (p.document && typeof p.document === 'object') ? p.document
        : (p.document_info && typeof p.document_info === 'object' ? p.document_info : {});
      const rso = (p.rso && typeof p.rso === 'object') ? p.rso : {};
      const obj = (p.object && typeof p.object === 'object') ? p.object : {};
      const rsoName = rso.rso_name ?? doc.rso_name;
      const validTo = doc.tu_valid_to ?? doc.validity_date;
      return { doc, rsoName, obj, validTo };
    }

    function connectionSchemeDisplay(conn) {
      const s = conn.scheme ?? conn.connection_type;
      const h = conn.heating_system;
      if (s != null && s !== '' && h != null && h !== '' && String(s) !== String(h)) {
        return esc(String(s)) + ' / ' + esc(String(h));
      }
      if (s != null && s !== '') return esc(String(s));
      if (h != null && h !== '') return esc(String(h));
      return null;
    }

    function buildParsedParamsTablesHtml(params) {
      const { doc, rsoName, obj, validTo } = documentBlockSources(params);
      const hl = heatLoadsFromParams(params);
      const cool = coolantFromParams(params);
      const pipe = pipelineFromParams(params);
      const conn = connectionFromParams(params);
      const met = meteringFromParams(params);

      const sections = [];

      sections.push(parsedSectionHtml('📄 \u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442', [
        parsedTableRow('\u0420\u0421\u041e', fmtParsedValueCell(rsoName, '')),
        parsedTableRow('\u041d\u043e\u043c\u0435\u0440 \u0422\u0423', fmtParsedValueCell(doc.tu_number, '')),
        parsedTableRow('\u0414\u0430\u0442\u0430 \u0422\u0423', fmtParsedValueCell(doc.tu_date, '')),
        parsedTableRow('\u0414\u0435\u0439\u0441\u0442\u0432\u0443\u0435\u0442 \u0434\u043e', fmtParsedValueCell(validTo, '')),
        parsedTableRow('\u0410\u0434\u0440\u0435\u0441 \u043e\u0431\u044a\u0435\u043a\u0442\u0430', fmtParsedValueCell(obj.object_address ?? doc.object_address, '')),
      ]));

      sections.push(parsedSectionHtml('🔥 \u0422\u0435\u043f\u043b\u043e\u0432\u044b\u0435 \u043d\u0430\u0433\u0440\u0443\u0437\u043a\u0438 (\u0413\u043a\u0430\u043b/\u0447)', [
        parsedTableRow('\u041e\u0431\u0449\u0430\u044f \u043d\u0430\u0433\u0440\u0443\u0437\u043a\u0430', fmtParsedValueCell(hl.total_load, ' \u0413\u043a\u0430\u043b/\u0447')),
        parsedTableRow('\u041e\u0442\u043e\u043f\u043b\u0435\u043d\u0438\u0435', fmtParsedValueCell(hl.heating_load, ' \u0413\u043a\u0430\u043b/\u0447')),
        parsedTableRow('\u0413\u0412\u0421', fmtParsedValueCell(hl.hot_water_load, ' \u0413\u043a\u0430\u043b/\u0447')),
        parsedTableRow('\u0412\u0435\u043d\u0442\u0438\u043b\u044f\u0446\u0438\u044f', fmtParsedValueCell(hl.ventilation_load, ' \u0413\u043a\u0430\u043b/\u0447')),
      ]));

      sections.push(parsedSectionHtml('🔥 \u0422\u0435\u043f\u043b\u043e\u043d\u043e\u0441\u0438\u0442\u0435\u043b\u044c', [
        parsedTableRow('\u0422\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430 \u043f\u043e\u0434\u0430\u0447\u0438', fmtParsedValueCell(cool.supply_temp, ' \u00b0C')),
        parsedTableRow('\u0422\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430 \u043e\u0431\u0440\u0430\u0442\u043a\u0438', fmtParsedValueCell(cool.return_temp, ' \u00b0C')),
        parsedTableRow('\u0414\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043f\u043e\u0434\u0430\u0447\u0438', fmtParsedValueCell(cool.supply_pressure_kgcm2, ' \u043a\u0433\u0441/\u0441\u043c\u00b2')),
        parsedTableRow('\u0414\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043e\u0431\u0440\u0430\u0442\u043a\u0438', fmtParsedValueCell(cool.return_pressure_kgcm2, ' \u043a\u0433\u0441/\u0441\u043c\u00b2')),
      ]));

      const wallMm = pipe.pipe_wall_thickness_mm;
      const innerMm = pipe.pipe_inner_diameter_mm;
      sections.push(parsedSectionHtml('🔧 \u0422\u0440\u0443\u0431\u043e\u043f\u0440\u043e\u0432\u043e\u0434', [
        parsedTableRow('\u041d\u0430\u0440\u0443\u0436\u043d\u044b\u0439 \u0434\u0438\u0430\u043c\u0435\u0442\u0440', fmtParsedValueCell(pipe.pipe_outer_diameter_mm, ' \u043c\u043c')),
        parsedTableRow('\u0422\u043e\u043b\u0449\u0438\u043d\u0430 \u0441\u0442\u0435\u043d\u043a\u0438', fmtParsedValueCell(wallMm, ' \u043c\u043c')),
        parsedTableRow('\u0412\u043d\u0443\u0442\u0440\u0435\u043d\u043d\u0438\u0439 \u0434\u0438\u0430\u043c\u0435\u0442\u0440', fmtParsedValueCell(innerMm, ' \u043c\u043c')),
      ]));

      const schemeStr = connectionSchemeDisplay(conn);
      sections.push(parsedSectionHtml('\u26a1 \u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435', [
        parsedTableRow('\u0422\u0438\u043f \u0441\u0438\u0441\u0442\u0435\u043c\u044b', fmtParsedValueCell(conn.system_type, '', fmtSystemTypeDisplay)),
        parsedTableRow('\u0421\u0445\u0435\u043c\u0430 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f', schemeStr === null
          ? '<td class="parsed-value-cell"><span class="parsed-null">\u2014</span></td>'
          : `<td class="parsed-value-cell"><span class="parsed-value">${schemeStr}</span></td>`),
      ]));

      const iface = met.data_interface ?? met.communication_interface;
      sections.push(parsedSectionHtml('📊 \u0423\u0447\u0451\u0442', [
        parsedTableRow('\u041a\u043b\u0430\u0441\u0441 \u0442\u0435\u043f\u043b\u043e\u0441\u0447\u0451\u0442\u0447\u0438\u043a\u0430', fmtParsedValueCell(met.heat_meter_class, '')),
        parsedTableRow('\u0418\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441', fmtParsedValueCell(iface, '')),
      ]));

      const legacyKeys = [
        ['heat_load_gvs', '\u041d\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0413\u0412\u0421 (legacy), \u0413\u043a\u0430\u043b/\u0447'],
        ['heat_load_ot', '\u041d\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u041e\u0422 (legacy), \u0413\u043a\u0430\u043b/\u0447'],
        ['heat_load_vent', '\u041d\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0432\u0435\u043d\u0442. (legacy), \u0413\u043a\u0430\u043b/\u0447'],
        ['t_supply', 'T \u043f\u043e\u0434\u0430\u0447\u0438 (legacy), \u00b0C'],
        ['t_return', 'T \u043e\u0431\u0440\u0430\u0442\u043a\u0438 (legacy), \u00b0C'],
        ['p_supply', 'P \u043f\u043e\u0434\u0430\u0447\u0438 (legacy)'],
        ['p_return', 'P \u043e\u0431\u0440\u0430\u0442\u043a\u0438 (legacy)'],
        ['pipe_diameter_supply', '\u0414\u0438\u0430\u043c. \u043f\u043e\u0434\u0430\u0447\u0438 (legacy), \u043c\u043c'],
        ['pipe_diameter_return', '\u0414\u0438\u0430\u043c. \u043e\u0431\u0440\u0430\u0442\u043a\u0438 (legacy), \u043c\u043c'],
        ['connection_scheme', '\u0421\u0445\u0435\u043c\u0430 \u043f\u0440\u0438\u0441\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u044f (legacy)'],
        ['meter_brand', '\u041c\u0430\u0440\u043a\u0430 \u043f\u0440\u0438\u0431\u043e\u0440\u0430 (legacy)'],
        ['circuits_count', '\u041a\u043e\u043d\u0442\u0443\u0440\u043e\u0432 \u0443\u0447\u0451\u0442\u0430 (legacy)'],
      ];
      const legacyRows = legacyKeys
        .filter(([k]) => params[k] !== undefined && params[k] !== null && params[k] !== '')
        .map(([k, label]) => parsedTableRow(label, fmtParsedValueCell(params[k], '')));
      if (!hasNestedParsingShape(params) && legacyRows.length > 0) {
        sections.push(parsedSectionHtml('📎 \u0423\u0441\u0442\u0430\u0440\u0435\u0432\u0448\u0438\u0439 \u0444\u043e\u0440\u043c\u0430\u0442 (\u043f\u043b\u043e\u0441\u043a\u0438\u0435 \u043f\u043e\u043b\u044f)', legacyRows));
      }

      return `
        <details class="parsed-params-details">
          <summary>\u0418\u0437\u0432\u043b\u0435\u0447\u0451\u043d\u043d\u044b\u0435 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b \u25b6</summary>
          <div class="parsed-details-body">${sections.join('')}</div>
        </details>`;
    }

    function renderParsedParams(params, missing) {
      const card = document.getElementById('parsedCard');
      const content = document.getElementById('parsedContent');
      card.style.display = 'block';

      const empty = isParsedParamsEmpty(params);
      const warnings = (!empty && params.warnings) ? params.warnings : [];
      const confidence = !empty ? params.parse_confidence : undefined;

      let html = '';

      if (confidence !== undefined && confidence !== null) {
        const pct = Math.round(Number(confidence) * 100);
        const color = pct >= 80 ? '#16a34a' : pct >= 60 ? '#d97706' : '#dc2626';
        html += `
          <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
            <span style="font-size:13px; color:var(--c-text-secondary);">\u0423\u0432\u0435\u0440\u0435\u043d\u043d\u043e\u0441\u0442\u044c \u043f\u0430\u0440\u0441\u0438\u043d\u0433\u0430:</span>
            <span style="font-size:18px; font-weight:700; color:${color};">${pct}%</span>
          </div>
        `;
      }

      if (empty) {
        html += '<p class="parsed-empty-msg">\u041f\u0430\u0440\u0441\u0438\u043d\u0433 \u043d\u0435 \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d</p>';
      } else {
        html += buildParsedParamsTablesHtml(params);
      }

      if (missing && missing.length > 0) {
        html += `
          <div style="margin-top:14px;">
            <div style="font-size:13px; font-weight:600; color:var(--c-warn); margin-bottom:8px;">
              \u041d\u0435\u0434\u043e\u0441\u0442\u0430\u044e\u0449\u0438\u0435 \u0434\u0430\u043d\u043d\u044b\u0435 (${missing.length}):
            </div>
            <div style="font-size:13px; color:var(--c-text-secondary);">${missing.map(esc).join(', ')}</div>
          </div>
        `;
      }

      if (warnings.length > 0) {
        html += `
          <div class="warnings-list" style="margin-top:14px;">
            <div style="font-size:13px; font-weight:600; color:var(--c-warn); margin-bottom:6px;">\u041f\u0440\u0435\u0434\u0443\u043f\u0440\u0435\u0436\u0434\u0435\u043d\u0438\u044f:</div>
            ${warnings.map(w => `<div class="warning-item">${esc(w)}</div>`).join('')}
          </div>
        `;
      }

      content.innerHTML = html;
    }
