/**
 * @file: src/utils/pricing.test.ts
 * @description: Unit-тесты на расчёт цены тарифов (чистые функции).
 * @dependencies: vitest.
 * @created: 2026-04-21
 */

import { describe, it, expect } from 'vitest';
import {
  EXPRESS_PRICE,
  INDIVIDUAL_PRICES,
  calcExpressPrice,
  calcIndividualPrice,
  formatPrice,
} from './pricing';

describe('calcIndividualPrice', () => {
  it('возвращает корректную цену для 1/2/3 контуров', () => {
    expect(calcIndividualPrice(1)).toBe(22500);
    expect(calcIndividualPrice(2)).toBe(35000);
    expect(calcIndividualPrice(3)).toBe(50000);
  });

  it('для неизвестного числа контуров отдаёт цену за 1 контур', () => {
    expect(calcIndividualPrice(0)).toBe(INDIVIDUAL_PRICES[1]);
    expect(calcIndividualPrice(4)).toBe(INDIVIDUAL_PRICES[1]);
    expect(calcIndividualPrice(-1)).toBe(INDIVIDUAL_PRICES[1]);
  });
});

describe('calcExpressPrice', () => {
  it('для 1 контура — фикс EXPRESS_PRICE', () => {
    expect(calcExpressPrice(1)).toBe(EXPRESS_PRICE);
    expect(EXPRESS_PRICE).toBe(11250);
  });

  it('для >1 контура отдаёт цену «Индивидуального»', () => {
    expect(calcExpressPrice(2)).toBe(INDIVIDUAL_PRICES[2]);
    expect(calcExpressPrice(3)).toBe(INDIVIDUAL_PRICES[3]);
  });
});

describe('formatPrice', () => {
  it('форматирует число по ru-RU с разделителем тысяч', () => {
    // Intl.NumberFormat('ru-RU') использует неразрывный пробел (U+00A0).
    expect(formatPrice(22500)).toMatch(/^22.500$/);
    expect(formatPrice(1000000)).toMatch(/^1.000.000$/);
    expect(formatPrice(0)).toBe('0');
  });
});
