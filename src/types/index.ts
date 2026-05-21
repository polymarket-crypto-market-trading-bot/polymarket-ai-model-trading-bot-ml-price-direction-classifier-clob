export type Side = 'buy' | 'sell';

export type BotMode = 'monitor' | 'live' | 'paper';

export type OrderType = 'market' | 'limit';

export type TradeSignal = {
  id: string;
  symbol: string;
  side: Side;
  price: number;
  size: number;
  notionalUsdt: number;
  source: 'whale_trade' | 'orderbook_wall' | 'volume_spike';
  timestamp: number;
  confidence: number;
};

export type CopyTradeRequest = {
  signal: TradeSignal;
  copySize: number;
  copyNotionalUsdt: number;
  orderType: OrderType;
};

export type CopyTradeResult = {
  success: boolean;
  orderId?: string;
  symbol: string;
  side: Side;
  size: number;
  price: number;
  mode: BotMode;
  error?: string;
};

export type Position = {
  symbol: string;
  side: Side;
  entryPrice: number;
  size: number;
  notionalUsdt: number;
  openedAt: number;
  signalId: string;
};

export type DailyStats = {
  date: string;
  tradesExecuted: number;
  totalVolumeUsdt: number;
  signalsDetected: number;
  whaleEvents: number;
};

export type WhaleEvent = {
  symbol: string;
  side: Side;
  price: number;
  size: number;
  notionalUsdt: number;
  tradeId: string;
  timestamp: number;
};

export type OrderBookLevel = {
  price: number;
  size: number;
};

export type OrderBookSnapshot = {
  symbol: string;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  timestamp: number;
};

export type AccountBalance = {
  currency: string;
  available: number;
  holds: number;
};

export type KuCoinApiResponse<T> = {
  code: string;
  data: T;
  msg?: string;
};

export type SymbolTicker = {
  symbol: string;
  buy: number;
  sell: number;
  last: number;
  vol: number;
  volValue: number;
};

export type PlaceOrderParams = {
  symbol: string;
  side: Side;
  type: OrderType;
  size?: number;
  funds?: number;
  price?: number;
  clientOid?: string;
};

export type OrderResult = {
  orderId: string;
};

export type MarketTrade = {
  sequence: string;
  price: number;
  size: number;
  side: Side;
  time: number;
};

export type WebSocketMessage = {
  type: 'message' | 'welcome' | 'ack' | 'pong' | 'error';
  id?: string;
  topic?: string;
  subject?: string;
  data?: unknown;
};

export type StrategyContext = {
  symbol: string;
  recentTrades: MarketTrade[];
  orderBook?: OrderBookSnapshot;
  ticker?: SymbolTicker;
};

export type RiskCheckResult = {
  allowed: boolean;
  reason?: string;
};
