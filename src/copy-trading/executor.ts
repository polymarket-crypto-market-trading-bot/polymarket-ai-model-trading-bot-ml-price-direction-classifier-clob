import type { AppConfig } from '../config/index.js';
import { KuCoinClient } from '../kucoin/client.js';
import { generateClientOid } from '../kucoin/auth.js';
import { getLogger } from '../services/logger.js';
import type {
  CopyTradeRequest,
  CopyTradeResult,
  Position,
  TradeSignal,
} from '../types/index.js';
import { calculateSlippagePercent, roundSize } from '../utils/decimal.js';
import { RiskManager } from './riskManager.js';

export class CopyTradeExecutor {
  constructor(
    private readonly config: AppConfig,
    private readonly client: KuCoinClient,
    private readonly riskManager: RiskManager,
  ) {}

  async execute(
    signal: TradeSignal,
    accountBalanceUsdt: number,
  ): Promise<CopyTradeResult> {
    const logger = getLogger();

    const riskCheck = this.riskManager.validateSignal(signal, accountBalanceUsdt);
    if (!riskCheck.allowed) {
      logger.warn(
        { symbol: signal.symbol, reason: riskCheck.reason },
        'Trade blocked by risk manager',
      );
      return {
        success: false,
        symbol: signal.symbol,
        side: signal.side,
        size: 0,
        price: signal.price,
        mode: this.config.BOT_MODE,
        error: riskCheck.reason,
      };
    }

    const { size, notionalUsdt } = this.riskManager.calculateCopySize(
      signal,
      accountBalanceUsdt,
    );

    const request: CopyTradeRequest = {
      signal,
      copySize: roundSize(size),
      copyNotionalUsdt: notionalUsdt,
      orderType: 'market',
    };

    if (this.config.BOT_MODE === 'monitor') {
      logger.info(
        { signal: signal.id, side: signal.side, notionalUsdt },
        'Monitor mode: signal logged, no execution',
      );
      return this.buildResult(request, true, 'monitor-skip');
    }

    if (this.config.BOT_MODE === 'paper') {
      logger.info(
        {
          signal: signal.id,
          symbol: signal.symbol,
          side: signal.side,
          size: request.copySize,
          notionalUsdt,
        },
        'Paper trade executed',
      );

      this.recordPaperPosition(signal, request);
      return this.buildResult(request, true, `paper-${Date.now()}`);
    }

    return this.executeLiveOrder(request);
  }

  private async executeLiveOrder(
    request: CopyTradeRequest,
  ): Promise<CopyTradeResult> {
    const logger = getLogger();
    const { signal } = request;

    try {
      const ticker = await this.client.getTicker(signal.symbol);
      const expectedPrice = signal.side === 'buy' ? ticker.sell : ticker.buy;

      const slippage = calculateSlippagePercent(expectedPrice, signal.price);
      if (slippage > this.config.MAX_SLIPPAGE_PERCENT) {
        logger.warn(
          { slippage, max: this.config.MAX_SLIPPAGE_PERCENT },
          'Slippage too high, skipping trade',
        );
        return {
          success: false,
          symbol: signal.symbol,
          side: signal.side,
          size: request.copySize,
          price: signal.price,
          mode: 'live',
          error: `Slippage ${slippage.toFixed(2)}% exceeds limit`,
        };
      }

      const orderParams =
        signal.side === 'buy'
          ? {
              symbol: signal.symbol,
              side: signal.side as 'buy' | 'sell',
              type: 'market' as const,
              funds: request.copyNotionalUsdt,
              clientOid: generateClientOid(),
            }
          : {
              symbol: signal.symbol,
              side: signal.side as 'buy' | 'sell',
              type: 'market' as const,
              size: request.copySize,
              clientOid: generateClientOid(),
            };

      const result = await this.client.placeOrder(orderParams);

      const position: Position = {
        symbol: signal.symbol,
        side: signal.side,
        entryPrice: expectedPrice,
        size: request.copySize,
        notionalUsdt: request.copyNotionalUsdt,
        openedAt: Date.now(),
        signalId: signal.id,
      };
      this.riskManager.recordPosition(position);

      logger.info(
        { orderId: result.orderId, symbol: signal.symbol, side: signal.side },
        'Live order executed',
      );

      return this.buildResult(request, true, result.orderId);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      logger.error({ err: error, symbol: signal.symbol }, 'Live order failed');
      return {
        success: false,
        symbol: signal.symbol,
        side: signal.side,
        size: request.copySize,
        price: signal.price,
        mode: 'live',
        error: message,
      };
    }
  }

  private recordPaperPosition(signal: TradeSignal, request: CopyTradeRequest): void {
    const position: Position = {
      symbol: signal.symbol,
      side: signal.side,
      entryPrice: signal.price,
      size: request.copySize,
      notionalUsdt: request.copyNotionalUsdt,
      openedAt: Date.now(),
      signalId: signal.id,
    };
    this.riskManager.recordPosition(position);
  }

  private buildResult(
    request: CopyTradeRequest,
    success: boolean,
    orderId?: string,
    error?: string,
  ): CopyTradeResult {
    return {
      success,
      orderId,
      symbol: request.signal.symbol,
      side: request.signal.side,
      size: request.copySize,
      price: request.signal.price,
      mode: this.config.BOT_MODE,
      error,
    };
  }
}
