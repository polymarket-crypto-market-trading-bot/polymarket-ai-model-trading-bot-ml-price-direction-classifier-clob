import type { StrategyContext, TradeSignal } from '../types/index.js';
import type { AppConfig } from '../config/index.js';
import { calculateNotional } from '../utils/decimal.js';

export interface Strategy {
  readonly name: string;
  evaluate(context: StrategyContext): TradeSignal | null;
}

export class WhaleMirrorStrategy implements Strategy {
  readonly name = 'whale_mirror';

  constructor(private readonly config: AppConfig) {}

  evaluate(context: StrategyContext): TradeSignal | null {
    const largeTrades = context.recentTrades.filter((trade) => {
      const notional = calculateNotional(trade.price, trade.size);
      return notional >= this.config.WHALE_MIN_TRADE_USDT;
    });

    if (largeTrades.length === 0) return null;

    const latest = largeTrades[largeTrades.length - 1]!;
    const notional = calculateNotional(latest.price, latest.size);

    return {
      id: `mirror-${context.symbol}-${latest.sequence}`,
      symbol: context.symbol,
      side: latest.side,
      price: latest.price,
      size: latest.size,
      notionalUsdt: notional,
      source: 'whale_trade',
      timestamp: latest.time,
      confidence: 0.75,
    };
  }
}

export class OrderBookImbalanceStrategy implements Strategy {
  readonly name = 'orderbook_imbalance';

  constructor(private readonly config: AppConfig) {}

  evaluate(context: StrategyContext): TradeSignal | null {
    if (!context.orderBook) return null;

    const bidVolume = context.orderBook.bids
      .slice(0, 10)
      .reduce((sum, l) => sum + calculateNotional(l.price, l.size), 0);

    const askVolume = context.orderBook.asks
      .slice(0, 10)
      .reduce((sum, l) => sum + calculateNotional(l.price, l.size), 0);

    const imbalance = Math.abs(bidVolume - askVolume);
    if (imbalance < this.config.WHALE_ORDERBOOK_WALL_USDT) return null;

    const side = bidVolume > askVolume ? ('buy' as const) : ('sell' as const);
    const dominantVolume = Math.max(bidVolume, askVolume);

    return {
      id: `imbalance-${context.symbol}-${Date.now()}`,
      symbol: context.symbol,
      side,
      price: context.ticker?.last ?? 0,
      size: 0,
      notionalUsdt: dominantVolume,
      source: 'orderbook_wall',
      timestamp: Date.now(),
      confidence: Math.min(0.9, 0.6 + imbalance / this.config.WHALE_ORDERBOOK_WALL_USDT * 0.1),
    };
  }
}

export class StrategyRegistry {
  private readonly strategies: Strategy[] = [];

  register(strategy: Strategy): this {
    this.strategies.push(strategy);
    return this;
  }

  evaluateAll(context: StrategyContext): TradeSignal[] {
    return this.strategies
      .map((s) => s.evaluate(context))
      .filter((signal): signal is TradeSignal => signal !== null);
  }
}

export function createDefaultStrategies(config: AppConfig): StrategyRegistry {
  return new StrategyRegistry()
    .register(new WhaleMirrorStrategy(config))
    .register(new OrderBookImbalanceStrategy(config));
}
