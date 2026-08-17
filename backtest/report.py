"""Backtest report generation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from backtest.engine import BacktestResult
from config.settings import Settings
from utils.logging import get_logger

logger = get_logger(__name__)


def generate_backtest_report(result: BacktestResult, settings: Settings) -> dict:
    days = max(len(result.timestamps) / (24 * 60), 1)
    years = days / 365.25
    cagr = 0.0
    if years > 0 and result.initial_capital > 0:
        cagr = (result.final_capital / result.initial_capital) ** (1 / years) - 1

    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "initial_capital_usd": result.initial_capital,
        "final_capital_usd": result.final_capital,
        "total_return_pct": round(result.total_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "max_drawdown_pct": round(result.max_drawdown * 100, 2),
        "win_rate_pct": round(result.win_rate * 100, 2),
        "sharpe": round(result.sharpe, 3),
        "profit_factor": round(result.profit_factor, 3)
        if result.profit_factor != float("inf")
        else "inf",
        "exposure_time_ratio": round(result.exposure_time, 3),
        "trade_count": len(result.trades),
        "assumptions": {
            "fee_bps": settings.backtest_fee_bps,
            "slippage_bps": settings.backtest_slippage_bps,
            "latency_ms": settings.backtest_latency_ms,
        },
    }

    exports = settings.exports_path
    exports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    json_path = exports / f"backtest_report_{stamp}.json"
    json_path.write_text(json.dumps(report, indent=2))

    if result.trades:
        trades_df = pd.DataFrame(
            [
                {
                    "timestamp": t.timestamp.isoformat(),
                    "side": t.side,
                    "token": t.token,
                    "price": t.price,
                    "size_usd": t.size_usd,
                    "pnl": t.pnl,
                    "direction": t.direction,
                    "confidence": t.confidence,
                }
                for t in result.trades
            ]
        )
        csv_path = exports / f"backtest_trades_{stamp}.csv"
        trades_df.to_csv(csv_path, index=False)
        report["trades_csv"] = str(csv_path)

    report["report_json"] = str(json_path)
    logger.info("Backtest report saved to %s", json_path)
    return report
