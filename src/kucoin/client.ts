import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios';
import type { AppConfig } from '../config/index.js';
import { getKuCoinBaseUrl, hasApiCredentials } from '../config/index.js';
import { signRequest, type AuthCredentials } from './auth.js';
import { retry, isAxiosError } from '../utils/index.js';
import type {
  AccountBalance,
  KuCoinApiResponse,
  MarketTrade,
  OrderBookSnapshot,
  OrderResult,
  PlaceOrderParams,
  SymbolTicker,
} from '../types/index.js';

type TokenResponse = {
  token: string;
  instanceServers: Array<{
    endpoint: string;
    encrypt: boolean;
    protocol: string;
    pingInterval: number;
    pingTimeout: number;
  }>;
};

export class KuCoinClient {
  private readonly http: AxiosInstance;
  private readonly credentials: AuthCredentials | null;

  constructor(config: AppConfig) {
    this.http = axios.create({
      baseURL: getKuCoinBaseUrl(config),
      timeout: 15_000,
      headers: { 'Content-Type': 'application/json' },
    });

    this.credentials = hasApiCredentials(config)
      ? {
          apiKey: config.KUCOIN_API_KEY,
          apiSecret: config.KUCOIN_API_SECRET,
          passphrase: config.KUCOIN_API_PASSPHRASE,
        }
      : null;
  }

  async getTicker(symbol: string): Promise<SymbolTicker> {
    const response = await this.publicGet<{
      symbol: string;
      buy: string;
      sell: string;
      last: string;
      vol: string;
      volValue: string;
    }>(`/api/v1/market/stats?symbol=${symbol}`);

    const data = response.data;
    return {
      symbol: data.symbol,
      buy: Number(data.buy),
      sell: Number(data.sell),
      last: Number(data.last),
      vol: Number(data.vol),
      volValue: Number(data.volValue),
    };
  }

  async getAllTickers(): Promise<SymbolTicker[]> {
    const response = await this.publicGet<{ ticker: SymbolTicker[] }>(
      '/api/v1/market/allTickers',
    );
    return response.data.ticker;
  }

  async getOrderBook(symbol: string, depth = 20): Promise<OrderBookSnapshot> {
    const response = await this.publicGet<{
      sequence: string;
      time: number;
      bids: [string, string][];
      asks: [string, string][];
    }>(`/api/v1/market/orderbook/level2_${depth}?symbol=${symbol}`);

    return {
      symbol,
      bids: response.data.bids.map(([price, size]) => ({
        price: Number(price),
        size: Number(size),
      })),
      asks: response.data.asks.map(([price, size]) => ({
        price: Number(price),
        size: Number(size),
      })),
      timestamp: response.data.time,
    };
  }

  async getRecentTrades(symbol: string): Promise<MarketTrade[]> {
    const response = await this.publicGet<MarketTrade[]>(
      `/api/v1/market/histories?symbol=${symbol}`,
    );
    return response.data.map((trade) => ({
      ...trade,
      price: Number(trade.price),
      size: Number(trade.size),
    }));
  }

  async getAccounts(currency = 'USDT'): Promise<AccountBalance[]> {
    this.requireCredentials();
    const response = await this.privateGet<
      Array<{ currency: string; available: string; holds: string }>
    >(`/api/v1/accounts?currency=${currency}&type=trade`);

    return response.data.map((account) => ({
      currency: account.currency,
      available: Number(account.available),
      holds: Number(account.holds),
    }));
  }

  async getUsdtBalance(): Promise<number> {
    const accounts = await this.getAccounts('USDT');
    return accounts.reduce((sum, acc) => sum + acc.available, 0);
  }

  async placeOrder(params: PlaceOrderParams): Promise<OrderResult> {
    this.requireCredentials();

    const body: Record<string, string | number> = {
      clientOid: params.clientOid ?? `whale-${Date.now()}`,
      side: params.side,
      symbol: params.symbol,
      type: params.type,
    };

    if (params.type === 'market') {
      if (params.side === 'buy' && params.funds) {
        body.funds = params.funds;
      } else if (params.size) {
        body.size = params.size;
      }
    } else {
      if (params.price) body.price = params.price;
      if (params.size) body.size = params.size;
    }

    const response = await this.privatePost<OrderResult>(
      '/api/v1/orders',
      body,
    );
    return response.data;
  }

  async getBulletToken(isPrivate = false): Promise<TokenResponse> {
    if (isPrivate) {
      this.requireCredentials();
      const response = await this.privatePost<TokenResponse>(
        '/api/v1/bullet-private',
        {},
      );
      return response.data;
    }

    const response = await this.publicPost<TokenResponse>(
      '/api/v1/bullet-public',
      {},
    );
    return response.data;
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.publicGet('/api/v1/timestamp');
      return true;
    } catch {
      return false;
    }
  }

  private async publicGet<T>(path: string): Promise<KuCoinApiResponse<T>> {
    return retry(async () => {
      const response = await this.http.get<KuCoinApiResponse<T>>(path);
      this.assertSuccess(response.data);
      return response.data;
    }, { shouldRetry: this.shouldRetryRequest });
  }

  private async publicPost<T>(
    path: string,
    body: unknown,
  ): Promise<KuCoinApiResponse<T>> {
    return retry(async () => {
      const response = await this.http.post<KuCoinApiResponse<T>>(path, body);
      this.assertSuccess(response.data);
      return response.data;
    }, { shouldRetry: this.shouldRetryRequest });
  }

  private async privateGet<T>(path: string): Promise<KuCoinApiResponse<T>> {
    return retry(async () => {
      const config = this.buildAuthConfig('GET', path, '');
      const response = await this.http.get<KuCoinApiResponse<T>>(path, config);
      this.assertSuccess(response.data);
      return response.data;
    }, { shouldRetry: this.shouldRetryRequest });
  }

  private async privatePost<T>(
    path: string,
    body: Record<string, unknown>,
  ): Promise<KuCoinApiResponse<T>> {
    return retry(async () => {
      const bodyStr = JSON.stringify(body);
      const config = this.buildAuthConfig('POST', path, bodyStr);
      const response = await this.http.post<KuCoinApiResponse<T>>(
        path,
        body,
        config,
      );
      this.assertSuccess(response.data);
      return response.data;
    }, { shouldRetry: this.shouldRetryRequest });
  }

  private buildAuthConfig(
    method: string,
    path: string,
    body: string,
  ): AxiosRequestConfig {
    this.requireCredentials();
    const timestamp = Date.now();
    const { signature, passphrase } = signRequest(
      this.credentials!,
      method,
      path,
      body,
      timestamp,
    );

    return {
      headers: {
        'KC-API-KEY': this.credentials!.apiKey,
        'KC-API-SIGN': signature,
        'KC-API-TIMESTAMP': String(timestamp),
        'KC-API-PASSPHRASE': passphrase,
        'KC-API-KEY-VERSION': '2',
      },
    };
  }

  private assertSuccess<T>(response: KuCoinApiResponse<T>): void {
    if (response.code !== '200000') {
      throw new Error(
        `KuCoin API error [${response.code}]: ${response.msg ?? 'Unknown error'}`,
      );
    }
  }

  private requireCredentials(): void {
    if (!this.credentials) {
      throw new Error(
        'KuCoin API credentials are required for this operation',
      );
    }
  }

  private shouldRetryRequest = (error: unknown): boolean => {
    if (isAxiosError(error)) {
      const status = error.response?.status;
      return status === undefined || status >= 500 || status === 429;
    }
    return false;
  };
}
