import type { AppConfig } from '../config/index.js';
import type { OrderBookSnapshot, Side, TradeSignal, WhaleEvent } from '../types/index.js';
import { calculateNotional } from '../utils/decimal.js';

export class WhaleDetector {
  private readonly lastSignalBySymbol = new Map<string, number>();
  private readonly recentWhaleSides = new Map<string, Side[]>();

  constructor(private readonly config: AppConfig) {}

  detectWhaleTrade(event: WhaleEvent): TradeSignal | null {
    if (event.notionalUsdt < this.config.WHALE_MIN_TRADE_USDT) {
      return null;
    }

    if (!this.canEmitSignal(event.symbol)) {
      return null;
    }

    this.recordSignal(event.symbol, event.side);

    const confidence = this.calculateTradeConfidence(event);

    return {
      id: `whale-trade-${event.tradeId}`,
      symbol: event.symbol,
      side: event.side,
      price: event.price,
      size: event.size,
      notionalUsdt: event.notionalUsdt,
      source: 'whale_trade',
      timestamp: event.timestamp,
      confidence,
    };
  }

  detectOrderBookWall(orderBook: OrderBookSnapshot): TradeSignal | null {
    const { symbol } = orderBook;
    const threshold = this.config.WHALE_ORDERBOOK_WALL_USDT;

    const largestBid = this.findLargestWall(orderBook.bids);
    const largestAsk = this.findLargestWall(orderBook.asks);

    const bidNotional = largestBid
      ? calculateNotional(largestBid.price, largestBid.size)
      : 0;
    const askNotional = largestAsk
      ? calculateNotional(largestAsk.price, largestAsk.size)
      : 0;

    if (bidNotional < threshold && askNotional < threshold) {
      return null;
    }

    if (!this.canEmitSignal(symbol)) {
      return null;
    }

    const isBidWall = bidNotional >= askNotional;
    const wall = isBidWall ? largestBid! : largestAsk!;
    const notional = isBidWall ? bidNotional : askNotional;
    const side: Side = isBidWall ? 'buy' : 'sell';

    this.recordSignal(symbol, side);

    return {
      id: `whale-wall-${symbol}-${Date.now()}`,
      symbol,
      side,
      price: wall.price,
      size: wall.size,
      notionalUsdt: notional,
      source: 'orderbook_wall',
      timestamp: orderBook.timestamp,
      confidence: Math.min(0.95, 0.6 + (notional / threshold) * 0.1),
    };
  }

  detectVolumeSpike(
    symbol: string,
    recentTrades: Array<{ notionalUsdt: number; side: Side; timestamp: number }>,
    windowMs = 60_000,
  ): TradeSignal | null {
    const now = Date.now();
    const windowTrades = recentTrades.filter((t) => now - t.timestamp <= windowMs);

    if (windowTrades.length < 3) return null;

    const totalVolume = windowTrades.reduce((sum, t) => sum + t.notionalUsdt, 0);
    const avgTradeSize = totalVolume / windowTrades.length;
    const spikeThreshold = this.config.WHALE_MIN_TRADE_USDT * 0.5;

    if (avgTradeSize < spikeThreshold || totalVolume < this.config.WHALE_MIN_TRADE_USDT) {
      return null;
    }

    if (!this.canEmitSignal(symbol)) return null;

    const buyVolume = windowTrades
      .filter((t) => t.side === 'buy')
      .reduce((sum, t) => sum + t.notionalUsdt, 0);
    const sellVolume = totalVolume - buyVolume;
    const side: Side = buyVolume >= sellVolume ? 'buy' : 'sell';

    this.recordSignal(symbol, side);

    return {
      id: `volume-spike-${symbol}-${now}`,
      symbol,
      side,
      price: 0,
      size: 0,
      notionalUsdt: totalVolume,
      source: 'volume_spike',
      timestamp: now,
      confidence: Math.min(0.85, 0.5 + (totalVolume / this.config.WHALE_MIN_TRADE_USDT) * 0.15),
    };
  }

  private findLargestWall(
    levels: Array<{ price: number; size: number }>,
  ): { price: number; size: number } | null {
    if (levels.length === 0) return null;

    return levels.reduce((max, level) => {
      const notional = calculateNotional(level.price, level.size);
      const maxNotional = calculateNotional(max.price, max.size);
      return notional > maxNotional ? level : max;
    });
  }

  private canEmitSignal(symbol: string): boolean {
    const lastSignal = this.lastSignalBySymbol.get(symbol) ?? 0;
    return Date.now() - lastSignal >= this.config.WHALE_COOLDOWN_MS;
  }

  private recordSignal(symbol: string, side: Side): void {
    this.lastSignalBySymbol.set(symbol, Date.now());

    const sides = this.recentWhaleSides.get(symbol) ?? [];
    sides.push(side);
    if (sides.length > 10) sides.shift();
    this.recentWhaleSides.set(symbol, sides);
  }

  private calculateTradeConfidence(event: WhaleEvent): number {
    const ratio = event.notionalUsdt / this.config.WHALE_MIN_TRADE_USDT;
    const baseConfidence = Math.min(0.99, 0.55 + Math.log10(ratio + 1) * 0.15);

    const recentSides = this.recentWhaleSides.get(event.symbol) ?? [];
    const sameSideCount = recentSides.filter((s) => s === event.side).length;
    const momentumBonus = sameSideCount >= 2 ? 0.05 : 0;

    return Math.min(0.99, baseConfidence + momentumBonus);
  }

  resetCooldown(symbol: string): void {
    this.lastSignalBySymbol.delete(symbol);
  }
}
