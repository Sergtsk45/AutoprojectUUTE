/**
 * @file: backend/static/js/admin/config.js
 * @description: Константы и глобальное состояние админки (статусы, цвета, опросник).
 *   Фаза E3 (минимальный вариант) — вынос из inline <script> в admin.html.
 *   Подключается как обычный <script> (не ES-модуль) — все идентификаторы
 *   доступны глобально для admin.js / views-*.js / onclick-хендлеров в HTML.
 *   Порядок подключения: config.js → utils.js → views-parsed.js →
 *   views-calc.js → admin.js.
 * @created: 2026-04-22 (E3)
 */

// ── Config & State ──────────────────────────────────────────────────────────
const API_BASE = window.location.origin + '/api/v1';
let currentOrderId = null;
let refreshTimer = null;

const ORDER_ID_URL_RE =
  /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/;

// ── Status helpers ──────────────────────────────────────────────────────────
const STATUS_LABELS = {
  new: 'Новая',
  tu_parsing: 'Парсинг ТУ',
  tu_parsed: 'ТУ распарсены',
  waiting_client_info: 'Ожидание клиента',
  client_info_received: 'Ответ получен',
  data_complete: 'Данные собраны',
  generating_project: 'Генерация проекта',
  review: 'На проверке',
  awaiting_contract: 'Ожидание реквизитов',
  contract_sent: 'Договор отправлен',
  advance_paid: 'Аванс получен',
  awaiting_final_payment: 'Ожидание остатка',
  rso_remarks_received: 'Замечания РСО',
  completed: 'Завершена',
  error: 'Ошибка',
};

const STATUS_COLORS = {
  new: '#9e9e9e',
  tu_parsing: '#2196f3',
  tu_parsed: '#1976d2',
  waiting_client_info: '#ff9800',
  client_info_received: '#f57c00',
  data_complete: '#66bb6a',
  generating_project: '#7e57c2',
  review: '#f9a825',
  awaiting_contract: '#ff9800',
  contract_sent: '#f57c00',
  advance_paid: '#66bb6a',
  awaiting_final_payment: '#42a5f5',
  rso_remarks_received: '#2563eb',
  completed: '#4caf50',
  error: '#f44336',
};

const STATUS_ORDER = [
  'new', 'tu_parsing', 'tu_parsed', 'waiting_client_info',
  'client_info_received', 'contract_sent', 'advance_paid', 'awaiting_final_payment',
  'rso_remarks_received',
  'completed',
];

const POST_PARSE_STATUSES = new Set([
  'tu_parsed', 'waiting_client_info', 'client_info_received',
  'data_complete', 'generating_project', 'review', 'completed',
  'awaiting_contract', 'contract_sent', 'advance_paid', 'awaiting_final_payment',
  'rso_remarks_received',
]);

// Parsing poll state
let parsingPollTimer = null;
let parsingPollCount = 0;
let parsingPollBusy = false;

// Waiting-for-email poll state (обновляем карточку пока авто-письмо ещё не ушло)
let waitingEmailPollTimer = null;

// Sending-project poll state (ждём смены статуса advance_paid → completed после отправки проекта)
let sendingProjectPollTimer = null;

// ── Survey (опросник для custom-заказов) ────────────────────────────────────
const SURVEY_LABELS = {
  building_type: 'Тип здания',
  floors: 'Этажность',
  construction_year: 'Год постройки',
  heat_supply_source: 'Источник теплоснабжения',
  connection_type: 'Схема подключения',
  system_type: 'Тип системы',
  temp_schedule: 'Температурный график',
  supply_temp: 'Температура подачи, °C',
  return_temp: 'Температура обратки, °C',
  pressure_supply: 'Давление подачи, кгс/см²',
  pressure_return: 'Давление обратки, кгс/см²',
  heat_load_total: 'Нагрузка суммарная, Гкал/ч',
  heat_load_heating: 'Нагрузка отопления, Гкал/ч',
  heat_load_hw: 'Нагрузка ГВС, Гкал/ч',
  heat_load_vent: 'Нагрузка вентиляции, Гкал/ч',
  heat_load_tech: 'Нагрузка технология, Гкал/ч',
  pipe_dn_supply: 'Ду подачи, мм',
  pipe_dn_return: 'Ду обратки, мм',
  has_mud_separators: 'Грязевики',
  has_filters: 'Фильтры',
  manufacturer: 'Производитель',
  manufacturer_other: 'Производитель (другой)',
  flow_meter_type: 'Тип расходомера',
  accuracy_class: 'Класс точности',
  meter_location: 'Место установки узла учёта',
  distance_to_vru: 'Расстояние до ВРУ или щита собственных нужд ТП, м',
  rso_requirements: 'Требования РСО',
  comments: 'Комментарии',
};

/** Перевод enum-значений опросника на русский для отображения инженеру. */
const SURVEY_VALUE_MAP = {
  building_type: { residential: 'Жилое', public: 'Общественное', industrial: 'Промышленное' },
  system_type: { open: 'Открытая', closed: 'Закрытая' },
  connection_type: { dependent: 'Зависимая', independent: 'Независимая' },
  manufacturer: { esko: 'Эско 3Э', teplokom: 'Теплоком', logika: 'Логика (СПТ)', pulsar: 'Пульсар', other: 'Другой' },
  flow_meter_type: { ultrasonic: 'Ультразвуковой', electromagnetic: 'Электромагнитный' },
  has_mud_separators: { yes: 'Да', no: 'Нет' },
  has_filters: { yes: 'Да', no: 'Нет' },
};

const SURVEY_SECTIONS = [
  {
    title: '🏢 Объект',
    keys: ['building_type', 'floors', 'construction_year', 'heat_supply_source'],
  },
  {
    title: '⚡ Теплоснабжение',
    keys: ['connection_type', 'system_type', 'temp_schedule', 'supply_temp', 'return_temp', 'pressure_supply', 'pressure_return'],
  },
  {
    title: '🔥 Тепловые нагрузки, Гкал/ч',
    keys: ['heat_load_total', 'heat_load_heating', 'heat_load_hw', 'heat_load_vent', 'heat_load_tech'],
  },
  {
    title: '🔧 Трубопроводы',
    keys: ['pipe_dn_supply', 'pipe_dn_return', 'has_mud_separators', 'has_filters'],
  },
  {
    title: '📊 Приборы учёта',
    keys: ['manufacturer', 'manufacturer_other', 'flow_meter_type', 'accuracy_class', 'meter_location'],
  },
  {
    title: '➕ Дополнительно',
    keys: ['distance_to_vru', 'rso_requirements', 'comments'],
  },
];
