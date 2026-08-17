"""Core unit tests."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from config.settings import Settings
from features.pipeline import FeaturePipeline, build_training_dataset
from execution.position_sizing import compute_stake_usd
from execution.risk import RiskManager


def _sample_candles(n: int = 200) -> pd.DataFrame:
    start = datetime(2025, 1, 1)
    rows = []
    price = 0.5
    for i in range(n):
        delta = np.random.uniform(-0.01, 0.01)
        price = max(0.05, min(0.95, price + delta))
        ts = start + timedelta(minutes=i)
        rows.append(
            {
                "timestamp": ts,
                "open": price,
                "high": price + 0.005,
                "low": price - 0.005,
                "close": price,
                "volume": 100 + i,
                "buy_volume": 55 + i * 0.1,
                "sell_volume": 45 + i * 0.1,
                "spread": 0.01,
                "order_book_imbalance": 0.1,
                "liquidity_usd": 10000,
            }
        )
    return pd.DataFrame(rows)


def test_feature_pipeline_no_leakage_in_labels():
    settings = Settings()
    candles = _sample_candles(150)
    dataset, pipeline = build_training_dataset(candles, settings)
    assert not dataset.empty
    assert "label" in dataset.columns
    assert set(dataset["label"].unique()).issubset({"UP", "DOWN", "NEUTRAL"})


def test_time_split_preserves_order():
    settings = Settings()
    pipeline = FeaturePipeline(settings=settings)
    df = pd.DataFrame({"timestamp": range(100), "close": np.arange(100), "label_id": 1})
    train, val, test = pipeline.time_split(df)
    assert len(train) + len(val) + len(test) == 100
    assert train.iloc[-1]["timestamp"] < val.iloc[0]["timestamp"]


def test_risk_manager_blocks_low_liquidity():
    settings = Settings(min_liquidity_usd=5000)
    risk = RiskManager(settings)
    ok, reason = risk.can_trade(liquidity_usd=1000)
    assert not ok
    assert "Liquidity" in reason


def test_risk_circuit_breaker():
    settings = Settings(max_consecutive_losses=3)
    risk = RiskManager(settings)
    for _ in range(3):
        risk.register_close(-10)
    ok, reason = risk.can_trade(liquidity_usd=10000)
    assert not ok
    assert "Circuit breaker" in reason


def test_position_sizing_respects_threshold():
    settings = Settings(confidence_threshold=0.65, fixed_stake_usd=25)
    stake = compute_stake_usd(
        settings,
        confidence=0.5,
        expected_edge=0.1,
        available_capital=1000,
    )
    assert stake == 0.0

    stake = compute_stake_usd(
        settings,
        confidence=0.8,
        expected_edge=0.1,
        available_capital=1000,
    )
    assert stake == 25.0


def test_backtest_engine_runs():
    from backtest.engine import BacktestEngine
    from models.classifier import PriceDirectionClassifier

    settings = Settings()
    candles = _sample_candles(200)
    dataset, pipeline = build_training_dataset(candles, settings)
    train_df, _, _ = pipeline.time_split(dataset)
    pipeline.fit_scaler(train_df)
    X = pipeline.scale(train_df)
    y = train_df["label_id"].astype(int).values
    classifier = PriceDirectionClassifier(settings, pipeline)
    classifier.fit(X, y)

    engine = BacktestEngine(settings)
    result = engine.run(candles, classifier, pipeline)
    assert result.final_capital > 0
    assert isinstance(result.win_rate, float)
