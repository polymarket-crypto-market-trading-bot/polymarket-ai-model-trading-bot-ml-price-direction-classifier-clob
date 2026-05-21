# KuCoin Whale Copy Trading Bot

Production-grade TypeScript bot that monitors KuCoin for whale activity and executes risk-managed copy trades in real time.

## Features

- **Real-time whale detection** via KuCoin WebSocket (large trades, order book walls, volume spikes)
- **Copy trading engine** with configurable copy ratio and position sizing
- **Multi-layer risk management** — daily limits, max positions, stop-loss, take-profit, slippage guard
- **Three operating modes** — `monitor`, `paper`, `live`
- **Pluggable strategies** — whale mirror, order book imbalance
- **Production logging** with structured Pino output
- **Fully typed** TypeScript with Zod config validation

## Architecture

```
src/
├── config/           # Environment validation (Zod)
├── kucoin/           # REST client, WebSocket, API auth
├── whale/            # Whale detection logic
├── copy-trading/     # Engine, executor, risk manager
├── strategies/       # Trading strategies
├── services/         # Logger
├── utils/            # Decimal math, retry, helpers
├── types/            # Shared TypeScript types
├── app.ts            # Application bootstrap
└── index.ts          # Entry point
```

## Quick Start

### 1. Navigate to project folder

```bash
cd KuCoin-whale-copy-trading-bot
```

### 2. Install dependencies

```bash
npm install
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your settings. For paper trading (recommended first run), defaults work out of the box:

```env
BOT_MODE=paper
TRADING_SYMBOLS=BTC-USDT,ETH-USDT
WHALE_MIN_TRADE_USDT=50000
COPY_RATIO=0.01
```

For **live trading**, set `BOT_MODE=live` and add your KuCoin API credentials:

```env
BOT_MODE=live
KUCOIN_API_KEY=your_api_key
KUCOIN_API_SECRET=your_api_secret
KUCOIN_API_PASSPHRASE=your_passphrase
```

> **Security:** Never commit `.env` or share API credentials. Use KuCoin API keys with **Trade** permission only — disable withdrawal.

### 4. Build

```bash
npm run build
```

### 5. Run

```bash
# Development (hot reload)
npm run dev

# Production
npm start

# Direct run without build
npm run bot
```

## Operating Modes

| Mode      | Description                                      |
|-----------|--------------------------------------------------|
| `monitor` | Detect and log whale signals — no trades         |
| `paper`   | Simulate copy trades with virtual balance        |
| `live`    | Execute real orders on KuCoin (requires API keys)|

## Configuration Reference

| Variable                    | Default              | Description                              |
|-----------------------------|----------------------|------------------------------------------|
| `TRADING_SYMBOLS`         | `BTC-USDT,ETH-USDT`  | Comma-separated pairs to monitor         |
| `WHALE_MIN_TRADE_USDT`      | `50000`              | Minimum trade size to classify as whale  |
| `WHALE_ORDERBOOK_WALL_USDT` | `100000`             | Order book wall detection threshold      |
| `WHALE_COOLDOWN_MS`         | `30000`              | Cooldown between signals per symbol      |
| `COPY_RATIO`                | `0.01`               | Fraction of whale size to copy (1%)      |
| `MAX_POSITION_USDT`         | `1000`               | Maximum single position in USDT          |
| `MAX_DAILY_TRADES`          | `20`                 | Daily trade limit                        |
| `MAX_SLIPPAGE_PERCENT`      | `0.5`                | Max allowed slippage for live orders     |
| `STOP_LOSS_PERCENT`         | `2`                  | Stop-loss percentage                     |
| `TAKE_PROFIT_PERCENT`       | `4`                  | Take-profit percentage                   |
| `MAX_OPEN_POSITIONS`        | `3`                  | Maximum concurrent open positions        |
| `MIN_ACCOUNT_BALANCE_USDT`  | `100`                | Minimum balance required to trade        |

## Strategies

### Whale Mirror
Mirrors large individual trades that exceed the whale threshold.

### Order Book Imbalance
Detects significant bid/ask wall imbalances indicating institutional activity.

### Volume Spike
Identifies clusters of large trades within a rolling time window.

## Scripts

```bash
npm run build       # Compile TypeScript
npm start           # Run compiled bot
npm run dev         # Development with hot reload
npm run bot         # Run directly via tsx
npm test            # Run all tests
npm run typecheck   # Type check without emit
```

## How It Works

1. Connects to KuCoin public WebSocket for real-time trade and order book feeds
2. **WhaleDetector** filters events above configured USDT thresholds
3. **RiskManager** validates signals against balance, limits, and open positions
4. **CopyTradeExecutor** sizes and places orders (paper or live)
5. **Position monitor** checks open positions every 15s for stop-loss / take-profit

## Disclaimer

Cryptocurrency trading involves substantial risk. This bot is provided for educational purposes. Past whale activity does not guarantee future results. Always test in `paper` mode before using `live` mode. The authors are not responsible for any financial losses.

---

## Technical Support

Need help setting up, configuring, or troubleshooting this bot?

### Contact us on Telegram

> ### [@tradingtermin](https://t.me/tradingtermin)
>
> **Telegram:** `@tradingtermin`

For technical support, bug reports, or integration questions — reach out on Telegram:

**[@tradingtermin](https://t.me/tradingtermin)**
