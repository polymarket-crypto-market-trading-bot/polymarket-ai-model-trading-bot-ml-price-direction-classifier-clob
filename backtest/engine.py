"""Event-driven backtest engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from config.settings import Settings
from features.pipeline import FeaturePipeline, build_training_dataset
from models.classifier import PriceDirectionClassifier
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BacktestTrade:
    timestamp: datetime
    side: str
    token: str
    price: float
    size_usd: float
    pnl: float
    direction: str
    confidence: float


@dataclass
class BacktestResult:
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    timestamps: list[datetime] = field(default_factory=list)
    initial_capital: float = 1000.0
    final_capital: float = 1000.0

    @property
    def total_return(self) -> float:
        if self.initial_capital <= 0:
            return 0.0
        return (self.final_capital - self.initial_capital) / self.initial_capital

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl > 0)
        return wins / len(self.trades)

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    @property
    def max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak = self.equity_curve[0]
        max_dd = 0.0
        for value in self.equity_curve:
            peak = max(peak, value)
            dd = (peak - value) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
        return max_dd

    @property
    def sharpe(self) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        returns = pd.Series(self.equity_curve).pct_change().dropna()
        if returns.std() == 0:
            return 0.0
        return float(np.sqrt(252 * 24 * 60) * returns.mean() / returns.std())

    @property
    def exposure_time(self) -> float:
        if not self.trades:
            return 0.0
        return len(self.trades) / max(len(self.timestamps), 1)


class BacktestEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(
        self,
        candles: pd.DataFrame,
        classifier: PriceDirectionClassifier,
        pipeline: FeaturePipeline,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> BacktestResult:
        df = candles.copy()
        if start:
            df = df[pd.to_datetime(df["timestamp"]) >= start]
        if end:
            df = df[pd.to_datetime(df["timestamp"]) <= end]
        df = df.sort_values("timestamp").reset_index(drop=True)

        dataset, _ = build_training_dataset(df, self.settings)
        if dataset.empty:
            raise RuntimeError("No labeled rows available for backtest")

        pipeline.fit_scaler(dataset.iloc[: int(len(dataset) * 0.7)])

        capital = self.settings.initial_capital_usd
        result = BacktestResult(
            initial_capital=capital,
            final_capital=capital,
        )
        open_position: dict | None = None
        fee_rate = self.settings.backtest_fee_bps / 10_000
        slip_rate = self.settings.backtest_slippage_bps / 10_000

        warmup = max(self.settings.feature_window_list) + self.settings.label_horizon_minutes + 5

        for i in range(warmup, len(dataset) - self.settings.label_horizon_minutes):
            row = dataset.iloc[i]
            ts = pd.Timestamp(row["timestamp"]).to_pydatetime()
            featured = pipeline.transform(dataset.iloc[: i + 1])
            if featured.empty:
                continue
            latest = featured.iloc[-1]
            pred = classifier.predict_one(latest)

            price = float(row["close"])
            result.timestamps.append(ts)
            result.equity_curve.append(capital)

            if open_position:
                horizon = self.settings.label_horizon_minutes
                exit_idx = min(i + horizon, len(dataset) - 1)
                exit_price = float(dataset.iloc[exit_idx]["close"])
                if open_position["entry_idx"] <= i - horizon:
                    direction_mult = 1 if open_position["side"] == "YES" else -1
                    raw_pnl = (
                        (exit_price - open_position["entry_price"])
                        * direction_mult
                        * open_position["size_shares"]
                    )
                    fees = open_position["size_usd"] * fee_rate * 2
                    pnl = raw_pnl - fees
                    capital += pnl
                    result.trades.append(
                        BacktestTrade(
                            timestamp=ts,
                            side=open_position["side"],
                            token="YES",
                            price=exit_price,
                            size_usd=open_position["size_usd"],
                            pnl=pnl,
                            direction=open_position["direction"],
                            confidence=open_position["confidence"],
                        )
                    )
                    open_position = None

            if open_position is None and pred.confidence >= self.settings.confidence_threshold:
                if pred.direction == "UP":
                    side = "YES"
                elif pred.direction == "DOWN":
                    side = "NO"
                else:
                    continue

                stake = min(self.settings.fixed_stake_usd, self.settings.max_position_size_usd, capital * 0.1)
                if stake <= 0:
                    continue

                entry_price = price * (1 + slip_rate) if side == "YES" else (1 - price) * (1 + slip_rate)
                size_shares = stake / max(entry_price, 0.01)
                open_position = {
                    "side": side,
                    "entry_price": entry_price,
                    "entry_idx": i,
                    "size_usd": stake,
                    "size_shares": size_shares,
                    "direction": pred.direction,
                    "confidence": pred.confidence,
                }
                capital -= stake * fee_rate

        result.final_capital = capital
        if result.equity_curve:
            result.equity_curve[-1] = capital
        logger.info(
            "Backtest complete — return=%.2f%% trades=%d win_rate=%.2f%%",
            result.total_return * 100,
            len(result.trades),
            result.win_rate * 100,
        )
        return result
