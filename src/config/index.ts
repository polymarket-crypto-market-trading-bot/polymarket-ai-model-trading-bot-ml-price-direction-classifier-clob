import { z } from 'zod';

const botModeSchema = z.enum(['monitor', 'live', 'paper']);

export const configSchema = z
  .object({
    KUCOIN_API_KEY: z.string().default(''),
    KUCOIN_API_SECRET: z.string().default(''),
    KUCOIN_API_PASSPHRASE: z.string().default(''),
    KUCOIN_ENV: z.enum(['production', 'sandbox']).default('production'),
    TRADING_SYMBOLS: z.string().default('BTC-USDT,ETH-USDT'),
    WHALE_MIN_TRADE_USDT: z.coerce.number().positive().default(50_000),
    WHALE_ORDERBOOK_WALL_USDT: z.coerce.number().positive().default(100_000),
    WHALE_COOLDOWN_MS: z.coerce.number().int().nonnegative().default(30_000),
    COPY_RATIO: z.coerce.number().positive().max(1).default(0.01),
    MAX_POSITION_USDT: z.coerce.number().positive().default(1_000),
    MAX_DAILY_TRADES: z.coerce.number().int().positive().default(20),
    MAX_SLIPPAGE_PERCENT: z.coerce.number().positive().max(10).default(0.5),
    STOP_LOSS_PERCENT: z.coerce.number().positive().max(50).default(2),
    TAKE_PROFIT_PERCENT: z.coerce.number().positive().max(100).default(4),
    MAX_OPEN_POSITIONS: z.coerce.number().int().positive().default(3),
    MIN_ACCOUNT_BALANCE_USDT: z.coerce.number().nonnegative().default(100),
    BOT_MODE: botModeSchema.default('paper'),
    LOG_LEVEL: z
      .enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace', 'silent'])
      .default('info'),
    LOG_PRETTY: z
      .union([z.boolean(), z.string()])
      .transform((v) => v === true || v === 'true')
      .default(true),
  })
  .superRefine((data, ctx) => {
    if (data.BOT_MODE === 'live') {
      if (!data.KUCOIN_API_KEY) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'KUCOIN_API_KEY is required when BOT_MODE=live',
          path: ['KUCOIN_API_KEY'],
        });
      }
      if (!data.KUCOIN_API_SECRET) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'KUCOIN_API_SECRET is required when BOT_MODE=live',
          path: ['KUCOIN_API_SECRET'],
        });
      }
      if (!data.KUCOIN_API_PASSPHRASE) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'KUCOIN_API_PASSPHRASE is required when BOT_MODE=live',
          path: ['KUCOIN_API_PASSPHRASE'],
        });
      }
    }
  });

export type AppConfig = z.infer<typeof configSchema>;

export function loadConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  const parsed = configSchema.safeParse(env);
  if (!parsed.success) {
    const messages = parsed.error.issues
      .map((issue) => `${issue.path.join('.')}: ${issue.message}`)
      .join('\n');
    throw new Error(`Invalid configuration:\n${messages}`);
  }
  return parsed.data;
}

export function getTradingSymbols(config: AppConfig): string[] {
  return config.TRADING_SYMBOLS.split(',')
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

export function getKuCoinBaseUrl(config: AppConfig): string {
  return config.KUCOIN_ENV === 'sandbox'
    ? 'https://openapi-sandbox.kucoin.com'
    : 'https://api.kucoin.com';
}

export function hasApiCredentials(config: AppConfig): boolean {
  return Boolean(
    config.KUCOIN_API_KEY &&
      config.KUCOIN_API_SECRET &&
      config.KUCOIN_API_PASSPHRASE,
  );
}
