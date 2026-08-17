"""Main trading loop."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd

from config.settings import Settings
from data.candle_builder import CandleBuilder
from data.clob_client import ClobClient
from data.gamma_client import GammaClient
from data.storage import Storage
from execution.orders import OrderExecutor
from execution.position_sizing import compute_stake_usd
from execution.risk import RiskManager
from features.pipeline import FeaturePipeline, build_training_dataset
from models.classifier import PriceDirectionClassifier
from models.train import train_model
from utils.logging import get_logger

logger = get_logger(__name__)


class TradingBot:
    def __init__(self, settings: Settings, mode: Literal["paper", "live"]) -> None:
        self.settings = settings
        self.mode = mode
        self.storage = Storage(settings)
        self.risk = RiskManager(settings)
        self.executor = OrderExecutor(settings, self.storage)
        self.gamma = GammaClient(settings)
        self.clob = ClobClient(settings)
        self.builder = CandleBuilder(interval_minutes=1)
        self.classifiers: dict[str, PriceDirectionClassifier] = {}
        self.markets = self.gamma.discover_markets()
        logger.info("Discovered %d markets", len(self.markets))

    def _load_or_train_classifier(self, market_id: str, token_id: str) -> PriceDirectionClassifier:
        if market_id in self.classifiers:
            return self.classifiers[market_id]

        artifact = self.settings.artifacts_path / f"model_{market_id}.pkl"
        if artifact.exists():
            classifier = PriceDirectionClassifier.load(artifact, self.settings)
        else:
            logger.info("Training model for market %s", market_id)
            train_model(market_id, self.settings)
            classifier = PriceDirectionClassifier.load(artifact, self.settings)

        self.classifiers[market_id] = classifier
        return classifier

    def _fetch_latest_candles(self, token_id: str, liquidity_usd: float) -> pd.DataFrame:
        history = self.clob.get_prices_history(token_id, interval="1m", fidelity=60)
        if history:
            candles = self.builder.from_price_points(history)
        else:
            trades = self.clob.get_trades(token_id, limit=500)
            candles = self.builder.from_trades(trades)

        book = self.clob.get_order_book(token_id)
        candles = self.builder.merge_snapshots(
            candles,
            spread=book.spread if book else 0.01,
            imbalance=book.imbalance if book else 0.0,
            liquidity_usd=liquidity_usd,
        )
        return CandleBuilder.ensure_min_rows(candles, min_rows=60)

    def _export_signal(
        self,
        *,
        market_id: str,
        token_id: str,
        prediction,
        action: str,
    ) -> None:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "market_id": market_id,
            "token_id": token_id,
            "direction": prediction.direction,
            "confidence": prediction.confidence,
            "expected_edge": prediction.expected_edge,
            "action": action,
            "mode": self.mode,
        }
        export_path = self.settings.exports_path / "signals.jsonl"
        with export_path.open("a") as f:
            f.write(json.dumps(payload) + "\n")

    def process_market(self, market) -> None:
        can_trade, reason = self.risk.can_trade(liquidity_usd=market.liquidity_usd)
        if not can_trade:
            logger.debug("Skip %s: %s", market.market_id, reason)
            return

        classifier = self._load_or_train_classifier(market.market_id, market.yes_token_id)
        candles = self._fetch_latest_candles(market.yes_token_id, market.liquidity_usd)
        if candles.empty:
            return

        pipeline = classifier.pipeline
        featured = pipeline.transform(candles)
        if featured.empty:
            return

        latest = featured.iloc[-1]
        prediction = classifier.predict_one(latest)
        self.storage.log_prediction(
            token_id=market.yes_token_id,
            direction=prediction.direction,
            confidence=prediction.confidence,
            expected_edge=prediction.expected_edge,
        )

        action = "HOLD"
        if prediction.confidence >= self.settings.confidence_threshold:
            if prediction.direction == "UP":
                action = "BUY_YES"
            elif prediction.direction == "DOWN":
                action = "BUY_NO"

        self._export_signal(
            market_id=market.market_id,
            token_id=market.yes_token_id,
            prediction=prediction,
            action=action,
        )

        if action == "HOLD":
            logger.info(
                "[%s] %s conf=%.2f — no trade",
                market.market_id,
                prediction.direction,
                prediction.confidence,
            )
            return

        token_id = market.yes_token_id if action == "BUY_YES" else market.no_token_id
        price = self.clob.get_midpoint(token_id) or self.clob.get_price(token_id) or 0.5
        stake = compute_stake_usd(
            self.settings,
            confidence=prediction.confidence,
            expected_edge=prediction.expected_edge,
            available_capital=self.executor.paper_balance
            if self.mode == "paper"
            else self.settings.initial_capital_usd,
        )
        if stake <= 0:
            return

        self.risk.register_open()
        self.executor.place_limit_order(
            mode=self.mode,
            market_id=market.market_id,
            token_id=token_id,
            side="BUY",
            price=price,
            size_usd=stake,
            maker_first=True,
        )
        logger.info(
            "[%s] Signal %s conf=%.2f — %s $%.2f",
            market.market_id,
            prediction.direction,
            prediction.confidence,
            action,
            stake,
        )

    def run(self, *, interval_seconds: int = 60) -> None:
        logger.info("Starting %s trading bot", self.mode.upper())
        try:
            while True:
                if not self.markets:
                    self.markets = self.gamma.discover_markets()
                for market in self.markets:
                    try:
                        self.process_market(market)
                    except Exception as exc:
                        logger.exception("Error processing market %s: %s", market.market_id, exc)
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        finally:
            self.gamma.close()
            self.clob.close()
