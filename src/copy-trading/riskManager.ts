import type { AppConfig } from '../config/index.js';
import type { Position, RiskCheckResult, TradeSignal } from '../types/index.js';
import { todayDateString, clamp } from '../utils/index.js';
import { multiply } from '../utils/decimal.js';

export class RiskManager {
  private readonly openPositions = new Map<string, Position>();
  private dailyTradeCount = 0;
  private dailyDate = todayDateString();

  constructor(private readonly config: AppConfig) {}

  validateSignal(
    signal: TradeSignal,
    accountBalanceUsdt: number,
  ): RiskCheckResult {
    this.resetDailyCounterIfNeeded();

    if (signal.confidence < 0.5) {
      return { allowed: false, reason: 'Signal confidence too low' };
    }

    if (this.dailyTradeCount >= this.config.MAX_DAILY_TRADES) {
      return { allowed: false, reason: 'Daily trade limit reached' };
    }

    if (this.openPositions.size >= this.config.MAX_OPEN_POSITIONS) {
      return { allowed: false, reason: 'Maximum open positions reached' };
    }

    if (accountBalanceUsdt < this.config.MIN_ACCOUNT_BALANCE_USDT) {
      return {
        allowed: false,
        reason: `Insufficient balance (min ${this.config.MIN_ACCOUNT_BALANCE_USDT} USDT)`,
      };
    }

    const existingPosition = this.openPositions.get(signal.symbol);
    if (existingPosition && existingPosition.side !== signal.side) {
      return {
        allowed: false,
        reason: 'Conflicting open position on same symbol',
      };
    }

    return { allowed: true };
  }

  calculateCopySize(
    signal: TradeSignal,
    accountBalanceUsdt: number,
  ): { size: number; notionalUsdt: number } {
    const whaleNotional = signal.notionalUsdt;
    const copyNotional = clamp(
      multiply(whaleNotional, this.config.COPY_RATIO),
      10,
      Math.min(this.config.MAX_POSITION_USDT, accountBalanceUsdt * 0.25),
    );

    const size =
      signal.price > 0 ? copyNotional / signal.price : copyNotional / 1;

    return {
      size,
      notionalUsdt: copyNotional,
    };
  }

  recordPosition(position: Position): void {
    this.openPositions.set(position.symbol, position);
    this.dailyTradeCount++;
  }

  closePosition(symbol: string): void {
    this.openPositions.delete(symbol);
  }

  getOpenPositions(): Position[] {
    return Array.from(this.openPositions.values());
  }

  getDailyTradeCount(): number {
    this.resetDailyCounterIfNeeded();
    return this.dailyTradeCount;
  }

  shouldStopLoss(position: Position, currentPrice: number): boolean {
    if (position.side === 'buy') {
      const lossPercent =
        ((position.entryPrice - currentPrice) / position.entryPrice) * 100;
      return lossPercent >= this.config.STOP_LOSS_PERCENT;
    }

    const lossPercent =
      ((currentPrice - position.entryPrice) / position.entryPrice) * 100;
    return lossPercent >= this.config.STOP_LOSS_PERCENT;
  }

  shouldTakeProfit(position: Position, currentPrice: number): boolean {
    if (position.side === 'buy') {
      const profitPercent =
        ((currentPrice - position.entryPrice) / position.entryPrice) * 100;
      return profitPercent >= this.config.TAKE_PROFIT_PERCENT;
    }

    const profitPercent =
      ((position.entryPrice - currentPrice) / position.entryPrice) * 100;
    return profitPercent >= this.config.TAKE_PROFIT_PERCENT;
  }

  private resetDailyCounterIfNeeded(): void {
    const today = todayDateString();
    if (today !== this.dailyDate) {
      this.dailyDate = today;
      this.dailyTradeCount = 0;
    }
  }
}
