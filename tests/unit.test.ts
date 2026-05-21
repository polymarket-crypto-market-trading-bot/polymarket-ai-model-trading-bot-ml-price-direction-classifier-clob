import { describe, it, expect, beforeEach } from 'vitest';
import { loadConfig } from '../src/config/index.js';
import { WhaleDetector } from '../src/whale/detector.js';
import { RiskManager } from '../src/copy-trading/riskManager.js';
import {
  calculateNotional,
  calculateSlippagePercent,
  multiply,
  roundSize,
} from '../src/utils/decimal.js';
import { createDefaultStrategies } from '../src/strategies/index.js';
import type { AppConfig } from '../src/config/index.js';

const testConfig: AppConfig = {
  KUCOIN_API_KEY: '',
  KUCOIN_API_SECRET: '',
  KUCOIN_API_PASSPHRASE: '',
  KUCOIN_ENV: 'production',
  TRADING_SYMBOLS: 'BTC-USDT,ETH-USDT',
  WHALE_MIN_TRADE_USDT: 50_000,
  WHALE_ORDERBOOK_WALL_USDT: 100_000,
  WHALE_COOLDOWN_MS: 30_000,
  COPY_RATIO: 0.01,
  MAX_POSITION_USDT: 1_000,
  MAX_DAILY_TRADES: 20,
  MAX_SLIPPAGE_PERCENT: 0.5,
  STOP_LOSS_PERCENT: 2,
  TAKE_PROFIT_PERCENT: 4,
  MAX_OPEN_POSITIONS: 3,
  MIN_ACCOUNT_BALANCE_USDT: 100,
  BOT_MODE: 'paper',
  LOG_LEVEL: 'silent',
  LOG_PRETTY: false,
};

describe('Config', () => {
  it('loads valid default configuration', () => {
    const config = loadConfig({
      BOT_MODE: 'paper',
      TRADING_SYMBOLS: 'BTC-USDT',
    });
    expect(config.BOT_MODE).toBe('paper');
    expect(config.WHALE_MIN_TRADE_USDT).toBe(50_000);
  });

  it('rejects live mode without API credentials', () => {
    expect(() =>
      loadConfig({
        BOT_MODE: 'live',
        KUCOIN_API_KEY: '',
        KUCOIN_API_SECRET: '',
        KUCOIN_API_PASSPHRASE: '',
      }),
    ).toThrow(/KUCOIN_API_KEY is required/);
  });

  it('accepts live mode with credentials', () => {
    const config = loadConfig({
      BOT_MODE: 'live',
      KUCOIN_API_KEY: 'key',
      KUCOIN_API_SECRET: 'secret',
      KUCOIN_API_PASSPHRASE: 'pass',
    });
    expect(config.BOT_MODE).toBe('live');
  });
});

describe('Decimal utilities', () => {
  it('calculates notional correctly', () => {
    expect(calculateNotional(50_000, 1)).toBe(50_000);
    expect(calculateNotional(0.5, 100)).toBe(50);
  });

  it('rounds size down', () => {
    expect(roundSize(1.123456789, 4)).toBe(1.1234);
  });

  it('calculates slippage percent', () => {
    expect(calculateSlippagePercent(100, 100.5)).toBeCloseTo(0.5, 5);
  });

  it('multiplies precisely', () => {
    expect(multiply(50_000, 0.01)).toBe(500);
  });
});

describe('WhaleDetector', () => {
  let detector: WhaleDetector;

  beforeEach(() => {
    detector = new WhaleDetector(testConfig);
  });

  it('detects whale trades above threshold', () => {
    const signal = detector.detectWhaleTrade({
      symbol: 'BTC-USDT',
      side: 'buy',
      price: 50_000,
      size: 2,
      notionalUsdt: 100_000,
      tradeId: '12345',
      timestamp: Date.now(),
    });

    expect(signal).not.toBeNull();
    expect(signal!.source).toBe('whale_trade');
    expect(signal!.side).toBe('buy');
    expect(signal!.confidence).toBeGreaterThan(0.5);
  });

  it('ignores trades below threshold', () => {
    const signal = detector.detectWhaleTrade({
      symbol: 'BTC-USDT',
      side: 'buy',
      price: 50_000,
      size: 0.01,
      notionalUsdt: 500,
      tradeId: '12346',
      timestamp: Date.now(),
    });

    expect(signal).toBeNull();
  });

  it('respects cooldown between signals', () => {
    const event = {
      symbol: 'ETH-USDT',
      side: 'sell' as const,
      price: 3_000,
      size: 20,
      notionalUsdt: 60_000,
      tradeId: '999',
      timestamp: Date.now(),
    };

    const first = detector.detectWhaleTrade(event);
    const second = detector.detectWhaleTrade({
      ...event,
      tradeId: '1000',
      timestamp: Date.now(),
    });

    expect(first).not.toBeNull();
    expect(second).toBeNull();
  });

  it('detects order book walls', () => {
    const signal = detector.detectOrderBookWall({
      symbol: 'BTC-USDT',
      bids: [{ price: 50_000, size: 3 }],
      asks: [{ price: 50_100, size: 0.1 }],
      timestamp: Date.now(),
    });

    expect(signal).not.toBeNull();
    expect(signal!.source).toBe('orderbook_wall');
    expect(signal!.side).toBe('buy');
  });

  it('detects volume spikes', () => {
    const now = Date.now();
    const trades = [
      { notionalUsdt: 30_000, side: 'buy' as const, timestamp: now - 1000 },
      { notionalUsdt: 35_000, side: 'buy' as const, timestamp: now - 500 },
      { notionalUsdt: 40_000, side: 'buy' as const, timestamp: now },
    ];

    const signal = detector.detectVolumeSpike('BTC-USDT', trades);
    expect(signal).not.toBeNull();
    expect(signal!.source).toBe('volume_spike');
  });
});

describe('RiskManager', () => {
  let riskManager: RiskManager;

  beforeEach(() => {
    riskManager = new RiskManager(testConfig);
  });

  it('allows valid signals', () => {
    const result = riskManager.validateSignal(
      {
        id: 'test',
        symbol: 'BTC-USDT',
        side: 'buy',
        price: 50_000,
        size: 1,
        notionalUsdt: 50_000,
        source: 'whale_trade',
        timestamp: Date.now(),
        confidence: 0.8,
      },
      10_000,
    );

    expect(result.allowed).toBe(true);
  });

  it('blocks low confidence signals', () => {
    const result = riskManager.validateSignal(
      {
        id: 'test',
        symbol: 'BTC-USDT',
        side: 'buy',
        price: 50_000,
        size: 1,
        notionalUsdt: 50_000,
        source: 'whale_trade',
        timestamp: Date.now(),
        confidence: 0.3,
      },
      10_000,
    );

    expect(result.allowed).toBe(false);
    expect(result.reason).toContain('confidence');
  });

  it('calculates copy size with ratio cap', () => {
    const { notionalUsdt } = riskManager.calculateCopySize(
      {
        id: 'test',
        symbol: 'BTC-USDT',
        side: 'buy',
        price: 50_000,
        size: 2,
        notionalUsdt: 100_000,
        source: 'whale_trade',
        timestamp: Date.now(),
        confidence: 0.8,
      },
      10_000,
    );

    expect(notionalUsdt).toBe(1_000);
  });

  it('triggers stop loss for long positions', () => {
    const position = {
      symbol: 'BTC-USDT',
      side: 'buy' as const,
      entryPrice: 50_000,
      size: 0.01,
      notionalUsdt: 500,
      openedAt: Date.now(),
      signalId: 'test',
    };

    expect(riskManager.shouldStopLoss(position, 48_500)).toBe(true);
    expect(riskManager.shouldStopLoss(position, 49_500)).toBe(false);
  });

  it('triggers take profit for long positions', () => {
    const position = {
      symbol: 'BTC-USDT',
      side: 'buy' as const,
      entryPrice: 50_000,
      size: 0.01,
      notionalUsdt: 500,
      openedAt: Date.now(),
      signalId: 'test',
    };

    expect(riskManager.shouldTakeProfit(position, 52_100)).toBe(true);
    expect(riskManager.shouldTakeProfit(position, 51_000)).toBe(false);
  });
});

describe('Strategies', () => {
  it('evaluates whale mirror strategy', () => {
    const registry = createDefaultStrategies(testConfig);
    const signals = registry.evaluateAll({
      symbol: 'BTC-USDT',
      recentTrades: [
        {
          sequence: '1',
          price: 50_000,
          size: 2,
          side: 'buy',
          time: Date.now(),
        },
      ],
    });

    expect(signals.length).toBeGreaterThan(0);
    expect(signals[0]!.source).toBe('whale_trade');
  });

  it('evaluates order book imbalance strategy', () => {
    const registry = createDefaultStrategies(testConfig);
    const signals = registry.evaluateAll({
      symbol: 'BTC-USDT',
      recentTrades: [],
      orderBook: {
        symbol: 'BTC-USDT',
        bids: Array.from({ length: 10 }, () => ({ price: 50_000, size: 5 })),
        asks: [{ price: 50_100, size: 0.1 }],
        timestamp: Date.now(),
      },
      ticker: { symbol: 'BTC-USDT', buy: 50_000, sell: 50_010, last: 50_005, vol: 100, volValue: 5_000_000 },
    });

    expect(signals.some((s) => s.source === 'orderbook_wall')).toBe(true);
  });
});
