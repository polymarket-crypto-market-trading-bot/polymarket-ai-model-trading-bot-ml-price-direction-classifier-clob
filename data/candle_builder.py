"""Build OHLCV candles from trades and mid prices."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from data.clob_client import ClobClient, Trade


class CandleBuilder:
    def __init__(self, interval_minutes: int = 1) -> None:
        self.interval_minutes = interval_minutes

    def from_trades(self, trades: list[Trade]) -> pd.DataFrame:
        if not trades:
            return self._empty_frame()

        rows = [
            {
                "timestamp": t.timestamp,
                "price": t.price,
                "volume": t.size,
                "side": t.side,
            }
            for t in trades
        ]
        df = pd.DataFrame(rows).set_index("timestamp").sort_index()
        ohlcv = df["price"].resample(f"{self.interval_minutes}min").ohlc()
        volume = df["volume"].resample(f"{self.interval_minutes}min").sum()
        buy_volume = (
            df[df["side"] == "buy"]["volume"]
            .resample(f"{self.interval_minutes}min")
            .sum()
        )
        sell_volume = (
            df[df["side"] == "sell"]["volume"]
            .resample(f"{self.interval_minutes}min")
            .sum()
        )

        result = ohlcv.copy()
        result["volume"] = volume
        result["buy_volume"] = buy_volume
        result["sell_volume"] = sell_volume
        result = result.dropna(subset=["close"]).reset_index()
        result.rename(columns={"index": "timestamp"}, inplace=True)
        return result

    def from_price_points(
        self,
        points: list[tuple[datetime, float]],
        *,
        volume: float = 0.0,
    ) -> pd.DataFrame:
        if not points:
            return self._empty_frame()

        df = pd.DataFrame(points, columns=["timestamp", "price"]).set_index("timestamp")
        ohlcv = df["price"].resample(f"{self.interval_minutes}min").ohlc()
        result = ohlcv.dropna(subset=["close"]).reset_index()
        result["volume"] = volume
        result["buy_volume"] = volume / 2
        result["sell_volume"] = volume / 2
        return result

    def merge_snapshots(
        self,
        candles: pd.DataFrame,
        *,
        spread: float | None = None,
        imbalance: float | None = None,
        liquidity_usd: float | None = None,
    ) -> pd.DataFrame:
        out = candles.copy()
        if spread is not None:
            out["spread"] = spread
        if imbalance is not None:
            out["order_book_imbalance"] = imbalance
        if liquidity_usd is not None:
            out["liquidity_usd"] = liquidity_usd
        return out

    @staticmethod
    def _empty_frame() -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "buy_volume",
                "sell_volume",
            ]
        )

    @staticmethod
    def ensure_min_rows(candles: pd.DataFrame, min_rows: int = 60) -> pd.DataFrame:
        if len(candles) >= min_rows:
            return candles
        if candles.empty:
            return candles

        last = candles.iloc[-1].copy()
        rows = []
        ts = pd.Timestamp(candles.iloc[-1]["timestamp"])
        for i in range(min_rows - len(candles)):
            ts = ts - timedelta(minutes=1)
            row = last.copy()
            row["timestamp"] = ts.to_pydatetime()
            rows.append(row)
        pad = pd.DataFrame(rows)
        return pd.concat([pad, candles], ignore_index=True).sort_values("timestamp")
