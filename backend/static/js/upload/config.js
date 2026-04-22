/**
 * @file: config.js
 * @description: Конфигурация и глобальное состояние страницы /upload/<id>.
 *   Экспортирует через глобальный scope: API_BASE, ORDER_ID, PARAM_LABELS,
 *   POST_PARSE_STATUSES, CUSTOM_EDITABLE_STATUSES, PARAM_TO_SURVEY,
 *   SURVEY_REQUIRED_FIELDS и mutable state (orderData, isNewOrder,
 *   surveySavedCustom, uploadedCategories, parsingPoll*).
 * @dependencies: нет (подключается первым)
 * @created: 2026-04-22
 */

// ── Config ──────────────────────────────────────────────────────────
    const API_BASE = window.location.origin + '/api/v1';

    // Extract order ID from URL: /upload/<uuid>
    const pathParts = window.location.pathname.split('/');
    const ORDER_ID = pathParts[pathParts.length - 1] || pathParts[pathParts.length - 2];

    // Подписи для кодов из order.missing_params (дублируют backend param_labels.py)
    const PARAM_LABELS = {
      tu: { label: 'Технические условия', hint: 'Документ от теплоснабжающей организации' },
      company_card: { label: 'Карточка организации', hint: 'Реквизиты для подготовки договора и счёта' },
      balance_act: { label: 'Акт разграничения балансовой принадлежности', hint: 'Для действующих объектов' },
      connection_plan: { label: 'План подключения потребителя к тепловой сети', hint: 'С указанием точек подключения' },
      heat_point_plan: { label: 'План теплового пункта с указанием мест установки узла учёта и ШУ', hint: '' },
      heat_scheme: { label: 'Принципиальная схема теплового пункта с узлом учёта', hint: '' },
      pipe_diameters: { label: 'Диаметры трубопроводов на вводе', hint: '' },
      heat_load_details: { label: 'Детализация тепловых нагрузок', hint: '' },
      coolant_params: { label: 'Параметры теплоносителя', hint: '' },
      meter_location_photo: { label: 'Фото места установки узла учёта', hint: '' },
    };

    // ── State ───────────────────────────────────────────────────────────
    let orderData = null;
    let isNewOrder = false;
    const uploadedCategories = new Set();
    /** Custom после парсинга ТУ: «Всё загружено» только после сохранения опроса и чеклиста. */
    let surveySavedCustom = false;

    /** Статусы после успешного парсинга ТУ (ожидание можно завершить). */
    const POST_PARSE_STATUSES = new Set([
      'tu_parsed', 'waiting_client_info', 'client_info_received',
      'data_complete', 'generating_project', 'review', 'contract_sent',
      'advance_paid', 'awaiting_final_payment', 'completed',
    ]);

    /** Custom: опросник редактируемый, возможна догрузка документов. */
    const CUSTOM_EDITABLE_STATUSES = [
      'tu_parsed', 'waiting_client_info', 'client_info_received',
      'data_complete', 'generating_project',
    ];

    let parsingPollTimer = null;
    let parsingPollCount = 0;

// ── PARAM_TO_SURVEY mapping (parsed TU → survey field id) ──────────
    const PARAM_TO_SURVEY = {
      'heat_loads.total_load': 'heat_load_total',
      'heat_loads.heating_load': 'heat_load_heating',
      'heat_loads.hot_water_load': 'heat_load_hw',
      'heat_loads.ventilation_load': 'heat_load_vent',
      'coolant.supply_temp': 'supply_temp',
      'coolant.return_temp': 'return_temp',
      'coolant.supply_pressure_kgcm2': 'pressure_supply',
      'coolant.return_pressure_kgcm2': 'pressure_return',
      'connection.connection_type': 'connection_type',
      'connection.system_type': 'system_type',
      'pipeline.pipe_outer_diameter_mm': 'pipe_dn_supply',
      'metering.heat_meter_class': 'accuracy_class',
      'metering.meter_location': 'meter_location',
      'object.object_type': 'building_type',
      'rso.rso_name': 'heat_supply_source',
      'object.city': 'city',
    };

// ── Обязательные поля опросного листа ──────────────────────────────
    const SURVEY_REQUIRED_FIELDS = [
      ['s_building_type',       'str'],
      ['s_heat_supply_source',  'str'],
      ['s_city',                'str'],
      ['s_connection_type',     'str'],
      ['s_system_type',         'str'],
      ['s_supply_temp',         'num'],
      ['s_return_temp',         'num'],
      ['s_pressure_supply',     'num'],
      ['s_pressure_return',     'num'],
      ['s_heat_load_total',     'num'],
      ['s_heat_load_heating',   'num'],
      ['s_pipe_dn_supply',      'num'],
      ['s_pipe_dn_return',      'num'],
      ['s_has_mud_separators',  'str'],
      ['s_has_filters',         'str'],
      ['s_manufacturer',        'str'],
      ['s_flow_meter_type',     'str'],
      ['s_distance_to_vru',     'num'],
    ];
