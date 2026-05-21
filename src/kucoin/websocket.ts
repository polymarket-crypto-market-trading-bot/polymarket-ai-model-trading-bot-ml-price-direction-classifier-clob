import WebSocket from 'ws';
import { EventEmitter } from 'node:events';
import type { KuCoinClient } from './client.js';
import { getLogger } from '../services/logger.js';
import type { MarketTrade, OrderBookSnapshot, Side, WebSocketMessage } from '../types/index.js';
import { calculateNotional } from '../utils/decimal.js';

export type WhaleTradeHandler = (trade: {
  symbol: string;
  side: Side;
  price: number;
  size: number;
  notionalUsdt: number;
  tradeId: string;
  timestamp: number;
}) => void;

type Subscription = {
  topic: string;
  handler: (data: unknown) => void;
};

export class KuCoinWebSocket {
  private ws: WebSocket | null = null;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 10;
  private readonly subscriptions = new Map<string, Subscription>();
  private connectId = 1;
  private readonly emitter = new EventEmitter();
  private isConnecting = false;
  private shouldReconnect = true;

  constructor(
    private readonly client: KuCoinClient,
    private readonly isPrivate = false,
  ) {}

  on(event: 'connected' | 'disconnected' | 'error', handler: (...args: unknown[]) => void): void {
    this.emitter.on(event, handler);
  }

  async connect(): Promise<void> {
    if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) return;
    this.isConnecting = true;

    try {
      const tokenData = await this.client.getBulletToken(this.isPrivate);
      const server = tokenData.instanceServers[0];
      if (!server) throw new Error('No WebSocket server available');

      const url = `${server.endpoint}?token=${tokenData.token}&connectId=${this.connectId++}`;
      this.ws = new WebSocket(url);

      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('WebSocket connection timeout')), 15_000);

        this.ws!.once('open', () => {
          clearTimeout(timeout);
          this.setupPing(server.pingInterval);
          this.reconnectAttempts = 0;
          this.isConnecting = false;
          getLogger().info('KuCoin WebSocket connected');
          this.emitter.emit('connected');
          this.resubscribeAll();
          resolve();
        });

        this.ws!.once('error', (err) => {
          clearTimeout(timeout);
          this.isConnecting = false;
          reject(err);
        });
      });

      this.ws.on('message', (raw) => this.handleMessage(raw.toString()));
      this.ws.on('close', () => this.handleClose());
      this.ws.on('error', (err) => {
        getLogger().error({ err }, 'WebSocket error');
        this.emitter.emit('error', err);
      });
    } catch (error) {
      this.isConnecting = false;
      throw error;
    }
  }

  subscribeMatchTrades(symbol: string, handler: WhaleTradeHandler): void {
    const topic = `/market/match:${symbol}`;
    this.subscriptions.set(topic, {
      topic,
      handler: (data: unknown) => {
        const trade = data as {
          sequence: string;
          price: string;
          size: string;
          side: Side;
          time: string;
        };

        handler({
          symbol,
          side: trade.side,
          price: Number(trade.price),
          size: Number(trade.size),
          notionalUsdt: calculateNotional(Number(trade.price), Number(trade.size)),
          tradeId: trade.sequence,
          timestamp: Number(trade.time),
        });
      },
    });

    this.sendSubscribe(topic);
  }

  subscribeOrderBook(symbol: string, handler: (snapshot: OrderBookSnapshot) => void): void {
    const topic = `/market/level2:${symbol}`;
    this.subscriptions.set(topic, {
      topic,
      handler: (data: unknown) => {
        const book = data as {
          bids?: [string, string][];
          asks?: [string, string][];
          changes?: {
            bids?: [string, string, string][];
            asks?: [string, string, string][];
          };
          timestamp?: number;
          time?: number;
        };

        const bids = book.bids ?? book.changes?.bids?.map(([price, size]) => [price, size]) ?? [];
        const asks = book.asks ?? book.changes?.asks?.map(([price, size]) => [price, size]) ?? [];

        if (!bids.length || !asks.length) {
          return;
        }

        handler({
          symbol,
          bids: bids.map(([price, size]) => ({
            price: Number(price),
            size: Number(size),
          })),
          asks: asks.map(([price, size]) => ({
            price: Number(price),
            size: Number(size),
          })),
          timestamp: book.timestamp ?? book.time ?? Date.now(),
        });
      },
    });

    this.sendSubscribe(topic);
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.clearPing();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    getLogger().info('KuCoin WebSocket disconnected');
    this.emitter.emit('disconnected');
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private sendSubscribe(topic: string): void {
    if (!this.isConnected()) return;

    const message = {
      id: Date.now().toString(),
      type: 'subscribe',
      topic,
      privateChannel: this.isPrivate,
      response: true,
    };

    this.ws!.send(JSON.stringify(message));
    getLogger().debug({ topic }, 'Subscribed to topic');
  }

  private resubscribeAll(): void {
    for (const { topic } of this.subscriptions.values()) {
      this.sendSubscribe(topic);
    }
  }

  private handleMessage(raw: string): void {
    let message: WebSocketMessage;
    try {
      message = JSON.parse(raw) as WebSocketMessage;
    } catch {
      getLogger().warn({ raw }, 'Failed to parse WebSocket message');
      return;
    }

    if (message.type === 'pong') return;

    if (message.type === 'message' && message.topic && message.data) {
      const subscription = this.subscriptions.get(message.topic);
      if (subscription) {
        try {
          subscription.handler(message.data);
        } catch (error) {
          getLogger().error(
            { err: error, topic: message.topic },
            'WebSocket subscription handler failed',
          );
        }
      }
    }

    if (message.type === 'error') {
      getLogger().error({ message }, 'WebSocket server error');
    }
  }

  private handleClose(): void {
    this.clearPing();
    this.ws = null;
    this.emitter.emit('disconnected');

    if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30_000);
      getLogger().warn(
        { attempt: this.reconnectAttempts, delayMs: delay },
        'WebSocket closed, reconnecting',
      );
      setTimeout(() => {
        void this.connect().catch((err) => {
          getLogger().error({ err }, 'WebSocket reconnection failed');
        });
      }, delay);
    }
  }

  private setupPing(intervalMs: number): void {
    this.clearPing();
    this.pingInterval = setInterval(() => {
      if (this.isConnected()) {
        this.ws!.send(JSON.stringify({ id: Date.now().toString(), type: 'ping' }));
      }
    }, intervalMs);
  }

  private clearPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}

export function parseMarketTradesFromRest(trades: MarketTrade[]): MarketTrade[] {
  return trades.map((t) => ({
    ...t,
    price: Number(t.price),
    size: Number(t.size),
  }));
}
