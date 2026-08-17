# FAQ — Polymarket Trading Bot

## What is this project?

An open-source **Polymarket Trading Bot — AI Model Trading Bot** that uses machine learning to classify short-term YES/NO price direction on Polymarket prediction markets and execute trades via the CLOB API.

## How is this different from other Polymarket bots?

| Bot type | This project |
|----------|--------------|
| Polymarket sniper bot | ML confidence gating instead of pure speed |
| Polymarket copy trading bot | Independent signal generation, not wallet mirroring |
| Polymarket arbitrage bot | Direction classifier, not cross-market arb |
| Polymarket market making bot | Taker/maker limit orders on directional signals |
| Polymarket LLM trading bot | Structured XGBoost features, optional LSTM extension |

## How do I run paper trading (dry run)?

```bash
cp .env.example .env
python -m bot paper
python -m bot dashboard
```

## How do I enable live trading?

1. Complete the Go Live Checklist in README
2. Set wallet and CLOB credentials in `.env`
3. Set `ENABLE_LIVE_TRADING=true`
4. Run `python -m bot live`

## Which APIs does the bot use?

- **Gamma API** — market discovery, `clobTokenIds`
- **CLOB REST** — order book, prices, order placement
- **WebSocket** — low-latency market updates

## Can I use this as a Polymarket trading bot tutorial?

Yes. Start with `python -m bot train --market-id <id>`, inspect `features/pipeline.py`, then run backtest and paper modes.

## How do I contribute?

See the **Contributing — Live Trading** section in README. Pull requests for execution, risk, and model improvements are welcome.

## Who maintains this?

The developer actively trades with this bot and welcomes discussion. Open a GitHub Issue or Discussion to connect.
