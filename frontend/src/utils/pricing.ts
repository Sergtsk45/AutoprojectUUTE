/**
 * @file: src/utils/pricing.ts
 * @description: Чистые функции расчёта стоимости проекта УУТЭ в лендинге.
 *   Источник правды для калькулятора в `CalculatorSection.tsx` и для default-значений
 *   в `EmailModal.tsx`. Изменение тарифов — только здесь.
 * @dependencies: использует `Intl.NumberFormat`, React-логики нет.
 * @created: 2026-04-21
 */

/** Число контуров, по которым предусмотрен тариф в калькуляторе. */
export type Circuits = 1 | 2 | 3;

/**
 * Цены тарифа «Индивидуальный» по количеству контуров, ₽.
 * Меняем здесь — синхронно обновится и калькулятор, и letter к заявке.
 */
export const INDIVIDUAL_PRICES: Record<Circuits, number> = {
  1: 22500,
  2: 35000,
  3: 50000,
} as const;

/** Тариф «Экспресс» / ЭСКО — доступен только для 1 контура, ₽. */
export const EXPRESS_PRICE = 11250;

/** Дефолт при некорректном `circuits` (консервативный минимум). */
const FALLBACK_PRICE = INDIVIDUAL_PRICES[1];

/**
 * Стоимость «Индивидуального» тарифа.
 * При неизвестном числе контуров возвращает цену за 1 контур (безопасный дефолт).
 */
export function calcIndividualPrice(circuits: number): number {
  if (circuits in INDIVIDUAL_PRICES) {
    return INDIVIDUAL_PRICES[circuits as Circuits];
  }
  return FALLBACK_PRICE;
}

/**
 * Итоговая цена «Экспресс»: для 1 контура — фикс, для остальных — как «Индивидуальный»
 * (тариф Экспресс недоступен, но функция возвращает что-то осмысленное).
 */
export function calcExpressPrice(circuits: number): number {
  return circuits === 1 ? EXPRESS_PRICE : calcIndividualPrice(circuits);
}

/** Формат цены для UI: «22 500» (неразрывный пробел как разделитель тысяч в ru-RU). */
export function formatPrice(price: number): string {
  return new Intl.NumberFormat('ru-RU').format(price);
}
