"""Model training workflow."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import Settings
from data.candle_builder import CandleBuilder
from data.clob_client import ClobClient
from data.gamma_client import GammaClient
from data.storage import Storage
from features.pipeline import FeaturePipeline, build_training_dataset
from models.classifier import PriceDirectionClassifier
from models.evaluate import evaluate_classifier
from utils.logging import get_logger

logger = get_logger(__name__)


def fetch_candles_for_market(
    market_id: str,
    settings: Settings,
) -> tuple[pd.DataFrame, str, str]:
    gamma = GammaClient(settings)
    clob = ClobClient(settings)
    builder = CandleBuilder(interval_minutes=1)

    try:
        market = gamma.get_market(market_id)
        if market is None:
            markets = gamma.discover_markets()
            market = next((m for m in markets if m.market_id == market_id), None)
        if market is None:
            raise ValueError(f"Market not found: {market_id}")

        token_id = market.yes_token_id
        history = clob.get_prices_history(token_id, interval="1m", fidelity=60)
        if history:
            candles = builder.from_price_points(history)
        else:
            trades = clob.get_trades(token_id, limit=1000)
            candles = builder.from_trades(trades)

        book = clob.get_order_book(token_id)
        spread = book.spread if book else 0.01
        imbalance = book.imbalance if book else 0.0
        candles = builder.merge_snapshots(
            candles,
            spread=spread,
            imbalance=imbalance,
            liquidity_usd=market.liquidity_usd,
        )
        candles = CandleBuilder.ensure_min_rows(candles, min_rows=120)
        return candles, token_id, market.market_id
    finally:
        gamma.close()
        clob.close()


def train_model(
    market_id: str,
    settings: Settings,
    *,
    save: bool = True,
) -> dict:
    logger.info("Training model for market %s", market_id)
    candles, token_id, resolved_market_id = fetch_candles_for_market(market_id, settings)

    storage = Storage(settings)
    storage.save_candles(token_id, candles)

    dataset, pipeline = build_training_dataset(candles, settings)
    if len(dataset) < 50:
        raise RuntimeError(
            f"Insufficient training rows ({len(dataset)}). Need at least 50 candles with labels."
        )

    train_df, val_df, test_df = pipeline.time_split(dataset)
    pipeline.fit_scaler(train_df)

    X_train = pipeline.scale(train_df)
    y_train = train_df["label_id"].astype(int).values
    X_val = pipeline.scale(val_df)
    y_val = val_df["label_id"].astype(int).values
    X_test = pipeline.scale(test_df)
    y_test = test_df["label_id"].astype(int).values

    classifier = PriceDirectionClassifier(settings, pipeline)
    classifier.fit(X_train, y_train)

    metrics = {
        "train": evaluate_classifier(classifier, X_train, y_train),
        "val": evaluate_classifier(classifier, X_val, y_val),
        "test": evaluate_classifier(classifier, X_test, y_test),
    }

    if save:
        artifact_path = settings.artifacts_path / f"model_{resolved_market_id}.pkl"
        classifier.save(artifact_path)
        logger.info("Saved model to %s", artifact_path)

    return {
        "market_id": resolved_market_id,
        "token_id": token_id,
        "rows": len(dataset),
        "metrics": metrics,
        "artifact": str(settings.artifacts_path / f"model_{resolved_market_id}.pkl"),
    }
