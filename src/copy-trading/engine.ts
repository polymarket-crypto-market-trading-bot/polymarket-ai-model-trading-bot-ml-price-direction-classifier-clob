import type { AppConfig } from '../config/index.js';
import { getTradingSymbols } from '../config/index.js';
import { KuCoinClient } from '../kucoin/client.js';
import { KuCoinWebSocket } from '../kucoin/websocket.js';
import { WhaleDetector } from '../whale/detector.js';
import { RiskManager } from './riskManager.js';
import { CopyTradeExecutor } from './executor.js';
import { getLogger } from '../services/logger.js';
import type { CopyTradeResult, DailyStats, TradeSignal } from '../types/index.js';
import { todayDateString, formatUsdt } from '../utils/index.js';

export class CopyTradingEngine {
  private readonly symbols: string[];
  private readonly whaleDetector: WhaleDetector;
  private readonly riskManager: RiskManager;
  private readonly executor: CopyTradeExecutor;
  private readonly websocket: KuCoinWebSocket;
  private readonly recentTrades = new Map<
    string,
    Array<{ notionalUsdt: number; side: 'buy' | 'sell'; timestamp: number }>
  >();
  private readonly stats: DailyStats;
  private running = false;
  private positionMonitorInterval: ReturnType<typeof setInterval> | null = null;
  private orderBookPollInterval: ReturnType<typeof setInterval> | null = null;

  constructor(
    private readonly config: AppConfig,
    private readonly client: KuCoinClient,
  ) {
    this.symbols = getTradingSymbols(config);
    this.whaleDetector = new WhaleDetector(config);
    this.riskManager = new RiskManager(config);
    this.executor = new CopyTradeExecutor(config, client, this.riskManager);
    this.websocket = new KuCoinWebSocket(client, false);
    this.stats = {
      date: todayDateString(),
      tradesExecuted: 0,
      totalVolumeUsdt: 0,
      signalsDetected: 0,
      whaleEvents: 0,
    };
  }

  async start(): Promise<void> {
    const logger = getLogger();

    if (this.running) {
      logger.warn('Engine already running');
      return;
    }

    logger.info(
      {
        mode: this.config.BOT_MODE,
        symbols: this.symbols,
        whaleThreshold: formatUsdt(this.config.WHALE_MIN_TRADE_USDT),
      },
      'Starting KuCoin whale copy trading engine',
    );

    const healthy = await this.client.healthCheck();
    if (!healthy) {
      throw new Error('KuCoin API health check failed');
    }

    await this.websocket.connect();

    for (const symbol of this.symbols) {
      this.subscribeSymbol(symbol);
    }

    this.running = true;
    this.startOrderBookPolling();
    this.startPositionMonitor();

    logger.info('Engine started successfully');
  }

  async stop(): Promise<void> {
    const logger = getLogger();
    this.running = false;

    if (this.positionMonitorInterval) {
      clearInterval(this.positionMonitorInterval);
      this.positionMonitorInterval = null;
    }

    if (this.orderBookPollInterval) {
      clearInterval(this.orderBookPollInterval);
      this.orderBookPollInterval = null;
    }

    this.websocket.disconnect();
    logger.info({ stats: this.stats }, 'Engine stopped');
  }

  getStats(): DailyStats {
    return { ...this.stats };
  }

  isRunning(): boolean {
    return this.running;
  }

  private subscribeSymbol(symbol: string): void {
    const logger = getLogger();

    this.websocket.subscribeMatchTrades(symbol, (trade) => {
      this.stats.whaleEvents++;

      const signal = this.whaleDetector.detectWhaleTrade({
        symbol: trade.symbol,
        side: trade.side,
        price: trade.price,
        size: trade.size,
        notionalUsdt: trade.notionalUsdt,
        tradeId: trade.tradeId,
        timestamp: trade.timestamp,
      });

      this.trackRecentTrade(symbol, trade.notionalUsdt, trade.side, trade.timestamp);

      if (signal) {
        void this.handleSignal(signal);
        return;
      }

      const spikeSignal = this.whaleDetector.detectVolumeSpike(
        symbol,
        this.recentTrades.get(symbol) ?? [],
      );
      if (spikeSignal) {
        void this.handleSignal(spikeSignal);
      }
    });

    logger.info({ symbol }, 'Subscribed to whale trade feed');
  }

  private startOrderBookPolling(): void {
    const poll = async (): Promise<void> => {
      if (!this.running) return;

      for (const symbol of this.symbols) {
        try {
          const orderBook = await this.client.getOrderBook(symbol, 20);
          const signal = this.whaleDetector.detectOrderBookWall(orderBook);
          if (signal) {
            void this.handleSignal(signal);
          }
        } catch (error) {
          getLogger().error({ err: error, symbol }, 'Order book poll failed');
        }
      }
    };

    void poll();
    this.orderBookPollInterval = setInterval(() => {
      void poll();
    }, 30_000);
  }

  private async handleSignal(signal: TradeSignal): Promise<void> {
    const logger = getLogger();
    this.stats.signalsDetected++;

    logger.info(
      {
        id: signal.id,
        symbol: signal.symbol,
        side: signal.side,
        source: signal.source,
        notional: formatUsdt(signal.notionalUsdt),
        confidence: signal.confidence.toFixed(2),
      },
      'Whale signal detected',
    );

    const balance = await this.getAccountBalance();
    const result = await this.executor.execute(signal, balance);

    if (result.success) {
      this.stats.tradesExecuted++;
      this.stats.totalVolumeUsdt += signal.notionalUsdt * this.config.COPY_RATIO;
    }
  }

  private async getAccountBalance(): Promise<number> {
    if (this.config.BOT_MODE === 'paper' || this.config.BOT_MODE === 'monitor') {
      return Math.max(this.config.MIN_ACCOUNT_BALANCE_USDT, 10_000);
    }

    try {
      return await this.client.getUsdtBalance();
    } catch (error) {
      getLogger().error({ err: error }, 'Failed to fetch balance, using minimum');
      return this.config.MIN_ACCOUNT_BALANCE_USDT;
    }
  }

  private trackRecentTrade(
    symbol: string,
    notionalUsdt: number,
    side: 'buy' | 'sell',
    timestamp: number,
  ): void {
    const trades = this.recentTrades.get(symbol) ?? [];
    trades.push({ notionalUsdt, side, timestamp });

    const cutoff = Date.now() - 120_000;
    const filtered = trades.filter((t) => t.timestamp >= cutoff);
    this.recentTrades.set(symbol, filtered);
  }

  private startPositionMonitor(): void {
    this.positionMonitorInterval = setInterval(() => {
      void this.monitorPositions();
    }, 15_000);
  }

  private async monitorPositions(): Promise<void> {
    if (!this.running) return;

    const positions = this.riskManager.getOpenPositions();
    if (positions.length === 0) return;

    for (const position of positions) {
      try {
        const ticker = await this.client.getTicker(position.symbol);
        const currentPrice = ticker.last;

        if (this.riskManager.shouldStopLoss(position, currentPrice)) {
          getLogger().warn(
            { symbol: position.symbol, currentPrice },
            'Stop loss triggered',
          );
          await this.closePosition(position, currentPrice, 'stop_loss');
        } else if (this.riskManager.shouldTakeProfit(position, currentPrice)) {
          getLogger().info(
            { symbol: position.symbol, currentPrice },
            'Take profit triggered',
          );
          await this.closePosition(position, currentPrice, 'take_profit');
        }
      } catch (error) {
        getLogger().error(
          { err: error, symbol: position.symbol },
          'Position monitor error',
        );
      }
    }
  }

  private async closePosition(
    position: ReturnType<RiskManager['getOpenPositions']>[number],
    currentPrice: number,
    reason: string,
  ): Promise<CopyTradeResult | void> {
    const closeSide = position.side === 'buy' ? 'sell' : 'buy';

    const signal: TradeSignal = {
      id: `close-${reason}-${position.symbol}-${Date.now()}`,
      symbol: position.symbol,
      side: closeSide,
      price: currentPrice,
      size: position.size,
      notionalUsdt: position.notionalUsdt,
      source: 'whale_trade',
      timestamp: Date.now(),
      confidence: 1,
    };

    if (this.config.BOT_MODE === 'live') {
      const result = await this.executor.execute(signal, await this.getAccountBalance());
      if (result.success) {
        this.riskManager.closePosition(position.symbol);
      }
      return result;
    }

    this.riskManager.closePosition(position.symbol);
    getLogger().info({ symbol: position.symbol, reason }, 'Paper/monitor position closed');
  }
}
