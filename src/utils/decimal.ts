import { Decimal } from 'decimal.js';

Decimal.set({ precision: 20, rounding: Decimal.ROUND_DOWN });

export function toDecimal(value: number | string): InstanceType<typeof Decimal> {
  return new Decimal(value);
}

export function multiply(a: number, b: number): number {
  return toDecimal(a).mul(b).toNumber();
}

export function divide(a: number, b: number): number {
  if (b === 0) return 0;
  return toDecimal(a).div(b).toNumber();
}

export function roundSize(size: number, precision = 8): number {
  return toDecimal(size).toDecimalPlaces(precision, Decimal.ROUND_DOWN).toNumber();
}

export function roundPrice(price: number, precision = 8): number {
  return toDecimal(price).toDecimalPlaces(precision, Decimal.ROUND_HALF_UP).toNumber();
}

export function calculateNotional(price: number, size: number): number {
  return multiply(price, size);
}

export function calculateSlippagePercent(expected: number, actual: number): number {
  if (expected === 0) return 0;
  return Math.abs(divide(actual - expected, expected)) * 100;
}

export function applyPercent(value: number, percent: number): number {
  return multiply(value, divide(percent, 100));
}

export function percentChange(from: number, to: number): number {
  if (from === 0) return 0;
  return multiply(divide(to - from, from), 100);
}
