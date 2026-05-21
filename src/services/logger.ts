import pino from 'pino';
import type { AppConfig } from '../config/index.js';

let loggerInstance: pino.Logger | null = null;

export function createLogger(config: AppConfig): pino.Logger {
  if (loggerInstance) return loggerInstance;

  const transport =
    config.LOG_PRETTY && process.env.NODE_ENV !== 'production'
      ? {
          target: 'pino-pretty',
          options: {
            colorize: true,
            translateTime: 'SYS:standard',
            ignore: 'pid,hostname',
          },
        }
      : undefined;

  loggerInstance = pino({
    level: config.LOG_LEVEL,
    ...(transport ? { transport } : {}),
    base: {
      service: 'kucoin-whale-copy-trading-bot',
    },
  });

  return loggerInstance;
}

export function getLogger(): pino.Logger {
  if (!loggerInstance) {
    throw new Error('Logger not initialized. Call createLogger first.');
  }
  return loggerInstance;
}

export function resetLogger(): void {
  loggerInstance = null;
}
