import type { AppConfig } from './config/index.js';
import { loadConfig, getTradingSymbols } from './config/index.js';
import { KuCoinClient } from './kucoin/client.js';
import { CopyTradingEngine } from './copy-trading/engine.js';
import { createLogger, getLogger } from './services/logger.js';

export class WhaleCopyTradingBot {
  private readonly config: AppConfig;
  private readonly client: KuCoinClient;
  private readonly engine: CopyTradingEngine;
  private shutdownHandlersRegistered = false;

  constructor(config?: AppConfig) {
    this.config = config ?? loadConfig();
    createLogger(this.config);
    this.client = new KuCoinClient(this.config);
    this.engine = new CopyTradingEngine(this.config, this.client);
  }

  async start(): Promise<void> {
    this.registerShutdownHandlers();
    await this.engine.start();
    this.printBanner();
  }

  async stop(): Promise<void> {
    await this.engine.stop();
  }

  getEngine(): CopyTradingEngine {
    return this.engine;
  }

  getConfig(): AppConfig {
    return this.config;
  }

  private printBanner(): void {
    const logger = getLogger();
    const symbols = getTradingSymbols(this.config);

    logger.info('═══════════════════════════════════════════════════════');
    logger.info('  KuCoin Whale Copy Trading Bot');
    logger.info(`  Mode: ${this.config.BOT_MODE.toUpperCase()}`);
    logger.info(`  Symbols: ${symbols.join(', ')}`);
    logger.info(`  Whale threshold: $${this.config.WHALE_MIN_TRADE_USDT.toLocaleString()} USDT`);
    logger.info(`  Copy ratio: ${(this.config.COPY_RATIO * 100).toFixed(2)}%`);
    logger.info('═══════════════════════════════════════════════════════');
  }

  private registerShutdownHandlers(): void {
    if (this.shutdownHandlersRegistered) return;
    this.shutdownHandlersRegistered = true;

    const shutdown = async (signal: string) => {
      getLogger().info({ signal }, 'Shutdown signal received');
      await this.stop();
      process.exit(0);
    };

    process.on('SIGINT', () => void shutdown('SIGINT'));
    process.on('SIGTERM', () => void shutdown('SIGTERM'));
  }
}

export async function bootstrap(): Promise<WhaleCopyTradingBot> {
  const bot = new WhaleCopyTradingBot();
  await bot.start();
  return bot;
}
