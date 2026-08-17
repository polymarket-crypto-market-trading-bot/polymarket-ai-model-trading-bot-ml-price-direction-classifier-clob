"""Leakage-safe feature engineering pipeline."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from config.settings import Settings


DIRECTION_MAP = {"DOWN": 0, "NEUTRAL": 1, "UP": 2}
INV_DIRECTION_MAP = {v: k for k, v in DIRECTION_MAP.items()}


@dataclass
class FeaturePipeline:
    settings: Settings
    feature_columns: list[str] | None = None
    scaler: StandardScaler | None = None

    def transform(self, candles: pd.DataFrame) -> pd.DataFrame:
        df = candles.copy()
        df = df.sort_values("timestamp").reset_index(drop=True)

        for window in self.settings.feature_window_list:
            df[f"return_{window}m"] = df["close"].pct_change(window)
            df[f"volatility_{window}m"] = df["close"].pct_change().rolling(window).std()
            df[f"volume_ma_{window}m"] = df["volume"].rolling(window).mean()
            df[f"momentum_{window}m"] = df["close"] - df["close"].shift(window)

        df["hl_range"] = (df["high"] - df["low"]) / df["close"].replace(0, np.nan)
        df["buy_sell_ratio"] = df["buy_volume"] / (df["sell_volume"] + 1e-9)
        df["trade_flow"] = df["buy_volume"] - df["sell_volume"]

        if "spread" not in df.columns:
            df["spread"] = 0.01
        if "order_book_imbalance" not in df.columns:
            df["order_book_imbalance"] = 0.0
        if "liquidity_usd" not in df.columns:
            df["liquidity_usd"] = self.settings.min_liquidity_usd

        df["spread_pct"] = df["spread"] / df["close"].replace(0, np.nan)
        df["log_liquidity"] = np.log1p(df["liquidity_usd"])

        if "time_to_expiry_hours" not in df.columns:
            df["time_to_expiry_hours"] = 24.0

        feature_cols = self._feature_columns(df)
        df = df.dropna(subset=feature_cols).reset_index(drop=True)
        return df

    def fit_scaler(self, df: pd.DataFrame) -> None:
        feature_cols = self._feature_columns(df)
        self.feature_columns = feature_cols
        self.scaler = StandardScaler()
        self.scaler.fit(df[feature_cols].values)

    def scale(self, df: pd.DataFrame) -> np.ndarray:
        if self.scaler is None or self.feature_columns is None:
            raise RuntimeError("Scaler not fitted")
        return self.scaler.transform(df[self.feature_columns].values)

    def add_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        horizon = self.settings.label_horizon_minutes
        threshold = self.settings.direction_return_threshold
        out = df.copy()
        future_close = out["close"].shift(-horizon)
        future_return = (future_close - out["close"]) / out["close"].replace(0, np.nan)

        labels = []
        for ret in future_return:
            if pd.isna(ret):
                labels.append(np.nan)
            elif ret > threshold:
                labels.append("UP")
            elif ret < -threshold:
                labels.append("DOWN")
            else:
                labels.append("NEUTRAL")
        out["label"] = labels
        out["label_id"] = out["label"].map(DIRECTION_MAP)
        return out.dropna(subset=["label"]).reset_index(drop=True)

    def time_split(
        self,
        df: pd.DataFrame,
        *,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        n = len(df)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        train = df.iloc[:train_end].copy()
        val = df.iloc[train_end:val_end].copy()
        test = df.iloc[val_end:].copy()
        return train, val, test

    def _feature_columns(self, df: pd.DataFrame) -> list[str]:
        if self.feature_columns:
            return self.feature_columns
        exclude = {
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "label",
            "label_id",
        }
        return [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]


def build_training_dataset(
    candles: pd.DataFrame,
    settings: Settings,
) -> tuple[pd.DataFrame, FeaturePipeline]:
    pipeline = FeaturePipeline(settings=settings)
    featured = pipeline.transform(candles)
    labeled = pipeline.add_labels(featured)
    return labeled, pipeline
