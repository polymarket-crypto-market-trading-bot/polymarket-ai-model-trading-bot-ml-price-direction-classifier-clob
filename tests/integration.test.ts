import { describe, it, expect, beforeEach } from 'vitest';
import { KuCoinClient } from '../src/kucoin/client.js';
import { CopyTradeExecutor } from '../src/copy-trading/executor.js';
import { RiskManager } from '../src/copy-trading/riskManager.js';
import { createLogger, resetLogger } from '../src/services/logger.js';
import type { AppConfig } from '../src/config/index.js';

const testConfig: AppConfig = {
  KUCOIN_API_KEY: 'test-key',
  KUCOIN_API_SECRET: 'test-secret',
  KUCOIN_API_PASSPHRASE: 'test-pass',
  KUCOIN_ENV: 'production',
  TRADING_SYMBOLS: 'BTC-USDT',
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

describe('CopyTradeExecutor', () => {
  let client: KuCoinClient;
  let executor: CopyTradeExecutor;

  beforeEach(() => {
    resetLogger();
    createLogger(testConfig);
    client = new KuCoinClient(testConfig);
    executor = new CopyTradeExecutor(testConfig, client, new RiskManager(testConfig));
  });

  it('executes paper trades without API calls', async () => {
    const result = await executor.execute(
      {
        id: 'signal-1',
        symbol: 'BTC-USDT',
        side: 'buy',
        price: 50_000,
        size: 1,
        notionalUsdt: 50_000,
        source: 'whale_trade',
        timestamp: Date.now(),
        confidence: 0.85,
      },
      10_000,
    );

    expect(result.success).toBe(true);
    expect(result.mode).toBe('paper');
    expect(result.orderId).toMatch(/^paper-/);
  });

  it('blocks trades in monitor mode', async () => {
    const monitorConfig = { ...testConfig, BOT_MODE: 'monitor' as const };
    const monitorExecutor = new CopyTradeExecutor(
      monitorConfig,
      client,
      new RiskManager(monitorConfig),
    );

    const result = await monitorExecutor.execute(
      {
        id: 'signal-2',
        symbol: 'BTC-USDT',
        side: 'sell',
        price: 50_000,
        size: 1,
        notionalUsdt: 50_000,
        source: 'whale_trade',
        timestamp: Date.now(),
        confidence: 0.85,
      },
      10_000,
    );

    expect(result.success).toBe(true);
    expect(result.orderId).toBe('monitor-skip');
  });
});

describe('KuCoinClient', () => {
  it('passes health check against public API', async () => {
    const client = new KuCoinClient({
      ...testConfig,
      KUCOIN_API_KEY: '',
      KUCOIN_API_SECRET: '',
      KUCOIN_API_PASSPHRASE: '',
    });

    const healthy = await client.healthCheck();
    expect(healthy).toBe(true);
  }, 20_000);

  it('fetches public ticker data', async () => {
    const client = new KuCoinClient({
      ...testConfig,
      KUCOIN_API_KEY: '',
      KUCOIN_API_SECRET: '',
      KUCOIN_API_PASSPHRASE: '',
    });

    const ticker = await client.getTicker('BTC-USDT');
    expect(ticker).toBeDefined();
    expect(Number(ticker.last)).toBeGreaterThan(0);
  }, 20_000);

  it('fetches order book snapshot', async () => {
    const client = new KuCoinClient({
      ...testConfig,
      KUCOIN_API_KEY: '',
      KUCOIN_API_SECRET: '',
      KUCOIN_API_PASSPHRASE: '',
    });

    const book = await client.getOrderBook('BTC-USDT', 20);
    expect(book.bids.length).toBeGreaterThan(0);
    expect(book.asks.length).toBeGreaterThan(0);
    expect(book.bids[0]!.price).toBeGreaterThan(0);
  }, 20_000);

  it('fetches recent trades', async () => {
    const client = new KuCoinClient({
      ...testConfig,
      KUCOIN_API_KEY: '',
      KUCOIN_API_SECRET: '',
      KUCOIN_API_PASSPHRASE: '',
    });

    const trades = await client.getRecentTrades('BTC-USDT');
    expect(Array.isArray(trades)).toBe(true);
  }, 20_000);
});

describe('Auth signing', () => {
  it('generates consistent signatures', async () => {
    const { signRequest, generateClientOid } = await import('../src/kucoin/auth.js');

    const creds = {
      apiKey: 'key',
      apiSecret: 'secret',
      passphrase: 'pass',
    };

    const result = signRequest(creds, 'GET', '/api/v1/accounts', '', 1700000000000);
    expect(result.signature).toBeTruthy();
    expect(result.passphrase).toBeTruthy();

    const oid1 = generateClientOid();
    const oid2 = generateClientOid();
    expect(oid1).not.toBe(oid2);
    expect(oid1).toMatch(/^whale-bot-/);
  });
});
